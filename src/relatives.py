#!usr/bin/env
# -*- coding: utf-8 -*-

__all__ = ['get_blood_relatives']


# X-мать, Y-отец, x-дочь, y-сын
# W-wife, H-husband

def fill_person(person, relation, relatives, deep):
    if deep and len(relation) >= deep:
        return False
    exist_relation = relatives.get(person.uid)
    if exist_relation and len(exist_relation) <= len(relation):
        return False
    relatives[person.uid] = relation
    return True
    
def fill_children(person, prefix, relatives, deep):
    for family in person.families:
        for child in family.children:
            if child.person:
               relation = prefix + child.person.choose_by_sex('y', 'x')
               if fill_person(child.person, relation, relatives, deep):
                   fill_children(child.person, relation, relatives, deep)
    
def fill_parents(person, prefix, relatives, deep):
    father = person.father.person
    if father:
        relation = prefix + 'Y'
        if fill_person(father, relation, relatives, deep):
            fill_children(father, relation, relatives, deep)
            fill_parents(father, relation, relatives, deep)
    mother = person.mother.person
    if mother:
        relation = prefix + 'X'
        if fill_person(mother, relation, relatives, deep):
            fill_children(mother, relation, relatives, deep)
            fill_parents(mother, relation, relatives, deep)

                   
def get_blood_relatives(person):
    deep = None
    relatives = {person.uid: ''}
    fill_children(person, '', relatives, deep)
    fill_parents(person, '', relatives, deep)
    del relatives[person.uid]
    return relatives

    