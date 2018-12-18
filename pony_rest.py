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

import falcon
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
BaseEntity = database.Entity


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
    def on_get(self, req, resp):
        resp.body = json.dumps(export(), ensure_ascii=False)


class Table:
    op_map = {
        "eq": "=",
        "gt": ">",
        "lt": "<",
        "like": "like",
    }

    args_not_used = {"order", "select", }

    def __init__(self, entity):
        converts = {}
        for i in entity._attrs_:
            if not i.column:
                continue
            t = i.py_type
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

    def _select(self, params):
        """Must under with db_session, and read the doc:
        https://docs.ponyorm.com/queries.html#using-raw-sql-ref
        """
        filters = []
        args = []

        for k, v in params.items():
            if k in self.args_not_used:
                continue
            op, _, value = v.partition(".")
            if not value:
                continue

            value = self.converts[k](value)
            op = self.op_map[op]
            idx = len(args)
            filters.append(f"{k} {op} $args[{idx}]")
            args.append(value)

        q = self.entity.select()
        if filters:
            q = q.filter(lambda x: raw_sql(" and ".join(filters)))

        order = params.get("order", None)
        if order:
            field, _, sc = order.partition(".")
            sc = sc or "asc"
            q = q.order_by(getattr(getattr(self.entity, field), sc))

        return q

    def on_get(self, req, resp):
        single = ".object" in req.get_header("Accept", default="")
        if single:
            start, stop = 0, 0
        else:
            list_range = req.get_header("Range")
            if list_range:
                start, stop = map(int, list_range.split("-"))
            else:
                start, stop = 0, 99
        exact = "count=exact" in req.get_header("Prefer", default="")
        count = "*"
        only = req.params.get("select", None)
        only = only and only.split(",")

        # https://docs.ponyorm.com/api_reference.html#Entity.to_dict
        # http://postgrest.org/en/latest/api.html#vertical-filtering-columns
        with db_session:
            q = self._select(req.params)
            if exact:
                count = q.count()
            lst = [i.to_dict(only) for i in q[start:stop + 1]]

        result = lst[0] if single else lst
        resp.set_header("Content-Range", f"{start}-{stop}/{count}")
        resp.body = json.dumps(result, default=default, ensure_ascii=False)

    def on_post(self, req, resp):
        with db_session:
            self.entity(**json.load(req.stream))

    def on_patch(self, req, resp):
        info = json.load(req.stream)
        if not info:
            return
        with db_session:
            single, = self._select(req.params)
            single.set(**info)

    def on_delete(self, req, resp):
        with db_session:
            single, = self._select(req.params)
            single.delete()


def make_app():
    import yaml
    try:
        with open("database.yaml") as f:
            options, *_ = yaml.load_all(f)  # only need the first options
            fn = options.get("filename")
            if fn and fn != ":memory:":
                from os.path import abspath
                options["filename"] = abspath(fn)  # patch sqlite
    except FileNotFoundError:
        options = dict(provider="sqlite", filename=":memory:",
                       create_db=True, create_tables=True)
    create_tables = options.pop("create_tables", False)
    database.bind(**options)
    database.generate_mapping(create_tables=create_tables)

    app = falcon.API()
    for i in BaseEntity.__subclasses__():
        name = i.__name__.lower()
        app.add_route(f"/{name}", Table(i))
    app.add_route(f"/", Export())
    return app


def start(port=3333, addr="", sock=None):
    application = make_app()
    try:
        from bjoern import run
        args = [f"unix:{sock}"] if sock else [addr, port]
        run(application, *args)
    except ImportError:
        from wsgiref.simple_server import make_server
        make_server(addr, port, application).serve_forever()


if __name__ == '__main__':
    start(addr='127.0.0.1', sock='s')
