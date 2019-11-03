#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['create_package']

import shutil
import os.path
import codecs
import hashlib
import re
from common_utils import first_or_default, convert_to_utf8
from geddate import GedDate

# Загрузка базы данных и дерева единым пакетом
# Внутри: 
# tree.ged - выгрузка в формате gedcom
# tree.xml - выгрузка в фортмате xml
# tree_img.png - картинка с деревом или tree_img.svg
# tree_img.svg.files - портреты людей для загрузки в дереве
# tree_img.xml - карта узлов в дереве
# files.tsv - соответствие исходных имен файлов в tree.ged и относительных путей в папке files (tsv)
# files - папка с картинками

def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:len(text)-len(suffix)]
    
def create_folder(folder, empty=False):
    if empty and os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

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
        if img == 'tree_img.png' or img.endswith('_tree_img.png'):
            self.name = "" if img == 'tree_img.png' else strip_end(img, '_tree_img.png')
            self.vector = False
            self.xml = strip_end(img, '.png') + '.xml'
            self.files = None
        elif img == 'tree_img.svg' or img.endswith('_tree_img.svg'):
            self.name = "" if img == 'tree_img.svg' else strip_end(img, '_tree_img.svg')
            self.vector = True
            self.xml = None
            self.files = img + '.files'
        else:
            self.valid = False

        
        
def select_tree_img_files(folder):
    """Ищет *_tree_img.png или *_tree_img.svg файлы, составляет список требуемых *_tree_img.xml файлов"""
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
    if tree.xml:
        copy(src_dir, dst_dir, [tree.xml])
        convert_to_utf8(os.path.join(dst_dir, tree.xml))
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
        copy(export_dir, tmp_dir, ['tree.ged'])
        gedcom = os.path.join(tmp_dir, 'tree.ged')
        convert_to_utf8(gedcom)
        drop_tree_prefix_from_uid(gedcom)
        if os.path.exists(os.path.join(export_dir, 'tree.xml')):
            copy(export_dir, tmp_dir, ['tree.xml'])
            convert_to_utf8(os.path.join(tmp_dir, 'tree.xml'))
        for tree in trees:
            copy_tree_img(tree, export_dir, tmp_dir)
        files_dir = os.path.join(tmp_dir, 'files')    
        files = copy_documents(gedcom, files_dir)
        with codecs.open(os.path.join(tmp_dir, 'files.tsv'), 'w+', 'utf-8') as files_out:
            for path, copied in files.items():
                files_out.write('{0}\t{1}\n'.format(path, copied))        
        return shutil.make_archive(os.path.join(export_dir, archive_name), 'zip', tmp_dir) 
    finally:
        shutil.rmtree(tmp_dir)
  
#######################################################################
#### SERVER SIDE ######################################################
#######################################################################

from gedcom import GedcomReader, GedcomWriter, Gedcom
import xml.etree.ElementTree
from datetime import date

def set_default_documents_for_persons(gedcom, treexml):
    '''для ДЖ3: для каждого документа персоны находим "основной" и проставляем ему тег default (DFLT)
    '''
    # составляем словарь uid персоны -> title основного документа
    default_documents = dict()
    for person in treexml.iter('r'):
        person_uid = person.attrib['id']
        for document in person.iter('doc'):
            if document.get('default') == "T":
                title_element = document.find('title')
                if title_element is not None:
                    title = title_element.text
                    default_documents[person_uid] = title
                    break
                else:
                    print('Документ установленный как основной для ['+person.find('fullname').text +'] не имеет заголовка')
    # по созданному списку выставляем аттрибут DFLT для основных документов персоны
    for person in gedcom.persons:
        person_uid = person.get('_UID')
        if person_uid not in default_documents:
            continue
        has_default = False
        for document in person.documents:
            title = document.get('TITL')
            if default_documents[person_uid] == title:
                document['DFLT'] = 'T'
                has_default = True
                break
        if not has_default and len(person.documents) > 0:
            print('Person '+person_uid+' has not default document with title '+ default_documents[person_uid])



