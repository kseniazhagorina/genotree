#!usr/bin/env
# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree
import codecs
import traceback
import re
import random, string
import json
from collections import defaultdict
from copy import copy
from datetime import date
from dateutil.relativedelta import relativedelta
from gedcom import GedcomReader
from geddate import GedDate
from genery_note import Note
from relatives import get_blood_relatives
from common_utils import *
from upload import load_package, select_tree_img_files


class TreeMapSvg:
    class Node:
        def __init__(self, id):
            self.id = id

    def __init__(self, content):
        self.nodes = {}
        self.svg_content = content[content.find('<svg'):]
        for m in re.finditer(r'person-uid="(?P<uid>\d+)"', content):
            uid = m.group('uid')
            self.nodes[uid] = TreeMapSvg.Node(uid)

def get_tree_map(filename):
    if filename.endswith('.svg'):
        with codecs.open(filename, 'r', 'utf-8') as svg:
            return TreeMapSvg(svg.read())
    raise Exception('not supported for tree map file type: {}'.format(filename))

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
        '''Семья по отношению к конкретному человеку (ребенку или супругу)'''
        def __init__(self, family_id, me, husband=None, wife=None, children=None, events=None):
            self.id = family_id
            self.me = me #RelPerson

            # не None если я - супруг/супруга
            self.spouse = None #RelPerson

            # не None если я - один из детей
            self.mother = None #RelPerson
            self.father = None #RelPerson
            self.is_parent_family = False # это родительская семья для me

            self.children = [] #[RelPerson]
            self.events = [copy(event) for event in events] #[Event]

            if me.role in ['Мать', 'Отец']:
                person2 = first_or_default([husband, wife], lambda p: p is not None and p.uid != me.person.uid)
                if person2:
                    self.spouse = RelPerson(person2.choose_by_sex('Супруг', 'Супруга'), person2)
                    for e in self.events:
                        # тут только MARR и DIV
                        e.members = e.members + [self.spouse]
                        e.head = Event.get_event_head(e.type, me.person.sex)

                for child in children:
                    child_role = child.choose_by_sex('Сын', 'Дочь', 'Ребенок')
                    self.children.append(RelPerson(child_role, child))

            elif me.role in ['Сын', 'Дочь', 'Ребенок']:
                if me.person.father.person == husband and me.person.mother.person == wife:
                    if wife:
                        self.mother = RelPerson('Мать', wife)
                    if husband:
                        self.father = RelPerson('Отец', husband)
                    self.is_parent_family = True

                    for e in self.events:
                        e.head = Event.get_event_head(e.type, sex='U')
                        for spouse in [husband, wife]:
                            if spouse:
                                e.members = list(e.members) + [RelPerson(spouse.choose_by_sex('Супруг(отец)', 'Супруга(мать)'), spouse)]

                elif me.person.father.person == husband:
                    # новый брак отца
                    self.mother = RelPerson('Жена отца', wife)

                    for e in self.events:
                        e.head = Event.get_event_head(e.type, sex='U')
                        for spouse in [husband, wife]:
                            if spouse:
                                e.members = list(e.members) + [RelPerson(spouse.choose_by_sex('Супруг(отец)', 'Супруга(мачеха)'), spouse)]

                elif me.person.mother.person == wife:
                    # новый брак матери
                    self.father = RelPerson('Муж матери', husband)

                    for e in self.events:
                        e.head = Event.get_event_head(e.type, sex='U')
                        for spouse in [husband, wife]:
                            if spouse:
                                e.members = list(e.members) + [RelPerson(spouse.choose_by_sex('Супруг(отчим)', 'Супруга(мать)'), spouse)]

                for child in children:
                    child_role = child.choose_by_sex('Брат', 'Сестра', 'Сиблинг') if child.uid != me.person.uid else 'Я'
                    self.children.append(RelPerson(child_role, child))

            self.first_date = Event.first_date_of(self.events + self.children_birth_events(filter_for_me=False))
            self.last_date = Event.last_date_of(self.events + self.children_birth_events(filter_for_me=False))

        def children_birth_events(self, filter_for_me=True):
            '''рождения детей в браке'''

            births = []
            for child in self.children:
                # событие рождение ребенка для родителей или братьев/сестер
                # участник - ребенок
                birth = copy(first_or_default(child.person.events, lambda e: e.type == 'BIRT', Event(type='BIRT', head=None)))
                birth.type = 'FAML'
                birth.head = child.person.choose_by_sex('Родился', 'Родилась') + ' ' + child.role.lower()
                birth.members = [RelPerson(child.person.choose_by_sex('Родился', 'Родилась'), child.person)] + birth.members
                births.append(birth)

                if filter_for_me:
                    # если точные даты рождения детей неизвестны ориентирумся на порядок
                    # рождения братьев до меня - не являются событиями в моей жизни
                    if child.person.uid == self.me.person.uid:
                        births = []

            return births


        def marr_div_events(self):
            events = []
            me = self.me
            for event in self.events:
                event_date = (event.date.to_date() if event.date else
                              self.first_date if event.type == 'MARR' else
                              self.last_date if event.type == 'DIV' else
                              None)
                if event_date:
                    if me.person.birth and me.person.birth.date and event_date <= me.person.birth.date.to_date():
                        continue
                    elif me.person.death and me.person.death.date and event_date > me.person.death.date.to_date():
                        continue

                if self.me.role in ['Сын', 'Дочь', 'Ребенок']:
                    if event_date is None or me.person.birth is None or me.person.birth.date is None:
                        if event.type == 'MARR' and self.is_parent_family:
                            # скорее всего свадьба была до рождения детей в этой семье
                            continue
                events.append(event)
            return events

        def death_events(self):
            '''смерти членов семьи'''
            deaths = []
            for member in self.children + [self.mother, self.father, self.spouse]:
                if member is None or member.person is None:
                    continue
                death = copy(first_or_default(member.person.events, lambda e: e.type == 'DEAT' and e.date is not None, None))
                if death is None:
                    continue

                death.type = 'FAML'
                death.head = member.person.choose_by_sex('Умер', 'Умерла') + ' ' + member.role.lower()
                death.members = [RelPerson(member.person.choose_by_sex('Умер', 'Умерла'), member.person)] + death.members

                if (self.me.person.birth and
                    self.me.person.birth.date and
                    self.me.person.birth.date.to_date() > death.date.to_date()):
                    # брат или сестра умерли раньше чем мы родились
                    continue

                if self.me.person.death and self.me.person.death.date:
                    # ребенок или брат/сестра/родитель умер раньше чем мы
                    if self.me.person.death.date.to_date() > death.date.to_date():
                        deaths.append(death)
                else:

                    if member.role in ['Сын', 'Дочь', 'Ребенок']:
                        # ребенок умер в молодом возрасте а смерть родителя неизвестна
                        if member.person.age() is not None and member.person.age() < 40:
                            deaths.append(death)
                    else:
                        # родитель умер в молодом возрасте ребенка а смерть ребенка неизвестна
                        if self.me.person.age_at(death) is not None:
                            deaths.append(death)

            death = list(sorted(deaths, key=Event.order))
            return death

        def all_events(self):
            events = []
            events = Event.merge(events, self.marr_div_events())
            events = Event.merge(events, self.children_birth_events())
            events = Event.merge(events, self.death_events())
            return events


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

        self.parent_family = None #Family - семья непосредственных родителей ребенка
        self.other_parent_families = [] #[Family] предыдущие и последующие браки родителей
        self.own_families = families or [] #[Family] собственные браки и дети в них

        self.relatives = {}
        self.photo = photo
        self.photos = photos or [] #[Document]
        self.sources = sources or [] #[Document]
        self.events = [] #[Event]
        self.ext_events = []

    def choose_by_sex(self, male, female, unknown=None):
        return choose_by_sex(self.sex, male, female, unknown)

    def is_alive(self):
        return self.death is None

    def age_at(self, some_event):
        birth_date = self.birth.date.to_date() if self.birth and self.birth.date else None
        event_date = some_event.date.to_date() if some_event and some_event.date else None
        if birth_date is not None and event_date is not None and event_date > birth_date:
            return relativedelta(event_date, birth_date).years
        else:
            return None

    def age(self):
        birth_date = self.birth.date.to_date() if self.birth and self.birth.date else None
        death_date = self.death.date.to_date() if self.death and self.death.date else None
        end_date = date.today() if self.is_alive() else death_date
        if birth_date is not None and end_date is not None:
            return relativedelta(end_date, birth_date).years
        else:
            return None

