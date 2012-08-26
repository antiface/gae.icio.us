#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
from webapp2 import RequestHandler
from google.appengine.api import users
from handlers.myutils import login_required
from handlers.models import *

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))

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

class GetComment(RequestHandler):
  @login_required
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    self.response.write(bm.comment)

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

class AssignTag(RequestHandler):
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
  def get(self):
    ui = UserInfo.query(UserInfo.user == users.get_current_user()).get()
    if ui.mys == False:
      ui.mys = True
      html = '<i class="icon-envelope"></i> MYS is ON'
    else:
      ui.mys = False
      html = '<i class="icon-envelope"></i> MYS is OFF'
    ui.put()
    self.response.write(html)