def validate_marriage(marriage, marriage_event):
    '''для ДЖ3: проверяем данные о бракосочетании
      (повторные браки плохо выгружаются в gedcom ДЖ3 и данные с xml могут не совпадать)
    '''
    valid = True
    date = marriage.find('date')
    gedcom_date = GedDate.Gedcom.format(GedDate.Genery.parse(date.text)) if date is not None else None
    if gedcom_date:
        if gedcom_date != marriage_event.get('DATE', None):
            print ('Date of marriage in gedcom: {} date in xml: {} ({})'.format(marriage_event.get('DATE'), date, gedcom_date))
            marriage_event['DATE'] = gedcom_date
            valid = False
    elif marriage_event.get('DATE', None):
        print ('Date of marriage in gedcom: {} date in xml: {} ({})'.format(marriage_event.get('DATE'))) 
        del marriage_event['DATE']
        valid = False
      
    comment = marriage.find('comment')
    comment = comment.text if comment is not None else None
    if comment:
        if (marriage_event.get('NOTE', '').split() != comment.split()):
            print ('Comment of marriage in gedcom: {} comment in xml: {}'.format(marriage_event.get('NOTE'), comment)) 
            marriage_event['NOTE'] = comment
            valid = False
    elif marriage_event.get('NOTE', None):
        print ('Comment of marriage in gedcom: {} comment in xml: None'.format(marriage_event.get('NOTE'))) 
        del marriage_event['NOTE']
        valid = False
        
    place = marriage.find('pl_short')
    place = place.text if place is not None else None
    if place:
        if marriage_event.get('PLAC', None) != place:
            print ('Place of marriage in gedcom: {} place in xml: {}'.format(marriage_event.get('PLAC'), place)) 
            marriage_event['PLAC'] = place
            valid = False
    elif marriage_event.get('PLAC', None):
        print ('Place of marriage in gedcom: {} place in xml: None'.format(marriage_event.get('PLAC')))
        del marriage_event['PLAC']
        valid = False
    
    if not valid:
        marriage_event.documents = []
        marriage_event.sources = []
    return valid

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
        
        
def validate_gedcom_with_xml(gedcom, treexml):
    '''для ДЖ3: устанавниваем событие развод для семьи (оно есть в treexml, но отсутствует в gedcom)'''
    # по gedcom составляем список (uid-супруга1, uid-супруга2) -> family
    person_id_to_uid = dict()
    for person in gedcom.persons:
        person_id_to_uid[person.id] = person.get('_UID', 'unknown')
    
    families_by_uids = dict()
    for family in gedcom.families:
        husb_uid = person_id_to_uid.get(family.get('HUSB'), '')
        wife_uid = person_id_to_uid.get(family.get('WIFE'), '')
        
        families_by_uids[(husb_uid, wife_uid)] = family
        families_by_uids[(wife_uid, husb_uid)] = family

    
        
    # по xml находим у людей события divorce, которые в gedcom не выгружаются
    for person in treexml.iter('r'):
        person_uid = person.attrib['id']
        for spouse in person.iter('spouse'):
            spouse_uid = spouse.get('id')
            family = families_by_uids.get((person_uid, spouse_uid)) or families_by_uids.get((spouse_uid, person_uid))
            if family is None:
                print('Family ', (person_uid, spouse_uid), ' is not found')
                continue
            
            marriage = spouse.find('marriage')
            marriage_event = first_or_default(family.events, lambda event: event.event_type=='MARR')
            if marriage is not None and marriage_event is not None:
                valid = validate_marriage(marriage, marriage_event)
                if not valid:
                    print ('Marriage of persons {} and {} does not valid'.format(person_uid, spouse_uid))                
                
            divorce = spouse.find('divorce')
            if divorce is not None:
                divorce_event = Gedcom.Event('DIV')
                date = divorce.find('date')
                if date is not None:
                    divorce_event['DATE'] = date.text
                comment = divorce.find('comment')
                if comment is not None:
                    divorce_event['NOTE'] = comment
                family.events.append(divorce_event)                

def set_documents_to_marriage(gedcom):
    '''для ДЖ3: документы указанные как документы семьи на самом деле относятся к событию свадьба'''
    for family in gedcom.families:
        marr = first_or_default(family.events, lambda event: event.event_type=='MARR')
        if marr:
            marr.documents = family.documents
            family.documents = []
            
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

def load_tree_img(tree, src_dir, static_dir, data_dir):
    if not tree.valid:
        return
    copy(src_dir, static_dir, [tree.img])
    if tree.vector:
        convert_svg(os.path.join(static_dir, tree.img))
    if tree.xml:
        copy(src_dir, data_dir, [tree.xml])
    if tree.files:
        files = list(os.listdir(os.path.join(src_dir, tree.files)))
        copy(os.path.join(src_dir, tree.files), os.path.join(static_dir, 'files', 'preview'), files)
    
def is_gedcom_drevo_v3(gedcom):
    if gedcom.meta and gedcom.meta.sources:
        source = gedcom.meta.souces[0]
        if source.get('NAME') == 'Древо Жизни' and source.get('VERS', '').startswith('3.'):
            return True
    return False


def load_package(archive, site, static_dir, data_dir):
    '''распаковывает архив базы данных
       static_dir - папка для картинок/документов
       data_dir - папка для данных
    '''
    tmp_dir = 'tmp/data'
    try:
        create_folder(tmp_dir, empty=True)
        shutil.unpack_archive(archive, tmp_dir)
        
        create_folder(static_dir, empty=True)
        create_folder(data_dir, empty=True)
        
        # обработка gedcom файла
        gedcom = GedcomReader().read_gedcom(os.path.join(tmp_dir, 'tree.ged'))
        if is_gedcom_drevo_v3(gedcom):
            treexml = xml.etree.ElementTree.fromstring(codecs.open(os.path.join(tmp_dir, 'tree.xml'), 'r', 'utf-8').read())
            set_default_documents_for_persons(gedcom, treexml)
            set_documents_to_marriage(gedcom)
            validate_gedcom_with_xml(gedcom, treexml)
        GedcomWriter().write_gedcom(gedcom, os.path.join(data_dir, 'tree.ged'))
        
        copy(tmp_dir, data_dir, ['files.tsv'])
        copy(tmp_dir, static_dir, ['files'])
        
        # копирование документов
        trees = select_tree_img_files(tmp_dir)
        for tree in trees:
            load_tree_img(tree, tmp_dir, static_dir, data_dir)
        
        with codecs.open(os.path.join(static_dir, 'sitemap.xml'), 'w', 'utf-8') as sitemap:
            sitemap.write(generage_sitemap(site, [tree.name for tree in trees], gedcom))

    finally:
        shutil.rmtree(tmp_dir)
 
        
       
    
