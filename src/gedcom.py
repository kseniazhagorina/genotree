#!usr/bin/env
# -*- coding: utf-8 -*-

#http://wiki-en.genealogy.net/GEDCOM-Tags

import codecs

class Gedcom:
    EVENT_TYPES = ['RESI',   # проживание
                   'BIRT',   # рождение
                   'DEAT',   # смерть
                   'EDUC',   # обучение
                   'OCCU',   # устройство на работу
                   '__2',    # служба в армии (v3)
                   'RETI',   # выход на пенсию
                   'EVEN',   # пользовательское событие
                   'MARR',   # свадьба
                   'DIV'     # развод
             ]
    MULTI_ATTRS = ['CHIL', 'FAMS']  # поля которые могут встречаться несколько раз
    IGNORE_INNER = ['NAME', 'FILE', 'PLAC'] # игнорировать все вложенные данные в объект, использовать только заголовок
    
    def __init__(self):
        self.meta = None
        self.families = []
        self.persons = []
        self.sources = []
    
    class MetaData(dict):
        def __init__(self):
            self.sources = []
            
    class Family(dict):
        def __init__(self, family_id):
            self.id = family_id
            self.events = []
            self.documents = []
            
    class Person(dict):
        def __init__(self, person_id):
            self.id = person_id
            self.events = []
            self.documents = []
            self.sources = []
    
    class Event(dict):
        def __init__(self, event_type):
            self.event_type = event_type
            self.documents = []
            self.sources = []
                
    class Document(dict):
        def __init__(self):
            self.sources = []
 
    class Source(dict):
        def __init__(self, source_id):
            self.id = source_id
            
class GedcomReader:

    def read_gedcom(self, filename):
        with codecs.open(filename, 'r', encoding='utf-8') as file:
            lines = [line.strip('\r\n') for line in file]
            
        blocks = self.split_on_blocks(lines)
        gedcom = Gedcom()
        for head,block_lines in blocks:
            head = head.strip()
            if head.endswith('HEAD'):
                gedcom.meta = self.read_meta(head, block_lines)
            if head.endswith('INDI'):
                person = self.read_person(head, block_lines)
                gedcom.persons.append(person)
            if head.endswith('FAM'):
                family = self.read_family(head, block_lines)
                gedcom.families.append(family)
            if head.endswith('SOUR'):
                source = self.read_source(head, block_lines)
                gedcom.sources.append(source)
                
        return gedcom
    
    def read_block(self, lines, at):
        '''читает блок данных
        at - первая строка - начало блока
        возвращает остальные строки - вложенные в блок (могут отсутствовать)'''
        intent = int(lines[at][0])
        block_lines = []
        at += 1
        while at < len(lines):
            line = lines[at]
            if int(line[0]) <= intent:
                break
            block_lines.append(line)
            at += 1
            
        return block_lines 
    
    def split_on_blocks(self, lines):
        i = 0
        blocks = []
        while i < len(lines):
            head = lines[i].split(maxsplit=1)[1] #без интента 
            block = self.read_block(lines, i)
            blocks.append((head, block))
            i += len(block) + 1
        return blocks    
    
    def add_info(self, obj, head, lines):
        '''obj: one of Person, Family, Source, Event, Document'''
        if head.startswith('NOTE') or head.startswith('TEXT'):
            key, text = self.read_note(head, lines)
            obj[key] = text
        elif head.startswith('DATA'):
            self.add_all_info(obj, lines)
        elif 'sources' in obj.__dict__ and head.startswith('SOUR') :
            obj.sources.append(self.read_source_ref(head, lines))
        elif 'events' in obj.__dict__ and any(head.startswith(s) for s in Gedcom.EVENT_TYPES):
            obj.events.append(self.read_event(head, lines))
        elif 'documents' in obj.__dict__ and head.startswith('OBJE') :
            obj.documents.append(self.read_document(head, lines))   
        elif len(lines) == 0 or any(head.startswith(s) for s in Gedcom.IGNORE_INNER):
            key, value = self.read_simple(head)
            if key in Gedcom.MULTI_ATTRS:
                if key not in obj:
                    obj[key] = []
                obj[key].append(value)
            else:    
                obj[key] = value
        else:
            print('undefined: [{head}] in {obj_type}:{obj}'.format(head=head, obj_type=type(obj), obj=str(obj)))
    
    def add_all_info(self, obj, lines):
        blocks = self.split_on_blocks(lines)
        for head,block_lines in blocks:
            self.add_info(obj, head, block_lines)
            
    def read_family(self, head, lines):
        family_id = head.split(maxsplit=1)[0].strip()
        family = Gedcom.Family(family_id)
        self.add_all_info(family, lines)
        return family
    
    def read_meta(self, head, lines):
        '''блок HEAD - метаданные о дереве'''
        pass
        
    def read_person(self, head, lines):
        '''блок INDI - персональные данные'''
        person_id = head.split(maxsplit=1)[0].strip()
        person = Gedcom.Person(person_id)
        self.add_all_info(person, lines)
        return person  
    
    def read_source(self, head, lines):
        '''блок SOUR - источники (включает заголовок источника и описание)'''
        source_id = head.split(maxsplit=1)[0].strip()
        source = Gedcom.Source(source_id)
        self.add_all_info(source, lines)
        return source

    def read_event(self, head, lines):
        event_type=head.split(maxsplit=1)[0].strip()
        event = Gedcom.Event(event_type)
        self.add_all_info(event, lines)
        return event
    
    def read_document(self, head, lines):
        document = Gedcom.Document()
        self.add_all_info(document, lines)
        return document
    
    def read_source_ref(self, head, lines):
        source_id = head.split(maxsplit=1)[1].strip()
        source = Gedcom.Source(source_id)
        self.add_all_info(source, lines)
        return source        
    
    def read_simple(self, head):
        '''простой однострочный блок вроде CONC, NAME, SEX, OCCU, PLAC, DATE, FILE и т.д.'''
        parts = head.split(maxsplit=1)
        key = parts[0].strip()
        value = parts[1] if len(parts) >= 2 else ""
        return (key, value)
    
    def read_note(self, head, lines):
        key, text = self.read_simple(head)
        for block_head, block_lines in self.split_on_blocks(lines):
            next_key, value = self.read_simple(block_head)
            text += value if next_key == 'CONC' else '\n'+value #CONCatenate vs CONTinued
        text = text.strip()   
        return (key, text)    
           
    
