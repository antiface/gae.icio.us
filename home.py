#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2, os, webapp2
from google.appengine.api import users, mail, app_identity
from google.appengine.ext import ndb, deferred
from handlers import ajax, config, utils
from handlers.models import Bookmarks, UserInfo, Feeds, Tags
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
        if self.request.get('oauth_token'):
            access_token = sess.obtain_access_token(request_token)
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

class AddFeed(webapp2.RequestHandler):
    def post(self):
        from libs.feedparser import parse
        user = users.get_current_user()
        url = self.request.get('url')
        p = parse(str(url))
        try:
            d = p['items'][0]
        except IndexError:
            pass
        if user:
            q = ndb.gql("""SELECT * FROM Feeds
            WHERE user = :1 AND url = :2""", user, url)
            if q.get() is None:
                feed = Feeds()
                def txn():
                    feed.blog    = p.feed.title
                    feed.root    = p.feed.link
                    feed.user    = user
                    feed.feed    = url
                    feed.url     = d.link
                    feed.put()
                ndb.transaction(txn)
                deferred.defer(utils.new_bm, d, feed.key, _queue="admin")
            self.redirect(self.request.referer)
        else:
            self.redirect('/')
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('id')))
        feed.key.delete()


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
        if bm.ha_mys(): 
            deferred.defer(utils.send_bm, bm.key, _target="worker", _queue="emails")
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
        if bm.ha_mys(): 
            deferred.defer(utils.send_bm, bm.key, _target="worker", _queue="emails")


class EditBM(webapp2.RequestHandler):
    def get(self):
        bm = Bookmarks.get_by_id(int(self.request.get('bm')))
        if users.get_current_user() == bm.user:
            def txn():
                bm.url     = self.request.get('url').encode('utf8')
                bm.title   = self.request.get('title').encode('utf8')
                bm.comment = self.request.get('comment').encode('utf8')
                bm.put()
            ndb.transaction(txn)
        self.redirect('/')


class DeleteTag(webapp2.RequestHandler):
    def get(self):
        tag = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == tag.user:
            tag.key.delete()
        self.redirect(self.request.referer)


class AssTagFeed(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag  = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            if tag in feed.tags:
                pass
            else:
                feed.tags.append(tag.key)
                feed.put()
        self.redirect(self.request.referer)


class RemoveTagFeed(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag  = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            feed.tags.remove(tag.key)
            feed.put()
        self.redirect(self.request.referer)    


class Empty_Trash(webapp2.RequestHandler):
    @utils.login_required
    def get(self):
        bmq = ndb.gql("""SELECT __key__ FROM Bookmarks
            WHERE user = :1 AND trashed = True 
            ORDER BY data DESC""", users.get_current_user())
        ndb.delete_multi(bmq.fetch())
        self.redirect(self.request.referer)


class CheckFeed(webapp2.RequestHandler):
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(utils.pop_feed, feed.key, _queue="admin")


class CheckFeeds(webapp2.RequestHandler):
    def get(self): 
        for feed in Feeds.query(): 
            deferred.defer(utils.pop_feed, feed.key, _target="worker", _queue="admin")


class SendDigest(webapp2.RequestHandler):
    def get(self): 
        for feed in Feeds.query(): 
            if feed.notify == 'digest': 
                deferred.defer(utils.feed_digest, feed.key, _target="worker", _queue="admin")


class SendDaily(webapp2.RequestHandler):
    def get(self): 
        for ui in UserInfo.query(): 
            if ui.daily: 
                deferred.defer(utils.daily_digest, ui.user, _target="worker", _queue="admin")

#####################################################################################

class Script(webapp2.RequestHandler):
    """change this handler for admin operations"""
    def get(self):
        for feed in Feeds.query():
            ui = UserInfo.query(UserInfo.user == feed.user).get()
            if feed.digest:
                feed.notify = 'digest'
            elif ui.mys:
                feed.notify = 'email'
            else:
                feed.notify = 'web'
            feed.put()


class del_attr(webapp2.RequestHandler):
    """delete old property from datastore"""
    def post(self): 
        model = self.request.get('model') 
        prop = self.request.get('prop') 
        q = ndb.gql("SELECT * FROM %s" % (model)) 
        for r in q: 
            deferred.defer(delatt, r.key, prop, _queue="admin", _target="worker") 
        self.redirect('/adm')

def delatt(rkey, prop): 
    r = rkey.get() 
    delattr(r, '%s' % prop) 
    r.put()

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
    ('/feed'             , AddFeed),
    ('/submit'           , AddBM),
    ('/submit2'          , AddBM2),
    ('/edit'             , EditBM),
    ('/deltag'           , DeleteTag),
    ('/atf'              , AssTagFeed),
    ('/rtf'              , RemoveTagFeed),
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
    ('/empty_trash'      , Empty_Trash),
    ('/adm'              , AdminPage),
    ('/adm/delattr'      , del_attr),
    ('/adm/script'       , Script),
    ('/adm/digest'       , SendDigest),
    ('/adm/daily'        , SendDaily),
    ('/adm/check'        , CheckFeeds),
    ('/checkfeed'        , CheckFeed),
    ('/_ah/mail/post@.*' , ReceiveMail),
    ], debug=debug)


def main():
        app.run()

if __name__ == "__main__":
        main()