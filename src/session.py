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
        self.auth[service] = dobj.convert(kwargs)
        self.auth[service].service = service
        self.auth[service].opened = time.time()
        self.auth[service].closed = None
        self.manager.update(self)

    def logout(self, service):
        if service in self.auth:
            self.auth[service].closed = time.time()
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
                return None
            return s
    
    def all_logins(self):
        logins = []
        for service, info in self.auth.items():
            if info.opened:
                logins.append((service, info.me.login))
                logins.append((service, info.me.uid))
        return logins