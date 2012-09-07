#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2, os, webapp2
from google.appengine.api import users, mail, app_identity
from google.appengine.ext import ndb, deferred
from handlers import ajax, config, utils, core
from handlers.models import Bookmarks, UserInfo
from handlers.parser import main_parser
from dropbox import client, session


#Dropbox staff
APP_KEY       = config.APP_KEY # "DELETE 'config.APP_KEY' AND PUT HERE YOUR APP_KEY"
APP_SECRET    = config.APP_SECRET #"DELETE 'config.APP_SECRET' AND PUT HERE YOUR APP_SECRET"
ACCESS_TYPE   = 'app_folder'
sess          = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE) 
request_token = sess.obtain_request_token()


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = utils.dtf


class BaseHandler(webapp2.RequestHandler):
    
    def ui(self):
        if users.get_current_user():
            q = UserInfo.query(UserInfo.user == users.get_current_user())
            if q.get():
                return q.get()
            else:
                ui      = UserInfo()
                ui.user = users.get_current_user()
                ui.put()
                return ui

    def generate(self, template_name, template_values={}):
        if users.get_current_user():      
            url      = users.create_logout_url("/")
            linktext = 'Logout'
        else:
            url      = users.create_login_url(self.request.uri)
            linktext = 'Login'
        values = {      
            'brand'   : app_identity.get_application_id(),
            'url'     : url,
            'linktext': linktext,
            'ui'      : self.ui(),
            }
        values.update(template_values)
        template = jinja_environment.get_template(template_name)
        self.response.write(template.render(values))


class SettingPage(BaseHandler):
    @utils.login_required
    def get(self):
        ui = self.ui()
        if not sess.is_linked():
            if self.request.get('oauth_token'):
                access_token = sess.obtain_access_token(request_token)            
                ui.token = str(access_token)
                ui.put()

        bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, self.ui().email)

        callback    = "%s/setting" % (self.request.host_url) 
        dropbox_url = sess.build_authorize_url(request_token, oauth_callback=callback)

        self.response.set_cookie('dropbox'   , '%s' % sess.is_linked())
        self.response.set_cookie('mys'       , '%s' % self.ui().mys)
        self.response.set_cookie('daily'     , '%s' % self.ui().daily)
        self.response.set_cookie('twitt'     , '%s' % self.ui().twitt)
        self.response.set_cookie('active-tab', 'setting')

        self.generate('setting.html', {'bookmarklet': bookmarklet, 'dropbox_url': dropbox_url})


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
            self.generate('home.html', {'bms': bms, 'tags': utils.tag_set(bmq), 'c': next_c })
        else:
            self.generate('git.html', {})


class ArchivedPage(BaseHandler):
    @utils.login_required
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
        self.generate('home.html', {'bms' : bms, 'tags': utils.tag_set(bmq), 'c': next_c })


class StarredPage(BaseHandler):
    @utils.login_required
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
        self.generate('home.html', {'bms' : bms, 'tags': utils.tag_set(bmq), 'c': next_c })


class TrashedPage(BaseHandler):
    @utils.login_required
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
        self.generate('home.html', {'bms' : bms, 'tags': utils.tag_set(bmq), 'c': next_c })


class NotagPage(BaseHandler):
    @utils.login_required
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
        self.generate('home.html', {'bms' : bms, 'tags': utils.tag_set(bmq), 'c': next_c })


class FilterPage(BaseHandler):
    @utils.login_required
    def get(self):
        tag_name = self.request.get('tag')
        tag_obj = ndb.gql("""SELECT * FROM Tags 
            WHERE user = :1 AND name = :2""", self.ui().user, tag_name).get()
        bmq = ndb.gql("""SELECT * FROM Bookmarks 
            WHERE user = :1 AND tags = :2
            ORDER BY data DESC""", self.ui().user, tag_obj.key)
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
            self.generate('home.html', {'tag_obj': tag_obj, 'bms': bms, 'tags': tagset, 'c': next_c })
        else:
            self.redirect('/')


