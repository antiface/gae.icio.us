import webapp2, jinja2
from google.appengine.api import users, urlfetch, mail
from google.appengine.ext import ndb, deferred

def dtf(value, format='%d-%m-%Y %H:%M'):
  return value.strftime(format)

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = dtf


class staff(ndb.Model):
  version = ndb.StringProperty()
  data = ndb.DateTimeProperty(auto_now=True)


class Tags(ndb.Model):
  data = ndb.DateTimeProperty(auto_now=True)
  user = ndb.UserProperty()
  name = ndb.StringProperty()
  def bm_set(self):
    return Bookmarks.query(Bookmarks.tags == self.key).order(Bookmarks.data)


class Bookmarks(ndb.Model):
  data = ndb.DateTimeProperty(auto_now=True)
  user = ndb.UserProperty()
  url = ndb.StringProperty()
  title = ndb.StringProperty(default='Senza titolo')
  comment = ndb.TextProperty()
  tags = ndb.KeyProperty(kind=Tags,repeated=True)
  archived = ndb.BooleanProperty(default=False)
  

class BaseHandler(webapp2.RequestHandler):
  def utente(self):
    return users.get_current_user()

  def generate(self, template_name, template_values={}):
    user = users.get_current_user()
    if self.utente():
      bookmarklet = """
javascript:location.href=
'%s/submit?url='+encodeURIComponent(location.href)+
'&title='+encodeURIComponent(document.title)+
'&user='+'%s'+
'&comment='+document.getSelection().toString()
""" % (self.request.host_url, user.email())
      url = users.create_logout_url(self.request.uri)
      linktext = 'Logout'
      nick = user.email()
    else:
      bookmarklet = None
      url = users.create_login_url(self.request.uri)
      linktext = 'Login'
      nick = 'Welcome'
    values = {
      'brand': self.request.host,
      'bookmarklet': bookmarklet,
      'nick': nick,
      'url': url,
      'linktext': linktext,
      'user': user,
      'miniurl': miniurl(),
      'version': ndb.Key('staff', 'chromium_v').get().version,
      }
    values.update(template_values)
    template = jinja_environment.get_template(template_name)
    self.response.out.write(template.render(values))


class MainPage(BaseHandler):
  def get(self):
    if self.utente():
      bms = ndb.gql("SELECT * FROM Bookmarks WHERE user = :1 AND archived = FALSE ORDER BY data DESC", self.utente())
      self.generate('home.html', {'bms': bms})
    else:
      self.generate('hero.html', {})


class ArchivedPage(BaseHandler):
  def get(self):
    if self.utente():
      bms = ndb.gql("SELECT * FROM Bookmarks WHERE user = :1 AND archived = TRUE ORDER BY data DESC LIMIT 25", self.utente())
      self.generate('home.html', {'bms': bms})
    else:
      self.generate('hero.html', {})


class SearchPage(BaseHandler):
  def get(self):
    if self.utente():
      tag_name = self.request.get('tag')
      q = ndb.gql("SELECT * FROM Tags WHERE user = :1 AND name = :2 ORDER BY data DESC", self.utente(), tag_name)
      bms = q.get().bm_set()
      self.generate('home.html', {'bms': bms})
    else:
      self.generate('hero.html', {})


class Bookmark(webapp2.RequestHandler):
  def get(self):
    b = Bookmarks()
    b.url = self.request.get('url').encode('utf8')
    b.title = self.request.get('title').encode('utf8')
    b.comment = self.request.get('comment').encode('utf8')
    b.user = users.User(str(self.request.get('user')))
    b.put()
    deferred.defer(sendbm, b)
    self.redirect('/')


class Tag(webapp2.RequestHandler):
  def post(self):
    bm = Bookmarks.get_by_id(int(self.request.get('id')))
    tag_str = self.request.get('tag')
    if users.get_current_user() == bm.user:
      tag = ndb.gql("SELECT * FROM Tags WHERE user = :1 AND name = :2", users.get_current_user(), tag_str).get()
      if tag is None:
        newtag = Tags()
        newtag.name = tag_str
        newtag.user = users.get_current_user()
        newtag.put()
      else:
        newtag = tag
      bm.tags.append(newtag.key)
      bm.put()
    self.redirect(self.request.referer)
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.remove(tag.key)
      bm.put()
    self.redirect(self.request.referer)


class DeleteBM(webapp2.RequestHandler):
  def get(self):
    b = Bookmarks.get_by_id(int(self.request.get('id')))
    if users.get_current_user() == b.user:
      b.key.delete()
    self.redirect(self.request.referer)


class ArchiveBM(webapp2.RequestHandler):
  def get(self):
    b = Bookmarks.get_by_id(int(self.request.get('id')))
    if users.get_current_user() == b.user:
      if b.archived == False:
        b.archived = True
      else:
        b.archived = False
      b.put()
    self.redirect(self.request.referer)


class Tasks(webapp2.RequestHandler):
  def get(self):
    deferred.defer(version)

    
def miniurl():
  version = ndb.Key('staff', 'chromium_v').get().version
  return "http://commondatastorage.googleapis.com/chromium-browser-snapshots/Win/" + version + "/mini_installer.exe"

def version():
  url = "http://commondatastorage.googleapis.com/chromium-browser-snapshots/Win/LAST_CHANGE"
  chromium = ndb.Key('staff', 'chromium_v').get()
  result = urlfetch.fetch(url, deadline=1)
  if chromium is None:
    chromium = staff(id='chromium_v')
  chromium.version = result.content
  chromium.put()

def sendbm(b):
      message = mail.EmailMessage()
      message.sender = b.user.email()
      message.to = b.user.email()
      message.subject = '(Pbox) '+ b.title
      message.html = "%s (%s)<br>%s<br><br>%s" % (b.title, b.data, b.url, b.comment)
      message.send()


app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/admin/tasks', Tasks),
  ('/submit', Bookmark),
  ('/tag', Tag),
  ('/delete', DeleteBM),
  ('/archive', ArchiveBM),
  ('/archived', ArchivedPage),
  ('/search', SearchPage),
  ], debug=True)

def main():
  run_wsgi_app(app)