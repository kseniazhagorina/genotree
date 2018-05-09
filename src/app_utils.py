#!usr/bin/env
# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree
import codecs
import chardet
import re
import random, string
from copy import copy
from datetime import date
from dateutil.relativedelta import relativedelta
from gedcom import GedcomReader
from geddate import GedDate
from genery_note import Note
from relatives import get_blood_relatives
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
    
def random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))    

def normalize_path(path):
    if path is None:
        return None
    if '156aDVYsQ2' in path:
        print ('normalize_path({}) = {}'.format(path, '/'.join(path.split('\\'))))    
    return '/'.join(path.split('\\'))
   
class dobj(dict):
    '''все что может быть сериализовано - в dict остальное в __dict__'''           
    @staticmethod
    def convert(value):
        if isinstance(value, (list, tuple)):
            converted_value = [dobj.convert(x) for x in value]
            return tuple(converted_value) if isinstance(value, tuple) else converted_value
        if isinstance(value, dict) and not isinstance(value, dobj):
            return dobj(dict((k, dobj.convert(v)) for k,v in value.items()))       
        return value
        
    @staticmethod
    def is_json(value):
        return value is None or isinstance(value, (str, int, float, bool, list, dict, tuple))

    def __init__(self, d=None):
        d = d or {}
        for key, value in d.items():
            self.__setattr__(key, value)

    def __getattr__(self, name):
        return self[name] if name in self else self.__dict__[name]
        
    def __setattr__(self, name, value):
        converted = dobj.convert(value)
        self.__delattr__(name)
        if dobj.is_json(value):
            self[name] = converted
        else:
            self.__dict__[name] = value
            
    def __delattr__(self, name):
        if name in self:
            del self[name]
        elif name in self.__dict__:
            del self.__dict__[name]
        
        


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

def choose_by_sex(sex, male, female, unknown=None):
    if sex == 'M':
        return male
    if sex == 'F':
        return female
    return unknown if unknown is not None else male

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
        def __init__(self, spouse=None, children=None, events=None):
            self.spouse = spouse #RelPerson
            self.children = children or [] #[RelPerson]
            self.events = events or [] #[Event]

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
        self.families = families or [] #[Family]
        self.relatives = {}
        self.photo = photo
        self.photos = photos or [] #[Document]
        self.sources = sources or [] #[Document]
        self.events = [] #[Event]

    def choose_by_sex(self, male, female, unknown=None):
        return choose_by_sex(self.sex, male, female, unknown)

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
        self.path = normalize_path(path)
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
        self.document_path = normalize_path(document_path) # путь до сохраненного документа-источника

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
            quote = Note.parse(opendet('src/static/tree/files/'+normalize_path(document.path)).read())
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

    @staticmethod
    def from_gedcom_event(event, sex, gedcom, files):
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
            event_head = choose_by_sex(sex, 'Родился', 'Родилась')
        elif event_type == 'DEAT':
            event_head = choose_by_sex(sex, 'Умер', 'Умерла')
        elif event_type == 'RESI':
            has_from_to = event_comment_row is not None and ('Откуда:' in event_comment_row or 'Куда:' in event_comment_row)
            if event_place is not None and not has_from_to:
                # это не событие, это место жительства
                event_type = 'RESIDENCE'
            else:
                # это событие переезд
                event_head = 'Переезд'
        elif event_type == 'EDUC':
            event_head = 'Обучение'
        elif event_type == 'OCCU':
            event_head = 'Устройство на работу'
        elif event_type == '__2':
            event_head = 'Служба в армии'
        elif event_type == 'MARR':
            event_head = choose_by_sex(sex, 'Женился', 'Вышла замуж')
        elif event_type == 'DIV':
            event_head = choose_by_sex(sex, 'Развелся', 'Развелась')

        return Event(type=event_type, head=event_head, date=event_date, place=event_place,
                     comment = event_comment, photo = event_photo, photos = event_photos,
                     sources = event_sources)

    @staticmethod
    def order(event):
        '''метод для получения ключа для упорядочивания персональных событий'''
        d = event.date.to_date() if event.date else None
        if event.type == 'BIRT':
            return (-1, d or GedDate.MIN) # рождение в начале
        if event.type == 'DEAT':
            return (1 if d is None else 0, d or GedDate.MIN) # смерть без даты в конце
        return (0, d or GedDate.MIN)

    @staticmethod
    def merge(personal_events, family_events):
        events = []
        p = 0
        f = 0
        while p < len(personal_events) and f < len(family_events):
            if Event.order(personal_events[p]) <= Event.order(family_events[f]):
                events.append(personal_events[p])
                p += 1
            else:
                events.append(family_events[f])
                f += 1
        if p < len(personal_events):
            events += personal_events[p:]
        if f < len(family_events):
            events += family_events[f:]
        return events