class Document:
    def __init__(self, path, sys_path, title=None, comment=None, content=None, is_photo=False, is_primary=False):
        '''comment - Note
           content - text from .txt files
        '''
        self.path = normalize_path(path)
        self.sys_path = normalize_path(sys_path)
        self.title = title
        self.comment = comment
        self.content = content
        self.is_photo = is_photo
        self.is_primary = is_primary

    @staticmethod
    def from_gedcom_document(document, files):
        file_path = files.get(document.get('FILE', ''))
        if file_path:
            sys_path = normalize_path(os.path.join(files.directory, file_path))
            if os.path.exists(sys_path):
                ext = os.path.splitext(file_path)[-1].lower()
                title = document.get('TITL', '')
                comment = Note.parse(document.get('NOTE'))
                is_photo = ext in ['.jpg', '.jpeg', '.png', '.tiff', '.gif']
                content = opendet(sys_path).read() if ext == '.txt' else None
                is_primary = document.get('_PRIM') == 'Y'
                document = Document(path=file_path, sys_path=sys_path,
                                    title=title, comment=comment, content=content, is_photo=is_photo, is_primary=is_primary)
                return document
            else:
                print('File not found: {}'.format(sys_path))
        return None

def get_documents(documents, files):
    '''документы персоны или события распределить на фотографии и документы-источники'''
    photos = []
    docs = []
    for document in documents:
        doc = Document.from_gedcom_document(document, files)
        if doc is None:
            continue
        if doc.is_photo:
            photos.append(doc)
        else:
            docs.append(doc)
    photos = list(sorted(photos, key = lambda d: d.is_primary, reverse=True)) # сначала дефолтный документ
    return photos, docs


