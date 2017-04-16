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
        super(self.__class__, self).__init__(text = key+": "+value, privacy=privacy)
        self.key = key
        self.value = value

class TagSection(KeyValueSection):
    '''Tags: участник ВОВ, private, еще какой-то тег'''
    def __init__(self, key, value, privacy=PrivacyMode.PUBLIC):
        super(self.__class__, self).__init__(key, value, privacy)
        self.tags = set([tag for tag in [part.strip() for part in value.split(',')] if tag != ""])

class Note:
    possible_keys = ['Куда', 'Откуда', 'Образовательное учреждение', 'Специальность', 'Причина смерти', 'Внешность','Примеч.', 'Tags']
    key_value_regex = re.compile(r'^(?P<key>{0}):\s*(?P<value>.*)'.format('|'.join(possible_keys)))
    privacy_mode_regex = re.compile(r'^(?P<mode>public|protected|private):$')
    def __init__(self, sections=[]):
        self.sections = sections

    def __repr__(self):
        text = '\n'.join([s.text for s in self.sections])
        return text

    def filter(self, privacy=PrivacyMode.PUBLIC, text=True, key_values=True, tags=True):
        sections = [s for s in self.sections
                   if s.privacy <= privacy and (
                        (type(s) == NoteSection and text) or
                        (type(s) == KeyValueSection and key_values) or
                        (type(s) == TagSection and tags)
                    )]
        if len(sections) == 0:
            return None
        return Note(sections)

    def has_tag(self, tag):
        for s in self.sections:
            if isinstance(s, TagSection):
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


