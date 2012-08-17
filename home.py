#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import webapp2, jinja2, os
from google.appengine.api import users, mail, app_identity
from google.appengine.ext import ndb
from handlers.feedparser import parse
from handlers.myutils import login_required
from handlers.models import *
from handlers.core import *

def dtf(value, format='%d-%m-%Y %H:%M'):
  return value.strftime(format)

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = dtf


class BaseHandler(webapp2.RequestHandler):
  def utente(self):
    return users.get_current_user()
  def ui(self):
    try:
      return UserInfo.query(UserInfo.user == self.utente()).get()
    except:
      ui = UserInfo()
      ui.user = users.get_current_user()
      ui.put()
      return UserInfo.query(UserInfo.user == self.utente()).get()
  def tag_list(self):
    return ndb.gql("""SELECT * FROM Tags
        WHERE user = :1 ORDER BY count DESC""", self.utente())
  def generate(self, template_name, template_values={}):
    if self.utente():
      bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, self.utente().email())
      url = users.create_logout_url("/")
      linktext = 'Logout'
      nick = self.utente().email()
    else:
      bookmarklet = '%s' % self.request.host_url
      url = users.create_login_url(self.request.uri)
      linktext = 'Login'
      nick = 'Welcome'
    values = {      
      'brand': app_identity.get_application_id(),
      'bookmarklet': bookmarklet,
      'nick': nick,
      'url': url,
      'linktext': linktext,
      'user': self.utente(),
      }
    values.update(template_values)
    template = jinja_environment.get_template(template_name)
    self.response.out.write(template.render(values))


class MainPage(BaseHandler):
  def get(self):
    if self.utente():
      bms = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND archived = False 
        ORDER BY data DESC""", self.utente())
      self.generate('home.html', {'bms': bms,
                                  'tag_list': self.tag_list() })
    else:
      self.generate('hero.html', {})


class ArchivedPage(BaseHandler):
  @login_required
  def get(self):
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND archived = True 
        ORDER BY data DESC LIMIT 25""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': self.tag_list() })

class StarredPage(BaseHandler):
  @login_required
  def get(self):
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND starred = True 
        ORDER BY data DESC LIMIT 25""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': self.tag_list() })


class NotagPage(BaseHandler):
  @login_required
  def get(self):
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND have_tags = False
        ORDER BY data DESC""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': self.tag_list() })


class PreviewPage(BaseHandler):
  @login_required
  def get(self):
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND have_prev = True
        ORDER BY data DESC""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': self.tag_list() })


class SearchPage(BaseHandler):
  @login_required
  def get(self):
    tag_name = self.request.get('tag')
    tag_obj = ndb.gql("""SELECT * FROM Tags 
      WHERE user = :1 AND name = :2 
      ORDER BY data DESC""", self.utente(), tag_name).get()
    if tag_obj.count == 0:
      self.redirect('/')
    else:
      self.generate('home.html', {'tag_obj':  tag_obj,
                                  'bms':      tag_obj.bm_set(),
                                  'tag_list': tag_obj.refine_set() })        


class RefinePage(BaseHandler):
  @login_required
  def get(self):
    tag_name = self.request.get('tag')
    refine = self.request.get('refine')
    tag1 = ndb.gql("""SELECT __key__ FROM Tags 
      WHERE user = :1 AND name = :2""", self.utente(), tag_name).get()
    tag2 = ndb.gql("""SELECT __key__ FROM Tags 
      WHERE user = :1 AND name = :2""", self.utente(), refine).get()
    bms = ndb.gql("""SELECT * FROM Bookmarks 
      WHERE user = :1 AND tags = :2 AND tags = :3
      ORDER BY data DESC""", self.utente(), tag1, tag2)
    self.generate('home.html', {'bms': bms, 'tag_obj': None})


class EditPage(BaseHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if self.utente() == bm.user:      
      self.generate('edit.html', {'bm': bm})
    else:
      self.redirect('/')
  def post(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if self.utente() == bm.user:
      bm.url = self.request.get('url').encode('utf8')
      bm.title = self.request.get('title').encode('utf8')
      bm.comment = self.request.get('comment').encode('utf8')
      bm.put()
    self.redirect('/')


class SettingPage(BaseHandler):
  @login_required
  def get(self):
      feeds = Feeds.query(Feeds.user == self.utente())
      self.generate('setting.html', {'feeds': feeds})

#### Test ####
class ViewPage(BaseHandler):
  def get(self):
    url = "http://www.google.com/reader/public/atom/user/09422248633387831593/state/com.google/starred?n=10"
    d = parse(url)
    e = d.entries[0]    
    self.generate('feed.html', {'d': d, 'e': e})

debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
  ('/',           MainPage),
  ('/setting',    SettingPage),
  ('/search',     SearchPage),
  ('/refine',     RefinePage),
  ('/notag',      NotagPage),
  ('/previews',   PreviewPage),
  ('/edit',       EditPage),  
  ('/archived',   ArchivedPage),
  ('/starred',    StarredPage),
  ('/checkfeeds', CheckFeeds),
  ('/submit',     AddBM),
  ('/delete',     DelBM),
  ('/addtag',     AddTag),
  ('/deltag',     DeleteTag),
  ('/removetag',  RemoveTag),
  ('/asstag',     AssignTag),
  ('/archive',    ArchiveBM),
  ('/star',       StarBM),
  ('/feed',       AddFeed),
  ('/_ah/mail/.+',ReceiveMail),
  ('/view',       ViewPage),#for tests
  ], debug=debug)

def main():
  run_wsgi_app(app)