class GedcomWriter:
    def write_gedcom(self, gedcom, filename):
        with codecs.open(filename, 'w+', encoding='utf-8') as output:
            self.output = output
            for person in gedcom.persons:
                self.write_person_family_or_source(0, person, 'INDI')
            for family in gedcom.families:
                self.write_person_family_or_source(0, family, 'FAM')
            for source in gedcom.sources:
                self.write_person_family_or_source(0, source, 'SOUR')
        self.output = None        
    
    def write_person_family_or_source(self, intent, obj, suffix):
        self.output.write('{0} {1} {2}\n'.format(intent, obj.id, suffix))
        self.write_all_info(intent+1, obj)

    def write_all_info(self, intent, obj):
        for key, value in obj.items():
            if key in Gedcom.MULTI_ATTRS:
                self.write_multi_attribute(intent, key, value)
            else:
                self.write_attribute(intent, key, value)
        if 'events' in obj.__dict__:
            for event in obj.events:
                self.write_event(intent, event)
        if 'documents' in obj.__dict__:
            for document in obj.documents:
                self.write_document(intent, document)
        if 'sources' in obj.__dict__:
            for source in obj.sources:
                self.write_source_ref(intent, source)   
    
    def write_document(self, intent, document):
        self.output.write('{0} OBJE\n'.format(intent))
        self.write_all_info(intent+1, document)
    
    def write_event(self, intent, event):
        self.output.write('{0} {1}\n'.format(intent, event.event_type))
        self.write_all_info(intent+1, event)
    
    def write_source_ref(self, intent, source):
        self.output.write('{0} SOUR {1}\n'.format(intent, source.id))
        self.write_all_info(intent+1, source)
    
    def write_attribute(self, intent, key, value):
        if '\n' not in value:
            self.output.write('{0} {1} {2}\n'.format(intent, key, value))
        else:
            lines = [line for line in value.split('\n') if line != ""]
            self.output.write('{0} {1} {2}\n'.format(intent, key, lines[0]))
            for line in lines[1:]:
                self.output.write('{0} CONT {1}\n'.format(intent+1, line))
                
    def write_multi_attribute(self, intent, key, values):
        for value in values:
            self.write_attribute(intent, key, value)