# pony-rest

A subset implementation of `PostgREST`.

You should read [PostgREST](http://postgrest.org/) and [PonyORM](https://docs.ponyorm.com/) first.

### Install

```
pip install pony-rest
```

### Example

Edit `entities.py`:

```python
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
```

then:
```
python -m pony_rest
```

or via wsgi:
```
gunicorn pony_rest
```

### How to use this server to do CRUD

```sh
T=localhost:3333

# create new Person
curl -H 'content-type: application/json' -d '{"name": "foo", "age": 10}' $T/person

# read Person list
curl localhost:18000/person

# update Person where id is 1
curl -H 'content-type: application/json' -X PATCH -d '{"age": 10}' "$T/person?id=eq.1"

# delete Person where id is 1
curl -X DELETE "$T/person?id=eq.1"
```

### Connect your database

Install module [pyyaml](https://pyyaml.org/), then create a configure file: `database.yaml` in your working directory, likes:
```
provider: sqlite
filename: ":memory:"
create_db: true
create_tables: true
```

...and see [database.yaml](database.yaml) in this repo to find more.

Note: only the first block configurations in yaml file is used for database,
you could leave the old configurations in next blocks.

### Lots TODO...
