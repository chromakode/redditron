#!/usr/bin/env python

import sys
import re
import random
import bisect
from zlib import crc32

from tokenizer import Tokenizer, RegexTokenType, SpecialTokenType

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


SPECIAL_CHARACTERS = {'start':'\x02', 'end':'\x03'}

tokenizer = Tokenizer()
tokenizer.type['Special']     = SpecialTokenType(**SPECIAL_CHARACTERS)
tokenizer.type['Word']        = RegexTokenType(r'(\w+)')
tokenizer.type['Punctuation'] = RegexTokenType(r'([^\w\s%s]+)' % ''.join(SPECIAL_CHARACTERS.values()))

SpecialToken     = tokenizer.type['Special'] 
WordToken        = tokenizer.type['Word']
PunctuationToken = tokenizer.type['Punctuation']

tokenizer.joins = {
    (PunctuationToken,WordToken,'\'')   : '',
    (PunctuationToken,WordToken)        : ' ',
    (PunctuationToken,PunctuationToken) : '',
    (WordToken,WordToken)               : ' ',
    None                                : ''         
}

class Chain(dict):
    def __init__(self, basis=None, N=1, mhash=crc32):
        if isinstance(basis, dict):
            self.update(basis)
        
        self.N = N
        self.mhash = mhash
       
    def train(self, text):
        tokens = tokenizer.tokenize(text.lower())
        tokens.insert(0, SpecialToken['start'])
        tokens.append(SpecialToken['end'])

        for x in range(len(tokens)):
            for y in range(1, self.N+1):
                me = tokens[x]
                before = tokens[x-y:x]
                if before: # there is nothing before the beginning
                    before_str = ''.join(tokens[x-y:x]).encode('utf-8')
                    before_hash = self.mhash(before_str)
                    if before_hash in self:
                        self[before_hash][me] = self[before_hash].get(me, 0) + 1
                    else:
                        self[before_hash] = {me: 1}

    def generate(self, words=[SpecialToken['start']], maxlength=None):
        words = list(words)
        
        picked = None
        while picked != SpecialToken['end'] and (len(words) < maxlength or maxlength is None):
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
                picked = tokenizer.token(weighted_choice(candidates))
            else:
                raise ValueError('No candidate words available.')
            
            if picked.token_type is not SpecialToken:
                yield picked

            words.append(picked)
            
    def generate_text(self, words=[SpecialToken['start']], maxlength=None):
        return tokenizer.join(self.generate(words, maxlength))