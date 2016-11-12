# -*- coding: utf-8 -*-

import re

class ReMaker:
    class NextName:
        def __init__(self, name):
            self.name = name
            self.ind = 0
        def __call__(self, _match):
            self.ind += 1
            return self.name + '_{0:04}'.format(self.ind)

    def __init__(self, group_names):
        self.group_names = dict([(name, ReMaker.NextName(name)) for name in group_names])

    def rename_groups(self, regex_string):
        '''
        переименовывает встречающиеся группы с именем name в группы name_1, name_2, ...
        после прогона через make куски регулярок можно склеивать в бОльшие регулярки и по-прежнему пользоваться именованными группами
        '''
        for name, get_next_name in self.group_names.items():
            regex_string = re.sub(r'(?<=\(\?P<){0}(?=>)'.format(name), get_next_name, regex_string)
        return regex_string

    def remove_groups(self, regex_string):
        for name in self.group_names:
            regex_string = re.sub('\?P<{0}>'.format(name), "", regex_string)
        return regex_string

    @staticmethod
    def group(match, name):
        groups = [(gname, gvalue) for gname,gvalue in match.groupdict().items() if gname.startswith(name+'_') and gvalue is not None]
        groups = list(sorted(groups, key=lambda item: item[0])) #sort by gname
        if len(groups) > 0:
            return groups[0][1]
        return None

class GedDate:
    '''
    дата для генеалогических целей - какие-то части могут отсутствовать
    а также есть специальные пометки для обозначения временных периодов и точности
    http://wiki-en.genealogy.net/GEDCOM/DATE-Tag
    '''

    STANDARD = 0
    # ranges
    BEFORE = 1 # До 1927, BEF 1927
    AFTER = 2  # После 1970, AFT 1970 (после 31 дек 1970)
    BETWEEN = 3 # Между 21.10.2006 и 28.10.2006, BET 21 OCT 2006 AND 28 OCT 2006
    # approximated
    ABOUT = 4 # Около 08.1990, ABT AUG 1990
    CALCULATED = 5 # Вычислено 20.09.1957, CAL 20 SEP 1957
    ESTIMATED = 6 # Предположительно 1895, EST 1985
    OR = 7 # 1910 или 1911, 1919 OR 1911
    # periods
    FROM_TO = 8 # С 1925 по 06.1928, FROM 1925 TO JUN 1928
    FROM = 9 # С 07.1987 , FROM JUL 1987
    TO = 10 # По 08.1989, TO AUG 1989

    #форматы
    Gedcom = None
    Genery = None

    @staticmethod
    def parse(s):
        return GedDate.Gedcom.parse(s) or GedDate.Genery.parse(s)

    def __init__(self, date=None, date2=None, type=None):
        '''date,date2 - None or 3-tuple (year, month, date) some of items can be None'''
        self.date = date
        self.date2 = date2
        self.type = type
        self.format = GedDate.Genery

    def __eq__(self, other):
        return self.date == other.date and self.date2 == other.date2 and self.type == other.type

    def __repr__(self):
        return self.format.format(self)

class DateFormat(object):
    def __init__(self, date_regex, monthes, formats):
        '''
        date_regex - регулярное выражение для стандартной даты с именованными группами day,month,year
        monthes именование месяцев в стандартной дате
        formats - dict (GedDate.type -> 'FROM {0} TO {1}')
        '''
        rm = ReMaker(['day', 'month', 'year'])
        self.date_regex = re.compile(rm.rename_groups('^{0}$'.format(date_regex)))

        self.type_to_format = formats
        self.regex_to_type = []
        # собираем регулярки в которых day, month и year уже непоименованы
        # т.к. есть ограничение на 100 именованых групп
        date_regex = rm.remove_groups(date_regex)
        for date_type, date_format in formats.items():
            d1 = '(?P<date1>{0})'.format(date_regex)
            d2 = '(?P<date2>{0})'.format(date_regex)
            format_regex_str = r'^{0}$'.format(
                                date_format.format(d1, d2))
            format_regex = re.compile(format_regex_str)
            self.regex_to_type.append((format_regex, date_type))

        self.monthes = monthes


    '''общие методы для парсинга и печати дат
    конкретные реализации отличаются набором регулярных выражений'''
    def parse(self, s):
        s = s.strip()
        if s == "":
            return None
        for date_format, date_type in self.regex_to_type:
            m = date_format.match(s)
            if m is not None:
                date1 = self.parse_simple_date(m.groupdict().get('date1')) #date1 или date2 не всегда существуют
                date2 = self.parse_simple_date(m.groupdict().get('date2'))
                if date1 is None and date2 is None:
                    return None
                return GedDate(date1, date2, date_type)
        return None

    def __try_int(self, s):
        try:
            return int(s)
        except:
            return None

    def parse_simple_date(self, date_str):
        if date_str is None:
            return None
        m = self.date_regex.match(date_str)
        if m is not None:
            day_str = ReMaker.group(m, 'day')
            month_str = ReMaker.group(m, 'month')
            year_str = ReMaker.group(m, 'year')
            day = self.__try_int(day_str)
            month = self.monthes.index(month_str) if month_str in self.monthes else None
            year = self.__try_int(year_str)
            if day is None and month is None and year is None:
                return None
            return (year, month, day)
        return None

    def format(self, date):
        if date is None or (date.date is None and date.date2 is None):
            return ""
        d1 = self.format_simple_date(date.date)
        d2 = self.format_simple_date(date.date2)
        return self.type_to_format[date.type].format(d1, d2)

    def format_simple_date(self, date_as_tuple):
        pass

