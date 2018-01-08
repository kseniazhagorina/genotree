#!usr/bin/env
# -*- coding: utf-8 -*-

import sqlite3
import uuid
import json
from app_utils import dobj

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return dobj(d)
        
class Db:
    def __init__(self, db_filename):
        self.db_file = db_filename
        
    def connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = dict_factory
        return conn
        
def create_db(db_filename):
    db = Db(db_filename)
    conn = db.connection()
    cursor = conn.cursor()
    ua = UserAccessTable(cursor)
    ua.create()
    sessions = UserSessionTable(cursor)
    sessions.create()
    conn.commit()
    return db     
        

class UserAccessTable:
    '''Protected-доступ отдельных пользователей к отдельным персонам в древе'''
    class Status(str):
        ACCEPTED = 'ACCEPTED'
        FORBIDDEN = 'FORBIDDEN'
        MODERATION = 'MODERATION'
        
    class How(str):
        IMPORTED = 'IMPORTED'
        MODERATED = 'MODERATED'
        AUTOMATIC = 'AUTOMATIC'
            
    def __init__(self, cursor):
        self.c = cursor

    def create(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS user_access (
                             service, login, person_uid, status, how,
                             UNIQUE (service, login, person_uid)
                         )''')
        
    def accept_if_not_forbidden(self, service, login, person_uid, how):
        '''сохраняет права доступа как accepted, если не указано forbidden
           return: true if access is provided
        '''
        exist_row = self.get(service, login, person_uid)           
        if exist_row:
            if exist_row.status == UserAccessTable.Status.FORBIDDEN:
                return False
            if exist_row.status == UserAccessTable.Status.ACCEPTED:
                return True
            self.delete(service, login, person_uid)
        self.insert(service, login, person_uid, UserAccessTable.Status.ACCEPTED, how)
        return True
    
    def get(self, service, login, person_uid):
        self.c.execute('''
            SELECT * FROM user_access 
            WHERE service=? and login=? and person_uid=?''', 
            (service, login, person_uid))
        return self.c.fetchone()
    
    def get_accepted(self, service, login):
        accepted = self.c.execute('''
            SELECT * FROM user_access 
            WHERE service=? and login=? and status=?''', 
            (service, login, UserAccessTable.Status.ACCEPTED))
        return [item.person_uid for item in accepted]
        
    def delete(self, service, login, person_uid):
        self.c.execute('''
            DELETE FROM user_access WHERE rowid IN 
                (SELECT rowid FROM user_access 
                WHERE service=? and login=? and person_uid=?)''', 
            (service, login, person_uid))
            
    def insert(self, service, login, person_uid, status, how):
        self.c.execute('''
            INSERT INTO user_access VALUES (?, ?, ?, ?, ?)''',
            (service, login, person_uid, status, how))
            
    def accept(self, service, login, person_uid, how):
        self.delete(service, login, person_uid)
        self.insert(service, login, person_uid, UserAccessTable.Status.ACCEPTED, how)
        
    def forbid(self, service, login, person_uid, how):
        self.delete(service, login, person_uid)
        self.insert(service, login, person_uid, UserAccessTable.Status.FORBIDDEN, how)
        
    def send_on_moderation(self, service, login, person_uid):
        exist_row = self.get(service, login, person_uid)
        if exist_row is not None:
            return False
        self.insert(service, login, person_uid, UserAccessTable.Status.MODERATION, UserAccessTable.How.AUTOMATIC)


class UserSessionTable:
    '''Сессии пользователя. 
       Пользователь может иметь несколько открытых сессий с одним session_id (на разные логины) одновременно.
       created - дата и время когда пользователь зарегистрировался на сервисе
       closed - дата и время когда пользователь нажал выйти
       user_data - данные пользователя связанные с сессией
    '''   
    def __init__(self, cursor):
        self.c = cursor

    def create(self):
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS user_session (
                session_id UNIQUE PRIMARY KEY, user_data, created DEFAULT CURRENT_TIMESTAMP, closed DEFAULT NULL,
                UNIQUE (session_id)
            )''')

    def open(self, user_data):
        session_id = uuid.uuid4().hex
        data = json.dumps(user_data, ensure_ascii=False)
        self.c.execute('''
            INSERT INTO user_session (session_id, user_data) 
            VALUES (?, ?)''',
            (session_id, data))
        return session_id
    
    def get(self, session_id):
        self.c.execute('''
            SELECT * from user_session WHERE session_id=?''',
            (session_id,))
        session = self.c.fetchone()
        return session
        
    def get_data(self, session_id, only_opened=True):
        session = self.get(session_id)
        if session is None:
            return None
        if only_opened and session.closed is not None:
            return None
        data = json.loads(session.user_data)
        return data
    
    def delete(self, session_id):
        self.c.execute('''
            DELETE FROM user_session WHERE rowid IN 
                (SELECT rowid FROM user_session 
                WHERE session_id=?)''', 
            (session_id,))
    
    def update(self, session_id, user_data):
        session = self.get(session_id)
        if session is None or session.closed is not None:
            return False
        
        data = json.dumps(user_data, ensure_ascii=False)
        self.delete(session_id)    
        self.c.execute('''
            INSERT INTO user_session (session_id, user_data, created) 
            VALUES (?, ?, ?)''',
            (session_id, data, session.created))
        return True            
         
    def close(self, session_id):
        session = self.get(session_id)
        if session is None or session.closed is not None:
            return False
        self.delete(session_id)    
        self.c.execute('''
            INSERT INTO user_session 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
            (session_id, session.user_data, session.created))
        return True          
            
        
    
        
            