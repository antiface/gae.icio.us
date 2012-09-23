#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
import webapp2
import os
from google.appengine.api import users, mail, app_identity
from google.appengine.ext import ndb, deferred, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from handlers import ajax, utils, core
from handlers.models import Bookmarks, UserInfo, Feeds, Tags
from handlers.parser import main_parser
from libs.bs4 import BeautifulSoup

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates', 'partials']))
jinja_environment.filters['dtf'] = utils.dtf


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
            url = users.create_logout_url("/")
            linktext = 'Logout'

        else:
            url = users.create_login_url(self.request.uri)
            linktext = 'Login'
        values = {
            'brand' : app_identity.get_application_id(),
            'url' : url,
            'linktext': linktext,
            'ui' : self.ui(),
            'admin'  : users.is_current_user_admin()
            }
        values.update(template_values)
        template = jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class SettingPage(BaseHandler):
    def get(self):
        ui = self.ui()
        upload_url = blobstore.create_upload_url('/upload')

        bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, ui.email)

        self.response.set_cookie('mys' , '%s' % ui.mys)
        self.response.set_cookie('daily' , '%s' % ui.daily)
        self.response.set_cookie('twitt' , '%s' % ui.twitt)
        self.response.set_cookie('active-tab', 'setting')

        self.generate('setting.html', {'bookmarklet': bookmarklet,
                                        'upload_url': upload_url,
                                        })


class InboxPage(BaseHandler):
    def get(self):
        if users.get_current_user(): 
            bmq = Bookmarks.query(Bookmarks.trashed == False)
            bmq = bmq.filter(Bookmarks.archived == False)
            bmq = bmq.filter(Bookmarks.user == users.get_current_user())
            bmq = bmq.order(-Bookmarks.data)
            c = ndb.Cursor(urlsafe=self.request.get('c'))
            bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
            if more:
                next_c = next_curs.urlsafe()
            else:
                next_c = None
            self.response.set_cookie('active-tab', 'inbox')
            self.generate('home.html', {'bms': bms, 'c': next_c })
        else:
            self.response.set_cookie('active-tab', 'hero')
            self.generate('hero.html', {})


class ArchivedPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.trashed == False)
        bmq = bmq.filter(Bookmarks.archived == True)
        bmq = bmq.filter(Bookmarks.user == users.get_current_user())
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'archive')
        self.generate('home.html', {'bms' : bms, 'c': next_c })


class SharedPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.trashed == False)
        bmq = bmq.filter(Bookmarks.shared == True)
        bmq = bmq.filter(Bookmarks.user == users.get_current_user())
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'shared')
        self.generate('home.html', {'bms' : bms, 'c': next_c })


class StarredPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.trashed == False)
        bmq = bmq.filter(Bookmarks.starred == True)
        bmq = bmq.filter(Bookmarks.user == users.get_current_user())
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'starred')
        self.generate('home.html', {'bms' : bms, 'c': next_c })


class TrashedPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.trashed == True)
        bmq = bmq.filter(Bookmarks.user == users.get_current_user())
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'trash')
        self.generate('home.html', {'bms' : bms, 'c': next_c })


class NotagPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.trashed == False)
        bmq = bmq.filter(Bookmarks.have_tags == False)
        bmq = bmq.filter(Bookmarks.user == users.get_current_user())
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'untagged')
        self.generate('home.html', {'bms' : bms, 'c': next_c })


class FilterPage(BaseHandler):
    def get(self):
        tag_name = self.request.get('tag')
        tag_obj = Tags.query(Tags.user == users.get_current_user())
        tag_obj = tag_obj.filter(Tags.name == tag_name).get()
        bmq = Bookmarks.query(Bookmarks.user == users.get_current_user())
        bmq = bmq.filter(Bookmarks.tags == tag_obj.key)
        bmq = bmq.order(-Bookmarks.data)
        if tag_obj:
            c = ndb.Cursor(urlsafe=self.request.get('c'))
            bms, next_curs, more = bmq.fetch_page(10, start_cursor=c)
            if more:
                next_c = next_curs.urlsafe()
            else:
                next_c = None
            tagset = utils.tag_set(bmq)
            tagset.remove(tag_obj.key)
            self.response.set_cookie('active-tab', '')
            self.generate('home.html', {'tag_obj': tag_obj, 
                                        'bms': bms, 
                                        'tags': tagset, 
                                        'c': next_c })
        else:
            self.redirect('/')


class RefinePage(BaseHandler):
    def get(self):
        tag_name = self.request.get('tag')
        refine = self.request.get('refine')
        tagq = Tags.query(Tags.user == users.get_current_user())
        tag1 = tagq.filter(Tags.name == tag_name).get()
        tag2 = tagq.filter(Tags.name == refine).get()
        bmq = Bookmarks.query(Bookmarks.user == users.get_current_user())
        bmq = bmq.filter(Bookmarks.tags == tag1.key)
        bmq = bmq.filter(Bookmarks.tags == tag2.key)
        bmq = bmq.order(-Bookmarks.data)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.generate('home.html', {'bms' : bms, 'c': next_c })

class StreamPage(BaseHandler):
    def get(self):
        bmq = Bookmarks.query(Bookmarks.shared == True, Bookmarks.trashed == False)
        bmq = bmq.filter(Bookmarks.user != users.get_current_user())
        bmq = bmq.order(Bookmarks.user, -Bookmarks.data, Bookmarks._key)
        c = ndb.Cursor(urlsafe=self.request.get('c'))
        bms, next_curs, more = bmq.fetch_page(10, start_cursor=c) 
        if more:
            next_c = next_curs.urlsafe()
        else:
            next_c = None
        self.response.set_cookie('active-tab', 'stream')
        self.generate('public.html', {'bms' : bms, 'c': next_c })


