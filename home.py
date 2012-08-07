import webapp2, jinja2, os, core
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Tags, Bookmarks

def dtf(value, format='%d-%m-%Y %H:%M'):
  return value.strftime(format)

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader('templates'))
jinja_environment.filters['dtf'] = dtf


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


debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/search', SearchPage),
  ('/refine', RefinePage),
  ('/notag', NotagPage),
  ('/edit', EditPage),  
  ('/archived', ArchivedPage),
  ('/submit', core.AddBM),
  ('/delete', core.DelBM),
  ('/addtag', core.AddTag),
  ('/deltag', core.DeleteTag),
  ('/removetag', core.RemoveTag),
  ('/asstag', core.AssignTag),
  ('/archive', core.ArchiveBM),
  ], debug=debug)

def main():
  run_wsgi_app(app)