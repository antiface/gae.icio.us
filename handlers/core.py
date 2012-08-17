#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from webapp2 import RequestHandler
from email import header, utils
from google.appengine.api import users, mail
from google.appengine.ext import ndb, deferred
from handlers.feedparser import parse
from handlers.myutils import *
from handlers.models import *


class CheckFeeds(RequestHandler):
  def get(self):
    feeds = Feeds.query()
    for feed in feeds:
      deferred.defer(pop_feed, feed, _target="gaeicious", _queue="admin")


class AddFeed(RequestHandler):
  def post(self):
    user = users.get_current_user()
    url = self.request.get('url')
    p = parse(url)
    d = p.entries[0]
    if user:
      q = ndb.gql("""SELECT * FROM Feeds
      WHERE user = :1 AND url = :2""", user, url)
      if q.get() is None:
        feed = Feeds()
        def txn():
          feed.blog = p.feed.title
          feed.root = p.feed.link
          feed.user = user
          feed.feed = url
          feed.url  = d.link
          feed.title = d.title
          feed.comment = d.description
          feed.put()
        ndb.transaction(txn)
        deferred.defer(new_bm, feed, _queue="fast")
      else:
        pass
      self.redirect(self.request.referer)
    else:
      self.redirect('/')
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('id')))
    feed.key.delete()
    self.redirect(self.request.referer)


class ReceiveMail(RequestHandler):
  def post(self):    
    message = mail.InboundEmailMessage(self.request.body)
    texts = message.bodies('text/plain')
    for text in texts:
      txtmsg = ""
      txtmsg = text[1].decode()
    url = txtmsg.encode('utf8')
    bm = Bookmarks()
    bm.url = url.split('?utm_')[0].split('&feature')[0]
    bm.title = header.decode_header(message.subject)[0][0]
    bm.comment = 'Sent via email'
    bm.user = users.User(utils.parseaddr(message.sender)[1])
    bm.put()
    deferred.defer(sendbm, bm, _queue="emails")

class AddBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks()
    url = self.request.get('url')#.encode('utf8')
    bm.url = url.split('?utm_')[0].split('&feature')[0]
    bm.title = self.request.get('title')#.encode('utf8')
    bm.comment = self.request.get('comment').encode('utf-8')
    bm.user = users.User(str(self.request.get('user')))
    bm.put()
    deferred.defer(sendbm, bm, _queue="emails")
    self.redirect('/edit?bm=%s' % bm.key.id())


class DelBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      for tag in bm.tags:
        t = tag.get()
        t.count -= 1
        t.put()        
      bm.key.delete()
    self.redirect(self.request.referer)

class ArchiveBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.archived == False:
        bm.archived = True
      else:
        bm.archived = False
      bm.put()
    self.redirect(self.request.referer)

class StarBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.starred == False:
        bm.starred = True
      else:
        bm.starred = False
      bm.put()
    self.redirect(self.request.referer)

class AssignTag(RequestHandler):
  def get(self):
    bm  = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.append(tag.key)
      bm.put()
      tag.count += 1
      tag.put()
    self.redirect(self.request.referer)

class RemoveTag(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.remove(tag.key)
      bm.put()
      tag.count -= 1
      tag.put()
    self.redirect(self.request.referer)

class AddTag(RequestHandler):
  def get(self):
    user = users.get_current_user()
    tag_str = self.request.get('tag')
    if user:
      tag = ndb.gql("""SELECT * FROM Tags
      WHERE user = :1 AND name = :2""", user, tag_str).get()
      if tag is None:
        newtag = Tags()
        newtag.name = tag_str
        newtag.user = user        
      else:
        newtag = tag
      newtag.put()
    self.redirect(self.request.referer)
    
class DeleteTag(RequestHandler):
  def get(self):
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == tag.user:
      tag.key.delete()
    self.redirect(self.request.referer)