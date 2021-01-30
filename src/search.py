#!usr/bin/env
# -*- coding: utf-8 -*-

from collections import defaultdict

import re

class Term:
    words_regex = re.compile('\w+')
    END = None
    
    @staticmethod
    def split(text):
        return Term.words_regex.findall(text.lower().replace('ё', 'е'))    
    
    
    
class Trie:

    class Node(dict):
        
        '''{char -> Node}'''
        def __init__(self):
            self.docs = set()
            
        def get_or_create(self, c):
            if c not in self:
                self[c] = Trie.Node()
            return self[c]
            
           
    def __init__(self):
        self.__root = Trie.Node()
       
    def add(self, doc_id, word):
        current = self.__root
        for c in word:
            current = current.get_or_create(c)
            current.docs.add(doc_id)
        current = current.get_or_create(Term.END)
        current.docs.add(doc_id)        
        
    def find(self, word, prefix=True):
        current = self.__root
        for c in word:
            current = current.get(c, None)
            if current is None:
                return set()
        if not prefix:
            current = current.get(Term.END, None)
            if current is None:
                return set()
        return current.docs


class SearchEngine:

    def __init__(self, person_snippets):
        self.trie = Trie()
        
        for person_uid, person in person_snippets.items():
            words = set(Term.split(str(person.name)))
            for word in words:
                self.trie.add(person_uid, word)
                
    def search_strict(self, text):
        words = set(Term.split(text))
        matched = None
        for word in words:
            found = self.trie.find(word, prefix=False)
            matched = matched & found if matched is not None else found
        return list(matched)
    
    def search(self, text):
        words = set(Term.split(text))
        hits = defaultdict(int)
        for word in words:
            docs = self.trie.find(word, prefix=True)
            for d in docs:
                hits[d] += 1

        return [x[0] for x in sorted(hits.items(), key=lambda x: x[1], reverse=True)] 
