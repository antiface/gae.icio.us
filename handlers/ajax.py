#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
from webapp2 import RequestHandler
from google.appengine.api import users
from handlers.utils import login_required
from handlers.models import *

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))

class TrashBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.trashed == False:
        bm.trashed = True
        bm.archived = False
        bm.put()
      else:
        bm.key.delete()

class ArchiveBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.trashed:
        bm.archived = False
        bm.trashed = False
      elif bm.archived:
        bm.archived = False
      else:
        bm.archived = True
      bm.put()

class GetComment(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    self.response.write(bm.comment)

class GetTagsFeed(RequestHandler):
  @login_required
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    template = jinja_environment.get_template('gettagsfeed.html')   
    values = {'feed': feed} 
    other_tags = template.render(values)
    self.response.write(other_tags)

class GetTags(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    template = jinja_environment.get_template('other_tags.html')   
    values = {'bm': bm} 
    other_tags = template.render(values)
    self.response.write(other_tags)

class GetEdit(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    template = jinja_environment.get_template('edit.html')   
    values = {'bm': bm} 
    html_page = template.render(values)
    self.response.write(html_page)

class StarBM(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.starred == False:
        bm.starred = True
        html = '<i class="icon-star">'
      else:
        bm.starred = False
        html = '<i class="icon-star-empty">'
      bm.put()
    self.response.write(html)

class AddTag(RequestHandler):
  @login_required
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

class AssignTag(RequestHandler):
  @login_required
  def get(self):
    bm  = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.append(tag.key)
      bm.put()
    template = jinja_environment.get_template('tags.html')   
    values = {'bm': bm} 
    tags = template.render(values)
    self.response.write(tags)
    
class RemoveTag(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.remove(tag.key)
      bm.put()
    template = jinja_environment.get_template('tags.html')   
    values = {'bm': bm} 
    tags = template.render(values)
    self.response.write(tags)


class SetMys(RequestHandler):
  @login_required
  def get(self):
    ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
    if ui.mys == False:
      ui.mys = True
      html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
    else:
      ui.mys = False
      html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
    ui.put()
    self.response.write(html)

class SetDaily(RequestHandler):
  @login_required
  def get(self):
    ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
    if ui.daily == False:
      ui.daily = True
      html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
    else:
      ui.daily = False
      html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
    ui.put()
    self.response.write(html)

class SetTwitt(RequestHandler):
  @login_required
  def get(self):
    ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
    if ui.twitt == False:
      ui.twitt = True
      html = '<i class="icon-thumbs-up"></i> <strong>Enabled </strong>'
    else:
      ui.twitt = False
      html = '<i class="icon-thumbs-down"></i> <strong>Disabled</strong>'
    ui.put()
    self.response.write(html)


class SetDigest(RequestHandler):
  @login_required
  def get(self):
    feed = Feeds.get_by_id(int(self.request.get('feed')))
    if feed.digest == False:
      feed.digest = True
      html = '<strong>Digest</strong>'
    else:
      feed.digest = False
      html = '<strong>MYS</strong>'
    feed.put()
    self.response.write(html)    