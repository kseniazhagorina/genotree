# A very simple Flask Hello World app for you to get started with...

from flask import Flask, redirect

app = Flask(__name__)

new_url = 'http://me-in-history.ru'


@app.route('/')
def root():
    return redirect(new_url, code=301)


@app.route('/<path:page>')
def anypage(page):
    return redirect('{new_url}/{page}'.format(page=page, new_url=new_url),
                    code=301)