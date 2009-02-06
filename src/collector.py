# A simple script to periodically scrape comments from reddit and stash them in a couchdb.

import sys
import time

from couchdb.client import Server, Database, ResourceConflict

from comment import fetch_latest_comments, fetch_link_comments, flatten_comments
from utils import set_line

def store_comments(db, new_comments):
    comments = []
        
    for comment in new_comments:
        if comment['id'] in db:
            # Update comment data
            new_comment = comment
            comment = db[new_comment['id']]
            comment.update(new_comment)
        else:
            comment['_id'] = comment['id']
            
        del comment['id'] # Remove old id key
        comments.append(comment)
    
    return db.update(comments)

def collect_comments(db, new_comments):
    count = 0;
    for doc in store_comments(db, new_comments):
        count += 1;
        
    print 'Collected %s comments.' % count

def poll_collect(db, seconds):
    while True:
        collect_comments(db, fetch_latest_comments())
        
        for remaining in range(seconds, 0, -1):
            set_line('Requesting comments again in %s seconds...' % remaining)
            time.sleep(1)
        set_line('')

def get_db(server, db_name):
    try:
        db = server.create(db_name)
    except ResourceConflict:
        db = server[db_name]
        
    return db

def main():
    couch_uri = 'http://localhost:5984/'
    db_name   = 'redditron-comments'
    
    server = Server(couch_uri)
    db = get_db(server, db_name)
    
    if (len(sys.argv) == 1):
        poll_collect(db, 4*60)
    else:
        collect_comments(db, flatten_comments(fetch_link_comments(sys.argv[1])))

if __name__ == '__main__':
     main()
