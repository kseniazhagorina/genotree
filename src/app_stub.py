#!usr/bin/env
# -*- coding: utf-8 -*-

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Site me-in-history.ru on reconstruction now.'
        
    
