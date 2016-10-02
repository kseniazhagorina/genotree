#!usr/bin/env
# -*- coding: utf-8 -*-

from app_utils import get_tree, get_tree_map, get_person_snippets
from gedcom import GedcomReader

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True

tree_map = get_tree_map('data/tree_img.xml')
gedcom = GedcomReader().read_gedcom('data/tr_tree.ged')
persons_snippets = get_person_snippets(gedcom)

@app.route('/')
def tree():
    return render_template('tree.html', map=tree_map, person_snippets=persons_snippets)

if __name__ == "__main__":
    app.run()
    
    