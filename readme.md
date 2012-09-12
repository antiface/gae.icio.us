How to install
---
- checkout the [repository](https://github.com/presveva/gae.icio.us/zipball/master)
- create a new app in [appengine](https://appengine.google.com/)
- change the 'app-id' in app.yaml
- [deploy](https://developers.google.com/appengine/docs/python/tools/uploadinganapp#Uploading_the_App) in google app engine

Goodies
---
- Tagging
    - Associate tags to the bookmark
    - Filter and refine the bookmarks by tags
- Content optimization
    - Images, Youtube and Vimeo video is incorporated as comment
    - Urls is sanitized 
    - Mail yourself (You can receive an email for each bookmark)
- Dropbox integration
    - If dropbox integration is active, each url that point to an image, mp3 or avi is uploaded in to your dropbox.
- Shared
    - The user can share a bookmark and other user can see it in "stream page"

How to post
---
- Bookmarklet
  - Drag and drop the bookmarklet in your bookmarks bar
  - Selected text and click on bookmarklet
  - if you select a text, this is "insert as comment"
- Post via email
  - From:  the email used in app-id
  - To:      post@app-id.appspotmail.com
  - Subject: the title of the post
  - Body:    the link of the post
- Feed subscription
  - Add your feed urls in Feeds page
  - the app creates a new bookmark for each new item in the feed
  - if MYS is active you will get new posts in your inbox