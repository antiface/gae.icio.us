#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb

class UserInfo(ndb.Model):
    user  = ndb.UserProperty() 
    email = ndb.ComputedProperty(lambda self: self.user.email())
    data  = ndb.DateTimeProperty(auto_now=True)
    mys   = ndb.BooleanProperty(default=False)
    daily = ndb.BooleanProperty(default=False)
    twitt = ndb.BooleanProperty(default=False)
    @property
    def tag_list(self):
        return Tags.query(Tags.user == self.user)


class Tags(ndb.Model):
    data = ndb.DateTimeProperty(auto_now=True)
    user = ndb.UserProperty(required=True)
    name = ndb.StringProperty()
    @property
    def bm_set(self):
        return ndb.gql("""SELECT * FROM Bookmarks
            WHERE tags = :1 ORDER BY data DESC""", self.key)
    @property
    def refine_set(self):
        other = []
        for bm in self.bm_set():
            for tag in bm.tags:
                if not tag in other:
                    other.append(tag)
        other.remove(self.key)
        return other

class Feeds(ndb.Model):
    user    = ndb.UserProperty() 
    data    = ndb.DateTimeProperty(auto_now=True)
    tags    = ndb.KeyProperty(kind=Tags,repeated=True)
    feed    = ndb.StringProperty()#url
    blog    = ndb.StringProperty()#feed.title
    root    = ndb.StringProperty()#feed.link
    digest  = ndb.BooleanProperty(default=False)

    url     = ndb.StringProperty()#link
    title   = ndb.StringProperty()#title
    comment = ndb.TextProperty()#description

    @property
    def id(self):
        return self.key.id()

    @property
    def other_tags(self):
        q = ndb.gql("SELECT name FROM Tags WHERE user = :1", self.user)
        all_user_tags = [tagk.key for tagk in q]
        for tagk in self.tags:
            all_user_tags.remove(tagk)
        return all_user_tags


class Bookmarks(ndb.Model):
    data      = ndb.DateTimeProperty(auto_now=True)
    create    = ndb.DateTimeProperty(auto_now_add=True)
    user      = ndb.UserProperty(required=True)
    original  = ndb.StringProperty()
    url       = ndb.StringProperty()
    title     = ndb.StringProperty()
    comment   = ndb.TextProperty()
    feed      = ndb.KeyProperty(kind=Feeds)
    tags      = ndb.KeyProperty(kind=Tags,repeated=True)
    archived  = ndb.BooleanProperty(default=False)
    starred   = ndb.BooleanProperty(default=False)
    trashed   = ndb.BooleanProperty(default=False)
    have_tags = ndb.ComputedProperty(lambda self: bool(self.tags))

    @property
    def id(self):
        return self.key.id()
        
    @property
    def other_tags(self):
        q = ndb.gql("SELECT name FROM Tags WHERE user = :1", self.user)
        all_user_tags = [tagk.key for tagk in q]
        for tagk in self.tags:
            all_user_tags.remove(tagk)
        return all_user_tags

    def ha_mys(self):
        return UserInfo.query(UserInfo.user == self.user).get().mys