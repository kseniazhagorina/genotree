#!usr/bin/env
# -*- coding: utf-8 -*-

import upload
from common_utils import convert_to_utf8

def create_package(version):
    '''create package at local machine'''
    archive = upload.create_package(r'D:\site\{}'.format(version), 'data')
    print(archive)
    
# scp data.zip kzhagorina@ssh.pythonanywhere.com:~/me-in-history/upload/data.zip


def load_to_develop(version):
    '''load package at dev-server at local machine'''
    archive = r'D:\site\{}\data.zip'.format(version)
    upload.load_package(archive,
                        'http://localhost:5000',    
                        r'D:\Development\Python\IPythonNotebooks\genotree\src\static\tree',
                        r'D:\Development\Python\IPythonNotebooks\genotree\data\tree')



# cd genotree/src
# python3
def load_to_production():
    '''load package at pythonanywhere server'''
    archive = '../upload/data.zip'
    upload.load_package(archive,
                        'http://me-in-history.ru',
                        'static/tree',
                        '../data/tree')
    
    