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

import tornado.web


def json_default(x):
    if isinstance(x, datetime):
        ts = x.replace(tzinfo=pendulum.local_timezone()).timestamp()
        x = pendulum.from_timestamp(ts).astimezone()
    return str(x)


class BaseHandler(tornado.web.RequestHandler):
    def write_json(self, obj):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(obj, default=json_default, ensure_ascii=False,
                              separators=(",", ":")))

    @property
    def json(self):
        if not hasattr(self, "_json"):
            self._json = json.loads(self.request.body)
        return self._json


database = pony.orm.Database()
BaseEntity = database.Entity


class ExportHandler(BaseHandler):
    def get(self):
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
        self.write_json(lst)


def magic_it(Entity):
    from urllib.parse import parse_qsl
    from pony.orm import db_session, raw_sql
    from pony.converting import str2datetime, str2date

    op_map = {
        "eq": "=",
        "gt": ">",
        "lt": "<",
        "like": "like",
    }

    args_not_used = {"order", "select", }

    def identity(x):
        return x

    converts = {}

    for i in Entity._attrs_:
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

    class Handler(BaseHandler):
        """Implement subset of postgrest, see:
        https://postgrest.org/
        """

        def _select(self):
            """Must under with db_session, and read the doc:
            https://docs.ponyorm.com/queries.html#using-raw-sql-ref
            """
            filters = []
            args = []

            for k, v in parse_qsl(self.request.query):
                if k in args_not_used:
                    continue
                op, _, value = v.partition(".")
                if not value:
                    continue

                value = converts[k](value)
                op = op_map[op]
                idx = len(args)
                filters.append(f"{k} {op} $args[{idx}]")
                args.append(value)

            q = Entity.select()
            if filters:
                q = q.filter(lambda x: raw_sql(" and ".join(filters)))

            order = self.get_argument("order", None)
            if order:
                field, _, sc = order.partition(".")
                sc = sc or "asc"
                q = q.order_by(getattr(getattr(Entity, field), sc))

            return q

        def get(self):
            headers = self.request.headers
            single = ".object" in headers.get("Accept", "")
            if single:
                start, stop = 0, 0
            else:
                try:
                    start, stop = map(int, headers["Range"].split("-"))
                except KeyError:
                    start, stop = 0, 99
            exact = "count=exact" in headers.get("Prefer", "")
            count = "*"

            # https://docs.ponyorm.com/api_reference.html#Entity.to_dict
            # http://postgrest.org/en/latest/api.html#vertical-filtering-columns
            only = self.get_argument("select", None)
            only = only and only.split(",")
            with db_session:
                q = self._select()
                if exact:
                    count = q.count()
                lst = [i.to_dict(only) for i in q[start:stop + 1]]

            self.set_header("Content-Range", f"{start}-{stop}/{count}")

            if single:
                self.write_json(lst[0])
            else:
                self.write_json(lst)

        def post(self):
            with db_session:
                Entity(**self.json)

        def patch(self):
            if not self.json:
                return
            with db_session:
                single, = self._select()
                single.set(**self.json)

        def delete(self):
            with db_session:
                single, = self._select()
                single.delete()

    name = Entity.__name__.lower()
    return f"/{name}", Handler


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
    handlers = [
        magic_it(i)
        for i in BaseEntity.__subclasses__()
    ]
    handlers.append(("/", ExportHandler))
    return tornado.web.Application(handlers)


def make_application():
    from tornado.wsgi import WSGIAdapter
    return WSGIAdapter(make_app())


def start(port=3333, addr="", sock=None):
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()
    app = make_app()
    if sock:
        from tornado.httpserver import HTTPServer
        from tornado.netutil import bind_unix_socket
        unix_socket = bind_unix_socket(sock, 0o666)
        HTTPServer(app, xheaders=True).add_socket(unix_socket)
    else:
        app.listen(port, addr, xheaders=True)
    from tornado.ioloop import IOLoop
    IOLoop.current().start()


if __name__ == '__main__':
    start(addr='127.1.1.1', sock='s')
