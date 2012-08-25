#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from webapp2 import RequestHandler
from email import header, utils
from google.appengine.api import users, mail
from google.appengine.ext import ndb, deferred
from handlers.myutils import *
from handlers.models import *


class script(RequestHandler):
  def get(self):
    for bm in Bookmarks.query():
      deferred.defer(parsebm, bm, _target="worker", _queue="admin")  

class CheckFeeds(RequestHandler):
  def get(self):
    for feed in Feeds.query():
      deferred.defer(pop_feed, feed, _target="worker", _queue="admin")    


class Empty_Trash(RequestHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT __key__ FROM Bookmarks
      WHERE user = :1 AND trashed = True 
      ORDER BY data DESC""", users.get_current_user())
    for bm in bmq:
      deferred.defer(del_bm, bm, _target="worker", _queue="admin")
    self.redirect('/')

class SetMys(RequestHandler):
  def get(self):
    ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
    if ui.mys == False:
      ui.mys = True
    else:
      ui.mys = False
    ui.put()
    self.redirect(self.request.referer)

class AddFeed(RequestHandler):
  def post(self):
    from libs.feedparser import parse
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
        deferred.defer(new_bm, d, feed, _target="worker", _queue="admin")
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
    def txn():
      bm.original = url
      bm.title = header.decode_header(message.subject)[0][0]
      bm.comment = 'Sent via email'
      bm.user = users.User(utils.parseaddr(message.sender)[1])
      bm.put()
    ndb.transaction(txn)
    deferred.defer(parsebm, bm, _queue="parser")

class AddBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks()
    def txn(): 
      bm.original = self.request.get('url')
      bm.title = self.request.get('title')
      bm.comment = self.request.get('comment')
      bm.user = users.User(str(self.request.get('user')))
      bm.put()
    ndb.transaction(txn)
    deferred.defer(parsebm, bm, _queue="parser")
    self.redirect('/')

class EditBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      def txn():
        bm.url = self.request.get('url').encode('utf8')
        bm.title = self.request.get('title').encode('utf8')
        bm.comment = self.request.get('comment').encode('utf8')
        bm.put()
      ndb.transaction(txn)
    self.redirect('/')

class TrashBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.trashed == False:
        bm.trashed = True
        bm.archived = False
      else:
        bm.trashed = False
      bm.put()

class ArchiveBM(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.archived == False:
        bm.archived = True
      else:
        bm.archived = False
      bm.put()

class RemoveTag(RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.remove(tag.key)
      bm.put()
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


class AssTagFeed(RequestHandler):
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == feed.user:
      if tag in feed.tags:
        pass
      else:
        feed.tags.append(tag.key)
        feed.put()
    self.redirect(self.request.referer)

class RemoveTagFeed(RequestHandler):
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == feed.user:
      feed.tags.remove(tag.key)
      feed.put()
    self.redirect(self.request.referer)    