def get_person_snippets(gedcom, files):
    snippets = dict()
    indi_to_uid = dict()
    for person in gedcom.persons:
        person_uid = person['_UID']
        name = GedName.parse(person.get('NAME', ''))
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

        for e in person.events:
            event = Event.from_gedcom_event(e, sex, gedcom, files)

            if event.type == 'BIRT':
                snippet.birth = PersonSnippet.ShortEvent(date=event.date, place=event.place)
            if event.type == 'DEAT':
                snippet.death = PersonSnippet.ShortEvent(date=event.date, place=event.place)
            if event.type == 'RESIDENCE':
                snippet.residence = event.place

            if event.head is not None:
                snippet.events.append(event)


        snippet.events = list(sorted(snippet.events, key=Event.order))
        snippets[person_uid] = snippet

    for family in gedcom.families:
        wife = snippets.get(indi_to_uid.get(family.get('WIFE')), None)
        husband = snippets.get(indi_to_uid.get(family.get('HUSB')), None)
        children = []
        children_birth = []

        def get_children(family):
            '''все дети в семье отсортированные по дате рождения'''
            children = []
            for child_indi in family.get('CHIL', []):
                child = snippets.get(indi_to_uid.get(child_indi), None)
                if child is None:
                    print ('cant find child with id ['+child_indi+']')
                    continue
                children.append(child)
            return list(sorted(children, key=lambda child: child.birth.date.to_date() or GedDate.MIN if child.birth and child.birth.date else GedDate.MIN))

        for child in get_children(family):
            child.mother.person = wife
            child.father.person = husband
            child_role = child.choose_by_sex('Сын', 'Дочь', 'Ребенок')
            children.append(RelPerson(child_role, child))

            # событие для родителей - участник - ребенок
            birth = copy(first_or_default(child.events, lambda e: e.type == 'BIRT', Event(type='BIRT', head=None)))
            birth.type = 'CHIL'
            birth.head = child.choose_by_sex('Родился', 'Родилась') + ' ' + (child.name.name or child.choose_by_sex('сын', 'дочь', 'ребенок'))
            birth.members = birth.members + [RelPerson(child.choose_by_sex('Родился', 'Родилась'), child)]
            children_birth.append(birth)

            # событие для ребенка - участники - родители
            birth = first_or_default(child.events, lambda e: e.type == 'BIRT')
            if birth:
                if child.father.person:
                    birth.members.append(child.father)
                if child.mother.person:
                    birth.members.append(child.mother)

        marr = first_or_default(family.events, lambda e: e.event_type == 'MARR')
        div = first_or_default(family.events, lambda e: e.event_type == 'DIV')

        def get_family_for(person1, person2=None):
            spouse = RelPerson(person2.choose_by_sex('Супруг', 'Супруга'), person2) if person2 else None
            parent = RelPerson(person2.choose_by_sex('Отец', 'Мать'), person2) if person2 else None
            events = []
            if marr:
                marr_event = Event.from_gedcom_event(marr, person1.sex, gedcom, files)
                if spouse:
                    marr_event.members.append(spouse)
                events.append(marr_event)
            for birth in children_birth:
                birth_event = copy(birth)
                if parent:
                    birth_event.members = birth_event.members + [parent]
                events.append(birth_event)
            if div:
                div_event = Event.from_gedcom_event(div, person1.sex, gedcom, files)
                if spouse:
                    div_event.members.append(spouse)
                events.append(div_event)


            return PersonSnippet.Family(spouse, children, events)

        if wife:
            wife.families.append(get_family_for(wife, husband))
        if husband:
            husband.families.append(get_family_for(husband, wife))



    def first_date_of(events):
        mind = None
        for e in events:
            d = e.date.to_date() if e.date else None
            if d is not None and (mind is None or d < mind):
                mind = d
        return mind


    for person in snippets.values():
        person.families = list(sorted(person.families, key=lambda fam: first_date_of(fam.events) or GedDate.MIN))
        family_events = []
        for family in person.families:
            family_events += family.events
        person.events = Event.merge(person.events, family_events)

    for person in snippets.values():
        person.relatives = get_blood_relatives(person)
        
    return snippets

def get_person_owners(persons_snippets):
    '''Находим ссылки на страницы в соц.сетях в комментариях к персонам и в источниках'''
    vk = re.compile(r'https?://(vk\.com|vkontakte\.ru)/(?P<id>[\w\.]+)')
    ok = re.compile(r'https?://(ok|odnoklassniki)\.ru/(?:profile/)?(?P<id>[\w\.]+)')
    owners = set() # (service, login, person_uid)
    for uid, person in persons_snippets.items():
        text = str(person.comment) if person.comment else ''
        for match in  vk.finditer(text):
            id = match.group('id')
            owners.add(('vk', id, uid))
        for match in  ok.finditer(text):
            id = match.group('id')
            owners.add(('ok', id, uid))
    return owners    

def get_files_dict(filename):
    dict = {}
    with codecs.open(filename, 'r', 'utf-8') as input:
        for line in input:
            k, v = line.strip().split('\t')
            dict[k] = v
    return dict








