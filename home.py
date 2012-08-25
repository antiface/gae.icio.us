#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import webapp2, jinja2, os
from google.appengine.api import users, mail, app_identity
from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from handlers import core, ajax, myutils
from handlers.myutils import *

def dtf(value, format='%d-%m-%Y %H:%M'):
  return value.strftime(format)

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = dtf


class BaseHandler(webapp2.RequestHandler):
  def ui(self):
    if users.get_current_user():
      q = UserInfo.query(UserInfo.user == users.get_current_user())
      if q.get():
        return q.get()
      else:
        ui = UserInfo()
        ui.user = users.get_current_user()
        ui.put()
        return ui
    
  def generate(self, template_name, template_values={}):
    if users.get_current_user():
      bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, self.ui().user.email())
      url = users.create_logout_url("/")
      linktext = 'Logout'
      nick = self.ui().user.email()
      ui = self.ui()
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
      'ui': self.ui(),
      }
    values.update(template_values)
    template = jinja_environment.get_template(template_name)
    self.response.set_cookie('mys', '%s' % self.ui().mys)
    self.response.out.write(template.render(values))


class InboxPage(BaseHandler):
  def get(self):
    if users.get_current_user():      
      bmq = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND archived = False AND trashed = False 
        ORDER BY data DESC""", self.ui().user)
      c = ndb.Cursor(urlsafe=self.request.get('c'))
      bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
      if more:
        next_c = next_curs.urlsafe()
      else:
        next_c = None
      self.response.set_cookie('active-tab', 'inbox')
      self.generate('home.html', 
        {'bms': bms, 'tags': tag_set(bmq), 'c': next_c })
    else:
      self.generate('git.html', {})


class ArchivedPage(BaseHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT * FROM Bookmarks
      WHERE user = :1 AND archived = True AND trashed = False 
      ORDER BY data DESC""", self.ui().user)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.response.set_cookie('active-tab', 'archive')
    self.generate('home.html', 
      {'bms' : bms, 'tags': tag_set(bmq), 'c': next_c })

class StarredPage(BaseHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT * FROM Bookmarks
      WHERE user = :1 AND starred = True AND trashed = False 
      ORDER BY data DESC""", self.ui().user)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.response.set_cookie('active-tab', 'starred')
    self.generate('home.html', 
      {'bms' : bms, 'tags': tag_set(bmq), 'c': next_c })

class TrashedPage(BaseHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT * FROM Bookmarks
      WHERE user = :1 AND trashed = True 
      ORDER BY data DESC""", self.ui().user)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.response.set_cookie('active-tab', 'trash')
    self.generate('home.html', 
      {'bms' : bms, 'tags': tag_set(bmq), 'c': next_c })


class NotagPage(BaseHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT * FROM Bookmarks
      WHERE user = :1 AND have_tags = False AND trashed = False 
      ORDER BY data DESC""", self.ui().user)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.response.set_cookie('active-tab', 'untagged')
    self.generate('home.html', 
      {'bms' : bms, 'tags': tag_set(bmq), 'c': next_c })


class PreviewPage(BaseHandler):
  @login_required
  def get(self):
    bmq = ndb.gql("""SELECT * FROM Bookmarks
      WHERE user = :1 AND have_prev = True
      ORDER BY data DESC""", self.ui().user)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.response.set_cookie('active-tab', 'previews')
    self.generate('home.html', 
      {'bms' : bms, 'tags': tag_set(bmq), 'c': next_c })


class FilterPage(BaseHandler):
  @login_required
  def get(self):
    tag_name = self.request.get('tag')
    tag_obj = ndb.gql("""SELECT * FROM Tags 
      WHERE user = :1 AND name = :2""", self.ui().user, tag_name).get()
    if tag_obj:
      tagset = tag_set(tag_obj.bm_set)
      tagset.remove(tag_obj.key)
      self.response.set_cookie('active-tab', '')
      self.generate('home.html', 
        {'tag_obj': tag_obj, 'bms': tag_obj.bm_set, 'tags': tagset })
    else:
      self.redirect('/')


class RefinePage(BaseHandler):
  @login_required
  def get(self):
    tag_name = self.request.get('tag')
    refine = self.request.get('refine')
    tag1 = ndb.gql("""SELECT __key__ FROM Tags 
      WHERE user = :1 AND name = :2""", self.ui().user, tag_name).get()
    tag2 = ndb.gql("""SELECT __key__ FROM Tags 
      WHERE user = :1 AND name = :2""", self.ui().user, refine).get()
    bmq = ndb.gql("""SELECT * FROM Bookmarks 
      WHERE user = :1 AND tags = :2 AND tags = :3
      ORDER BY data DESC""", self.ui().user, tag1, tag2)
    c = ndb.Cursor(urlsafe=self.request.get('c'))
    bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
    if more:
      next_c = next_curs.urlsafe()
    else:
      next_c = None
    self.generate('home.html', 
      {'bms' : bms, 'tag_obj': None, 'c': next_c })

class FeedsPage(BaseHandler):
  @login_required
  def get(self):    
    feeds = ndb.gql("""SELECT * FROM Feeds 
      WHERE user = :1 ORDER BY data DESC""", self.ui().user)
    self.response.set_cookie('active-tab', 'feeds')
    self.generate('feeds.html', {'feeds': feeds})

class TagCloudPage(BaseHandler):
  @login_required
  def get(self):   
    self.response.set_cookie('active-tab', 'tagcloud')
    self.generate('tagcloud.html', {})


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
  def post(self):
    upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
    blob_info = upload_files[0]
    self.redirect('/serve/%s' % blob_info.key())

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self, resource):
    # resource = str(urllib.unquote(resource))
    blob_info = blobstore.BlobInfo.get(resource)
    self.send_blob(blob_info)


debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
  ('/',           InboxPage),
  ('/feeds',      FeedsPage),
  ('/filter',     FilterPage),
  ('/refine',     RefinePage),
  ('/notag',      NotagPage),
  ('/previews',   PreviewPage),
  ('/archived',   ArchivedPage),
  ('/starred',    StarredPage),
  ('/trashed',    TrashedPage),
  ('/tagcloud',   TagCloudPage),
  ('/empty_trash',core.Empty_Trash),
  ('/feed',       core.AddFeed),
  ('/submit',     core.AddBM),
  ('/edit',       core.EditBM),
  ('/addtag',     core.AddTag),
  ('/deltag',     core.DeleteTag),
  ('/atf',        core.AssTagFeed),
  ('/rtf',        core.RemoveTagFeed),
  ('/setmys',     ajax.SetMys),
  ('/archive',    ajax.ArchiveBM),
  ('/trash',      ajax.TrashBM),
  ('/star',       ajax.StarBM),
  ('/removetag',  ajax.RemoveTag),
  ('/assigntag',  ajax.AssignTag),
  ('/gettags',    ajax.GetTags),
  ('/getcomment', ajax.GetComment),
  ('/getedit',    ajax.GetEdit),
  ('/adm/script', myutils.Script),
  ('/adm/check',  myutils.CheckFeeds),
  ('/checkfeed',  myutils.CheckFeed),
  ('/upload',     UploadHandler),
  ('/serve/([^/]+)?', ServeHandler),
  ('/_ah/mail/post@.*',core.ReceiveMail),
  ], debug=debug)

def main():
  run_wsgi_app(app)