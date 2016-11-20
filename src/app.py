#!usr/bin/env
# -*- coding: utf-8 -*-

from app_utils import get_tree, get_tree_map, get_person_snippets, get_privacy_settings, get_files_dict
from gedcom import GedcomReader
from upload import load_package

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True

class Data:
    def load(self, archive=None):
        if archive is not None:
            load_package(archive, 'static/tree', 'data/tree')
        self.tree_img = '/static/tree/tree_img.png'
        self.files_dir = '/static/tree/files'
        self.files = get_files_dict('data/tree/files.tsv')
        self.tree_map = get_tree_map('data/tree/tree_img.xml')
        self.gedcom = GedcomReader().read_gedcom('data/tree/tree.ged')
        self.persons_snippets = get_person_snippets(self.gedcom, self.files)
        self.privacy_settings = get_privacy_settings(self.persons_snippets)
    
    
data = Data()        
data.load()

@app.route('/')
def tree():
    return render_template('tree.html', data=data)
    
@app.route('/admin/load/<archive>')
def load(archive):
    load_package('data/{0}.zip'.format(archive))
    data.load(archive)

if __name__ == "__main__":
    app.run()
    
    