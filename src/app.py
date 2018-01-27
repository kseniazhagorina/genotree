#!usr/bin/env
# -*- coding: utf-8 -*-

import traceback
from app_utils import get_tree, get_tree_map, get_person_snippets, get_person_owners, get_files_dict, random_string
from gedcom import GedcomReader
from upload import load_package, select_tree_img_files
from privacy import Privacy, PrivacyMode
from session import Session
from db_api import create_db, UserAccessManager, UserSessionManager
import oauth_api as oauth
import json
import threading

from flask import Flask, render_template, request, url_for, redirect, session
app = Flask(__name__)
app.debug = True
app.secret_key = open('data/config/app.secret.txt').read().strip()

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

# pythonanywhere не поддерживает threading
def async(f):
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target = f, args = args, kwargs = kwargs)
        thr.start()
    return wrapper

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
            self.load_error = 'Данные сайта обновляются прямо сейчас'          
            if archive is not None:
                load_package(archive, 'src/static/tree', 'data/tree')
            
            self.files_dir = '/static/tree/files'
            self.files = get_files_dict('data/tree/files.tsv')
            
            self.gedcom = GedcomReader().read_gedcom('data/tree/tree.ged')
            self.persons_snippets = get_person_snippets(self.gedcom, self.files)
            self.persons_owners = get_person_owners(self.persons_snippets)
            
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
    
    @async
    def async_load(self, archive=None):        
        self.load(archive)

data = Data()        
data.load()

db = create_db('data/db/tree.db')
access_manager = UserAccessManager(db, data)
session_manager = UserSessionManager(db)
        
class Context:
    '''Данные о том, какой пользователь запрашивает страницу, его настройки приватности
       Какая страница была запрошена, какое дерево сейчас отображается
       user: Session пользователя
    '''
    def __init__(self, data, user=None, requested_tree=None):
        self.data = data
        self.tree = data.trees.get(requested_tree) #may be None
        self.user = user
        self.access = access_manager.get(self.user.all_logins() if user else [])
        
    class PersonContext:
        '''контекст отображения персоны в дереве'''
        def __init__(self, person_uid, context):
            self.files_dir = context.data.files_dir
            self.person_uid = person_uid
            # все персоны публичны, события публичны только для живых, 
            # пользователи имеют доступ public или protected в зависимости от выданных прав
            person = context.data.persons_snippets[person_uid]
            self.privacy = Privacy(privacy=PrivacyMode.PUBLIC,
                                   events_privacy=Privacy.is_events_protected(person),
                                   access=context.access.get(person_uid))
            # в каких деревьях за исключением текущего присутствует данная персона
            self.tree = context.tree
            curr_tree_uid = self.tree.uid if self.tree else None
            self.trees = [tree for tree in context.data.trees.values() if person_uid in tree.map.nodes and tree.uid != curr_tree_uid]
            
    def person_context(self, person_uid):
        return Context.PersonContext(person_uid, self)         


def check_data_is_valid(func):
    def wrapper(*args, **kwargs):
        if not data.is_valid():
            return 'Что-то пошло не так... Попробуйте зайти на сайт позже.\n\n'+data.load_error
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__    
    return wrapper
    
def get_user(func):
    def wrapper(*args, **kwargs):
        user = None
        if 'suid' in session:
            session_id, ts = session.get('suid')
            user = session_manager.get(session_id, ts)
            if user:
                session['suid'] = (user.id, user.ts)
            else:
                del session['suid']
        kwargs['user'] = user
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper    
        
@app.route('/<tree_name>')
@check_data_is_valid
@get_user
def tree(tree_name, user):
    tree_name = tree_name or data.default_tree_name
    if tree_name in data.trees:
        return render_template('tree.html', context=Context(data, user=user, requested_tree=tree_name))
    return 'Дерево \'{0}\' не найдено...'.format(tree_name)
          

@app.route('/')
def default_tree():
    return tree(None)
    
@app.route('/person/<person_uid>')
@check_data_is_valid
@get_user
def biography(person_uid, user):
    if person_uid in data.persons_snippets:
        person_snippet = data.persons_snippets[person_uid]
        person_context = Context(data, user=user).person_context(person_uid)
        return render_template('biography.html', person=person_snippet, context=person_context)
    return 'Персона \'{0}\' не найдена...'.format(person_uid)

@app.route('/admin/load/<archive>')
def load(archive):
    archive = 'upload/{0}.zip'.format(archive)
    data.async_load(archive)
    return 'Loading data from {} started!'.format(archive)

@app.route('/lk')
@get_user
def user_profile(user):
    return render_template('user_profile.html', api=OAuth(), user=user, context=Context(data, user=user))
    
@app.route('/login/auth/<service>')
@get_user
def auth(service, user):
    code = request.args['code']
    token = OAuth().get(service).auth.get_access_token(code)
    service_session = OAuth().get(service).session(token)
    me = service_session.me()
    
    if user is None:
        user = session_manager.open()
    user.login(service, token=token, me=me)
    session['suid'] = (user.id, user.ts)
    return redirect(url_for('user_profile'), code=302)

@app.route('/login/unauth/<service>')
@get_user
def unauth(service, user):
    if user:
        user.logout(service)
        if not user.is_authenticated():
            session_manager.close(user)
            del session['suid']     
    return redirect(url_for('user_profile'), code=302)
        
    
if __name__ == "__main__":
    app.run()
    
        
    