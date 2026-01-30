#!usr/bin/env
# -*- coding: utf-8 -*-

from common_utils import dobj, create_folder
from jinja2 import Template
import codecs
import os.path
import shutil

from markupsafe import Markup

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

def copy_static(site_config):
    '''Дефолтный статический контент типа js и css и img берется из src/static
       и он может быть перезаписан кастомным контентом для конкретного сайта'''

    create_folder(site_config['static'])
    shutil.copytree(src=site_config['common_static'], dst=site_config['static'], dirs_exist_ok=True)
    shutil.copytree(src=site_config['custom_static'], dst=site_config['static'], dirs_exist_ok=True)


# с помощью этого метода можно вставлять куски html
def make_include_content_func(site_config):
    def include_content(name):
        path = os.path.join(site_config['content_static'], name)
        with open(path, encoding="utf-8") as f:
            return Markup(f.read())
    return include_content

