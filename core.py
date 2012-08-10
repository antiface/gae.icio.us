#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from webapp2 import RequestHandler
from email import header, utils
from google.appengine.api import users, mail
from google.appengine.ext import ndb, deferred
from models import Tags, Bookmarks
from utils import *
import base64, logging

class ReceiveMail(RequestHandler):
  def post(self):
    message = mail.InboundEmailMessage(self.request.body)
    texts = message.bodies('text/plain')
    for text in texts:
      txtmsg = ""
      txtmsg = text[1].decode()
    bm = Bookmarks()
    url = txtmsg.encode('utf8')
    bm.url = url.split('?utm_')[0].split('&feature')[0]
    bm.user = users.User(utils.parseaddr(message.sender)[1])
    bm.title = header.decode_header(message.subject)[0][0]
    bm.comment = 'Sent via email'
    bm.put()
    deferred.defer(sendbm, bm)

class AddBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks()
    url = self.request.get('url').encode('utf8')
    bm.url = url.split('?utm_')[0].split('&feature')[0]
    bm.title = self.request.get('title').encode('utf8')
    bm.comment = self.request.get('comment').encode('utf8')
    bm.user = users.User(str(self.request.get('user')))
    bm.put()
    deferred.defer(sendbm, bm)
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


