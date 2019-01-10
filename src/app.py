#!usr/bin/env
# -*- coding: utf-8 -*-

from app_utils import Data, first_or_default
from gedcom import GedcomReader
from privacy import Privacy, PrivacyMode
from session import Session
from db_api import create_db, UserAccessManager, UserSessionManager, UserSessionTable
import oauth_api as oauth
import json
import threading

from flask import Flask, render_template, request, url_for, redirect, abort, session
app = Flask(__name__)
app.debug = True
app.secret_key = open('data/config/app.secret.txt').read().strip()

oauth.API = None
def OAuth():   
    if oauth.API is None:
        config = json.loads(open('data/config/oauth.config').read())
        oauth.API = oauth.Api(url_for, config)
    return oauth.API



data = Data('src/static/tree', 'data/tree')        
data.load()
if data.load_error:
    raise Exception(data.load_error)

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
            return 'Что-то пошло не так... Попробуйте зайти на сайт позже.\n\n'+data.load_error, 500
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

ADMIN = [('vk', 'kzhagorina')]    
def only_for_admin(func):
    
    def wrapper(*args, **kwargs):
        if 'suid' in session:
            session_id, ts = session.get('suid')
            user = session_manager.get(session_id, ts)
            if user is not None:
                if any(login in ADMIN for login in user.all_logins()):
                    return func(*args, **kwargs)
        abort(403)
    wrapper.__name__ = func.__name__
    return wrapper

    
@app.route('/sources')
def sources():
    return render_template('sources.html')
    
@app.route('/<tree_name>')
@check_data_is_valid
@get_user
def tree(tree_name, user):
    tree_name = tree_name or data.default_tree_name
    if tree_name not in data.trees:
        abort(404)
    return render_template('tree.html', user=user, context=Context(data, user=user, requested_tree=tree_name))
          

@app.route('/')
def default_tree():
    return tree(None)
    
@app.route('/person/<person_uid>')
@check_data_is_valid
@get_user
def biography(person_uid, user):
    if person_uid not in data.persons_snippets:
        abort(404)
    person_snippet = data.persons_snippets[person_uid]
    person_context = Context(data, user=user).person_context(person_uid)
    return render_template('biography.html', user=user, person=person_snippet, context=person_context)

@app.route('/admin/load/<archive>')
@only_for_admin
def load(archive):
    archive = 'upload/{0}.zip'.format(archive)
    data.async_load(archive)
    return 'Loading data from {} started!'.format(archive)
    
@app.route('/admin/users')
@only_for_admin
def view_users():
    users = []
    with db.connection() as conn:
        us = UserSessionTable(conn.cursor())
        for s in us.get_all():
            user_session = Session.from_json(s.data, session_manager)
            users.append((user_session, s.opened, s.closed))
    return render_template('view_users.html', users=users)        
                

@app.route('/lk')
@get_user
def user_profile(user):
    context = Context(data, user=user)
    owned = [data.persons_snippets[uid] for uid in context.access.roles.get('OWNER', []) if uid in data.persons_snippets]
    first_owned = first_or_default(owned)
    relatives = list(sorted(context.access.access.keys(), key=lambda uid: len(first_owned.relatives.get(uid, 'nnn'))))
    relatives = [data.persons_snippets[uid] for uid in relatives if uid in data.persons_snippets]
    return render_template('user_profile.html', 
                           api=OAuth(), user=user, context=Context(data, user=user),
                           owned=owned, relatives=relatives)
    
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
    return render_template('js_redirect.html', target=url_for('user_profile'), goals=['authentication'], user=user)

@app.route('/login/unauth/<service>')
@get_user
def unauth(service, user):
    if user:
        user.logout(service)
        if not user.is_authenticated():
            session_manager.close(user)
            del session['suid']     
    return redirect(url_for('user_profile'), code=302)

@app.errorhandler(404)
@check_data_is_valid
@get_user
def page_not_found(e, user):
    return render_template('error404.html', context=Context(data, user=user)), 404
        
    
if __name__ == "__main__":
    app.run()
    
        
    
