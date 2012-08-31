#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import urllib, datetime, urlparse, jinja2, time
from webapp2 import RequestHandler
from google.appengine.api import users, mail, app_identity, urlfetch, capabilities
from google.appengine.ext import deferred, blobstore
from models import *

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))

class Script(RequestHandler):
  def get(self):
    if capabilities.CapabilitySet('datastore_v3', capabilities=['write']).is_enabled():
      for feed in Feeds.query(): 
        feed.digest = False
        feed.put()

class CheckFeed(RequestHandler):
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    deferred.defer(pop_feed, feed, _target="worker", _queue="admin")

class CheckFeeds(RequestHandler):
  def get(self):
    if capabilities.CapabilitySet('datastore_v3', capabilities=['write']).is_enabled():
      for feed in Feeds.query():   
        deferred.defer(pop_feed, feed, _target="worker", _queue="admin")

class SendDigest(RequestHandler):
  def get(self):
    if capabilities.CapabilitySet('datastore_v3', capabilities=['write']).is_enabled():        
      for feed in Feeds.query(Feeds.digest == True):
        deferred.defer(feed_digest, feed, _target="worker", _queue="admin")

class SendDaily(RequestHandler):
  def get(self):
    if capabilities.CapabilitySet('mail').is_enabled():
      for ui in UserInfo.query():
        if ui.daily:
          deferred.defer(daily_digest, ui.user, _target="worker", _queue="admin")


def pop_feed(feed):
  from libs.feedparser import parse
  p = parse(feed.feed)
  e = 0
  d = p.entries[e]
  while feed.url != d.link and e < 50:
    deferred.defer(new_bm, d, feed, _target="worker", _queue="importer")
    e += 1
    try:
      d = p.entries[e]
    except IndexError:
      break
  d = p.entries[0]
  feed.url = d.link
  feed.title = d.title.encode('utf-8')
  feed.comment = d.description.encode('utf-8')
  feed.put()

def new_bm(d, feed):
  bm = Bookmarks()
  bm.feed = feed.key
  bm.user = feed.user
  bm.put()
  def txn():    
    bm.original = d.link
    bm.url = d.link
    bm.title = d.title.encode('utf-8')
    bm.comment = d.description.encode('utf-8')
    bm.tags = feed.tags
    bm.put()
  ndb.transaction(txn)
  deferred.defer(parse_bm, bm, _target="worker", _queue="parser")

def parse_bm(bm):
  ## url
  try:
    u = urlfetch.fetch(url=bm.original, follow_redirects=True)
    bm.url = u.final_url.split('?')[0]
  except:
    bm.url = bm.original.split('?')[0]
  #merge tags
  q = Bookmarks.query(ndb.OR(Bookmarks.original == bm.original, Bookmarks.url == bm.url))
  if q.count >= 2:
    tag_list = []
    for old in q:
      for t in old.tags:
        if t not in tag_list:
          tag_list.append(t)
          bm.tags = tag_list
      old.trashed = True
      old.put()  
  ## video previews
  url_parsed = urlparse.urlparse(bm.original)
  query = urlparse.parse_qs(url_parsed.query)
  if url_parsed.netloc == 'www.youtube.com':    
    video = query["v"][0]
    bm.url = 'http://www.youtube.com/watch?v=%s' % video
    bm.comment = '''<iframe width="640" height="360" 
    src="http://www.youtube.com/embed/%s" frameborder="0" 
    allowfullscreen></iframe>''' % video
  if url_parsed.netloc == 'vimeo.com': 
    video = url_parsed.path.split('/')[-1]
    bm.url = 'http://vimeo.com/%s' % video
    bm.comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff" 
    width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen 
    allowFullScreen></iframe>''' % video
  bm.put()
  if bm.ha_mys() and capabilities.CapabilitySet("mail").is_enabled() and bm.feed.get().digest == False:
      deferred.defer(sendbm, bm, _queue="emails")


def daily_digest(user):
  timestamp = time.time() - 86400
  period = datetime.datetime.fromtimestamp(timestamp)
  bmq = ndb.gql("""SELECT * FROM Bookmarks 
    WHERE user = :1 AND create > :2 AND trashed = False
    ORDER BY create DESC""", user, period)
  title = '(%s) Digest: %s' % (app_identity.get_application_id(), time.time())
  template = jinja_environment.get_template('digest.html')  
  values = {'bmq': bmq, 'title': title} 
  html = template.render(values)
  if bmq.get():
    deferred.defer(send_digest, user.email(), html, title, _target="worker", _queue="emails")

def feed_digest(feed):
  bmq = ndb.gql("""SELECT * FROM Bookmarks 
    WHERE user = :1 AND feed = :2
    ORDER BY data DESC""", feed.user, feed.key)
  title = '(%s) Digest: %s' % (app_identity.get_application_id(), feed.blog)
  template = jinja_environment.get_template('digest.html') 
  values = {'bmq': bmq, 'title': title} 
  html = template.render(values)
  if bmq.get():
    deferred.defer(send_digest, feed.user.email(), html, title, _target="worker", _queue="emails")
    for bm in bmq:
      bm.trashed = True
      bm.feed = None
      bm.put()


def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
  message.to = bm.user.email()
  message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()

def send_digest(email, html, title):
  message = mail.EmailMessage()
  message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
  message.to = email
  message.subject =  title
  message.html = html
  message.send()

def login_required(handler_method):
  def check_login(self):
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url(self.request.url))
    else:
      handler_method(self)
  return check_login

def tag_set(bmq):
  tagset = []
  for bm in bmq:
    for tag in bm.tags:
      if not tag in tagset:
        tagset.append(tag)
  return tagset


## under costruction
def upload(bmfile):
  upload_url = blobstore.create_upload_url('/upload')
  urlfetch.fetch(url=upload_url, payload=urllib.urlencode({"file": bmfile}), method=urlfetch.POST)

# if urlparse.urlparse('%s' % bm.url).path.split('.')[1] == 'mp3':
#   deferred.defer(upload, bm.url)
