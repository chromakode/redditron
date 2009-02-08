#!/usr/bin/env python

import sys
import re
import random
import math
import bisect
from zlib import crc32

from tokenizer import Tokenizer, RegexTokenType, CharacterTokenType

def weighted_choice(weight_dict):
    accum = 0
    choices = []
    for weight in weight_dict.itervalues():
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

class ModifiedDict:
    def __init__(self, d, func):
        self.d = d
        self.func = func
        
    def __getitem__(self, key):
        return self.func(self.d[key])
        
    def __iter__(self):
        return iter(self.d)
    
    def keys(self):
        return self.d.keys()
    
    def iterkeys(self):
        return self.d.iterkeys()
    
    def iteritems(self):
        for k, v in self.d.iteritems():
            yield k, self.func(v)
        
    def itervalues(self):
        for v in self.d.itervalues():
            yield self.func(v)

def simple_english_tokenizer(tokenizer=None):
    if not tokenizer:
        tokenizer   = Tokenizer()
    
    word        = tokenizer.type['Word']        = RegexTokenType(r'(\w+\'\w+|\w+)', priority=0)
    punctuation = tokenizer.type['Punctuation'] = RegexTokenType(r'([^\w\s%s]+)', priority=1)

    tokenizer.joins = {
        (punctuation,word,'\'')   : '',
        (punctuation,word)        : ' ',
        (punctuation,punctuation) : '',
        (word,word)               : ' ',
        None                      : ''
    }
    
    return tokenizer

MarkovMarkerToken = CharacterTokenType(priority=-10, start='\x02', end='\x03')

class Chain(dict):
    def __init__(self, tokenizer=None, basis=None, N=1, mhash=crc32, debug=False):
        if tokenizer:
            self.tokenizer = tokenizer
        else:
            self.tokenizer = simple_english_tokenizer()
            
        self.tokenizer.type['MarkovMarker'] = MarkovMarkerToken
        
        if isinstance(basis, dict):
            self.update(basis)
        
        self.N = N
        self.mhash = mhash
        self.debug = debug
        
    def debug_msg(self, msg):
        if self.debug:
            print msg
            
    def debug_candidates(self, candidates):
        for token, weight in sorted(candidates.iteritems(), key=lambda (t,w):w, reverse=True):
            self.debug_msg("%s: %s" % (repr(token), weight))
       
    def train(self, text):
        tokens = self.tokenizer.tokenize(text.lower())
        tokens.insert(0, MarkovMarkerToken['start'])
        tokens.append(MarkovMarkerToken['end'])

        for x in range(len(tokens)):
            for y in range(1, min(self.N, x)+1):
                me = tokens[x]
                before = tokens[x-y:x]
                self.debug_msg("%d,%d: %s %s" % (x, y, before, repr(me)))
                if before: # there is nothing before the beginning
                    before_text = ''.join(before)
                    before_hash = self.mhash(before_text.encode('utf-8'))
                    
                    self.debug_msg("%s -> %s" % (repr(before_text), before_hash))
                    if before_hash in self:
                        self[before_hash][me] = self[before_hash].get(me, 0) + 1
                    else:
                        self[before_hash] = {me: 1}

    def generate(self, tokens=[MarkovMarkerToken['start']], N=None, maxlength=None):
        tokens = list(tokens)
        
        if N:
            N = min(N, self.N)
        else:
            N = self.N
        
        picked = None
        while picked != MarkovMarkerToken['end'] and (len(tokens) < maxlength or maxlength is None):
            # Truncate previous token list to the length of the max association distance (N)
            if len(tokens) > N:
                tokens = tokens[-N:]
                
            # The length of the longest string of past tokens used for association 
            max_seed_length = min(N, len(tokens))
            
            weights = list()
            for seed_length in range(1, max_seed_length+1):
                seed_text = ''.join(tokens[-seed_length:])
                seed_hash = self.mhash(seed_text.encode('utf-8'))
                if seed_hash in self:
                    weights.append(ModifiedDict(self[seed_hash], lambda x: seed_length*x))
                    
            candidates = merge_countlists(weights)
            
            if not candidates:
                raise ValueError('No candidate tokens available.')
                            
            self.debug_msg(tokens)
            self.debug_candidates(candidates)
            
            picked = self.tokenizer.token(weighted_choice(candidates))
            
            if picked.token_type is not MarkovMarkerToken:
                yield picked

            tokens.append(picked)
            
    def generate_text(self, text=MarkovMarkerToken['start'], N=None, maxlength=None):
        tokens = self.tokenizer.tokenize(text)
        return self.tokenizer.join(self.generate(tokens, N, maxlength))