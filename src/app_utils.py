#!usr/bin/env
# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree
from gedcom import GedcomReader
from geddate import GedDate
import re

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
        if self.surname_at_birth != "":
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
            patronymic =m.groupdict().get('patronymic')
            surname = m.groupdict().get('surname')
            surname_at_birth = m.groupdict().get('surname_at_birth')
            return GedName(name=name, patronymic=patronymic, surname=surname, surname_at_birth=surname_at_birth)
        return GedName(unparsed=s.strip())
            
                                
class PersonSnippet:
    '''модель для отображения сниппета о персоне на странице дерева'''
    class Event:
        def __init__(self, date=None, place=None, info=None):
            self.date = date
            self.place = place
            self.info = info # доп.информация отображаемая в скобочках
    class RelPerson:
        def __init__(self, role, uid, name=None):
            self.uid = uid
            self.role = role
            self.name = name
    class Family:
        def __init__(self, spouse=None, children=None):
            self.spouse = spouse #RelPerson
            self.children = children #RelPerson
        
    def __init__(self, person_uid, name=None, sex=None, birth=None, death=None, main_occupation=None, residence=None, photo=None, comment=None, mother=None, father=None, families=None):
        self.uid = person_uid
        self.name = name
        self.sex = sex
        self.birth = birth #event
        self.death = death #event
        self.main_occupation = main_occupation
        self.residence = residence
        self.comment = comment
        self.mother = mother #RelPerson
        self.father = father #RelPerson
        self.families = families or []
        self.photo = photo
        
    def choose_by_sex(self, male, female, unknown=None):
        if self.sex == 'M':
            return male
        if self.sex == 'F':
            return female
        return unknown if unknown is not None else male
        
        
def get_person_snippets(gedcom):
    snippets = dict()
    indi_to_uid = dict()
    for person in gedcom.persons:
        person_uid = person['_UID']
        name = str(GedName.parse(person.get('NAME', '')))
        sex = person.get('SEX', None)
        main_occupation = person.get('OCCU', None)
        comment = person.get('NOTE', None)
        main_document = first_or_default(person.documents, lambda d: d.get('DFLT') == 'T')
        photo = (main_document.get('FILE') if main_document else "").replace("\\","/")
        birth_event = first_or_default(person.events, lambda e: e.event_type == "BIRT")
        death_event = first_or_default(person.events, lambda e: e.event_type == "DEAT")
        residence_event = first_or_default(person.events, lambda e: e.event_type == "RESI" and 'PLAC' in e and \
                                     ('NOTE' not in e or ('Откуда:' not in e['NOTE'] and 'Куда:' not in e['NOTE'])))
        residence_place = residence_event.get('PLAC', None) if residence_event else None
        
        indi_to_uid[person.id] = person_uid
        snippet = PersonSnippet(person_uid, 
                                name=name,
                                photo=photo,
                                sex=sex,
                                main_occupation=main_occupation, 
                                residence=residence_place, 
                                comment=comment)
        if birth_event is not None:
            birth_date = GedDate.parse(birth_event.get('DATE', ''))
            snippet.birth = PersonSnippet.Event(date=birth_date, place=birth_event.get('PLAC', None))
        if death_event is not None:
            death_date = GedDate.parse(death_event.get('DATE', ''))
            snippet.death = PersonSnippet.Event(date=death_date, place=death_event.get('PLAC', None))
        snippets[person_uid] = snippet   
    
    for family in gedcom.families:
        wife = snippets.get(indi_to_uid.get(family.get('WIFE')), None)
        husband = snippets.get(indi_to_uid.get(family.get('HUSB')), None)
        mother = PersonSnippet.RelPerson('Мать', wife.uid, wife.name) if wife else None
        father = PersonSnippet.RelPerson('Отец', husband.uid, husband.name) if husband else None
        children = []
        for child_indi in family.get('CHIL', []):
            child = snippets.get(indi_to_uid.get(child_indi), None)
            if child is None:
                print ('cant find child with id ['+child_indi+']')
                continue
            child.mother = mother
            child.father = father 
            child_role = child.choose_by_sex('Сын', 'Дочь', 'Ребенок')
            children.append(PersonSnippet.RelPerson(child_role, child.uid, child.name))
        if wife:
            spouse = PersonSnippet.RelPerson('Супруг', husband.uid, husband.name) if husband else None
            wife.families.append(PersonSnippet.Family(spouse, children))
        if husband:
            spouse = PersonSnippet.RelPerson('Супруга', wife.uid, wife.name) if wife else None
            husband.families.append(PersonSnippet.Family(spouse, children))     
            
    return snippets
            
            
            
        
        
        
        
    
                
        