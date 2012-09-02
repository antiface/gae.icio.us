#!/usr/local/bin/python
# -*- coding: utf-8 -*-
from google.appengine.api import urlfetch, mail, app_identity, capabilities
from google.appengine.ext import ndb, deferred


def main_parser(bmk, db_user):
    import urlparse
    bm = bmk.get()
    # URLS
    try:
        u = urlfetch.fetch(url=bm.original, follow_redirects=True)
        bm.url = u.final_url.split('?utm_source')[0]
        bm.url = u.final_url.split('&feature')[0]
    except:
        bm.url = bm.original.split('?utm_source')[0]
        bm.url = bm.original.split('&feature')[0]
    # TAGS
    q = ndb.gql("SELECT * FROM Bookmarks WHERE user = :1 AND original = :2", bm.user, bm.original).fetch()
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
        video = query["v"][0]
        bm.url = 'http://www.youtube.com/watch?v=%s' % video
        bm.comment = '''<iframe width="640" height="360" 
        src="http://www.youtube.com/embed/%s" frameborder="0" 
        allowfullscreen></iframe>''' % video
    if url_parsed.netloc == 'vimeo.com': 
        video = url_parsed.path.split('/')[-1]
        bm.url = 'http://vimeo.com/%s' % video
        bm.comment = '''<iframe src="http://player.vimeo.com/video/%s?color=ffffff" 
        width="640" height="360" frameborder="0" webkitAllowFullScreen mozallowfullscreen 
        allowFullScreen></iframe>''' % video
    if bm.url.split('.')[-1] == '.jpg':
        bm.comment = '<img src="%s" alt="some_text"/>' % bm.url      
    # TITLE
    if bm.title == '':
        bm.title = url_parsed.path
    bm.put()
    # EMAILS
    if bm.ha_mys() and capabilities.CapabilitySet("mail").is_enabled():
        try:
            bm.feed.get().digest == True
            pass
        except:
            deferred.defer(send_bm, bm.key, _target="worker", _queue="emails")
    # DROPBOX
    if db_user is not None:
        if bm.url.split('.')[-1] == '.jpg' or '.mp3' or '.avi' or '.pdf':
            deferred.defer(db_put, bmk, db_user, _target="worker", _queue="dropbox")


def db_put(bmk, db_user):
    bm = bmk.get()
    file_name = bm.url.split('/')[-1]        
    f = urlfetch.fetch(url="%s" % bm.url, deadline=600)
    db_user.put_file('/%s' % file_name, f.content )


def send_bm(bmk):   
    bm = bmk.get()
    message = mail.EmailMessage()
    message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = bm.user.email()
    message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
    message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
    message.send()