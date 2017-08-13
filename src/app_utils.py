#!usr/bin/env
# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree
import codecs
import chardet
import re
from datetime import date
from dateutil.relativedelta import relativedelta
from gedcom import GedcomReader
from geddate import GedDate
from genery_note import Note
from privacy import PrivacyMode, Privacy

def opendet(filename):
    with open(filename, 'rb') as f:
        enc = chardet.detect(f.read())
    return codecs.open(filename, 'r', encoding=enc['encoding'])

def first_or_default(arr, predicate=None, default=None):
    for item in arr:
        if predicate is None or predicate(item):
            return item
    return default


class TreeMap:
    class Node:
        def __init__(self, node):
            self.uid = node.attrib['id']
            self.x1 = node.attrib['x1']
            self.y1 = node.attrib['y1']
            self.x2 = node.attrib['x2']
            self.y2 = node.attrib['y2']
            self.rect = ','.join([self.x1, self.y1, self.x2, self.y2])

    def __init__(self, root):
        self.date = root.attrib['date']
        self.height = root.attrib['height']
        self.width = root.attrib['width']
        self.nodes = dict()
        for xml_node in root.iter('n'):
            tree_node = TreeMap.Node(xml_node)
            self.nodes[tree_node.uid] = tree_node

def get_tree_map(filename):
    root = xml.etree.ElementTree.parse(filename).getroot()
    tree_map = TreeMap(root)
    return tree_map

def get_tree(gedcom_filename):
    return GedcomReader().read_gedcom(gedcom_filename)


class GedName:
    def __init__(self, name=None, patronymic=None, surname=None, surname_at_birth=None, unparsed=None):
        self.name = name or ""
        self.patronymic = patronymic or ""
        self.surname = surname or ""
        self.surname_at_birth = surname_at_birth or ""
        self.unparsed = unparsed

    def __repr__(self):
        if self.unparsed is not None:
            return self.unparsed
        parts = []
        if self.surname != "":
            parts.append(self.surname)
        if self.surname_at_birth != "" and self.surname_at_birth != self.surname:
            parts.append('('+self.surname_at_birth+')')
        parts.append(self.name if self.name != "" else '...')
        if self.patronymic != "":
            parts.append(self.patronymic)
        return ' '.join(parts)

    # Александр Сергеевич /Пушкин/
    # Наталья Николаевна /Пушкина (Гончарова)/
    gedcom_name_regex = re.compile('^(((?P<name>[\w\?-]*) )?(?P<patronymic>[\w\?-]*) )?/(?P<surname>[\w\?-]*)\s*(\((?P<surname_at_birth>[\w\?-]*)\))?/$')
    @staticmethod
    def parse(s):
        m = GedName.gedcom_name_regex.match(s)
        if m is not None:
            name = m.groupdict().get('name')
            patronymic = m.groupdict().get('patronymic')
            surname = m.groupdict().get('surname')
            surname_at_birth = m.groupdict().get('surname_at_birth')
            return GedName(name=name, patronymic=patronymic, surname=surname, surname_at_birth=surname_at_birth)
        return GedName(unparsed=s.strip())

class RelPerson:
    '''человек+отношение'''
    def __init__(self, role, person=None):
        self.role = role
        self.person = person #PersonSnippet
        
class PersonSnippet:
    '''модель для отображения сниппета о персоне на странице дерева'''
    class ShortEvent:
        '''краткая информация о событии, отображаемая в сниппете на странице дерева'''
        def __init__(self, date=None, place=None, info=None):
            self.date = date
            self.place = place
            self.info = info # доп.информация отображаемая в скобочках
    
    class Family:
        def __init__(self, spouse=None, children=None):
            self.spouse = spouse #RelPerson
            self.children = children #RelPerson

    def __init__(self, person_uid,
                 name=None, sex=None, birth=None, death=None,
                 main_occupation=None, residence=None,
                 photo=None, photos=None, sources=None, comment=None,
                 mother=None, father=None, families=None):
        self.uid = person_uid
        self.name = name
        self.sex = sex
        self.birth = birth #ShortEvent
        self.death = death #ShortEvent
        self.main_occupation = main_occupation
        self.residence = residence
        self.comment = comment
        self.mother = mother #RelPerson
        self.father = father #RelPerson
        self.families = families or []
        self.photo = photo
        self.photos = photos or []
        self.sources = sources or []
        self.events = []

    def choose_by_sex(self, male, female, unknown=None):
        if self.sex == 'M':
            return male
        if self.sex == 'F':
            return female
        return unknown if unknown is not None else male

    def is_alive(self):
        return self.death is None

    def age(self):
        birth_date = self.birth.date.to_date() if self.birth and self.birth.date else None
        death_date = self.death.date.to_date() if self.death and self.death.date else None
        end_date = date.today() if self.is_alive() else death_date
        if birth_date is not None and end_date is not None:
            return relativedelta(end_date, birth_date).years
        else:
            return None

            
class Document:
    def __init__(self, path, title=None):
        self.path = path
        self.title = title

def get_documents(documents, files):
    '''документы персоны или события распределить на фотографии и документы-источники'''
    photos = []
    docs = []
    for document in sorted(documents, key = lambda d: d.get('DFLT') == 'T', reverse=True): # сначала DFLT документ
        file = files.get(document.get('FILE', ''))

        if file:
            ext = os.path.splitext(file)[-1].lower()
            title = document.get('TITL', '')
            document = Document(path=file, title=title)
            if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.gif']:
                photos.append(document)
            else:
                docs.append(document)
    return photos, docs


