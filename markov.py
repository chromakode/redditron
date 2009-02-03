#!/usr/bin/env python

import re
import random
import bisect
import sys
from zlib import crc32
from copy import copy

class Chain(dict): pass

class token(object):
    types = dict(punc = re.compile(r'[,!;:.]').match,
                 word = re.compile(r'[a-z-]+').match)
    def __init__(self,tok):
        self.tok = tok.lower()

    @property
    def type(self):
        for (t, fn) in self.types.iteritems():
            if fn(self.tok):
                return t

def weighted_choice(weight_dict):
    accum = 0
    choices = []
    for item, weight in weight_dict.iteritems():
        accum += weight
        choices.append(accum)
    
    rand = random.random() * accum
    index = bisect.bisect_right(choices, rand)

    return weight_dict.keys()[index]

def dict_merge(d1, d2, fn):
    ret = {}

    for d in d1, d2:
        for x,y in d.iteritems():
            if x in ret:
                ret[x] = fn(x, ret[x], y)
            else:
                ret[x] = y

    return ret

def sum_dicts(d1, d2):
    return dict_merge(d1, d2, lambda _key,x,y: x+y)

def merge_countlists(countlists):
    acc = dict()
    for x in countlists:
        acc = sum_dicts(x,acc)

    return acc

split_tokens = re.compile(r'(\s+|[a-z-]+|[,!;:.])')
whitespace   = re.compile(r'\s+|^$')
word         = re.compile(r'[a-z\'-]')
punctuation  = re.compile(r'[,!;:.]')
# chain =:= dict(key = dict(follower = count))
def update_chain(chain, text, N, mhash = crc32):
    tokens = []
    for x in split_tokens.split(text):
        x = x.lower()
        if x and not whitespace.match(x):
            tokens.append(x)

    for x in xrange(len(tokens)):
        for y in range(N):
            me = tokens[x]
            before = tokens[x-y:x]
            if before: # there is nothing before the beginning
                before = mhash(''.join(tokens[x-y:x]))
                if before in chain:
                    chain[before][me] = chain[before].get(me, 0) + 1
                else:
                    chain[before] = {me: 1}

    return chain

def make_text(chain, N, length, mhash=crc32, acc=[]):
    text = list(acc)

    for _x in xrange(length):
        if not text:
            text = [weighted_choice(chain[random.choice(chain.keys())])]

        if len(text) > N:
            text = text[-N:]

        seeds = [ text[x:]
                  for x in range(-1, -min(N,len(text))-1,-1) ] # huh?
        crcs  = [ mhash(''.join(seed))
                  for seed in seeds ]
        c_crcs= [ crc for crc in crcs if crc in chain ]
        weights = [ chain[crc] for crc in c_crcs ]
        candidates = merge_countlists(weights)

        if not candidates:
            # no candidates found for these tokens
            text = []
            continue

        picked = weighted_choice(candidates)

        yield picked

        text.append(picked)

def sentence_stream(stream, stdout):
    # so now we have a bunch of tokens. We can turn them into
    # sentences
    last_was_punc = True
    first         = True
    per_line = 15

    this_line = 0

    for x in stream:
        punc = punctuation.match(x)
        if not punc:
            stdout.write(' ')

        if last_was_punc:
            stdout.write(x[0].upper() + x[1:])
        else:
            stdout.write(x)

        last_was_punc = punc

        first = False

        this_line += 1

        if this_line > per_line:
            this_line = 0
            stdout.write('\n')


def main(N, length, howmany = None):
    lines = sys.stdin.readlines()
    
    chain = Chain()
    for line in lines:
        update_chain(chain, line, N)

    stream = make_text(chain, N, length)

    sentence_stream(stream, sys.stdout)

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) >= 2 else 5,
         int(sys.argv[2]) if len(sys.argv) >= 3 else 100,
         int(sys.argv[3]) if len(sys.argv) >= 4 else None)


    
        

