from couchdb.client import Server, Database, ResourceConflict

from markov import Chain
from utils import set_line

def build_chain(db):
    c = Chain(N=20)
    
    comment_count = len(db)
    for index, comment_id in enumerate(db):
        body = db[comment_id]['body']
        c.train(body)
        set_line('Loaded %s/%s comments...' % (index+1, comment_count))
    set_line('')
        
    return c

def main():
    couch_uri = 'http://localhost:5984/'
    db_name   = 'redditron-comments'
    
    server = Server(couch_uri)
    db = server[db_name]
    
    c = build_chain(db)
    for i in range(0, 100):
        print "---"
        print c.generate_text()
        print "---"

if __name__ == '__main__':
     main()
