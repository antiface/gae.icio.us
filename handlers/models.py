#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import urlparse
from google.appengine.ext import ndb

class UserInfo(ndb.Model):
  user = ndb.UserProperty() 
  data = ndb.DateTimeProperty(auto_now=True)
  mys = ndb.BooleanProperty(default=False)

class Feeds(ndb.Model):
  user = ndb.UserProperty() 
  data = ndb.DateTimeProperty(auto_now=True)
  feed = ndb.StringProperty()#url
  blog = ndb.StringProperty()#feed.title
  root = ndb.StringProperty()#feed.link

  url = ndb.StringProperty()#link
  title = ndb.StringProperty()#title
  comment = ndb.TextProperty()#description


class Tags(ndb.Model):
  data  = ndb.DateTimeProperty(auto_now=True)
  user  = ndb.UserProperty(required=True)
  name  = ndb.StringProperty()
  count = ndb.IntegerProperty(default=0)
  def bm_set(self):
    return ndb.gql("""SELECT * FROM Bookmarks
      WHERE tags = :1 ORDER BY data DESC""", self.key)
  def refine_set(self):
    other = []
    for bm in self.bm_set():
      for tag in bm.tags:
        if not tag in other:
          other.append(tag)
    other.remove(self.key)
    return other

class Bookmarks(ndb.Model):
  data = ndb.DateTimeProperty(auto_now=True)
  user = ndb.UserProperty(required=True)
  url = ndb.StringProperty()
  title = ndb.StringProperty()
  comment = ndb.TextProperty()
  tags = ndb.KeyProperty(kind=Tags,repeated=True)
  archived = ndb.BooleanProperty(default=False)
  starred = ndb.BooleanProperty(default=False)
  have_tags = ndb.ComputedProperty(lambda self: bool(self.tags))
  have_prev = ndb.ComputedProperty(lambda self: bool(self.preview()))
  def other_tags(self):
    q = ndb.gql("SELECT name FROM Tags WHERE user = :1", self.user)
    all_user_tags = [tagk.key for tagk in q]
    for tagk in self.tags:
      all_user_tags.remove(tagk)
    return all_user_tags
  def preview(self):
    url_data = urlparse.urlparse(self.url)
    query = urlparse.parse_qs(url_data.query)
    try:
      video = query["v"][0]
      return video
    except:
      return False
  def ha_mys(self):
    return UserInfo.query(UserInfo.user == self.user).get().mys