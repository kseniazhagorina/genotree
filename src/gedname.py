import re

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
    # иногда на концах имен, отчеств и фамилий бывают лишние пробелы
    gedcom_name_regex = re.compile('^(((?P<name>[\w\?-]*)\s*)?(?P<patronymic>[\w\?-]*)\s*)?/(?P<surname>[\w\?-]*)\s*(\((?P<surname_at_birth>[\w\?-]*)\s*\))?/$')
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