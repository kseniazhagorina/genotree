#!usr/bin/env
# -*- coding: utf-8 -*-

from db_api import UserSessionTable
from app_utils import dobj


class Session:
    def __init__(self):
        self.id = None
        self.auth = dobj() # vk -> {'token': ..., 'me': ..., 'session': ...}        
    
    
    def login(self, service, **kwargs):
        self.auth[service] = dobj.convert(kwargs)

    def logout(self):
        del self.auth[service]
        
    def is_authenticated(self, service=None):
        if service is None:
            return len(self.auth) > 0
        return service in self.auth
    
        