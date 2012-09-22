#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import jinja2
from google.appengine.api import mail, app_identity, urlfetch
from google.appengine.ext import deferred
from models import Bookmarks
from parser import main_parser


def dtf(value, format='%d/%m/%Y - %H:%M UTC'):
    return value.strftime(format)

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(['templates', 'partials']))
jinja_environment.filters['dtf'] = dtf


def pop_feed(feedk): 
    from libs.feedparser import parse
    feed = feedk.get()
    f = urlfetch.fetch(url="%s" % feed.feed, deadline=60)
    p = parse(f.content)
    e = 0 
    try:
        d = p['items'][e]
        while feed.url != d['link'] and e < 15:
            deferred.defer(new_bm, d, feedk, _target="worker", _queue="importer")
            e += 1 
            d = p['items'][e]
    except IndexError:
        pass
    s = p['items'][0]
    feed.url = s['link']
    feed.put()

def new_bm(d, feedk):
    feed = feedk.get()
    bm = Bookmarks()
    bm.feed = feed.key
    bm.user = feed.user
    bm.original = d['link']
    bm.title = d['title']
    try:
        bm.comment = d['description']
    except KeyError:
        bm.comment = 'no comment'
    bm.tags = feed.tags
    bm.put()
    deferred.defer(main_parser, bm.key, _target="worker", _queue="parser")



def daily_digest(user):
    import datetime, time
    timestamp = time.time() - 87000
    period = datetime.datetime.fromtimestamp(timestamp)

    bmq = Bookmarks.query(Bookmarks.user == user)
    bmq = bmq.filter(Bookmarks.trashed == False)
    bmq = bmq.filter(Bookmarks.create > period)
    bmq = bmq.order(-Bookmarks.create)
    t = datetime.datetime.fromtimestamp(time.time()) 
    title = '(%s) Daily digest for your activity: %s' % (app_identity.get_application_id(), dtf(t))
    template = jinja_environment.get_template('digest.html') 
    values = {'bmq': bmq, 'title': title} 
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, user.email(), html, title, _target="worker", _queue="emails")


def feed_digest(feedk):
    import datetime, time
    timestamp = time.time() - 87000
    period = datetime.datetime.fromtimestamp(timestamp)
    feed = feedk.get()
    bmq = Bookmarks.query(Bookmarks.user == feed.user)
    bmq = bmq.filter(Bookmarks.feed == feed.key)
    bmq = bmq.filter(Bookmarks.trashed == False)
    bmq = bmq.filter(Bookmarks.create > period)
    bmq = bmq.order(-Bookmarks.create)
    title = '(%s) Daily digest for %s' % (app_identity.get_application_id(), feed.blog)
    template = jinja_environment.get_template('digest.html') 
    values = {'bmq': bmq, 'title': title} 
    html = template.render(values)
    if bmq.get():
        deferred.defer(send_digest, feed.user.email(), html, title, _target="worker", _queue="emails")


def send_bm(bmk): 
    bm = bmk.get()
    message = mail.EmailMessage()
    message.sender = 'bm@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = bm.user.email()
    message.subject = "(%s) %s" % (app_identity.get_application_id(), bm.title)
    message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, dtf(bm.data), bm.url, bm.comment)
    message.send()

def send_digest(email, html, title):
    message = mail.EmailMessage()
    message.sender = 'bm@' + "%s" % app_identity.get_application_id() + '.appspotmail.com'
    message.to = email
    message.subject = title
    message.html = html
    message.send()

def tag_set(bmq):
    tagset = []
    for bm in bmq:
        for tag in bm.tags:
            if not tag in tagset:
                tagset.append(tag)
    return tagset