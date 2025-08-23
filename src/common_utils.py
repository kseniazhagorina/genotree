#!usr/bin/env
# -*- coding: utf-8 -*-

import os.path
import shutil
import codecs
import chardet
import random, string
from copy import copy

def opendet(filename):
    with open(filename, 'rb') as f:
        enc = chardet.detect(f.read())
    return codecs.open(filename, 'r', encoding=enc['encoding'])

def convert_to_utf8(filename):
    with opendet(filename) as input:
        data = input.read()
    with codecs.open(filename, 'w', 'utf-8') as output:
        output.write(data)

def create_folder(folder, empty=False):
    if empty and os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

def first_or_default(arr, predicate=None, default=None):
    for item in arr:
        if predicate is None or predicate(item):
            return item
    return default

def random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def normalize_path(path):
    if path is None:
        return None
    return '/'.join(path.split('\\'))

class dobj(dict):
    '''все что может быть сериализовано - в dict остальное в __dict__'''
    @staticmethod
    def convert(value):
        if isinstance(value, (list, tuple)):
            converted_value = [dobj.convert(x) for x in value]
            return tuple(converted_value) if isinstance(value, tuple) else converted_value
        if isinstance(value, dict) and not isinstance(value, dobj):
            return dobj(dict((k, dobj.convert(v)) for k,v in value.items()))
        return value

    @staticmethod
    def is_json(value):
        return value is None or isinstance(value, (str, int, float, bool, list, dict, tuple))

    def __init__(self, d=None):
        d = d or {}
        for key, value in d.items():
            self.__setattr__(key, value)

    def __getattr__(self, name):
        return self[name] if name in self else self.__dict__[name]

    def __setattr__(self, name, value):
        converted = dobj.convert(value)
        self.__delattr__(name)
        if dobj.is_json(value):
            self[name] = converted
        else:
            self.__dict__[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        elif name in self.__dict__:
            del self.__dict__[name]


def choose_by_sex(sex, male, female, unknown=None):
    if sex == 'M':
        return male
    if sex == 'F':
        return female
    return unknown if unknown is not None else male