class RefinePage(BaseHandler):
    @utils.login_required
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
        self.generate('home.html', {'bms' : bms, 'tag_obj': None, 'c': next_c })


class FeedsPage(BaseHandler):
    @utils.login_required
    def get(self):
        feeds = ndb.gql("""SELECT * FROM Feeds 
            WHERE user = :1 ORDER BY data DESC""", self.ui().user)
        self.response.set_cookie('active-tab', 'feeds')
        self.generate('feeds.html', {'feeds': feeds})


class TagCloudPage(BaseHandler):
    @utils.login_required
    def get(self):   
        self.response.set_cookie('active-tab', 'tagcloud')
        self.generate('tagcloud.html', {})


class AdminPage(BaseHandler):    
    def get(self):
        if users.is_current_user_admin(): 
            self.generate('admin.html', {})
        else: 
            self.redirect('/')
        
#########################################################

class AddBM(webapp2.RequestHandler):
    @utils.login_required
    def get(self):
        bm = Bookmarks()
        def txn(): 
            bm.original = self.request.get('url')
            bm.title    = self.request.get('title')
            bm.comment  = self.request.get('comment')
            bm.user     = users.User(str(self.request.get('user')))
            bm.put()
        ndb.transaction(txn) 
        if sess.is_linked():
            db_user = client.DropboxClient(sess) 
        else:
            db_user = None
        deferred.defer(main_parser, bm.key, db_user, _target="worker", _queue="parser")
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
            bm.title    = header.decode_header(message.subject)[0][0]
            bm.comment  = 'Sent via email'
            bm.user     = users.User(utils.parseaddr(message.sender)[1])
            bm.put()
        ndb.transaction(txn) 
        if sess.is_linked():
            db_user = client.DropboxClient(sess) 
        else:
            db_user = None
        deferred.defer(main_parser, bm.key, db_user, _target="worker", _queue="parser")


debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
    ('/'                 , InboxPage),
    ('/feeds'            , FeedsPage),
    ('/filter'           , FilterPage),
    ('/refine'           , RefinePage),
    ('/notag'            , NotagPage),
    ('/archived'         , ArchivedPage),
    ('/starred'          , StarredPage),
    ('/trashed'          , TrashedPage),
    ('/tagcloud'         , TagCloudPage),
    ('/setting'          , SettingPage),
    ('/adm'              , AdminPage),
    ('/submit'           , AddBM),
    ('/_ah/mail/post@.*' , ReceiveMail),
    ('/feed'             , core.AddFeed),
    ('/edit'             , core.EditBM),
    ('/deltag'           , core.DeleteTag),
    ('/atf'              , core.AssTagFeed),
    ('/rtf'              , core.RemoveTagFeed),
    ('/setmys'           , ajax.SetMys),
    ('/setdaily'         , ajax.SetDaily),
    ('/setnotify'        , ajax.SetNotify),
    ('/settwitt'         , ajax.SetTwitt),
    ('/archive'          , ajax.ArchiveBM),
    ('/trash'            , ajax.TrashBM),
    ('/star'             , ajax.StarBM),
    ('/addtag'           , ajax.AddTag),
    ('/removetag'        , ajax.RemoveTag),
    ('/assigntag'        , ajax.AssignTag),
    ('/gettags'          , ajax.GetTags),
    ('/gettagsfeed'      , ajax.GetTagsFeed),
    ('/getcomment'       , ajax.GetComment),
    ('/getedit'          , ajax.GetEdit),
    ('/empty_trash'      , core.Empty_Trash),
    ('/adm/script'       , core.Script),
    ('/adm/digest'       , core.SendDigest),
    ('/adm/daily'        , core.SendDaily),
    ('/adm/check'        , core.CheckFeeds),
    ('/adm/delattr'      , core.del_attr),
    ('/checkfeed'        , core.CheckFeed),
    ], debug=debug)


def main():
        app.run()

if __name__ == "__main__":
        main()