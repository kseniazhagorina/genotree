#!usr/bin/env
# -*- coding: utf-8 -*-

from common_utils import dobj
from jinja2 import Template
import codecs

def generate_content():
    '''Пререндерим некоторый контент с помощью jinja2 в папку static/generated_content'''
    def empty_block():
        return dobj({'title': '', 'children': []})
        
    sources = [empty_block()]
    with codecs.open('src/content/sources.txt', 'r', 'utf-8') as input:
        for line in input:
            if line.strip() == '':
                sources.append(empty_block())
                continue
            if line.startswith(' '):
                sources[-1].children.append(line.strip())
            else:
                sources[-1].title = line.strip()
             
    template = Template(codecs.open('src/templates/sources.html', 'r', 'utf-8').read())
    with codecs.open('src/static/content/sources.html', 'w', 'utf-8') as output:
        output.write(template.render(content=sources))
                