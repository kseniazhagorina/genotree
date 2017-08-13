#!usr/bin/env
# -*- coding: utf-8 -*-

import requests
import json

class Api:
    def __init__(self, url_for, config):
        make_url = lambda action, service: url_for(action, service=service, _external=True)
        
        def init_service(Service, name):
            s = None
            if name in config:
                s = Service(**config[name])
                s.auth_to(make_url('auth', name), make_url('unauth', name))
            self.__dict__[name] = s
        
        init_service(Vk, 'vk')
        init_service(Ok, 'ok')
        
            
    def get(self, service):
        if service in self.__dict__:
            return self.__dict__[service]
        return None

        
class Vk:
    version = "5.35";
    
    class Permitions:
        No = 0
        Friends = 2
        Photos = 4
        Audio = 8
        Video = 16
        Status = 1024
        Groups = 262144
        Email = 4194304
        Offline = 65536
        

    def __init__(self, id, secret):
        self.id = "5006214";
        self.secret = "auzFWlNTns4NSUNnpDC7";
        
    def auth_to(self, auth, unauth):
        self.auth = Vk.Auth(auth, unauth, self)
        
    def session(self, access_token):
        return Vk.Session(access_token, self)

    class Auth:
        '''Выполняет запросы для авторизации'''
        def __init__(self, auth, unauth, app):
            '''
            auth: url to process redirect for authenticate user
            unauth: url to process unauthentication user
            '''
            
            self.unauth_url = unauth
            self.auth_url = auth
            # https://oauth.vk.com/authorize?client_id=5006214&scope=Friends,%20Photos&redirect_uri=http://localhost:56853/AuthVk/Auth&response_type=code&v=5.35&display=page
            self.auth_dialog_url = "https://oauth.vk.com/authorize?client_id={app_id}&scope=Friends,Photos,Email&redirect_uri={redirect}&response_type=code&v={ver}&display=page".format(
                app_id=app.id, redirect=auth, ver=Vk.version)
            self.__get_access_token_url = "https://oauth.vk.com/access_token?client_id={app_id}&client_secret={secret}&code={{code}}&redirect_uri={redirect}".format(
                app_id=app.id, secret=app.secret, redirect=auth)
                
        def get_access_token(self, code):
            url = self.__get_access_token_url.format(code=code)
            token = json.loads(requests.get(url).text) 
            return token
        
    class Session:
        '''Хранит информацию о сессии (access_token) и позволяет делать запросы от имени пользователя'''
        def __init__(self, access_token, app):
            self.app = app
            self.token = access_token
    
    
        
class Ok:
    '''https://apiok.ru/ext/oauth/server'''
    
    class Permitions:
        VALUABLE_ACCESS = 1     # Основное разрешение, необходимо для вызова большинства методов
        LONG_ACCESS_TOKEN = 2	# Получение длинных токенов от OAuth авторизации
        PHOTO_CONTENT = 3       # Доступ к фотографиям
        GROUP_CONTENT = 4       # Доступ к группам
        VIDEO_CONTENT = 5       # Доступ к видео
        APP_INVITE = 6	        # Разрешение приглашать друзей в игру методом friends.appInvite
        GET_EMAIL = 7           # Email пользователя
    
    def __init__(self, id, public_key, private_key):
        self.id = id
        self.public_key = public_key
        self.private_key = private_key
        
    def auth_to(self, auth, unauth):
        self.auth = Ok.Auth(auth, unauth, self)
        
    def session(self, access_token):
        return Ok.Session(access_token, self) 

    class Auth:
        def __init__(self, auth, unauth, app):
            self.unauth_url = unauth
            self.auth_url = auth
            self.auth_dialog_url = "https://connect.ok.ru/oauth/authorize?client_id={app_id}&scope=VALUABLE_ACCESS,GET_EMAIL&response_type=code&redirect_uri={redirect}&layout=w".format(
                app_id=app.id, redirect=auth)
            self.__get_access_token_url = "https://api.ok.ru/oauth/token.do?code={{code}}&client_id={app_id}&client_secret={secret}&redirect_uri={redirect}&grant_type=authorization_code".format(
                app_id=app.id, redirect=auth, secret=app.private_key)
        
        def get_access_token(self, code):
            url = self.__get_access_token_url.format(code=code)
            token = json.loads(requests.post(url).text)
            return token

    class Session:
        def __init__(self, access_token, app):
            self.app = app
            self.access_token = access_token
    
    