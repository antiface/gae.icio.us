#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from google.appengine.api import users, mail, app_identity

def login_required(handler_method):
  def check_login(self):
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url(self.request.url))
    else:
      handler_method(self)
  return check_login

# def post_bm(bmk, url, title, comment, user):
#   bm = bmk.get()
#   bm.url = url
#   bm.title = title
#   bm.comment = comment
#   bm.user = user
#   bm.put()
#   deferred.defer(sendbm, bm)

def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = bm.user.email()
  message.to = bm.user.email()
  message.subject =  "(%s) %s" % (app_identity.get_application_id(), bm.title)
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()


