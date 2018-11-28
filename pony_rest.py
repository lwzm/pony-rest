#!/usr/bin/env python3

"""
money patch first
converting.str2datetime = my custom str2datetime must be first
"""
# money patch begin
from datetime import datetime, date

import pendulum
import pony.converting

def str2datetime(s):
    """
    parse yyyy-mm-dd HH:MM:SS or yyyy-mm-ddTHH:MM:SS[TZ]
    and return datetime with timezone
    """
    tz = pendulum.local_timezone()
    dt = pendulum.parse(s, tz=tz)
    return datetime.fromtimestamp(dt.timestamp(), tz=tz)

pony.converting.str2datetime = str2datetime

import pony.orm  # at end
assert pony.orm.dbapiprovider.str2datetime is str2datetime
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

        def _select(self):
            """
            see:
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
    with open("database.yaml") as f:
        options, *_ = yaml.load_all(f)
        fn = options["filename"]
        if fn != ":memory:":
            from os.path import abspath
            options["filename"] = abspath(fn)  # patch sqlite
    database.bind(**options)
    database.generate_mapping(create_tables=True)
    handlers = [
        magic_it(i)
        for i in BaseEntity.__subclasses__()
    ]
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