class Source:
    def __init__(self, name, page, quote, document_path):
        '''quote - Note'''
        self.name = name
        self.page = page
        self.quote = quote
        self.document_path = normalize_path(document_path) # путь до сохраненного документа-источника

    @staticmethod
    def from_gedcom_source(source, source_link):
        name = source.get('TITL', None)
        page = source_link.get('PAGE')
        link_note = Note.parse(source_link.get('NOTE')) or Note()
        source_note = Note.parse(source.get('TEXT')) or Note()
        quote = Note(link_note.sections + source_note.tags_sections)
        if len(quote.sections) == 0:
            quote = None
        return Source(name, page, quote, None)

    @staticmethod
    def from_document(document):
        ext = os.path.splitext(document.path)[-1].lower()
        name = document.title
        comment = document.comment or Note()
        content = Note.as_text(document.content) or Note()
        quote = Note(comment.sections + content.sections)
        if len(quote.sections) == 0:
            quote = None
        return Source(name, None, quote, document.path)

    @staticmethod
    def from_gedcom_sources(sources, source_links):
        for s_link in source_links:
            source = first_or_default(sources, lambda s: s.id == s_link.id)
            if source:
                yield Source.from_gedcom_source(source, s_link)

    @staticmethod
    def from_documents(documents):
        for document in documents:
            yield Source.from_document(document)

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
    def get_event_head(event_type, sex):
        if event_type == 'BIRT':
            event_head = choose_by_sex(sex, 'Родился', 'Родилась')
        elif event_type == 'DEAT':
            event_head = choose_by_sex(sex, 'Умер', 'Умерла')
        elif event_type == 'TRNS':
            event_head = 'Переезд'
        elif event_type == 'EDUC':
            event_head = 'Обучение'
        elif event_type == 'OCCU':
            event_head = 'Устройство на работу'
        elif event_type == '__2':
            event_head = 'Служба в армии'
        elif event_type == 'MARR':
            event_head = choose_by_sex(sex, 'Женился', 'Вышла замуж', 'Свадьба')
        elif event_type == 'DIV':
            event_head = choose_by_sex(sex, 'Развелся', 'Развелась', 'Развод')
        else:
            event_head = None
        return event_head

    @staticmethod
    def from_gedcom_event(event, sex, gedcom, files):
        event_type = event.event_type
        event_date = GedDate.parse(event.get('DATE', ''))
        event_place = event.get('PLAC', None)
        event_comment_row = event.get('NOTE', None)
        event_comment = Note.parse(event_comment_row)
        event_photos, event_docs = get_documents(event.documents, files)
        event_photo = first_or_default(event_photos)
        event_sources = list(Source.from_gedcom_sources(gedcom.sources, event.sources)) + list(Source.from_documents(event_docs))
        event_head = None

        if event_type == 'RESI':
            has_from_to = event_comment_row is not None and ('Откуда:' in event_comment_row or 'Куда:' in event_comment_row)
            if event_place is not None and not has_from_to:
                # это не событие, это место жительства
                event_type = 'RESIDENCE'
            else:
                # это событие переезд
                event_type = 'TRNS'
                event_head = 'Переезд'

        elif event_type == 'EVEN':
            event_head = event.get('TYPE', None)
        else:
            event_head = Event.get_event_head(event_type, sex) or ''


        return Event(type=event_type, head=event_head, date=event_date, place=event_place,
                     comment = event_comment, photo = event_photo, photos = event_photos,
                     sources = event_sources)

    @staticmethod
    def order(event):
        '''метод для получения ключа для упорядочивания персональных событий'''
        event_date = event.date.to_date() if event.date else None
        if event.type == 'BIRT':
            return (-1, event_date or GedDate.MIN) # рождение в начале
        if event.type == 'DEAT':
            return (1 if event_date is None else 0, event_date or GedDate.MIN) # смерть без даты в конце
        return (0, event_date or GedDate.MIN)

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

    @staticmethod
    def first_date_of(events):
        mind = None
        for e in events:
            d = e.date.to_date() if e.date else None
            if d is not None and (mind is None or d < mind):
                mind = d
        return mind

    @staticmethod
    def last_date_of(events):
        maxd = None
        for e in events:
            d = e.date.to_date() if e.date else None
            if d is not None and (maxd is None or d > maxd):
                maxd = d
        return maxd

