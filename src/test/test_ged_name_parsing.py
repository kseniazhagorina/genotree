#!usr/bin/env
# -*- coding: utf-8 -*-

import unittest
from  gedname import GedName


class T(unittest.TestCase):

    def check(self, parsed, name=None, patronymic=None, surname=None, surname_at_birth=None, unparsed=None):
        self.assertEqual(parsed.name, name, parsed)
        self.assertEqual(parsed.surname, surname)
        self.assertEqual(parsed.patronymic, patronymic)
        self.assertEqual(parsed.surname_at_birth, surname_at_birth)
        self.assertEqual(parsed.unparsed, unparsed)


    def test_standart(self):
        name = GedName.parse('Александр Сергеевич /Пушкин/')
        self.check(name, 'Александр', 'Сергеевич', 'Пушкин', '')

        name = GedName.parse('Наталья Николаевна /Пушкина (Гончарова)/')
        self.check(name, 'Наталья', 'Николаевна', 'Пушкина', 'Гончарова')

    def test_trailing_spases(self):

        name = GedName.parse('Иван /Иванов/')
        self.check(name, 'Иван', '', 'Иванов', '')

        name = GedName.parse('Иван /Иванов /')
        self.check(name, 'Иван', '', 'Иванов', '')

        name = GedName.parse('Иван   Петрович /Иванов (Смирнов )/')
        self.check(name, 'Иван', 'Петрович', 'Иванов', 'Смирнов')


if __name__ == '__main__':
    unittest.main()