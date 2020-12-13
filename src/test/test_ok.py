#!usr/bin/env
# -*- coding: utf-8 -*-

import unittest
import oauth_api as oapi

class T(unittest.TestCase):
    
    def test_ok_login_by_uid(self):
        # закрытый профиль без логина
        login = oapi.Ok.get_login_by_uid('513483009213')
        self.assertEqual(login, None)
        
        # еще один с которым проблемы
        login = oapi.Ok.get_login_by_uid('81065019273')
        self.assertEqual(login, None)
        
        login = oapi.Ok.get_login_by_uid('329919392375')
        self.assertEqual(login, 'ksenia.zhagorina')
        
if __name__ == '__main__':
    unittest.main()