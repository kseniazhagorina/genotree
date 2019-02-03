#!usr/bin/env
# -*- coding: utf-8 -*-

import re
from datetime import date
from dateutil.relativedelta import relativedelta

class PrivacyMode:
    PUBLIC = 0
    PROTECTED = 1
    PRIVATE = 2

class Privacy:
    AddressRegex = re.compile(r'\d+(\s*([/-]|(стр|корп|лит)\w*\.?)?)?(\s*([а-я]|\d+))?\b', flags=re.IGNORECASE)
    PhoneRegex = re.compile(r'(\b(моб|тел|сот)\w*\W*)[\d\(\)\s\+\-,]{5,}', flags=re.IGNORECASE|re.MULTILINE)
    EmailRegex = re.compile(r'\b(?P<login>[\w\-\.]+)@(?P<domain>\w+\.\w{2,6})\b', flags=re.IGNORECASE)
    
    def __init__(self, privacy, events_privacy, access):
        '''privacy - уровень приватности персоны
               public - для всех,
               protected - (не используется),
               private - для параноиков
           events_privacy - уровень приватности для событий
               public - для умерших
               protected - для живых и родившихся позднее 70 лет назад
               private - не используется
           access - права доступа пользователя
               public - незарегистрированный пользователь
               protected - зарегистрированный
               private - я
           Отдельно задается приватность для комментариев/отдельных событий/источников и т.п.               
        '''
        self.privacy = privacy
        self.events_privacy = events_privacy
        self.access = access

    def is_access_denied(self):
        '''доступ к информации запрещен если уровень ее приватности больше чем уровень доступа пользователя'''
        return self.access < self.privacy
        
    def is_access_to_events_denied(self):
        return self.access < self.events_privacy    

    def comment(self, comment):
        '''comment is instance of Note class'''
        comment = comment.filter(access=self.access, text=True, key_values=False, tags=False) if comment else None
        if comment is None:
            return None
        return self.phone(self.email(str(comment)))

    def address(self, place):
        return Privacy.AddressRegex.sub('***', place)

    def phone(self, text):
        return Privacy.PhoneRegex.sub(lambda match: re.sub('\d','*',match.group(0)), text)

    def email(self, text):
        return Privacy.EmailRegex.sub(lambda match: '*'*len(match.group('login'))+' @'+match.group('domain'), text)

    def sources(self, sources):
        return [s for s in sources if s.quote is None or s.quote.privacy() <= self.access]
    
    def events(self, events):
        if self.is_access_to_events_denied():
            return []
        return [e for e in events if e.comment is None or e.comment.privacy() <= self.access]    
    
    @staticmethod
    def is_events_protected(person):
        if person.is_alive():
            return True
        if person.birth and person.birth.date and relativedelta(date.today(), person.birth.date.to_date()).years < 70:
            return True
        return False
    
    @staticmethod    
    def person_privacy(person):
        if person.comment:
            return person.comment.privacy('person')
        return PrivacyMode.PUBLIC