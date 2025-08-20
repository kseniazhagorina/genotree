#!usr/bin/env
# -*- coding: utf-8 -*-

from app_utils import Data, first_or_default
from content_generator import generate_content
from gedcom import GedcomReader
from privacy import Privacy, PrivacyMode
from search import SearchEngine
from session import Session
from db_api import create_db, UserAccessManager, UserSessionManager, UserSessionTable
import oauth_api as oauth
import json
import threading
import os

from flask import Flask, render_template, send_from_directory, request, url_for, redirect, abort, session

config = json.loads(open('config/site.config').read())

app = Flask(
    __name__,
    template_folder=config["templates"],
    static_folder=config["common_static"]
)

app.debug = True
app.secret_key = open('config/app.secret.txt').read().strip()

oauth.API = None
def OAuth():
    if oauth.API is None:
        oauth_config = json.loads(open('config/oauth.config').read())
        oauth.API = oauth.Api(url_for, oauth_config)
    return oauth.API




data = Data(config["host"], config["tree_static"], config["tree_data"])
data.load()
if data.load_error:
    raise Exception(data.load_error)

search_engine = SearchEngine(data.persons_snippets)
db = create_db(config["db"])
access_manager = UserAccessManager(db, data)
session_manager = UserSessionManager(db)
generate_content(config)

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
        self.__persons_contexts = {}

    class PersonContext:
        '''контекст отображения персоны в дереве'''
        def __init__(self, person_uid, context):
            self.files_dir = context.data.files_dir
            self.person_uid = person_uid
            # все персоны публичны, если не указано иного, события публичны только для живых,
            # пользователи имеют доступ public или protected в зависимости от выданных прав
            person = context.data.persons_snippets[person_uid]
            self.privacy = Privacy(privacy=Privacy.person_privacy(person),
                                   events_privacy=Privacy.is_events_protected(person),
                                   access=context.access.get(person_uid))
            # в каких деревьях за исключением текущего присутствует данная персона
            self.tree = context.tree
            curr_tree_uid = self.tree.uid if self.tree else None
            self.trees = [tree for tree in context.data.trees.values() if person_uid in tree.map.nodes and tree.uid != curr_tree_uid]

    def person_context(self, person_uid):
        if person_uid not in self.data.persons_snippets:
            return None
        if person_uid not in self.__persons_contexts:
            self.__persons_contexts[person_uid] = Context.PersonContext(person_uid, self)
        return self.__persons_contexts[person_uid]

    def filter_access_denied(self, person_uids):
        for person_uid in person_uids:
            person_context = self.person_context(person_uid)
            if person_context and not person_context.privacy.is_access_denied():
                yield person_uid

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


@app.route('/sources.html')
def static_from_content():
    return send_from_directory(config["content_static"], request.path[1:])

@app.route('/faq.html')
def faq():
    return render_template('faq.html')

@app.route('/static/tree/<path:path>')
def static_from_tree(path):
    return send_from_directory(config["tree_static"], path)

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

@app.route('/<tree_name>')
@check_data_is_valid
@get_user
def tree(tree_name, user):
    if tree_name not in data.trees:
        abort(404)
    return render_template('tree.html', user=user, context=Context(data, user=user, requested_tree=tree_name))


@app.route('/')
def default_tree():
    return redirect(url_for('tree', tree_name=data.default_tree_name), code=301)

@app.route('/search')
@check_data_is_valid
@get_user
def search(user):
    text = request.args.get('text')
    tree_name = request.args.get('tree_name')
    on_page = 50
    context = Context(data, user=user, requested_tree=tree_name)
    strict = True
    found = search_engine.search_strict(text)
    if not found:
        strict = False
        found = search_engine.search(text)
    found = list(context.filter_access_denied(found))

    pages = max(1, int(len(found)/on_page) + int(len(found)%on_page != 0))
    page = min(max(int(request.args.get('page', 1)), 1), pages)

    show = found[(page-1)*on_page : page*on_page]

    return render_template('search.html', text=text, strict=strict, total=len(found), page=int(page), pages=pages, persons=show, context=context)

@app.route('/ajax/person_snippet/<tree_name>/<person_uid>')
@check_data_is_valid
@get_user
def person_snippet(tree_name, person_uid, user):
    tree_name = tree_name or data.default_tree_name
    if tree_name not in data.trees:
        print('unknown tree_name={}'.format(tree_name))
        abort(404)
    if person_uid not in data.persons_snippets:
        print('unknown person_uid={}'.format(person_uid))
        abort(404)
    person_snippet = data.persons_snippets[person_uid]
    person_context = Context(data, user=user, requested_tree=tree_name).person_context(person_uid)
    return render_template('tree_person_snippet.html', user=user, person=person_snippet, context=person_context)

@app.route('/person/<person_uid>')
@check_data_is_valid
@get_user
def biography(person_uid, user):
    if person_uid not in data.persons_snippets:
        abort(404)
    person_snippet = data.persons_snippets[person_uid]
    person_context = Context(data, user=user).person_context(person_uid)
    if person_context.privacy.is_access_denied():
        abort(403)
    return render_template('biography.html', user=user, person=person_snippet, context=person_context)


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

# сейчас нельзя войти на сайт через соц сети
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

@app.errorhandler(403)
@check_data_is_valid
@get_user
def page_not_found(e, user):
    return render_template('error403.html', context=Context(data, user=user)), 403

@app.errorhandler(404)
@check_data_is_valid
@get_user
def page_not_found(e, user):
    return render_template('error404.html', context=Context(data, user=user)), 404


if __name__ == "__main__":
    app.run()