class FeedsPage(BaseHandler):
    def get(self):
        feeds = Feeds.query(Feeds.user == users.get_current_user())
        feeds = feeds.order(-Feeds.data)
        self.response.set_cookie('active-tab', 'feeds')
        self.generate('feeds.html', {'feeds': feeds})


class TagCloudPage(BaseHandler):
    def get(self): 
        q = Tags.query(Tags.user == users.get_current_user())
        self.response.set_cookie('active-tab', 'tagcloud')
        self.generate('tagcloud.html', {'q': q})


class AdminPage(BaseHandler): 
    def get(self):        
        if users.is_current_user_admin(): 
            self.response.set_cookie('active-tab', 'admin')
            self.generate('admin.html', {})
        else: 
            self.redirect('/')


class AddBM(webapp2.RequestHandler): 
    def get(self):
        bm = Bookmarks()
        def txn(): 
            bm.original = self.request.get('url')
            bm.url = self.request.get('url')
            bm.title = self.request.get('title')
            bm.comment = self.request.get('comment')
            bm.user = users.User(str(self.request.get('user')))
            bm.put()
        ndb.transaction(txn) 
        main_parser(bm.key)
        self.redirect('/')


class ReceiveMail(webapp2.RequestHandler):
    def post(self):
        from email import header, utils
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
        deferred.defer(main_parser, bm.key, _queue="parser")

class CopyBM(webapp2.RequestHandler):
    def get(self):
        old = Bookmarks.get_by_id(int(self.request.get('bm')))
        bm = Bookmarks()
        def txn(): 
            bm.original = old.original
            bm.title = old.title
            bm.comment = old.comment
            bm.user = users.get_current_user()
            bm.put()
        ndb.transaction(txn) 
        deferred.defer(main_parser, bm.key, _queue="parser")


class UploadDelicious(blobstore_handlers.BlobstoreUploadHandler):
  def post(self):
    user = users.get_current_user()
    upload_files = self.get_uploads('file')
    blob_info = upload_files[0]
    ui = UserInfo.query(UserInfo.user == user).get()
    ui.delicious = blob_info.key()
    ui.put()
    self.redirect('/setting')


class ImportDelicious(BaseHandler): 
    def get(self):
        for ui in UserInfo.query():
            if ui.delicious:
                size = blobstore.BlobInfo.get(ui.delicious).size
                if ui.cursor < size:
                    self.parse(ui)

    def parse(self, ui):
        blob_reader = blobstore.BlobReader(ui.delicious)
        blob_reader.seek(ui.cursor)
        ui.cursor = ui.cursor + 9500
        future = ui.put_async()
        data = blob_reader.read(10000)
        soup = BeautifulSoup(data)
        future.get_result()
        for tag in soup.findAll('dt'):
            if tag.nextSibling and tag.nextSibling.name == 'dd':
                comment = tag.nextSibling.text
            else:
                comment = ""
            deferred.defer(utils.delicious, tag, comment, ui.user, _queue="admin")
        



debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
    ('/'                 , InboxPage),
    ('/feeds'            , FeedsPage),
    ('/filter'           , FilterPage),
    ('/refine'           , RefinePage),
    ('/notag'            , NotagPage),
    ('/archived'         , ArchivedPage),
    ('/starred'          , StarredPage),
    ('/shared'           , SharedPage),
    ('/trashed'          , TrashedPage),
    ('/stream'           , StreamPage),
    ('/tagcloud'         , TagCloudPage),
    ('/setting'          , SettingPage),
    ('/admin'            , AdminPage),
    ('/submit'           , AddBM),
    ('/_ah/mail/post@.*' , ReceiveMail),
    ('/copy'             , CopyBM),
    ('/feed'             , core.AddFeed),
    ('/edit'             , core.EditBM),
    ('/deltag'           , core.DeleteTag),
    ('/atf'              , core.AssTagFeed),
    ('/rtf'              , core.RemoveTagFeed),
    ('/empty_trash'      , core.Empty_Trash),
    ('/checkfeed'        , core.CheckFeed),
    ('/setmys'           , ajax.SetMys),
    ('/setdaily'         , ajax.SetDaily),
    ('/setnotify'        , ajax.SetNotify),
    ('/settwitt'         , ajax.SetTwitt),
    ('/archive'          , ajax.ArchiveBM),
    ('/trash'            , ajax.TrashBM),
    ('/star'             , ajax.StarBM),
    ('/share'            , ajax.ShareBM),
    ('/addtag'           , ajax.AddTag),
    ('/removetag'        , ajax.RemoveTag),
    ('/assigntag'        , ajax.AssignTag),
    ('/gettags'          , ajax.GetTags),
    ('/gettagsfeed'      , ajax.GetTagsFeed),
    ('/getcomment'       , ajax.GetComment),
    ('/getedit'          , ajax.GetEdit),
    ('/admin/upgrade'    , core.Upgrade),
    ('/admin/script'     , core.Script),
    ('/admin/digest'     , core.SendDigest),
    ('/admin/activity'   , core.SendActivity),
    ('/admin/check'      , core.CheckFeeds),
    ('/admin/delattr'    , core.del_attr),
    ('/upload'           , UploadDelicious),
    ('/admin/import'     , ImportDelicious),
    ], debug=debug)


def main():
    app.run()

if __name__ == "__main__":
    main()