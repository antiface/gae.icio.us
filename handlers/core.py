#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import utils
from webapp2 import RequestHandler
from google.appengine.api import users
from google.appengine.ext import ndb, deferred
from models import Feeds, Bookmarks, Tags, UserInfo

class AddFeed(RequestHandler): 
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
            q = Feeds.query(Feeds.user == user, Feeds.url == url)
            if q.get() is None:
                feed = Feeds()
                def txn():
                    feed.blog = p.feed.title
                    feed.root = p.feed.link
                    feed.user = user
                    feed.feed = url
                    feed.url = d.link
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


class DeleteTag(RequestHandler): 
    def get(self):
        tag = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == tag.user:
            tag.key.delete()
        self.redirect(self.request.referer)


class AssTagFeed(RequestHandler): 
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
    def get(self):
        feed = Feeds.get_by_id(int(self.request.get('feed')))
        tag  = Tags.get_by_id(int(self.request.get('tag')))
        if users.get_current_user() == feed.user:
            feed.tags.remove(tag.key)
            feed.put()
        self.redirect(self.request.referer) 


class Empty_Trash(RequestHandler): 
    def get(self):
        bmq = Bookmarks.query(Bookmarks.user == users.get_current_user())
        bmq = bmq.filter(Bookmarks.trashed == True)
        bmq = bmq.order(-Bookmarks.data).fetch()
        ndb.delete_multi([bmk.key for bmk in bmq])
        self.redirect(self.request.referer)

#### admin ###

class CheckFeed(RequestHandler): 
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


class SendActivity(RequestHandler):
    def get(self): 
        for ui in UserInfo.query(): 
            if ui.daily: 
                deferred.defer(utils.daily_digest, ui.user, _target="worker", _queue="admin")


#### don't care ###

class Upgrade(RequestHandler):
    """change this handler for admin operations"""
    def get(self):
        for tag in Tags.query():
            tag.put() 


def upgrade(itemk):
    for tag in Tags.query():
        tag.put()




class Script(RequestHandler): 
    def get(self):
        from parser import main_parser
        for bm in Bookmarks.query(Bookmarks.archived == False):
            deferred.defer(main_parser, bm.key, None, _queue="parser")


class del_attr(RequestHandler):
    """delete old property from datastore"""
    def post(self): 
        model = self.request.get('model') 
        prop = self.request.get('prop') 
        q = ndb.gql("SELECT * FROM %s" % (model)) 
        for r in q: 
            deferred.defer(delatt, r.key, prop, _queue="admin") 
        self.redirect('/admin')

def delatt(rkey, prop): 
    r = rkey.get() 
    delattr(r, '%s' % prop) 
    r.put()