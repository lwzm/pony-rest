#!/usr/bin/env python

import json
import random
import string
import unittest

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

    def test_get(self):
        rsp = self.fetch('/t')
        self.assertEqual(rsp.code, 200)
        self.assertIsInstance(json.loads(rsp.body), list)

    def test_post(self):
        s = "-".join(random.choice(string.ascii_letters) for _ in range(5))
        rsp = self.fetch('/t', method="POST", body=json.dumps({"s": s}))
        self.assertEqual(rsp.code, 200)
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


if __name__ == '__main__':
    unittest.main()
