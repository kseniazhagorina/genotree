#!usr/bin/env
# -*- coding: utf-8 -*-

from common_utils import dobj, create_folder
from jinja2 import Template
import codecs
import os.path

def generate_content(site_config):
    '''Пререндерим некоторый контент с помощью jinja2 в папку static/generated_content'''

    
    def empty_block():
        return dobj({'title': '', 'children': []})
        
    sources = [empty_block()]
    with codecs.open(os.path.join(site_config['content'], 'sources.txt'), 'r', 'utf-8') as input:
        for line in input:
            if line.strip() == '':
                sources.append(empty_block())
                continue
            if line.startswith(' '):
                sources[-1].children.append(line.strip())
            else:
                sources[-1].title = line.strip()
             
    template = Template(codecs.open(os.path.join(site_config['templates'], 'sources.html'), 'r', 'utf-8').read())
    create_folder(site_config['content_static'])
    with codecs.open(os.path.join(site_config['content_static'], 'sources.html'), 'w', 'utf-8') as output:
        output.write(template.render(content=sources))
                
