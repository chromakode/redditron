#!/usr/bin/env python

import sys
import re
import random
import bisect
import itertools
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

class TokenType:
    def is_match(cls, text): raise NotImplementedError
    def find_all(cls, text): raise NotImplementedError
    
class RegexTokenType(TokenType):
    def __init__(self, regex):
        self.regex = re.compile(regex)
    
    def is_match(self, text):
        return self.regex.match(text) is not None
    
    def find_all(self, text):
        return [(m.group(0), m.start()) for m in self.regex.finditer(text)]

class SpecialTokenType(TokenType):
    def __init__(self, **characters):
        self.characters = characters
        
    def __getitem__(self, key):
        return self.characters[key]
    
    def is_match(self, text):
        return text in self.characters.values()
    
    def find_all(self, text):
        return []
            
class Token:
    SpecialToken     = SpecialTokenType(start='\x02', end='\x03')
    WordToken        = RegexTokenType(r'(\w+)')
    PunctuationToken = RegexTokenType(r'([^\w\s%s]+)' % ''.join(SpecialToken.characters.values()))
    UnknownToken     = TokenType()

    types = [SpecialToken, WordToken, PunctuationToken]

    _joins = {(PunctuationToken,WordToken,'\'')   : '',
              (PunctuationToken,WordToken)        : ' ',
              (PunctuationToken,PunctuationToken) : '',
              (WordToken,WordToken)               : ' ',
              None                                : ''}
    
    class TokenClass(str):
        def __new__(self, text, token_type):
            return str.__new__(self, text)
        
        def __init__(self, value, token_type):
            self.token_type = token_type
    
    @classmethod
    def join(cls, tokens):
        output = list()
        
        tokens = [None] + list(tokens) + [None]
        for tokens in itertools.izip(tokens, tokens[1:]):
            types = []
            texts = []
            for token in tokens:
                if token:
                    types.append(token.token_type)
                    texts.append(str(token))
                else:
                    types.append(None)
                    texts.append(None)

            join_keys = (#(types[0],types[1],texts[0],texts[1]),
                         (types[0],types[1],texts[0]),
                         #(types[0],types[1],None,texts[1]),
                         (types[0],types[1]),
                         #(types[0]),
                         #(None,types[1])
                         )
            
            sep = cls._joins[None]
            for join_key in join_keys:
                if join_key in cls._joins:
                    sep = cls._joins[join_key]
                    break
            
            output.append(sep)
            if tokens[1]: output.append(tokens[1])
            
        return ''.join(output)
            
    @classmethod
    def tokenize(cls, text):
        '''Return tokens contained in text in order'''
        matches = []
        for token_type in cls.types:
            matches += token_type.find_all(text)
        
        tokens = [cls.new(m[0]) for m in sorted(matches, key=lambda m: m[1])]
        tokens.insert(0, cls.SpecialToken["start"])
        tokens.append(cls.SpecialToken["end"])
        
        return tokens
    
    @classmethod
    def new(cls, text):
        this_token_type = cls.UnknownToken
        for token_type in cls.types:
            if token_type.is_match(text):
                this_token_type = token_type
                break
        
        return cls.TokenClass(text, this_token_type)

class Chain(dict):
    def __init__(self, basis=None, N=1, mhash=crc32):
        if isinstance(basis, dict):
            self.update(basis)
        
        self.N = N
        self.mhash = mhash
       
    def train(self, text):
        tokens = Token.tokenize(text.lower())

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

    def generate(self, words=[Token.SpecialToken["start"]], maxlength=None):
        words = list(words)
        
        picked = None
        while picked != Token.SpecialToken["end"] and (len(words) < maxlength or maxlength is None):
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
            
            yield Token.new(picked)

            words.append(picked)
            
    def generate_text(self, words=[Token.SpecialToken["start"]], maxlength=None):
        return Token.join(self.generate(words, maxlength))