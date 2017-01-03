#!usr/bin/env
# -*- coding: utf-8 -*-

import traceback
from app_utils import get_tree, get_tree_map, get_person_snippets, get_files_dict
from gedcom import GedcomReader
from upload import load_package, select_tree_img_files
from privacy import Privacy, PrivacyMode

from flask import Flask, render_template, request
app = Flask(__name__)
app.debug = True

TREE_NAMES = {
    '': 'Общее',
    'zhagoriny': 'Жагорины',
    'motyrevy': 'Мотыревы',
    'cherepanovy': 'Черепановы',
    'farenuyk': 'Фаренюки'
}    

class Data:
    '''статические данные о персонах/загруженных деревьях не зависящие
       от текущего пользователя, запрошенной страницы, отображаемой персоны'''
    class Tree:
        def __init__(self, uid, img, map):
            self.uid = uid
            self.name = TREE_NAMES.get(uid) or uid
            self.img = img
            self.map = map
            
    def __init__(self):
        self.load_error = 'Data is unloaded.'
    
    def is_valid(self):
        return self.load_error is None
        
    def load(self, archive=None):
        try:
            self.load_error = 'Data is updated right now'          
            if archive is not None:
                load_package(archive, 'src/static/tree', 'data/tree')
            
            self.files_dir = '/static/tree/files'
            self.files = get_files_dict('data/tree/files.tsv')
            
            self.gedcom = GedcomReader().read_gedcom('data/tree/tree.ged')
            self.persons_snippets = get_person_snippets(self.gedcom, self.files)
            
            # Загружаем деревья - 
            tree_uids, pngs, xmls = select_tree_img_files('src/static/tree')
            if len(tree_uids) == 0:
                raise Exception('No files *_tree_img.png in /static/tree directory')
            self.trees = {}
            for tree_uid, png, xml in zip(tree_uids, pngs, xmls):
                self.trees[tree_uid] = Data.Tree(tree_uid, '/static/tree/'+png, get_tree_map('data/tree/'+xml))
            self.default_tree_name = '' if '' in self.trees else tree_uids[0]    
            self.load_error = None
        except:
            self.load_error = traceback.format_exc()

class Context:
    '''Данные о том, какой пользователь запрашивает страницу, его настройки приватности
       Какая страница была запрошена, какое дерево сейчас отображается
    '''
    def __init__(self, data, requested_tree):
        self.data = data
        self.tree = data.trees[requested_tree]
    
    class PersonContext:
        def __init__(self, data, tree, person_uid):
            self.files_dir = data.files_dir
            self.person_uid = person_uid
            # все персоны публичны, доступ для пользователей только public
            self.privacy = Privacy(privacy=PrivacyMode.PUBLIC, access=PrivacyMode.PUBLIC)
            # в каких деревьях за исключением текущего присутствует данная персона
            self.tree = tree
            self.trees = [tree for tree in data.trees.values() if tree.uid != self.tree.uid and person_uid in tree.map.nodes]
            
    
    def person_context(self, person_uid):
        return Context.PersonContext(self.data, self.tree, person_uid)         
    

data = Data()        
data.load()

@app.route('/<tree_name>')
def tree(tree_name):
    if data.is_valid():
        tree_name = tree_name or data.default_tree_name
        if tree_name in data.trees:
            return render_template('tree.html', context=Context(data, tree_name))
        return 'Дерево \'{0}\' не найдено...'.format(tree_name)
    return 'Something went wrong... =(\n' + data.load_error      

@app.route('/')
def default_tree():
    return tree(None)
    
    
  
    
@app.route('/admin/load/<archive>')
def load(archive):
    archive = 'upload/{0}.zip'.format(archive)
    data.load(archive)
    return 'Success!' if data.is_valid() else 'Fail!\n' + data.load_error 

if __name__ == "__main__":
    app.run()
    
    