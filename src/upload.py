#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['create_package']

import shutil
import os.path
import codecs

# Загрузка базы данных и дерева единым пакетом
# Внутри: 
# tree.ged - выгрузка в формате gedcom
# tree.xml - выгрузка в фортмате xml
# tree_img.png - картинка с деревом
# tree_img.xml - карта узлов в дереве
# files.tsv - соответствие исходных имен файлов в tree.ged и относительных путей в папке files (tsv)
# files - папка с картинками

import random, string
def random_string(length, letters=None):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def create_folder(folder, empty=False):
    if empty and os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)    

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
            if uid is None:
                continue
            if line.startswith('2 FILE'):
                file_path = line[len('2 FILE'):].strip()
                if file_path in files:
                    continue
                if not os.path.exists(file_path):
                    continue
                # копируем файл в папку folder/uid
                person_folder = os.path.join(folder, uid)
                create_folder(person_folder)
                ext = os.path.splitext(file_path)[-1]
                new_filename = random_string(10)+ext    
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
        copy(export_dir, tmp_dir, ['tree.ged', 'tree.xml', 'tree_img.png', 'tree_img.xml'])
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

def set_divorce_events_to_families(gedcom, treexml):
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

        
    # по xml находим у людей события divorce
    for person in treexml.iter('r'):
        person_uid = person.attrib['id']
        for spouse in person.iter('spouse'):
            spouse_uid = spouse.get('id')
            family = families_by_uids.get((person_uid, spouse_uid)) or families_by_uids.get((spouse_uid, person_uid))
            if family is None:
                print('Family ', (person_uid, spouse_uid), ' is not found')
                continue
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
        marrs = list(filter(lambda event: event.event_type=='MARR', family.events))
        if len(marrs) > 0:
            marr = marrs[0]
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
        
        # обработка gedcom файла
        gedcom = GedcomReader().read_gedcom(os.path.join(tmp_dir, 'tree.ged'))
        treexml = xml.etree.ElementTree.fromstring(codecs.open(os.path.join(tmp_dir, 'tree.xml'), 'r', 'utf-8').read())
        set_default_documents_for_persons(gedcom, treexml)
        set_documents_to_marriage(gedcom)
        set_divorce_events_to_families(gedcom, treexml)
        GedcomWriter().write_gedcom(gedcom, os.path.join(data_dir, 'tree.ged'))
        # копирование документов
        copy(tmp_dir, static_dir, ['tree_img.png'])
        copy(tmp_dir, data_dir, ['tree_img.xml', 'files.tsv'])

        files_dir = 'static/tree/files'
        if os.path.exists(files_dir):
            shutil.rmtree(files_dir)
        shutil.copytree(src=os.path.join(tmp_dir, 'files'), dst=files_dir)
    finally:
        shutil.rmtree(tmp_dir)
    
    
        
       
    