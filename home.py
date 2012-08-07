import webapp2, jinja2, os, urlparse
from google.appengine.api import users, mail
from google.appengine.ext import ndb, deferred

def dtf(value, format='%d-%m-%Y %H:%M'):
  return value.strftime(format)

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = dtf


class Tags(ndb.Model):
  data  = ndb.DateTimeProperty(auto_now=True)
  user  = ndb.UserProperty(required=True)
  name  = ndb.StringProperty()
  count = ndb.IntegerProperty(default=0)
  def bm_set(self):
    return ndb.gql("""SELECT * FROM Bookmarks
      WHERE tags = :1 ORDER BY data DESC""", self.key)
  def refine_set(self):
    q = ndb.gql("""SELECT * FROM Bookmarks
      WHERE tags = :1 AND user = :2""", self.key, self.user)
    other = []
    for bm in q:
      for tag in bm.tags:
        if not tag in other:
          other.append(tag)
    other.remove(self.key)
    return other

class Bookmarks(ndb.Model):
  data = ndb.DateTimeProperty(auto_now=True)
  user = ndb.UserProperty()
  url = ndb.StringProperty()
  title = ndb.StringProperty()
  comment = ndb.TextProperty()
  tags = ndb.KeyProperty(kind=Tags,repeated=True)
  archived = ndb.BooleanProperty(default=False)
  have_tags = ndb.ComputedProperty(lambda self: bool(self.tags))
  def other_tags(self):
    q = ndb.gql("SELECT __key__ FROM Tags WHERE user = :1", self.user)
    all_user_tags = [tagk for tagk in q]
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
      return None


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
      url = users.create_logout_url("/")
      linktext = 'Logout'
      nick = user.email()
    else:
      bookmarklet = '%s' % self.request.host_url
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
      }
    values.update(template_values)
    template = jinja_environment.get_template(template_name)
    self.response.out.write(template.render(values))


