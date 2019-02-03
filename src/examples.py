#!usr/bin/env
# -*- coding: utf-8 -*-

import upload
from common_utils import convert_to_utf8

def create_package():
    '''create package at local machine'''
    convert_to_utf8(r'D:\site\tree.ged')
    archive = upload.create_package(r'D:\site', 'data')
    print(archive)
    
# scp data.zip kzhagorina@ssh.pythonanywhere.com:~/genotree/upload/data.zip


def load_to_develop():
    '''load package at dev-server at local machine'''
    archive = r'D:\site\data.zip'
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
    
    