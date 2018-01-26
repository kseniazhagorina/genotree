#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['create_package']

import shutil
import os.path
import codecs
import hashlib
import re
from app_utils import first_or_default
from geddate import GedDate

# Загрузка базы данных и дерева единым пакетом
# Внутри: 
# tree.ged - выгрузка в формате gedcom
# tree.xml - выгрузка в фортмате xml
# tree_img.png - картинка с деревом
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

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
    
def select_tree_img_files(folder):
    """Ищет *_tree_img.png файлы, составляет список требуемых *_tree_img.xml файлов"""
    png_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and (f == 'tree_img.png' or f.endswith('_tree_img.png'))]
    xml_files = [strip_end(f, '.png')+'.xml' for f in png_files]
    names = ["" if f == 'tree_img.png' else strip_end(f, '_tree_img.png') for f in png_files]
    return names, png_files, xml_files
               
    
    
###################################################################################
##### CLIENT SIDE #################################################################
###################################################################################
        
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
                uid = line[len('1 _UID'):].strip()
                continue
            m = re.search('0 @F(?P<family>\d+)@ FAM', line)
            if m is not None:
                uid = m.group('family')
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

def copy(src_dir, dst_dir, filenames):
    create_folder(dst_dir)
    for file in filenames:
        src_path = os.path.join(src_dir, file)
        dst_path = os.path.join(dst_dir, file)
        if not os.path.exists(src_path):
            raise Exception('File {0} does not exists'.format(src_path))
        shutil.copy(src_path, dst_path)    
            
            
def create_package(export_dir, archive_name):
    '''export_dir - папка с экспортированными из genery данными
       dst - имя архива
    '''
    tmp_dir = os.path.join(export_dir, 'data')
    try:
        create_folder(tmp_dir, empty=True)
        _, png_files, xml_files = select_tree_img_files(export_dir)
        copy(export_dir, tmp_dir, ['tree.ged', 'tree.xml'] + png_files + xml_files)
        files_dir = os.path.join(tmp_dir, 'files')
        files = copy_documents(os.path.join(export_dir, 'tree.ged'), files_dir)
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

def set_default_documents_for_persons(gedcom, treexml):
    '''для каждого документа персоны находим "основной" и проставляем ему тег default (DFLT)'''
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
    '''проверяем данные о бракосочетании
      (повторные браки плохо выгружаются в gedcom и данные с xml могут не совпадать)
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
        
def validate_gedcom_with_xml(gedcom, treexml):
    '''Устанавниваем событие развод для семьи (оно есть в treexml, но отсутствует в gedcom)'''
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
    '''документы указанные как документы семьи на самом деле относятся к событию свадьба'''
    for family in gedcom.families:
        marr = first_or_default(family.events, lambda event: event.event_type=='MARR')
        if marr:
            marr.documents = family.documents
            family.documents = [] 
                
def load_package(archive, static_dir, data_dir):
    '''распаковывает архив базы данных
       static_dir - папка для картинок/документов
       data_dir - папка для данных
    '''
    tmp_dir = 'tmp/data'
    try:
        create_folder(tmp_dir, empty=True)
        shutil.unpack_archive(archive, tmp_dir)
        
        create_folder(static_dir)
        create_folder(data_dir)
        
        # обработка gedcom файла
        gedcom = GedcomReader().read_gedcom(os.path.join(tmp_dir, 'tree.ged'))
        treexml = xml.etree.ElementTree.fromstring(codecs.open(os.path.join(tmp_dir, 'tree.xml'), 'r', 'utf-8').read())
        set_default_documents_for_persons(gedcom, treexml)
        set_documents_to_marriage(gedcom)
        validate_gedcom_with_xml(gedcom, treexml)
        GedcomWriter().write_gedcom(gedcom, os.path.join(data_dir, 'tree.ged'))
        # копирование документов
        _, png_files, xml_files = select_tree_img_files(tmp_dir)
        copy(tmp_dir, static_dir, png_files)
        copy(tmp_dir, data_dir, ['files.tsv'] + xml_files)

        files_dir = os.path.join(static_dir, 'files')
        if os.path.exists(files_dir):
            shutil.rmtree(files_dir)
        shutil.copytree(src=os.path.join(tmp_dir, 'files'), dst=files_dir)
    finally:
        shutil.rmtree(tmp_dir)
    
    
        
       
    