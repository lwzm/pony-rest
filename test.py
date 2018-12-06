#!/usr/bin/env python

import json
import random
import string
import unittest

import pendulum
from tornado.testing import AsyncHTTPTestCase

from pony_rest import make_app, BaseEntity


class TestHelloApp(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        from pony.orm import Required, Optional, db_session
        from datetime import datetime
        class T(BaseEntity):
            s = Required(str)
            i = Optional(int)
            dt = Optional(datetime)
        cls.app = make_app()

    def get_app(self):
        return self.app

    def test_export(self):
        rsp = self.fetch('/')
        self.assertIsInstance(json.loads(rsp.body), list)

    def test_get(self):
        rsp = self.fetch('/t')
        self.assertEqual(rsp.code, 200)
        data = json.loads(rsp.body)
        self.assertIsInstance(data, list)

    def post_random(self):
        s = "-".join(random.choice(string.ascii_letters) for _ in range(5))
        rsp = self.fetch('/t', method="POST", body=json.dumps({"s": s}))
        self.assertEqual(rsp.code, 200)
        return s

    def delete(self, s):
        rsp = self.fetch(f'/t?s=eq.{s}', method="DELETE")
        self.assertEqual(rsp.code, 200)

    def test_modify(self):
        s = self.post_random()
        rsp = self.fetch(f'/t?s=eq.{s}', headers={
            "Accept": "application/vnd.pgrst.object+json",
        })
        self.assertEqual(rsp.code, 200)
        data = json.loads(rsp.body)
        self.assertIsInstance(data, dict)
        id = data["id"]
        rsp = self.fetch(f'/t?id=eq.{id}', method="PATCH", body=json.dumps({"s": "x"}))
        self.assertEqual(rsp.code, 200)
        rsp = self.fetch(f'/t?id=eq.{id}', method="DELETE")
        self.assertEqual(rsp.code, 200)

    def test_select(self):
        s = self.post_random()
        rsp = self.fetch(f'/t?s=eq.{s}&select=id,s')
        data = json.loads(rsp.body)
        self.assertEqual(set(data[0]), {"id", "s"})
        self.delete(s)

    def test_datetime(self):
        rsp = self.fetch('/t', method="POST", body=json.dumps({
            "s": "dt_1",
            "dt": "2011-11-11 00:00:00",
        }))
        self.assertEqual(rsp.code, 200)
        #print(json.loads(self.fetch('/t?s=eq.dt_1').body)[0]["dt"])
        rsp = self.fetch('/t', method="POST", body=json.dumps({
            "s": "dt_2",
            "dt": "2011-11-11T00:00:00Z",
        }))
        self.assertEqual(rsp.code, 200)
        rsp = self.fetch('/t', method="POST", body=json.dumps({
            "s": "dt_3",
            "dt": "2011-11-11T00:00:00+06",
        }))
        self.assertEqual(rsp.code, 200)


if __name__ == '__main__':
    unittest.main()
