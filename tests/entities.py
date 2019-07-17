#!/usr/bin/env python3

from datetime import datetime
from pony.orm import *


db = Database()


class T(db.Entity):
    s = Required(str)
    i = Optional(int)
    dt = Optional(datetime)
