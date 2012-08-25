#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from webapp2 import RequestHandler
from google.appengine.api import users, mail, app_identity, urlfetch, capabilities
from google.appengine.ext import deferred, blobstore
from models import *
from urlparse import urlparse
import urllib

class script(RequestHandler):
  def get(self):
    for bm in Bookmarks.query():
      if capabilities.CapabilitySet("datastore_v3", ["write"]).is_enabled():
        deferred.defer(parsebm, bm, _target="worker", _queue="parser")

class CheckFeeds(RequestHandler):
  def get(self):
    for feed in Feeds.query():
      if capabilities.CapabilitySet("datastore_v3", ["write"]).is_enabled():
        deferred.defer(pop_feed, feed, _target="worker", _queue="admin")    

class CheckFeed(RequestHandler):
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    deferred.defer(pop_feed, feed, _target="worker", _queue="admin") 


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

def del_bm(bmk): 
  bmk.delete()

def pop_feed(feed):
  from libs.feedparser import parse
  p = parse(feed.feed)
  e = 0
  d = p.entries[e]
  while feed.url != d.link and e < 100:
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
  def txn():    
    bm.original = d.link
    bm.url = d.link
    bm.title = d.title.encode('utf-8')
    bm.comment = d.description.encode('utf-8')
    bm.user = feed.user
    bm.tags = feed.tags
    bm.put()
  ndb.transaction(txn)
  deferred.defer(parsebm, bm, _target="worker", _queue="parser")
  

def parsebm(bm):  
  if bm.preview():
    bm.comment = '''<iframe width="640" height="480" 
    src="http://www.youtube.com/embed/%s" frameborder="0" 
    allowfullscreen></iframe>''' % bm.preview()
  try:
    u = urlfetch.fetch(url=bm.original, follow_redirects=True)
    bm.url = u.final_url.split('utm_')[0].split('&feature')[0]
  except:
    bm.url = bm.original.split('utm_')[0].split('&feature')[0]
  q = Bookmarks.query(ndb.OR(Bookmarks.original == bm.original, Bookmarks.url == bm.url))
  if q.count >= 2:
    tag_list = []
    for old in q:
      for t in old.tags:
        if t not in tag_list:
          tag_list.append(t)
          bm.tags = tag_list
      if old.comment != bm.comment:
        comment = '<br> -- previous comment -- <br>' + old.comment
        bm.comment = bm.comment + comment
      old.trashed = True
      old.put()    
  if bm.title == '':
    bm.title = bm.url
  bm.put()
  # if urlparse('%s' % bm.url).path.split('.')[1] == 'mp3':
    # deferred.defer(upload, bm.url)

  if bm.ha_mys():
    if capabilities.CapabilitySet("mail").is_enabled():
      deferred.defer(sendbm, bm, _queue="emails")

def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
  message.to = bm.user.email()
  message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()

def upload(bmfile):
  upload_url = blobstore.create_upload_url('/upload')
  urlfetch.fetch(url=upload_url, payload=urllib.urlencode({"file": bmfile}), method=urlfetch.POST)