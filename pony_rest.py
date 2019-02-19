#!/usr/bin/env python3

"""
money patch first
converting.str2datetime = my custom str2datetime must be first
"""

# money patch begin
from datetime import datetime, date
import pendulum

def str2datetime(s):
    """
    parse yyyy-mm-dd HH:MM:SS or yyyy-mm-ddTHH:MM:SS[TZ]
    and return datetime with timezone
    """
    tz = pendulum.local_timezone()
    dt = pendulum.parse(s, tz=tz)
    return datetime.fromtimestamp(dt.timestamp(), tz=tz)

import pony.converting
pony.converting.str2datetime = str2datetime
import pony.orm.dbapiprovider
pony.orm.dbapiprovider.str2datetime = str2datetime
# money patch end


import json

from falcon import API, Request, Response, HTTPNotFound
from pony.orm import db_session, raw_sql, Database
from pony.converting import str2datetime, str2date


def identity(x):
    return x


def default(x):
    if isinstance(x, datetime):
        ts = x.replace(tzinfo=pendulum.local_timezone()).timestamp()
        x = pendulum.from_timestamp(ts).astimezone()
    return str(x)


database = Database()
database._has_generated = False
BaseEntity = database.Entity

# https://docs.ponyorm.org/database.html#customizing-connection-behavior
@database.on_connect(provider='sqlite')
def _home_sqliterc(_, conn):
    import pathlib
    rc = pathlib.Path.home() / ".sqliterc"
    rc.exists() and conn.executescript(rc.read_text())


def export():
    from pony.orm import Json
    formats_for_js = {
        str: "string",
        int: "number",
        float: "float",
        bool: "boolean",
        datetime: "datetime",
        date: "date",
        Json: "json",
    }
    lst = []
    pks = {}
    try:
        import yaml
        with open("patch.yaml") as f:
            patch = yaml.load(f)
    except FileNotFoundError:
        patch = {}
    # 1
    for table in BaseEntity.__subclasses__():
        tableName = table.__name__.lower()
        tablePatch = patch.get(tableName, {})
        pk = None
        fs = []
        for column in table._attrs_:
            columnName = column.column
            if not columnName:
                continue
            assert column.py_type, column
            if column.is_pk:
                pk = columnName
                pks[table] = {
                    "tableName": tableName,
                    "columnName": columnName,
                }
            py_type = column.py_type
            type = formats_for_js.get(py_type, py_type)
            if type == "string" and not column.args:
                type = "text"
            o = {
                "columnName": columnName,
                "type": type,
            }
            if column.lazy:
                o["hide"] = True
            o.update(tablePatch.pop(columnName, {}))
            fs.append(o)

        t = {
            "tableName": tableName,
            "primaryKey": pk,
            "fs": fs,
        }
        t.update(tablePatch)
        lst.append(t)
    # 2
    for i in lst:
        for f in i["fs"]:
            t = f["type"]
            if not isinstance(t, str):
                assert issubclass(t, BaseEntity), t
                f["foreignKey"] = pks[f.pop("type")]
    # 3
    return lst


class Export:
    def on_get(self, req: Request, resp: Response):
        resp.media = export()


class Table:
    op_map = {
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "like": "like",
    }

    def __init__(self, entity):
        converts = {}
        for i in entity._attrs_:
            if not i.column:
                continue
            t = i.py_type
            if issubclass(i.py_type, BaseEntity):
                t = i.py_type._pk_.py_type
            conv = json.loads
            if t is datetime:
                conv = str2datetime
            elif t is date:
                conv = str2date
            elif t is str:
                conv = identity
            converts[i.column] = conv

        self.entity = entity
        self.converts = converts

    def _select(self, params, order=None):
        """Must under with db_session, and read the doc:
        https://docs.ponyorm.com/queries.html#using-raw-sql-ref
        """
        filters = []
        args = []

        for k, v in params.items():
            if k not in self.converts:
                continue
            op, _, value = v.partition(".")
            if not value:
                continue

            value = self.converts[k](value)
            op = self.op_map[op]
            idx = len(args)
            filters.append(f"x.{k} {op} $args[{idx}]")
            args.append(value)

        if filters:
            q = self.entity.select(lambda x: raw_sql(" and ".join(filters)))
        else:
            q = self.entity.select()

        if order:
            field, _, sc = order.partition(".")
            sc = sc or "asc"
            q = q.order_by(getattr(getattr(self.entity, field), sc))

        return q

    def on_get(self, req: Request, resp: Response):
        single = ".object" in req.get_header("Accept", default="")
        if single:
            start, stop = 0, 1
        else:
            list_range = req.get_header("Range")
            if list_range:
                start, stop = map(int, list_range.split("-"))
                stop += 1
            else:
                start, stop = 0, 100

        exact = "count=exact" in req.get_header("Prefer", default="")
        count = "*"
        limit = req.get_param("limit")
        offset = req.get_param("offset")
        if limit or offset:
            start = int(offset or 0)
            stop = start + int(limit or 100)
        order = req.get_param("order")
        only = req.get_param("select")
        only = only.split(",") if only else None

        # https://docs.ponyorm.com/api_reference.html#Entity.to_dict
        # http://postgrest.org/en/latest/api.html#vertical-filtering-columns
        with db_session:
            q = self._select(req.params, order)
            if exact and not single:
                count = q.count()
            lst = [i.to_dict(only, with_lazy=True) for i in q[start:stop]]

        if single:
            if not lst:
                raise HTTPNotFound()
            result = lst[0]
        else:
            resp.set_header("Content-Range", f"{start}-{stop}/{count}")
            result = lst
        resp.body = json.dumps(result, default=default, ensure_ascii=False)

    def on_post(self, req: Request, resp: Response):
        with db_session:
            self.entity(**req.media)

    def on_patch(self, req: Request, resp: Response):
        info = req.media
        if not info:
            return
        with db_session:
            single, = self._select(req.params)
            single.set(**info)

    def on_delete(self, req: Request, resp: Response):
        with db_session:
            single, = self._select(req.params)
            single.delete()


def generate_mapping():
    if database._has_generated:
        return
    database._has_generated = True
    import yaml
    try:
        with open("database.yaml") as f:
            options, *_ = yaml.load_all(f)  # only need the first options
    except FileNotFoundError:
        options = dict(provider="sqlite", filename=":memory:",
                       create_db=True, create_tables=True)
    fn = options.get("filename")
    if fn and fn != ":memory:":
        from os.path import abspath
        options["filename"] = abspath(fn)  # patch sqlite
    create_tables = options.pop("create_tables", False)
    database.bind(**options)
    database.generate_mapping(create_tables=create_tables)


def make_application():
    generate_mapping()
    app = API()
    for i in BaseEntity.__subclasses__():
        name = i.__name__.lower()
        app.add_route(f"/{name}", Table(i))
    app.add_route(f"/-1", Export())
    return app

make_app = make_application


def start(port=3333, addr="", sock=None):
    application = make_application()
    try:
        from bjoern import run
        args = [f"unix:{sock}"] if sock else [addr, port]
        run(application, *args)
    except ImportError:
        from wsgiref.simple_server import make_server
        make_server(addr, port, application).serve_forever()


if __name__ == '__main__':
    start(addr='127.0.0.1', sock='s')
