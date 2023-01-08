#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['create_package']

import shutil
import os.path
import codecs
import hashlib
import re
from common_utils import first_or_default, convert_to_utf8, create_folder
from geddate import GedDate

# Загрузка базы данных и дерева единым пакетом
# Внутри: 
# tree.ged - выгрузка в формате gedcom
# tree_img.svg - картинка с деревом в svg формате
# tree_img.svg.files - портреты людей для загрузки в дереве
# files.tsv - соответствие исходных имен файлов в tree.ged и относительных путей в папке files (tsv)
# files - папка с картинками

def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:len(text)-len(suffix)]
   

def copy(src_dir, dst_dir, filenames):
    create_folder(dst_dir)    
    for file in filenames:
        src_path = os.path.join(src_dir, file)
        dst_path = os.path.join(dst_dir, file)
        if not os.path.exists(src_path):
            raise Exception('File {0} does not exists'.format(src_path))
        if os.path.isfile(src_path):
            shutil.copy(src_path, dst_path)
        else:
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src=src_path, dst=dst_path)
        

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class TreeImg:
    def __init__(self, img):
        self.img = img
        self.valid = True
        if img == 'tree_img.svg' or img.endswith('_tree_img.svg'):
            self.name = "" if img == 'tree_img.svg' else strip_end(img, '_tree_img.svg')
            self.files = img + '.files'
        else:
            self.valid = False

        
        
def select_tree_img_files(folder):
    """Ищет *_tree_img.svg файлы"""
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    imgs = []
    for f in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, f)):
            img = TreeImg(f)
            if img.valid:
                imgs.append(img)
    return imgs
               
    
    
###################################################################################
##### CLIENT SIDE #################################################################
###################################################################################

def drop_tree_prefix_from_uid(gedcom):
    '''
    В ДЖ5 UID персоны выглядит как TREEID123_456 где TREEID123 один и тот же для всех персон
    '''
    outlines = []
    with codecs.open(gedcom, 'r', 'utf-8') as input:
        for line in input:
            if line.startswith('1 _UID'):
                uid = line[len('1 _UID'):].strip()
                uid = uid.split('_', maxsplit=1)
                if len(uid) <= 1:
                    return # tree prefix already dropped
                outlines.append('1 _UID {}\n'.format(uid[1]))
            else:
                outlines.append(line)
                
    with codecs.open(gedcom, 'w+', 'utf-8') as output:
        for line in outlines:
            output.write(line)
                
        
def copy_documents(gedcom, folder):
    '''
    Копируем нужные файлы с компьютера в папку folder
    Обрабатываем только файлы персон (строки вида "2 FILE D:/Some/File/path.jpg")
    '''
    create_folder(folder, empty=True)
    files = {}
    with codecs.open(gedcom, 'r', 'utf-8') as input:
        uid = None
        for line in input:
            if line.startswith('1 _UID'):
                uid = 'p' + line[len('1 _UID'):].strip()
                continue
            m = re.search('0 @F(?P<family>\d+)@ FAM', line)
            if m is not None:
                uid = 'f' + m.group('family')
                continue
            if uid is None:
                continue
            if line.startswith('2 FILE') or line.startswith('3 FILE'):
                file_path = line[len('2 FILE'):].strip()
                if file_path in files:
                    continue
                if not os.path.exists(file_path):
                    continue
                if '(private)' in file_path:
                    continue
                # копируем файл в папку folder/uid
                person_folder = os.path.join(folder, uid)
                create_folder(person_folder)
                ext = os.path.splitext(file_path)[-1]
                new_filename = md5(file_path)+ext    
                new_file_path = os.path.join(person_folder, new_filename)
                shutil.copy(src=file_path, dst=new_file_path)
                files[file_path] = os.path.join(uid, new_filename)
    return files               

def copy_tree_img(tree, src_dir, dst_dir):
    if not tree.valid:
        return
    copy(src_dir, dst_dir, [tree.img])
    if tree.files:
        copy(src_dir, dst_dir, [tree.files])

            
