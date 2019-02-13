
from falcon import HTTP_OK
from falcon.testing import TestClient


def test_post(client):
    resp = client.simulate_post('/t', json={"s": "x"})
    resp = client.simulate_post('/t', json={"s": "x"})
    assert resp.status == HTTP_OK


def test_get(client: TestClient, capsys):
    params = {"order": "id.desc"}
    resp = client.simulate_get('/t', params=params)
    assert resp.status == HTTP_OK
    assert isinstance(resp.json, list)
    v1, v2, *_ = (i["id"] for i in resp.json)
    assert v1 > v2
    assert "Content-Range" in resp.headers
    resp = client.simulate_get('/t', headers={"Prefer": "count=exact"})
    assert "Content-Range" in resp.headers
    r, n = resp.headers["Content-Range"].split("/")
    b, e = r.split("-")
    assert n.isdigit()
    assert b.isdigit()
    assert e.isdigit()


def test_patch(client):
    params = {"id": "eq.1"}
    s_new = "xxx"
    resp = client.simulate_patch('/t', params=params, json={"s": s_new})
    assert resp.status == HTTP_OK
    resp = client.simulate_get('/t', params=params, headers={"Accept": "application/vnd.pgrst.object+json"})
    assert resp.status == HTTP_OK
    assert "Content-Range" not in resp.headers
    assert isinstance(resp.json, dict)
    assert resp.json["s"] == s_new


def test_delete(client):
    resp = client.simulate_post('/t', json={"s": "to_delete"})
    assert resp.status == HTTP_OK
    resp = client.simulate_delete('/t', params={"s": "eq.to_delete"})
    assert resp.status == HTTP_OK
