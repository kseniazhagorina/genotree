# -*- coding: utf-8 -*-
from privacy import PrivacyMode
import re

class NoteSection:
    '''просто кусок текста в комментарии'''
    def __init__(self, text, privacy=PrivacyMode.PUBLIC):
        self.text = text
        self.privacy = privacy

class KeyValueSection(NoteSection):
    '''кусок текста вида:  "ключ: значение"'''
    def __init__(self, key, value, privacy=PrivacyMode.PUBLIC):
        super(KeyValueSection, self).__init__(key+": "+value, privacy=privacy)
        self.key = key
        self.value = value

class TagSection(KeyValueSection):
    '''Tags: участник ВОВ, private, еще какой-то тег'''
    def __init__(self, key, value, privacy=PrivacyMode.PUBLIC):
        super(TagSection, self).__init__(key, value, privacy)
        self.tags = set([tag for tag in [part.strip() for part in value.split(',')] if tag != ""])

class Note:
    possible_keys = ['Причина смерти', 'Внешность','Примеч.', 'Tags']
    key_value_regex = re.compile(r'^(?P<key>{0}):\s*(?P<value>.*)'.format('|'.join(possible_keys)))
    privacy_mode_regex = re.compile(r'^(?P<mode>public|protected|private):$')
    def __init__(self, sections=[]):
        self.sections = sections
        self.privacy_note = self.privacy('note')
        
    def __repr__(self):
        text = '\n'.join([s.text for s in self.sections])
        return text
    
    def privacy(self, item=None, default=PrivacyMode.PUBLIC):
        '''определяет приватность по тегам private_<item>, protected_<item>, public_<item>'''
        suff = '_'+item if item else ''
        if self.has_tag('private'+suff):
            return PrivacyMode.PRIVATE
        if self.has_tag('protected'+suff):
            return PrivacyMode.PROTECTED
        return default
        
    def filter(self, access=PrivacyMode.PUBLIC, text=True, key_values=True, tags=True):
        sections = []
        if self.privacy_note <= access:
            sections = [s for s in self.sections
                       if s.privacy <= access and (
                            (type(s) == NoteSection and text) or
                            (type(s) == KeyValueSection and key_values) or
                            (type(s) == TagSection and tags)
                        )]
        if len(sections) == 0:
            return None
        return Note(sections)
    
    @property
    def tags_sections(self):
        return [s for s in self.sections if isinstance(s, TagSection)]
        
    def has_tag(self, tag):
        for s in self.tags_sections:
            if tag in s.tags:
                    return True
        return False
    
    @staticmethod
    def parse(text):
        if text is None or text.strip() == "":
            return None
        sections = []
        section = None
        privacy = PrivacyMode.PUBLIC
        for line in text.split('\n'):
            m = Note.key_value_regex.match(line.strip())
            if m is not None:
                if section is not None:
                    sections.append(NoteSection(section, privacy))
                    section = None
                key = m.group('key')
                value = m.group('value').strip()
                if key == "Tags":
                    sections.append(TagSection(key, value, privacy))
                else:
                    sections.append(KeyValueSection(key, value, privacy))
                continue
            m = Note.privacy_mode_regex.match(line.strip())
            if m is not None:
                if section is not None:
                    sections.append(NoteSection(section, privacy))
                    section = None
                privacy_mode = m.group('mode')
                if privacy_mode == 'private':
                    privacy = PrivacyMode.PRIVATE
                elif privacy_mode == 'protected':
                    privacy = PrivacyMode.PROTECTED
                else:
                    privacy = PrivacyMode.PUBLIC
                continue
            section = section + '\n' + line if section is not None else line

        if section is not None:
            sections.append(NoteSection(section, privacy))
            section = None

        if len(sections) == 0:
            return None
        return Note(sections)


