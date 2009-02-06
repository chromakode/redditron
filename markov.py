#!/usr/bin/env python

import re
import random
import bisect
import sys
from zlib import crc32

START_TOKEN  = '\x02'
END_TOKEN    = '\x03'
token_re     = re.compile(r'\w+|[^\w\s]')
punctuation  = re.compile(r'[,!;:.]')

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

# chain =:= dict(key = dict(follower = count))
class Chain(dict):
    def __init__(self, basis=None, N=2, mhash=crc32):
        if isinstance(basis, dict):
            self.update(basis)
        
        self.N = N
        self.mhash = mhash
       
    def train(self, text):
        tokens = token_re.findall(text.lower())
        tokens.insert(0, START_TOKEN)
        tokens.append(END_TOKEN)

        for x in range(len(tokens)):
            for y in range(1, self.N+1):
                me = tokens[x]
                before = tokens[x-y:x]
                if before: # there is nothing before the beginning
                    before_hash = self.mhash(''.join(tokens[x-y:x]))
                    if before_hash in self:
                        self[before_hash][me] = self[before_hash].get(me, 0) + 1
                    else:
                        self[before_hash] = {me: 1}

    def generate(self, words=[START_TOKEN], maxlength=None):
        words = list(words)
        
        picked = None
        while picked != END_TOKEN and (len(words) < maxlength or maxlength is None):
            # Truncate previous word list to the length of the max association distance (N)
            if len(words) > self.N:
                words = words[-self.N:]
                
            # The length of the longest string of past words used for association 
            max_seed_length = min(self.N, len(words))

            weights = list()
            for seed_length in range(1, max_seed_length+1):
                seed_text = "".join(words[-seed_length:])
                seed_hash = self.mhash(seed_text)
                if seed_hash in self:
                    weights.append(self[seed_hash])
                    
            candidates = merge_countlists(weights)
            
            if candidates:            
                picked = weighted_choice(candidates)
            else:
                raise ValueError("No candidate words available.")
            
            yield picked

            words.append(picked)
            
class Token(object):
    types = dict(punc = re.compile(r'[,!;:.]').match,
                 word = re.compile(r'[a-z-]+').match)
    def __init__(self, tok):
        self.tok = tok.lower()

    @property
    def type(self):
        for (t, fn) in self.types.iteritems():
            if fn(self.tok):
                return t

