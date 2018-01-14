#!usr/bin/env
# -*- coding: utf-8 -*-

from db_api import UserSessionTable
from app_utils import dobj


class Session:
    def __init__(self, id):
        self.id = id
        self.auth = dobj() 
        # vk -> {
        #        'service': 'vk', 
        #        'token': ..., 
        #        'me': ..., 
        #        'session': сессия oauth для выполнения запросов
        # }        
    
    def login(self, service, **kwargs):
        self.auth[service] = dobj(kwargs)
        self.auth[service].service = service

    def logout(self, service):
        if service in self.auth:
            del self.auth[service]
        
    def is_authenticated(self, service=None):
        if service is None:
            return len(self.auth) > 0
        return service in self.auth
        
    def auth_info(self, service):
        return self.auth.get(service, None)        
            
 
    def all_logins(self):
        logins = []
        for service, info in self.auth.items():
            print('service: {}\ninfo: {}'.format(service, info))
            logins.append((service, info.me.login))
            logins.append((service, info.me.uid))
        return logins