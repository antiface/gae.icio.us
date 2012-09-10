#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import utils
from webapp2 import RequestHandler
from google.appengine.api import users
from google.appengine.ext import ndb, deferred
from models import Feeds, Bookmarks, Tags, UserInfo

class AddFeed(RequestHandler):
    @utils.login_required
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





class EditBM(RequestHandler):
    @utils.login_required
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


class DeleteTag(RequestHandler):
    @utils.login_required
    def get(self):
        tag = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == tag.user:
            tag.key.delete()
        self.redirect(self.request.referer)


class AssTagFeed(RequestHandler):
    @utils.login_required
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


class RemoveTagFeed(RequestHandler):
    @utils.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag  = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            feed.tags.remove(tag.key)
            feed.put()
        self.redirect(self.request.referer)    


class Empty_Trash(RequestHandler):
    @utils.login_required
    def get(self):
        bmq = ndb.gql("""SELECT __key__ FROM Bookmarks
            WHERE user = :1 AND trashed = True 
            ORDER BY data DESC""", users.get_current_user())
        ndb.delete_multi(bmq.fetch())
        self.redirect(self.request.referer)


class CheckFeed(RequestHandler):
    @utils.login_required
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        deferred.defer(utils.pop_feed, feed.key, _queue="admin")


class CheckFeeds(RequestHandler):
    def get(self): 
        for feed in Feeds.query(): 
            deferred.defer(utils.pop_feed, feed.key, _target="worker", _queue="admin")


class SendDigest(RequestHandler):
    def get(self): 
        for feed in Feeds.query(): 
            if feed.notify == 'digest': 
                deferred.defer(utils.feed_digest, feed.key, _target="worker", _queue="admin")


class SendDaily(RequestHandler):
    def get(self): 
        for ui in UserInfo.query(): 
            if ui.daily: 
                deferred.defer(utils.daily_digest, ui.user, _target="worker", _queue="admin")


class Script(RequestHandler):
    """change this handler for admin operations"""
    def get(self):        
        for item in UserInfo.query():
            deferred.defer(upgrade, item.key, _target="worker", _queue="admin")

class Upgrade(RequestHandler):
    """change this handler for admin operations"""
    def get(self):        
        for item in UserInfo.query():
            deferred.defer(upgrade, item.key, _target="worker", _queue="admin")
        for item in Feeds.query():
            deferred.defer(upgrade, item.key, _target="worker", _queue="admin") 
        for item in Tags.query():
            deferred.defer(upgrade, item.key, _target="worker", _queue="admin") 
        for item in Bookmarks.query():
            deferred.defer(upgrade, item.key, _target="worker", _queue="admin") 


def upgrade(itemk):
    item = itemk.get()
    item.uid = item.user.user_id()
    item.put()


class Upgrade(RequestHandler):
    """change this handler for admin operations"""
    def get(self):        
        for feed in UserInfo.query():
            feed.uid = feed.user.user_id()
            feed.put()


class del_attr(RequestHandler):
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