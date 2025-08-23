#!usr/bin/env
# -*- coding: utf-8 -*-

import upload
import json
import os.path
from common_utils import convert_to_utf8

def create_package_windows(version):
    '''create package at local machine'''
    archive = upload.create_package(r'D:\site\{}'.format(version), 'data')
    print(archive)

def create_package_linux(version):
    '''create package at local machine on linux'''
    archive = upload.create_package('/home/kzhagorina/family/zhagoriny_tree/site/{}'.format(version), 'data')
    print(archive)

# scp data.zip kzhagorina@ssh.pythonanywhere.com:~/me-in-history/upload/data.zip


def load_package_windows(version, config_file):
    '''load package at dev-server at local machine'''
    archive = r'D:\site\{}\data.zip'.format(version)


    upload.load_package(archive,
                        'http://localhost:5000',
                        r'D:\Development\Python\IPythonNotebooks\genotree\src\static\tree',
                        r'D:\Development\Python\IPythonNotebooks\genotree\data\tree')

def load_package_linux(config_dir):
    '''load package at dev-server at local machine'''
    config = json.loads(open(os.path.join(config_dir, 'site.config')).read())
    archive = os.path.join(config["upload"], 'data.zip')
    upload.load_package(archive,
                        config["host"],
                        config["tree_static"],
                        config["tree_data"],
                        os.path.join(config["tmp"], 'unpacked_data'))


def generate_develop_linux_config(config_dir):
    config = {
        "host": "http://localhost:5000",
        "author": {
            "name": "Жагорина Ксения Андреевна",
            "link": "/person/530",
            "contacts": {
                "odnoklassniki": "ksenia.zhagorina",
                "vk": "kzhagorina",
                "telegram" : "KseniaZhagorina",
                "whatsapp" : "aHR0cHM6Ly93YS5tZS83OTkyMDAwOTU5NA==",
                "instagram" : null
            }
        },

        "static" : "/home/kzhagorina/src/me-in-history/static",
        "tree_static": "/home/kzhagorina/src/me-in-history/static/tree",
        "content_static": "/home/kzhagorina/src/me-in-history/static/content",

        "tree_data": "/home/kzhagorina/src/me-in-history/data/tree",
        "db": "/home/kzhagorina/src/me-in-history/data/db/tree.db",

        "common_static" : "/home/kzhagorina/src/me-in-history/genotree/src/static",
        "custom_static" : "/home/kzhagorina/src/me-in-history/genotree/src/custom/me-in-history/static",
        "content": "/home/kzhagorina/src/me-in-history/genotree/src/content",

        "templates": "/home/kzhagorina/src/me-in-history/genotree/src/templates",
        "upload": "/home/kzhagorina/src/me-in-history/upload",
        "tmp": "/home/kzhagorina/src/me-in-history/tmp"
    }

    with open(os.path.join(config_dir, 'site.config'), 'w') as config_file:
        json.dump(config, config_file)

def generate_production_me_in_history_linux_config(config_dir):
    config = {
        "host": "http://me-in-history.ru",

        "author": {
            "name": "Александр Зиновьев",
            "link": "/person/530",
            "contacts": {
                "odnoklassniki": "ksenia.zhagorina",
                "vk": "kzhagorina",
                "telegram" : "KseniaZhagorina",
                "whatsapp" : "aHR0cHM6Ly93YS5tZS83OTkyMDAwOTU5NA==",
                "instagram" : null
            }
        },

        "static" : "/home/c62259/me-in-history.ru/static",
        "tree_static": "/home/c62259/me-in-history.ru/static/tree",
        "content_static": "/home/c62259/me-in-history.ru/static/content",

        "tree_data": "/home/c62259/me-in-history.ru/data/tree",
        "db": "/home/c62259/me-in-history.ru/data/db/tree.db",

        "common_static" : "/home/c62259/me-in-history.ru/genotree/src/static",
        "custom_static" : "/home/c62259/me-in-history.ru/genotree/src/custom/me-in-history/static",
        "content": "/home/c62259/me-in-history.ru/genotree/src/content",

        "templates": "/home/c62259/me-in-history.ru/genotree/src/templates",
        "upload": "/home/c62259/me-in-history.ru/upload",
        "tmp": "/home/c62259/me-in-history.ru/tmp"
    }

    with open(os.path.join(config_dir, 'site.config'), 'w') as config_file:
        json.dump(config, config_file)

def generate_production_tavatuy_linux_config(config_dir):
    config = {
        "host": "http://tavatuy-history.ru",

        "author": {
            "name": "Александр Зиновьев",
            "link": null,
            "contacts": {
            }
        },

        "static" : "/home/c109400/tavatuy-history.ru/static",
        "tree_static": "/home/c109400/tavatuy-history.ru/static/tree",
        "content_static": "/home/c109400/tavatuy-history.ru/static/content",

        "tree_data": "/home/c109400/tavatuy-history.ru/data/tree",
        "db": "/home/c109400/tavatuy-history.ru/data/db/tree.db",

        "common_static" : "/home/c109400/tavatuy-history.ru/genotree/src/static",
        "custom_static" : "/home/c109400/tavatuy-history.ru/genotree/src/custom/me-in-history/static",
        "content": "/home/c109400/tavatuy-history.ru/genotree/src/content",

        "templates": "/home/c109400/tavatuy-history.ru/genotree/src/templates",
        "upload": "/home/c109400/tavatuy-history.ru/upload",
        "tmp": "/home/c6c1094002259/tavatuy-history.ru/tmp"
    }

    with open(os.path.join(config_dir, 'site.config'), 'w') as config_file:
        json.dump(config, config_file)


