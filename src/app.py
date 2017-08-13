#!usr/bin/env
# -*- coding: utf-8 -*-

import traceback
from app_utils import get_tree, get_tree_map, get_person_snippets, get_files_dict
from gedcom import GedcomReader
from upload import load_package, select_tree_img_files
from privacy import Privacy, PrivacyMode
import oauth_api as oauth
import json

from flask import Flask, render_template, request, url_for
app = Flask(__name__)
app.debug = True

oauth.API = None
def OAuth():   
    if oauth.API is None:
        config = json.loads(open('data/config/oauth.config').read())
        oauth.API = oauth.Api(url_for, config)
    return oauth.API

DEFAULT_TREE = ''
TREE_NAMES = {
    DEFAULT_TREE: 'Общее',
    'zhagoriny': 'Жагорины',
    'motyrevy': 'Мотыревы',
    'cherepanovy': 'Черепановы',
    'farenuyk': 'Фаренюки'
}    

class Data:
    '''статические данные о персонах/загруженных деревьях не зависящие
       от текущего пользователя, запрошенной страницы, отображаемой персоны'''
    class Tree:
        def __init__(self, uid, img, map):
            self.uid = uid
            self.name = TREE_NAMES.get(uid) or uid
            self.img = img
            self.map = map
            
    def __init__(self):
        self.load_error = 'Data is unloaded.'
    
    def is_valid(self):
        return self.load_error is None
        
    def load(self, archive=None):
        try:
            self.load_error = 'Data is updated right now'          
            if archive is not None:
                load_package(archive, 'src/static/tree', 'data/tree')
            
            self.files_dir = '/static/tree/files'
            self.files = get_files_dict('data/tree/files.tsv')
            
            self.gedcom = GedcomReader().read_gedcom('data/tree/tree.ged')
            self.persons_snippets = get_person_snippets(self.gedcom, self.files)
            
            # Загружаем деревья - 
            tree_uids, pngs, xmls = select_tree_img_files('src/static/tree')
            if len(tree_uids) == 0:
                raise Exception('No files *_tree_img.png in /static/tree directory')
            self.trees = {}
            for tree_uid, png, xml in zip(tree_uids, pngs, xmls):
                tree_uid = tree_uid or DEFAULT_TREE
                self.trees[tree_uid] = Data.Tree(tree_uid, '/static/tree/'+png, get_tree_map('data/tree/'+xml))
            self.default_tree_name = DEFAULT_TREE if DEFAULT_TREE in self.trees else tree_uids[0]  
            self.load_error = None
        except:
            self.load_error = traceback.format_exc()

class Context:
    '''Данные о том, какой пользователь запрашивает страницу, его настройки приватности
       Какая страница была запрошена, какое дерево сейчас отображается
    '''
    def __init__(self, data, requested_tree=None):
        self.data = data
        self.tree = data.trees.get(requested_tree) #may be None
    
    class PersonContext:
        '''контекст отображения персоны в дереве'''
        def __init__(self, person_uid, data, tree=None):
            self.files_dir = data.files_dir
            self.person_uid = person_uid
            # все персоны публичны, доступ для пользователей только public
            self.privacy = Privacy(privacy=PrivacyMode.PUBLIC, access=PrivacyMode.PUBLIC)
            # в каких деревьях за исключением текущего присутствует данная персона
            self.tree = tree
            curr_tree_uid = self.tree.uid if self.tree else None
            self.trees = [tree for tree in data.trees.values() if person_uid in tree.map.nodes and tree.uid != curr_tree_uid]
            
    def person_context(self, person_uid):
        return Context.PersonContext(person_uid, self.data, self.tree)         
        
data = Data()        
data.load()

def check_data_is_valid(func):
    def wrapper(*args, **kwargs):
        if not data.is_valid():
            return 'Что-то пошло не так... Попробуйте зайти на сайт позже.\n\n'+data.load_error
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__    
    return wrapper 

        
@app.route('/<tree_name>')
@check_data_is_valid
def tree(tree_name):
    tree_name = tree_name or data.default_tree_name
    if tree_name in data.trees:
        return render_template('tree.html', context=Context(data, tree_name))
    return 'Дерево \'{0}\' не найдено...'.format(tree_name)
          

@app.route('/')
def default_tree():
    return tree(None)
    
@app.route('/person/<person_uid>')
@check_data_is_valid
def biography(person_uid):
    if person_uid in data.persons_snippets:
        person_snippet = data.persons_snippets[person_uid]
        person_context = Context(data).person_context(person_uid)
        return render_template('biography.html', person=person_snippet, context=person_context)
    return 'Персона \'{0}\' не найдена...'.format(person_uid)

@app.route('/admin/load/<archive>')
def load(archive):
    archive = 'upload/{0}.zip'.format(archive)
    data.load(archive)
    return 'Success!' if data.is_valid() else 'Fail!\n' + data.load_error

@app.route('/index')
def index():
    return render_template('index.html', api=OAuth())
    
@app.route('/login/auth/<service>')
def auth(service):
    code = request.args['code']
    token = OAuth().get(service).auth.get_access_token(code)
    return 'auth: {}\ntoken: {}'.format(request.args, token)

@app.route('/login/unauth/<service>')
def unauth(service):
    return 'unauth: {}'.format(request.args)
    
if __name__ == "__main__":
    app.run()
        
    