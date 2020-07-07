from flask import send_from_directory

from like import app

# TODO:
# add routes for loading templates
"""
pages:
- feed (shows posts from people you follow)
- user's page (shows posts from specific user)
- new post (form for making a new post) (thought, should I have a date column for post? then access posts like /user/1/posts/2020-05-25)
"""

@app.route('/')
def index():
    return send_from_directory('static/build', 'index.html')
