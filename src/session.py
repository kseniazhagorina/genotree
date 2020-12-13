#!usr/bin/env
# -*- coding: utf-8 -*-

import time
import json
import sys
from app_utils import dobj


class Session(dobj):
    @staticmethod
    def from_json(data, manager):
        data = dobj(json.loads(data))
        s = Session(manager=manager, **data)
        return s
        
    @staticmethod    
    def is_valid_auth_info(auth_info):
        if auth_info.me is None:
            return False
        return True
    
    
            
    def __init__(self, id, ts, manager, auth=None):
        self.manager = manager
        self.id = id
        self.ts = ts  # last updated timestamp
        self.auth = auth or dobj()        
        # vk -> {
        #        'service': 'vk', 
        #        'token': ..., 
        #        'me': ...,
        #        'opened': timestamp
        #        'closed': timestamp or None  
        # }
    

    def login(self, service, **kwargs):
        auth_info = dobj.convert(kwargs)
        auth_info.service = service
        auth_info.opened = time.time()
        auth_info.closed = None
        if not Session.is_valid_auth_info(auth_info):
            raise Exception('Invalid auth info {}'.format(auth_info))
        self.auth[service] = auth_info
        self.manager.update(self)
        return True

    def logout(self, service=None):
        candidates = [service] if service is not None else self.auth.keys()
        close_time = time.time()
        updated = False
        for service in candidates:
            s = self.auth.get(service, None)
            if s is not None and not s.closed:
                s.closed = close_time
                updated = True
        if updated:
            self.manager.update(self)
        
    def is_authenticated(self, service=None):
        if service is None:
            return any(v.closed is None for v in self.auth.values())
        return service in self.auth and self.auth[service].closed is None
        
    def auth_info(self, service=None, only_opened=True):
        candidates = [service] if service is not None else self.auth.keys()
        for service in candidates:
            s = self.auth.get(service, None)
            if only_opened and s is not None and s.closed:
                continue
            return s
        return None
    
    def all_logins(self):
        logins = []
        for service, info in self.auth.items():
            if info.opened:
                logins.append((service, info.me.login))
                logins.append((service, info.me.uid))
        return logins
        
    def is_valid(self):
        for service in self.auth:
            if not Session.is_valid_auth_info(self.auth[service]):
                return False
        return True