#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.api import users, mail, app_identity
from google.appengine.ext import deferred
from models import *


def login_required(handler_method):
  def check_login(self):
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url(self.request.url))
    else:
      handler_method(self)
  return check_login

def decr_tags(tag):
  def txn():
    t = tag.get()
    t.count -= 1
    t.put() 
  ndb.transaction(txn)

def pop_feed(feed):
  from feedparser import parse
  p = parse(feed.feed)
  e = 0
  d = p.entries[e]
  q = Bookmarks.query(Bookmarks.original == d.link)
  while q.get() is None and e < 5:
    feed.original = d.link
    feed.url = d.link.split('?utm_')[0].split('&feature')[0].encode('utf-8')
    feed.title = d.title.encode('utf-8')
    feed.comment = d.description.encode('utf-8')
    feed.put()
    e = e + 1
    d = p.entries[e]
    deferred.defer(new_bm, feed, _target="gaeicious", _queue="admin")

def new_bm(feed):
  bm = Bookmarks()
  def txn():    
    bm.original = feed.original
    bm.url = feed.url
    bm.title = feed.title
    bm.comment = feed.comment
    bm.user = feed.user
    bm.put()
  ndb.transaction(txn)
  if bm.preview():
    deferred.defer(preview, bm, _target="gaeicious", _queue="admin")
  if bm.ha_mys():
    deferred.defer(sendbm, bm, _target="gaeicious", _queue="emails")


def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
  message.to = bm.user.email()
  message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()

def preview(bm):
  if bm.preview():
    bm.comment = '''<iframe width="640" height="480" 
    src="http://www.youtube.com/embed/%s" frameborder="0" 
    allowfullscreen></iframe>''' % bm.preview()
    bm.put()