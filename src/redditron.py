from couchdb.client import Server, Database, ResourceConflict

from markov import Chain, simple_english_tokenizer
from tokenizer import Tokenizer, RegexTokenType
from utils import set_line
from lib.markdown import _Markdown as Markdown

import hashlib

def markdown_tokenizer(tokenizer=None):
    if not tokenizer:
        tokenizer = Tokenizer()
        
    simple_english_tokenizer(tokenizer)

    tokenizer.type['MarkdownAutoLink'] = RegexTokenType(Markdown.r_link, priority=-6)
    tokenizer.type['MarkdownLink'] = RegexTokenType(Markdown.r_DoAnchors2, priority=-6)
    tokenizer.type['MarkdownBold'] = RegexTokenType(Markdown.r_DoBold, priority=-5)
    tokenizer.type['MarkdownItalic'] = RegexTokenType(Markdown.r_DoItalics, priority=-4)
    
    # From markdown.py, but without the surrounding angle brackets
    tokenizer.type['Link'] = RegexTokenType(r"((https?|ftp):[^\'\">\s]+)", priority=-2)
    
    
    return tokenizer

def build_chain(db, max_comments=None):
    c = Chain(tokenizer=markdown_tokenizer(), N=10)
    
    comment_count = len(db)
    if max_comments:
        comment_count = min(comment_count, max_comments)
    
    for index, comment_id in enumerate(db):
        body = db[comment_id]['body']
        c.train(body)
        set_line('Loaded %s/%s comments...' % (index+1, comment_count))
        if max_comments and index+1 >= max_comments:
            break
        
    set_line('')
        
    return c

def main():
    couch_uri = 'http://localhost:5984/'
    db_name   = 'redditron-comments'
    
    server = Server(couch_uri)
    db = server[db_name]
    
    c = build_chain(db)
    outputs = []
    for i in range(0, 100):
        outputs.append(c.generate_text())
    
    print "\n---\n".join(outputs)

if __name__ == '__main__':
     main()