def create_package(export_dir, archive_name):
    '''export_dir - папка с экспортированными из genery данными
       dst - имя архива
    '''
    tmp_dir = os.path.join(export_dir, 'data')
    try:
        create_folder(tmp_dir, empty=True)
        trees = select_tree_img_files(export_dir)
        print('copy tree.ged')
        copy(export_dir, tmp_dir, ['tree.ged'])
        gedcom = os.path.join(tmp_dir, 'tree.ged')
        convert_to_utf8(gedcom)
        drop_tree_prefix_from_uid(gedcom)
        print('copy tree_img.svg files')
        for tree in trees:
            copy_tree_img(tree, export_dir, tmp_dir)
        files_dir = os.path.join(tmp_dir, 'files')  
        print('copy documents')        
        files = copy_documents(gedcom, files_dir)
        with codecs.open(os.path.join(tmp_dir, 'files.tsv'), 'w+', 'utf-8') as files_out:
            for path, copied in files.items():
                files_out.write('{0}\t{1}\n'.format(path, copied))
        print('make archive')                
        return shutil.make_archive(os.path.join(export_dir, archive_name), 'zip', tmp_dir) 
    finally:
        shutil.rmtree(tmp_dir)
  
#######################################################################
#### SERVER SIDE ######################################################
#######################################################################

from gedcom import GedcomReader, GedcomWriter, Gedcom
import xml.etree.ElementTree
from datetime import date


def convert_svg(svg_file):
    '''преобразует svg файл так, чтобы ссылки на картинки вели в static/tree/preview/xxx.jpg
       у нужных блоков был бы прописан класс 'select-person' и атрибут 'person-uid'
    '''
    files_dir_name = os.path.split(svg_file)[1] + '.files'
    svg = None
    with codecs.open(svg_file, 'r', 'utf-8') as f:
        svg = f.read()
    svg = re.sub(r'\sat:id="(\d+)"', r' class="select-person" person-uid="\1"', svg)
    svg = svg.replace(files_dir_name, '/static/tree/files/preview')
    svg = svg.replace('xlink:href=', 'href="/static/1x1_white.png" lazy-href=')      
    with codecs.open(svg_file, 'w+', 'utf-8') as f:
        f.write(svg)

            
def generage_sitemap(site, trees, gedcom):
    root = xml.etree.ElementTree.Element('urlset')
    root.attrib['xmlns'] = "http://www.sitemaps.org/schemas/sitemap/0.9"
    
    urls = []
    for tree_name in trees:
        urls.append(site + '/' + tree_name)
    for person in gedcom.persons:
        person_uid = person.get('_UID')
        if person_uid:
            urls.append(site + '/person/' + person_uid)
    
    for page in urls:
        url = xml.etree.ElementTree.SubElement(root, 'url')
        loc = xml.etree.ElementTree.SubElement(url, 'loc')
        loc.text = page
        lastmod = xml.etree.ElementTree.SubElement(url, 'lastmod')
        lastmod.text = date.today().strftime('%Y-%m-%d')
        
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml.etree.ElementTree.tostring(root, encoding='utf-8').decode('utf-8') + '\n'

def load_tree_img(tree, src_dir, static_dir):
    if not tree.valid:
        return
    copy(src_dir, static_dir, [tree.img])
    convert_svg(os.path.join(static_dir, tree.img))
    if tree.files:
        files = list(os.listdir(os.path.join(src_dir, tree.files)))
        copy(os.path.join(src_dir, tree.files), os.path.join(static_dir, 'files', 'preview'), files)


def load_package(archive, site, static_dir, data_dir, tmp_dir):
    '''распаковывает архив базы данных
       static_dir - папка для картинок/документов
       data_dir - папка для данных
    '''
    try:
        create_folder(tmp_dir, empty=True)
        print('unpack archive')
        shutil.unpack_archive(archive, tmp_dir)
        
        create_folder(static_dir, empty=True)
        create_folder(data_dir, empty=True)
        
        # обработка gedcom файла
        print('copy tree.ged')
        gedcom = GedcomReader().read_gedcom(os.path.join(tmp_dir, 'tree.ged'))
        GedcomWriter().write_gedcom(gedcom, os.path.join(data_dir, 'tree.ged'))
        
        print('copy documents')
        copy(tmp_dir, data_dir, ['files.tsv'])
        copy(tmp_dir, static_dir, ['files'])
        
        print('copy tree_img.svg files')
        trees = select_tree_img_files(tmp_dir)
        for tree in trees:
            load_tree_img(tree, tmp_dir, static_dir)
        
        with codecs.open(os.path.join(static_dir, 'sitemap.xml'), 'w', 'utf-8') as sitemap:
            sitemap.write(generage_sitemap(site, [tree.name for tree in trees], gedcom))

    finally:
        shutil.rmtree(tmp_dir)
 
        
       
    