def get_person_snippets(gedcom, files):
    snippets = dict()
    indi_to_uid = dict()

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

    for person in gedcom.persons:
        person_uid = person['_UID']
        name = GedName.parse(person.get('NAME', ''))
        sex = person.get('SEX')
        main_occupation = person.get('OCCU')
        comment = Note.parse(person.get('NOTE'))
        photos, docs = get_documents(person.documents, files)
        photo = first_or_default(photos)

        sources = list(Source.from_gedcom_sources(gedcom.sources, person.sources)) + list(Source.from_documents(docs))
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

    all_children = defaultdict(list) # uid->[(child, family_id)]

    for family in gedcom.families:
        wife = snippets.get(indi_to_uid.get(family.get('WIFE')), None)
        husband = snippets.get(indi_to_uid.get(family.get('HUSB')), None)

        for child in get_children(family):
            child.mother.person = wife
            child.father.person = husband

            # событие рождение для ребенка
            # добавляем участников - родителей
            birth = first_or_default(child.events, lambda e: e.type == 'BIRT')
            if birth:
                if child.father.person:
                    birth.members.append(child.father)
                if child.mother.person:
                    birth.members.append(child.mother)

            for parent in [wife, husband]:
                if parent:
                    all_children[parent.uid].append((child, family.id))


    for family in gedcom.families:

        # PersonSnippet
        wife = snippets.get(indi_to_uid.get(family.get('WIFE')), None)
        husband = snippets.get(indi_to_uid.get(family.get('HUSB')), None)
        children = []

        for child in get_children(family):
            children.append(child)

        events = []
        marr = first_or_default(family.events, lambda e: e.event_type == 'MARR')
        div = first_or_default(family.events, lambda e: e.event_type == 'DIV')
        if marr:
            marr_event = Event.from_gedcom_event(marr, 'U', gedcom, files)
            events.append(marr_event)
        if div:
            div_event = Event.from_gedcom_event(div, 'U', gedcom, files)
            events.append(div_event)

        events = list(sorted(events, key=Event.order))

        def get_family_for(me):
            if wife is not None and me.uid == wife.uid:
                return PersonSnippet.Family(family.id, me=RelPerson('Мать', me), wife=wife, husband=husband, children=children, events=events)
            if husband is not None and me.uid == husband.uid:
                return PersonSnippet.Family(family.id, me=RelPerson('Отец', me), wife=wife, husband=husband, children=children, events=events)
            return PersonSnippet.Family(family.id, me=RelPerson('Ребенок', me), wife=wife, husband=husband, children=children, events=events)

        for parent in [wife, husband]:
            if parent:
                parent.own_families.append(get_family_for(parent))
                for child, child_parent_family_id in all_children[parent.uid]:
                    if child_parent_family_id != family.id:
                        # ребенок из другой семьи отца/матери
                        # для него текущая семья будет другой семьей у отца/матери
                        child.other_parent_families.append(get_family_for(child))
                    elif child.parent_family is None:
                        # ребенок из текущей семьи - это его родная семя
                        child.parent_family = get_family_for(child)


    for person in snippets.values():
        person.own_families = list(sorted(person.own_families, key=lambda fam: fam.first_date or GedDate.MIN))
        family_events = []
        for family in [person.parent_family] + person.own_families + person.other_parent_families:
            if family:
                family_events = Event.merge(family_events, family.all_events())

        person.ext_events = Event.merge(person.events, family_events)

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

