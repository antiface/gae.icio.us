#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from models import Bookmarks
import utils


def main_parser(bmk, db_user):
    import urlparse
    bm = bmk.get()
    result = urlfetch.fetch(url=bm.original, follow_redirects=True, allow_truncated=True, deadline=600) 
    if result.status_code == 200 and result.final_url:
        a = result.final_url 
    else:
        a = bm.original 
    b = a.split('?utm_source')[0]
    c = b.split('&feature')[0]
    bm.url = c
    # TAGS
    q = Bookmarks.query(Bookmarks.user == bm.user, Bookmarks.original == bm.original).fetch()
    if q.count > 1:
        tag_list = []
        for e in q:
            for t in e.tags:
                if t not in tag_list:
                    tag_list.append(t)
                    bm.tags = tag_list
        ekeys = [e.key for e in q]
        ekeys.remove(bm.key)
        for ekey in ekeys:
            e = ekey.get()
            e.trashed = True
            e.put()  
    # COMMENTS
    url_parsed = urlparse.urlparse(bm.original)
    query = urlparse.parse_qs(url_parsed.query)
    if url_parsed.netloc == 'www.youtube.com':    
        video      = query["v"][0]
        bm.url     = 'http://www.youtube.com/watch?v=%s' % video
        bm.comment = '''<iframe width="640" height="360" 
        src="http://www.youtube.com/embed/%s" frameborder="0"
        allowfullscreen></iframe>''' % video
    if url_parsed.netloc == 'vimeo.com': 
        video      = url_parsed.path.split('/')[-1]
        bm.url     = 'http://vimeo.com/%s' % video
        bm.comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff" 
        width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen 
        allowFullScreen></iframe>''' % video
    if bm.url.split('.')[-1] == 'jpg':
        bm.comment = '<img src="%s" />' % bm.url      
    # TITLE
    if bm.title == '':
        bm.title = url_parsed.path
    bm.put()
    # Notify
    try:
        if bm.feed.get().notify == 'email': 
            deferred.defer(utils.send_bm, bm.key, _target="worker", _queue="emails")
    except:
        if bm.ha_mys: 
            deferred.defer(utils.send_bm, bm.key, _target="worker", _queue="emails")

    # DROPBOX
    if db_user is not None:
        if bm.url.split('.')[-1] == 'jpg' or 'mp3' or 'avi' or 'pdf':
            deferred.defer(utils.db_put, bmk, db_user, _target="worker", _queue="dropbox")