class GedcomDateFormat(DateFormat):
    def __init__(self):
        monthes = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        month_regex = r'(?P<month>{0})'.format('|'.join(monthes))
        day_regex = r'(?P<day>\d\d?)'
        year_regex = r'(?P<year>\d\d\d\d)'
        date_regex = r'(({d} {m} {y})|({d} {m})|({m} {y})|({d} {y})|({d})|({m})|({y}))'.format(d=day_regex, m=month_regex, y=year_regex)

        formats = {GedDate.STANDARD: '{0}',
                   GedDate.BEFORE: 'BEF {1}',
                   GedDate.AFTER: 'AFT {0}',
                   GedDate.BETWEEN: 'BET {0} AND {1}',
                   GedDate.ABOUT: 'ABT {0}',
                   GedDate.CALCULATED: 'CAL {0}',
                   GedDate.ESTIMATED: 'EST {0}',
                   GedDate.OR: '{0} OR {1}',
                   GedDate.FROM_TO: 'FROM {0} TO {1}',
                   GedDate.FROM: 'FROM {0}',
                   GedDate.TO: 'TO {1}'}

        super(GedcomDateFormat, self).__init__(date_regex, monthes, formats)

    def format_simple_date(self, date_as_tuple):
        '''(year, month, day) or None'''
        if date is None:
            return ''
        (year, month, day) = date
        if year is None and month is None and day is None:
            return ''
        parts = []
        if day is not None:
            parts.append(str(day))
        if month is not None:
            parts.append(self.monthes[month])
        if year is not None:
            parts.append(int(year))
        return ' '.join(parts)


class GeneryDateFormat(DateFormat):
    def __init__(self):
        monthes = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        month_regex = r'(?P<month>[01]\d)'
        day_regex = r'(?P<day>\d\d)'
        year_regex = r'(?P<year>\d\d\d\d)'
        date_regex = r'(((({d}|\?)\.)?({m}|\?)\.)?({y}|\?))'.format(d=day_regex, m=month_regex, y=year_regex)
        # example of correct dates: 23.04.?   06.2010   1992   31.?.2004    13.?.?    ?

        formats = {GedDate.STANDARD: '{0}',
                   GedDate.BEFORE: 'До {1}',
                   GedDate.AFTER: 'После {0}',
                   GedDate.BETWEEN: 'Между {0} и {1}',
                   GedDate.ABOUT: 'Около {0}',
                   GedDate.CALCULATED: 'Вычислено {0}',
                   GedDate.ESTIMATED: 'Предположительно {0}',
                   GedDate.OR: '{0} или {1}',
                   GedDate.FROM_TO: 'С {0} по {1}',
                   GedDate.FROM: 'С {0}',
                   GedDate.TO: 'По {1}'}

        super(GeneryDateFormat, self).__init__(date_regex, monthes, formats)

    def format_simple_date(self, date):
        '''(year, month, day) or None'''
        if date is None:
            return '?'
        (year, month, day) = date
        if year is None and month is None and day is None:
            return '?'
        year_str = '{0:04}'.format(year) if year is not None else '?'
        month_str = self.monthes[month] if month is not None else '?'
        day_str = '{0:02}'.format(day) if day is not None else '?'
        if day is not None:
            return '{0}.{1}.{2}'.format(day_str, month_str, year_str)
        elif month is not None:
            return '{0}.{1}'.format(month_str, year_str)
        else:
            return year_str


GedDate.Gedcom = GedcomDateFormat()
GedDate.Genery = GeneryDateFormat()