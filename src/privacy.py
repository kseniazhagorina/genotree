#!usr/bin/env
# -*- coding: utf-8 -*-

import re

class PrivacyMode:
    PUBLIC = 0
    PROTECTED = 1
    PRIVATE = 2

class Privacy:
    AddressRegex = re.compile(r'\d+(\s*([/-]|(стр|корп|лит)\w*\.?)?)?(\s*([а-я]|\d+))?\b', flags=re.IGNORECASE)
    PhoneRegex = re.compile(r'(\b(моб|тел|сот)\w*\W*)[\d\(\)\s\+\-,]{5,}', flags=re.IGNORECASE|re.MULTILINE)
    EmailRegex = re.compile(r'\b(?P<login>[\w\-\.]+)@(?P<domain>\w+\.\w{2,6})\b', flags=re.IGNORECASE)
    
    def __init__(self, privacy, access):
        '''privacy - уровень приватности персоны
               public - для умерших,
               protected - для живых,
               private - для параноиков
           access - права доступа пользователя
               public - незарегистрированный пользователь
               protected - зарегистрированный
               private - админ
        '''
        self.privacy = privacy
        self.access = access

    def is_access_denied(self):
        '''доступ к информации запрещен если уровень ее приватности больше чем уровень доступа пользователя'''
        return self.access < self.privacy

    def comment(self, comment):
        '''comment is instance of Note class'''
        comment = comment.filter(privacy=max(self.access, self.privacy), text=True, key_values=False, tags=False) if comment else None
        if comment is None:
            return None
        return self.phone(self.email(str(comment)))

    def address(self, place):
        return Privacy.AddressRegex.sub('***', place)

    def phone(self, text):
        return Privacy.PhoneRegex.sub(lambda match: re.sub('\d','*',match.group(0)), text)

    def email(self, text):
        return Privacy.EmailRegex.sub(lambda match: '*'*len(match.group('login'))+' @'+match.group('domain'), text)