class FilesDict(dict):
    pass

def get_files_dict(filename, files_path):
    files = FilesDict()
    files.directory = files_path
    with codecs.open(filename, 'r', 'utf-8') as input:
        for line in input:
            k, v = line.strip().split('\t')
            files[k] = v
    return files




class Data:
    '''статические данные о персонах/загруженных деревьях не зависящие
       от текущего пользователя, запрошенной страницы, отображаемой персоны'''

    DEFAULT_TREE_NAME = 'default'

    class Tree:
        def __init__(self, uid, name, img, map):
            self.uid = uid
            self.name = name
            self.img = img
            self.map = map


    def __init__(self, site, author, static_path, data_path):
        '''
           site - информация о сайте: host + title + description
           author - информация об авторе сайта
           static_path - path to src/static/tree
           data_path - path to data/tree
        '''
        self.site = site
        self.author = author
        self.load_error = 'Data is unloaded.'
        self.static_path = static_path
        self.data_path = data_path

    @property
    def trees_sorted_by_names(self):
        return list(sorted(self.trees.values(), key=lambda tree: tree.name))



    def is_valid(self):
        return self.load_error is None

    def load(self, archive=None):
        try:
            self.load_error = 'Данные сайта обновляются прямо сейчас'
            if archive is not None:
                load_package(archive, self.site["host"], self.static_path, self.data_path)

            self.files_dir = 'tree/files'
            self.files = get_files_dict(os.path.join(self.data_path, 'files.tsv'), os.path.join(self.static_path, 'files'))

            self.gedcom = GedcomReader().read_gedcom(os.path.join(self.data_path, 'tree.ged'))
            self.persons_snippets = get_person_snippets(self.gedcom, self.files)
            self.persons_owners = get_person_owners(self.persons_snippets)

            trees_config = os.path.join(self.data_path, 'trees.json')
            self.trees_names = json.loads(open(trees_config).read()) if os.path.exists(trees_config) else {}

            # Загружаем деревья -
            trees = select_tree_img_files(self.static_path)
            self.trees = {}
            for tree in trees:
                tree_uid = tree.name or Data.DEFAULT_TREE_NAME
                self.trees[tree_uid] = Data.Tree(tree_uid,
                                                 self.trees_names.get(tree_uid) or tree_uid,
                                                 '/static/tree/'+tree.img,
                                                 get_tree_map(os.path.join(self.static_path, tree.img)))

            if len(self.trees) == 0:
                raise Exception('No files *_tree_img.png in {} directory'.format(self.static_path))

            self.default_tree_name = Data.DEFAULT_TREE_NAME if Data.DEFAULT_TREE_NAME in self.trees else self.trees_sorted_by_names[0].uid
            self.load_error = None
        except:
            self.load_error = traceback.format_exc()