class MainPage(BaseHandler):
  def get(self):
    if self.utente():
      tag_list = ndb.gql("""SELECT * FROM Tags
        WHERE user = :1 ORDER BY count DESC""", self.utente())
      bms = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND archived = FALSE 
        ORDER BY data DESC""", self.utente())
      self.generate('home.html', {'bms': bms,
                                  'tag_list': tag_list 
                                  })
    else:
      self.generate('hero.html', {})


class ArchivedPage(BaseHandler):
  def get(self):
    if self.utente():
      tag_list = ndb.gql("""SELECT * FROM Tags
        WHERE user = :1 ORDER BY count DESC""", self.utente())
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND archived = TRUE 
        ORDER BY data DESC LIMIT 25""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': tag_list
                                  })
    else:
      self.generate('hero.html', {})


class NotagPage(BaseHandler):
  def get(self):
    if self.utente():
      tag_list = ndb.gql("""SELECT * FROM Tags
        WHERE user = :1 ORDER BY count DESC""", self.utente())
      bms = ndb.gql("""SELECT * FROM Bookmarks
        WHERE user = :1 AND have_tags = False
        ORDER BY data DESC""", self.utente())
      self.generate('home.html', {'bms'     : bms, 
                                  'tag_list': tag_list
                                  })
    else:
      self.generate('hero.html', {})


class SearchPage(BaseHandler):
  def get(self):
    if users.get_current_user():
      tag_name = self.request.get('tag')
      q = ndb.gql("""SELECT * FROM Tags 
        WHERE user = :1 AND name = :2 
        ORDER BY data DESC""", self.utente(), tag_name)
      if q.get().count != 0:
        self.generate('home.html', {'tag_obj':  q.get(),
                                    'bms':      q.get().bm_set(),
                                    'tag_list': q.get().refine_set()
                                    })
      else:
        self.redirect('/')
    else:
      self.generate('hero.html', {})


class RefinePage(BaseHandler):
  def get(self):
    if users.get_current_user():
      tag_name = self.request.get('tag')
      refine = self.request.get('refine')
      tag1 = ndb.gql("""SELECT __key__ FROM Tags 
        WHERE user = :1 AND name = :2""", self.utente(), tag_name).get()
      tag2 = ndb.gql("""SELECT __key__ FROM Tags 
        WHERE user = :1 AND name = :2""", self.utente(), refine).get()
      bms = ndb.gql("""SELECT * FROM Bookmarks 
        WHERE user = :1 AND tags = :2 AND tags = :3
        ORDER BY data DESC""", self.utente(), tag1, tag2)
      self.generate('home.html', {'bms': bms, 'tag_obj': None})
    else:
      self.generate('hero.html', {})


class EditPage(BaseHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:      
      self.generate('edit.html', {'bm': bm})
    else:
      self.redirect('/')
  def post(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      bm.url = self.request.get('url').encode('utf8')
      bm.title = self.request.get('title').encode('utf8')
      bm.comment = self.request.get('comment').encode('utf8')
      bm.put()
    self.redirect('/')


class AddBM(webapp2.RequestHandler):
  def get(self):
    if users.get_current_user():
      bm = Bookmarks()
      # bm.url = self.request.get('url').encode('utf8').split('?')[0]
      bm.url = self.request.get('url').encode('utf8')
      bm.title = self.request.get('title').encode('utf8')
      bm.comment = self.request.get('comment').encode('utf8')
      bm.user = users.User(str(self.request.get('user')))
      bm.put()
      deferred.defer(sendbm, bm)
      self.redirect('/edit?bm=%s' % bm.key.id())
    else:
      self.generate('hero.html', {})


class DelBM(webapp2.RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      for tag in bm.tags:
        t = tag.get()
        t.count -= 1
        t.put()        
      bm.key.delete()
    self.redirect(self.request.referer)


class ArchiveBM(webapp2.RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    if users.get_current_user() == bm.user:
      if bm.archived == False:
        bm.archived = True
      else:
        bm.archived = False
      bm.put()
    self.redirect(self.request.referer)


class AddTag(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    tag_str = self.request.get('tag')
    if user:
      tag = ndb.gql("""SELECT * FROM Tags
      WHERE user = :1 AND name = :2""", user, tag_str).get()
      if tag is None:
        newtag = Tags()
        newtag.name = tag_str
        newtag.user = user        
      else:
        newtag = tag
      newtag.put()
    self.redirect(self.request.referer)

class AssignTag(webapp2.RequestHandler):
  def get(self):
    bm  = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.append(tag.key)
      bm.put()
      tag.count += 1
      tag.put()
    self.redirect(self.request.referer)

class RemoveTag(webapp2.RequestHandler):
  def get(self):
    bm = Bookmarks.get_by_id(int(self.request.get('bm')))
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == bm.user:
      bm.tags.remove(tag.key)
      bm.put()
      tag.count -= 1
      tag.put()
    self.redirect(self.request.referer)

class DeleteTag(webapp2.RequestHandler):
  def get(self):
    tag = Tags.get_by_id(int(self.request.get('tag')))
    if users.get_current_user() == tag.user:
      tag.key.delete()
    self.redirect(self.request.referer)

def sendbm(bm):
  message = mail.EmailMessage()
  message.sender = bm.user.email()
  message.to = bm.user.email()
  message.subject = '(Pbox) '+ bm.title
  message.html = """
%s (%s)<br>%s<br><br>%s
""" % (bm.title, bm.data, bm.url, bm.comment)
  message.send()


debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/submit', AddBM),
  ('/delete', DelBM),
  ('/addtag', AddTag),
  ('/deltag', DeleteTag),
  ('/removetag', RemoveTag),
  ('/asstag', AssignTag),
  ('/archive', ArchiveBM),
  ('/archived', ArchivedPage),
  ('/search', SearchPage),
  ('/refine', RefinePage),
  ('/notag', NotagPage),
  ('/edit', EditPage),
  ], debug=debug)

def main():
  run_wsgi_app(app)