class Source:
    def __init__(self, name, page, quote, document_path):
        '''quote - Note'''
        self.name = name
        self.page = page
        self.quote = quote
        self.document_path = document_path # путь до сохраненного документа-источника

    @staticmethod
    def create_from_source(source, source_link):
        name = source.get('TITL', None)
        page = source_link.get('PAGE')
        quote = Note((Note.parse(source_link.get('NOTE')) or Note()).sections + (Note.parse(source.get('TEXT')) or Note()).tags_sections)
        return Source(name, page, quote, None)

    @staticmethod
    def create_from_document(document):
        ext = os.path.splitext(document.path)[-1].lower()
        name = document.title
        if ext == '.txt':
            quote = Note.parse(opendet('src/static/tree/files/'+document.path.replace('\\', '/')).read())
            return Source(name, None, quote, None)
        return Source(name, None, None, document.path)

    @staticmethod
    def create_from_sources(sources, source_links):
        for s_link in source_links:
            source = first_or_default(sources, lambda s: s.id == s_link.id)
            if source:
                yield Source.create_from_source(source, s_link)

    @staticmethod
    def create_from_documents(documents):
        for document in documents:
            yield Source.create_from_document(document)
            
class Event:
    '''Событие для отображения на странице биографии пользователя'''
    def __init__(self, type, head, date=None, place=None, members=None, 
                 photo=None, photos=None, sources=None, comment=None):
        self.type = type
        self.head = head
        self.date = date
        self.place = place
        self.comment = comment
        self.members = members or [] # [RelPerson]
        self.photo = photo
        self.photos = photos or []
        self.sources = sources or []
        
    
def get_person_snippets(gedcom, files):
    snippets = dict()
    indi_to_uid = dict()
    for person in gedcom.persons:
        person_uid = person['_UID']
        name = str(GedName.parse(person.get('NAME', '')))
        sex = person.get('SEX', None)
        main_occupation = person.get('OCCU', None)
        comment = Note.parse(person.get('NOTE', None))
        photos, docs = get_documents(person.documents, files)
        photo = first_or_default(photos)

        sources = list(Source.create_from_sources(gedcom.sources, person.sources)) + list(Source.create_from_documents(docs))
        indi_to_uid[person.id] = person_uid
        snippet = PersonSnippet(person_uid,
                                name=name,
                                sex=sex,
                                photos=photos,
                                photo=photo,
                                sources = sources,
                                main_occupation=main_occupation,

                                # позже при обработке семей будут назначены реальные люди
                                mother=RelPerson('Мать'),
                                father=RelPerson('Отец'),
                                comment=comment)
                                
        for event in person.events:
            event_type = event.event_type 
            event_date = GedDate.parse(event.get('DATE', ''))
            event_place = event.get('PLAC', None)
            event_comment_row = event.get('NOTE', None)
            event_comment = Note.parse(event_comment_row)
            event_photos, event_docs = get_documents(event.documents, files)
            event_photo = first_or_default(event_photos)
            event_sources = list(Source.create_from_sources(gedcom.sources, event.sources)) + list(Source.create_from_documents(event_docs))
            event_head = None

            if event_type == 'BIRT':
                event_head = snippet.choose_by_sex('Родился', 'Родилась')
                snippet.birth = PersonSnippet.ShortEvent(date=event_date, place=event_place)
            if event_type == 'DEAT':
                event_head = snippet.choose_by_sex('Умер', 'Умерла')
                snippet.death = PersonSnippet.ShortEvent(date=event_date, place=event_place)
            if event_type == 'RESI':
                has_from_to = event_comment_row is not None and ('Откуда:' in event_comment_row or 'Куда:' in event_comment_row)
                if event_place is not None and not has_from_to:
                    # это не событие, это место жительства
                    snippet.residence = event_place
                else:
                    # это событие переезд
                    event_head = 'Переезд'
            if event_type == 'EDUC':
                event_head = 'Обучение'
            if event_type == 'OCCU':
                event_head = 'Устройство на работу'
            if event_type == '__2':
                event_head = 'Служба в армии'
            
            if event_head is not None:
                snippet.events.append(
                    Event(type=event_type, head=event_head, date=event_date, place=event_place, 
                          comment = event_comment, photo = event_photo, photos = event_photos,
                          sources = event_sources))

        
        snippets[person_uid] = snippet

    for family in gedcom.families:
        wife = snippets.get(indi_to_uid.get(family.get('WIFE')), None)
        husband = snippets.get(indi_to_uid.get(family.get('HUSB')), None)
        children = []
        for child_indi in family.get('CHIL', []):
            child = snippets.get(indi_to_uid.get(child_indi), None)
            if child is None:
                print ('cant find child with id ['+child_indi+']')
                continue
            child.mother.person = wife
            child.father.person = husband
            child_role = child.choose_by_sex('Сын', 'Дочь', 'Ребенок')
            children.append(RelPerson(child_role, child))
        if wife:
            spouse = RelPerson('Супруг', husband)
            wife.families.append(PersonSnippet.Family(spouse, children))
        if husband:
            spouse = RelPerson('Супруга', wife)
            husband.families.append(PersonSnippet.Family(spouse, children))

    return snippets

def get_files_dict(filename):
    dict = {}
    with codecs.open(filename, 'r', 'utf-8') as input:
        for line in input:
            k, v = line.strip().split('\t')
            dict[k] = v
    return dict








