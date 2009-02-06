#!/usr/bin/env python

import re
import random
import bisect
import sys
from zlib import crc32

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
    
def has_method(instance, name):
  return hasattr(instance, name) and callable(getattr(instance, name))

START_TOKEN  = '\x02'
END_TOKEN    = '\x03'
SPECIAL_TOKENS = [START_TOKEN, END_TOKEN]

class Token(str):
    types = {'special':     lambda x: x in SPECIAL_TOKENS,
             'punctuation': re.compile(r'([^\w\s%s]+)' % ''.join(SPECIAL_TOKENS)),
             'word':        re.compile(r'(\w+)')}

    @property
    def token_name(self):
        for (name, test) in self.types.iteritems():
            re_matches = lambda t: has_method(t, 'match') and t.match(self)
            call_matches = lambda t: callable(t) and t(self)
            if re_matches(test) or call_matches(test):
                return name

# chain =:= dict(key = dict(follower = count))
class Chain(dict):
    def __init__(self, basis=None, N=2, mhash=crc32):
        if isinstance(basis, dict):
            self.update(basis)
        
        self.N = N
        self.mhash = mhash
       
    def train(self, text):
        text = text.lower()
        
        # Find all tokens in text
        matches = []
        for (name, test) in Token.types.iteritems():
            if has_method(test, 'finditer'):
                matches += test.finditer(text)
        
        start_pos = lambda m: m.start()
        tokens = [m.group(0) for m in sorted(matches, key=start_pos)]
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
                seed_text = ''.join(words[-seed_length:])
                seed_hash = self.mhash(seed_text)
                if seed_hash in self:
                    weights.append(self[seed_hash])
                    
            candidates = merge_countlists(weights)
            
            if candidates:            
                picked = weighted_choice(candidates)
            else:
                raise ValueError('No candidate words available.')
            
            yield Token(picked)

            words.append(picked)
            
   
