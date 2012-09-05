#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
from google.appengine.api import users, mail, app_identity, urlfetch
from google.appengine.ext import deferred, ndb
from models import Bookmarks
from parser import main_parser


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'))

def dtf(value, format='%d/%m/%Y - %H:%M UTC'):
    return value.strftime(format)

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
    d = p['items'][e]
    while feed.url != d['link'] and e < 10:
        deferred.defer(new_bm, d, feedk, _target="worker", _queue="importer")
        e += 1 
        try:
            d = p['items'][e]
        except IndexError:
            pass
    d = p['items'][0]
    feed.url     = d['link']
    feed.title   = d['title']
    feed.comment = d['description']
    feed.put()

def new_bm(d, feedk):
    feed = feedk.get()
    bm      = Bookmarks()
    bm.feed = feed.key
    bm.user = feed.user
    bm.original = d['link']
    bm.title    = d['title']
    try:
        bm.comment  = d['description']
    except KeyError:
        bm.comment = 'no comment'
    bm.tags     = feed.tags
    bm.put()
    deferred.defer(main_parser, bm.key, None, _target="worker", _queue="parser")



def daily_digest(user):
    import datetime, time
    timestamp = time.time() - 86400
    period    = datetime.datetime.fromtimestamp(timestamp)
    bmq = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND create > :2 AND trashed = False
        ORDER BY create DESC""", user, period)
    t = datetime.datetime.fromtimestamp(time.time()) 
    title    = '(%s) Daily digest for your activity: %s' % (app_identity.get_application_id(), dtf(t))
    template = jinja_environment.get_template('digest.html')  
    values   = {'bmq': bmq, 'title': title} 
    html     = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, user.email(), html, title, _target="worker", _queue="emails")


def feed_digest(feedk):
    feed = feedk.get()
    bmq = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND feed = :2 AND trashed = False
        ORDER BY data DESC""", feed.user, feed.key)
    title    = '(%s) 8 hourly digest for %s' % (app_identity.get_application_id(), feed.blog)
    template = jinja_environment.get_template('digest.html') 
    values   = {'bmq': bmq, 'title': title} 
    html     = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, feed.user.email(), html, title, _target="worker", _queue="emails")


def send_bm(bmk): 
    bm = bmk.get()
    message         = mail.EmailMessage()
    message.sender  = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to      = bm.user.email()
    message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
    message.html    = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, dtf(bm.data), bm.url, bm.comment)
    message.send()

def send_digest(email, html, title):
    message         = mail.EmailMessage()
    message.sender  = 'action@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to      = email
    message.subject =  title
    message.html    = html
    message.send()

def db_put(bmk, db_user):
    bm        = bmk.get()
    file_name = bm.url.split('/')[-1] 
    f         = urlfetch.fetch(url="%s" % bm.url, deadline=600)
    db_user.put_file('/%s' % file_name, f.content )

def tag_set(bmq):
    tagset = []
    for bm in bmq:
        for tag in bm.tags:
            if not tag in tagset:
                tagset.append(tag)
    return tagset