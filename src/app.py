#!usr/bin/env
# -*- coding: utf-8 -*-

import traceback
from app_utils import get_tree, get_tree_map, get_person_snippets, get_privacy_settings, get_files_dict
from gedcom import GedcomReader
from upload import load_package

from flask import Flask, render_template, request
app = Flask(__name__)
app.debug = True

class Data:
    def __init__(self):
        self.load_error = 'Data is unloaded.'
    
    def is_valid(self):
        return self.load_error is None
        
    def load(self, archive=None):
        try:
            self.load_error = 'Data is updated right now'          
            if archive is not None:
                load_package(archive, 'src/static/tree', 'data/tree')
            self.tree_img = '/static/tree/tree_img.png'
            self.files_dir = '/static/tree/files'
            self.files = get_files_dict('data/tree/files.tsv')
            self.tree_map = get_tree_map('data/tree/tree_img.xml')
            self.gedcom = GedcomReader().read_gedcom('data/tree/tree.ged')
            self.persons_snippets = get_person_snippets(self.gedcom, self.files)
            self.privacy_settings = get_privacy_settings(self.persons_snippets)
            self.load_error = None
        except:
            self.load_error = traceback.format_exc()
              
data = Data()        
data.load()

@app.route('/')
def tree():
    if data.is_valid():
        return render_template('tree.html', data=data)
    return 'Something went wrong... =(\n' + data.load_error
    
@app.route('/admin/load/<archive>')
def load(archive):
    archive = 'upload/{0}.zip'.format(archive)
    data.load(archive)
    return 'Success!' if data.is_valid() else 'Fail!\n' + data.load_error 

if __name__ == "__main__":
    app.run()
    
    