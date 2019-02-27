#!/usr/bin/env python3

"""
copy from
https://docs.ponyorm.org/firststeps.html#defining-entities
"""

from datetime import date
from datetime import datetime
from pony.orm import *


db = Database()


class Person(db.Entity):
    name = Required(str)
    age = Required(int)
    cars = Set('Car')


class Car(db.Entity):
    make = Required(str)
    model = Required(str)
    owner = Required(Person)


class T(db.Entity):
    s = Required(str)
    i = Optional(int)
    dt = Optional(datetime)
