import urllib
import simplejson

def strip_kind(things, omit_kinds=[]):
    return [ thing["data"] for thing in things if thing["kind"] not in omit_kinds]
    
def flatten_comments(comments):
    for comment in comments:
        # Remove the "replies" key
        comment = comment.copy()
        replies = comment["replies"]
        del comment["replies"]
        
        # Visit
        yield comment
        
        # Traverse
        if replies is not None:
            for comment in flatten_comments(strip_kind(replies["data"]["children"], "more")):
                yield comment

def fetch_latest_comments():
    comment_listing = simplejson.load(urllib.urlopen("http://www.reddit.com/comments.json"))
    return strip_kind(comment_listing["data"]["children"])
    
def fetch_link_comments(link_id):
    comment_listing = simplejson.load(urllib.urlopen("http://www.reddit.com/comments/%s.json" % link_id))
    return strip_kind(comment_listing[1]["data"]["children"], "more")
