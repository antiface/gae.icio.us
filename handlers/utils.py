#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import datetime, jinja2, time
from google.appengine.api import users, mail, app_identity, urlfetch
from google.appengine.ext import deferred, ndb
from models import Bookmarks
from parser import main_parser

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'))

def login_required(handler_method):
    def check_login(self):
        user = users.get_current_user()
        if not user:
            return self.redirect(users.create_login_url(self.request.url))
        else:
            handler_method(self)
    return check_login


def pop_feed(feedk):  
    from libs.feedparser import parse
    feed = feedk.get()
    f = urlfetch.fetch(url="%s" % feed.feed, deadline=60)
    p = parse(f.content)
    e = 0 
    d = p.entries[e]
    while feed.url != d.link and e < 5:
        deferred.defer(new_bm, d, feedk, _target="worker", _queue="importer")
        e += 1 
        d = p.entries[e]
    d = p.entries[0]
    feed.url = d.link
    feed.title = d.title.encode('utf-8')
    feed.comment = d.description.encode('utf-8')
    feed.put()

def new_bm(d, feedk):
    feed = feedk.get()
    bm = Bookmarks()
    bm.feed = feed.key
    bm.user = feed.user
    bm.put()
    def txn():    
        bm.original = d.link
        bm.url = d.link
        bm.title = d.title.encode('utf-8')
        bm.comment = d.description.encode('utf-8')
        bm.tags = feed.tags
        bm.put()
    ndb.transaction(txn)
    deferred.defer(main_parser, bm.key, None, _target="worker", _queue="parser")



def daily_digest(user):
    timestamp = time.time() - 86400
    period = datetime.datetime.fromtimestamp(timestamp)
    bmq = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND create > :2 AND trashed = False
        ORDER BY create DESC""", user, period)
    t=datetime.fromtimestamp(time.time()) 
    t.strftime('%Y-%m-%d %H:%M:%S')
    title = '(%s) 8 Daily digest for your activity: %s' % (app_identity.get_application_id(), t)
    template = jinja_environment.get_template('digest.html')  
    values = {'bmq': bmq, 'title': title} 
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, user.email(), html, title, _target="worker", _queue="emails")


def feed_digest(feedk):
    feed = feedk.get()
    bmq = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND feed = :2
        ORDER BY data DESC""", feed.user, feed.key)
    title = '(%s) 8 hourly digest for %s' % (app_identity.get_application_id(), feed.blog)
    template = jinja_environment.get_template('digest.html') 
    values = {'bmq': bmq, 'title': title} 
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, feed.user.email(), html, title, _target="worker", _queue="emails")
        for bm in bmq:
            bm.trashed = True
            bm.feed = None
            bm.put()


def send_digest(email, html, title):
    message = mail.EmailMessage()
    message.sender = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = email
    message.subject =  title
    message.html = html
    message.send()


def tag_set(bmq):
    tagset = []
    for bm in bmq:
        for tag in bm.tags:
            if not tag in tagset:
                tagset.append(tag)
    return tagset