import re

from utils import has_method, iterate_edges

class Token(unicode):
    def __new__(self, text, token_type):
        return unicode.__new__(self, text)
    
    def __init__(self, value, token_type):
        self.token_type = token_type

class TokenType(object):
    def is_match(self, text): raise NotImplementedError
    def find_all(self, text): raise NotImplementedError
    
class DummyTokenType(TokenType):
    def is_match(self, text):
        return False
    
    def find_all(self, text):
        return []
    
class RegexTokenType(TokenType):
    def __init__(self, regex):
        self.regex = re.compile(regex)
    
    def is_match(self, text):
        return self.regex.match(text) is not None
    
    def find_all(self, text):
        return [(Token(m.group(0),self), m.start())
                for m in self.regex.finditer(text)]

class SpecialTokenType(TokenType):
    def __init__(self, **characters):
        self.characters = characters
        
    def __getitem__(self, key):
        return self.characters[key]
    
    def is_match(self, text):
        return text in self.characters.values()
    
    def find_all(self, text):
        return []

class Tokenizer(object):
    def __init__(self, types={}, joins={}):
        self.type = types
        self.type['Unknown'] = DummyTokenType()
        
        self.joins = joins
    
    def __getattr__(self, name):
        if name in self.type:
            return self.type[name]
    
    def token(self, text):
        '''Convert a single token string into a Token'''
        this_token_type = self.UnknownToken
        for token_type in self.type.itervalues():
            if token_type.is_match(text):
                this_token_type = token_type
                break
        
        return Token(text, this_token_type)
    
    def tokenize(self, text):
        '''Return tokens contained in text in order'''
        token_matches = []
        for token_type in self.type.itervalues():
            token_matches += token_type.find_all(text)
        
        tokens = [m[0] for m in sorted(token_matches, key=lambda m: m[1])]
        
        return tokens
    
    def _join_keys(self, type1, type2, text1, text2):
        yield (type1,type2,text1,text2)
        yield (type1,type2,text1)
        yield (type1,type2,None,text2)
        yield (type1,type2)
        yield (type1)
        yield (None,type2)
            
    def join(self, tokens):
        output = list()
        
        tokendata = ((token,token.token_type,str(token))
                     for token in list(tokens))
        
        for (token1,type1,text1), (token2,type2,text2) in iterate_edges(tokendata,(None,None,None)):
            sep = self.joins[None]
            for join_key in self._join_keys(type1, type2, text1, text2):
                if join_key in self.joins:
                    sep = self.joins[join_key]
                    break
            
            output.append(sep)
            if text2: output.append(token2)
            
        return ''.join(output)