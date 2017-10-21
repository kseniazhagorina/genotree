#!usr/bin/env
# -*- coding: utf-8 -*-

import requests
import json
import urllib.parse as urlparse
import hashlib
from app_utils import first_or_default

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
        def __init__(self, token, app):
            self.app = app
            self.token = token
            self.access_token = self.token.get('access_token', '')
            self.user = None

        def me(self):
            if self.user is None and self.token is not None and 'user_id' in self.token:
                self.user = first_or_default(self.users([self.token['user_id']]))
            return self.user

        def users(self, uids):
            url = 'https://api.vk.com/method/users.get?user_ids={uids}&v=5.52&access_token={access_token}&fields=verified,sex,bdate,city,country,home_town,has_photo,photo_50,photo_100,photo_200_orig,photo_200,photo_400_orig,photo_max,photo_max_orig,online,domain,has_mobile,contacts,site,education,universities,schools,status,last_seen,followers_count,occupation,nickname,relatives,relation,personal,connections,exports,wall_comments,activities,interests,music,movies,tv,books,games,about,quotes,can_post,can_see_all_posts,can_see_audio,can_write_private_message,can_send_friend_request,is_favorite,is_hidden_from_feed,timezone,screen_name,maiden_name,crop_photo,is_friend,friend_status,career,military,blacklisted,blacklisted_by_me'
            url = url.format(access_token=self.access_token, uids=','.join(map(str, uids)))
            response = json.loads(requests.get(url).text)
            if 'response' not in response:
                print('Api.Vk error: {} respond {}'.format(url, response))
                return []
            return response['response']

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
        __FIELDS = 'ACCESSIBLE,AGE,ALLOWS_ANONYM_ACCESS,ALLOWS_MESSAGING_ONLY_FOR_FRIENDS,BECOME_VIP_ALLOWED,BIRTHDAY,BLOCKED,BLOCKS,CAN_VCALL,CAN_VMAIL,CITY_OF_BIRTH,COMMON_FRIENDS_COUNT,CURRENT_LOCATION,CURRENT_STATUS,CURRENT_STATUS_DATE,CURRENT_STATUS_DATE_MS,CURRENT_STATUS_ID,CURRENT_STATUS_MOOD,CURRENT_STATUS_TRACK_ID,EMAIL,FIRST_NAME,FRIEND,FRIEND_INVITATION,FRIEND_INVITE_ALLOWED,GENDER,GROUP_INVITE_ALLOWED,HAS_EMAIL,HAS_PHONE,HAS_SERVICE_INVISIBLE,INTERNAL_PIC_ALLOW_EMPTY,INVITED_BY_FRIEND,IS_ACTIVATED,LAST_NAME,LAST_ONLINE,LAST_ONLINE_MS,LOCALE,LOCATION,LOCATION_OF_BIRTH,MODIFIED_MS,NAME,ODKL_BLOCK_REASON,ODKL_EMAIL,ODKL_LOGIN,ODKL_MOBILE,ODKL_MOBILE_STATUS,ODKL_USER_OPTIONS,ODKL_USER_STATUS,ODKL_VOTING,ONLINE,PHOTO_ID,PIC1024X768,PIC128MAX,PIC128X128,PIC180MIN,PIC190X190,PIC224X224,PIC240MIN,PIC288X288,PIC320MIN,PIC50X50,PIC600X600,PIC640X480,PIC_1,PIC_2,PIC_3,PIC_4,PIC_5,PIC_BASE,PIC_FULL,PIC_MAX,PREMIUM,PRESENTS,PRIVATE,PYMK_PIC224X224,PYMK_PIC288X288,PYMK_PIC600X600,PYMK_PIC_FULL,REF,REGISTERED_DATE,REGISTERED_DATE_MS,RELATIONS,RELATIONSHIP,SEND_MESSAGE_ALLOWED,SHOW_LOCK,STATUS,UID,URL_CHAT,URL_CHAT_MOBILE,URL_PROFILE,URL_PROFILE_MOBILE,VIP'
        def __init__(self, token, app):
            self.app = app
            self.token = token
            self.access_token = self.token.get('access_token', '')
            self.user = None

        def __sig(self, url, with_access_token=True):
            '''
            при отсутствии значения session_secret_key:
               для вызова без сессии считаем session_secret_key = application_secret_key;
               для вызова в сессии session_secret_key = MD5(access_token + application_secret_key), переводим значение в нижний регистр;
            убираем из списка параметров session_key/access_token при наличии;
            параметры сортируются лексикографически по ключам;
            параметры соединяются в формате ключ=значение;
            sig = MD5(значения_параметров + session_secret_key);
            значение sig переводится в нижний регистр.

            в наших запросах изначально нет access_token или session_secret_key
            '''
            with_access_token &= bool(self.access_token)
            query = urlparse.urlparse(url).query
            params = list(sorted(query.split('&'), key=lambda p: p.split('=', 1)[0]))

            print('url: {}'.format(url))
            if with_access_token:

                sk = self.access_token + self.app.private_key
                print('sk: {}'.format(sk))
                secret_key = hashlib.md5(sk.encode()).hexdigest()
                print('secret_key: {}'.format(secret_key))
                url += '&access_token={}'.format(self.access_token)
            else:
                secret_key = self.app.private_key

            s = ''.join(params)+secret_key
            print('s: {}'.format(s))
            sig = hashlib.md5(s.encode()).hexdigest().lower()
            print('sig: {}'.format(sig))

            url = url + '&sig={}'.format(sig)
            return url

        def me(self):
            if self.user is None and self.access_token:
                url = 'https://api.ok.ru/api/users/getCurrentUser?application_key={application_key}&fields='+self.__FIELDS
                url = url.format(application_key=self.app.public_key)
                url = self.__sig(url)
                user = json.loads(requests.get(url).text)
                if 'error' in user:
                    print('Api.Ok error: {} respond {}'.format(url, user))
                    return None
                self.user = first_or_default(self.users([user['uid']]))
            return self.user

        def users(self, uids):
            url = 'https://api.ok.ru/api/users/getInfo?uids={uids}&application_key={application_key}&emptyPictures=true&fields='+self.__FIELDS
            url = url.format(application_key=self.app.public_key, uids=','.join(map(str, uids)))
            url = self.__sig(url)
            response = json.loads(requests.get(url).text)
            if 'error' in response:
                print('Api.Ok error: {} respond {}'.format(url, response))
                return []
            return response

