# pony-rest

A subset implementation of `PostgREST`.

You should read [PostgREST](http://postgrest.org/) and [PonyORM](https://docs.ponyorm.com/) first.

### Install

```
pip install pony-rest
```

### Example

Edit `app.py`:

```python
from datetime import datetime, date
from pony_rest import BaseEntity, start, make_app

from pony.orm import (
    PrimaryKey,
    Required,
    Optional,
    Set,
    Json,
    db_session,
)


class Person(BaseEntity):
    name = Required(str, 32)
    age = Required(int)
    data = Optional(Json)
    cars = Set(lambda: Car)


class Car(BaseEntity):
    make = Required(str, 64)
    model = Optional(str, 32, nullable=True)
    owner = Required(lambda: Person)


if __name__ == '__main__':
    start(18000)
else:
    application = make_app()  # wsgi app
```

### How to use this server to do CRUD

```sh
# create new Person
curl -d '{"name": "foo", "age": 10}' localhost:18000/person

# read Person list
curl localhost:18000/person

# update Person where id is 1
curl -X PATCH -d '{"age": 10}' 'localhost:18000/person?id=eq.1'

# delete Person where id is 1
curl -X DELETE 'localhost:18000/person?id=eq.1'
```

### Lots TODO...
