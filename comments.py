import urllib
import simplejson

def fetch_latest_comments():
  comment_listing = simplejson.load(urllib.urlopen("http://www.reddit.com/comments.json"))
  return [ entry["data"] for entry in comment_listing["data"]["children"] ]
