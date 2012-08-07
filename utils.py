from google.appengine.api import users, mail

def login_required(handler_method):
  def check_login(self):
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url(self.request.url))
    else:
      handler_method(self)
  return check_login


def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = bm.user.email()
  message.to = bm.user.email()
  message.subject = '(Pbox) '+ bm.title
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()