from urllib.parse import quote

import falcon
import pendulum


def test_query(client):
    n = 100
    for i in range(n):
        client.simulate_post('/t', json={"s": f"a{i}"})
    resp = client.simulate_get('/t', params={"order": "id"})
    v1, v2, *_ = (i["id"] for i in resp.json)
    assert v1 < v2
    resp = client.simulate_get('/t', params={"order": "id.desc"})
    v1, v2, *_ = (i["id"] for i in resp.json)
    assert v1 > v2
    resp = client.simulate_get('/t', params={"s": "like.a%"})
    assert len(resp.json) == n
    resp = client.simulate_get('/t', params={"s": "like.a_"})
    assert len(resp.json) == 10
    resp = client.simulate_get('/t', params={"s": "eq.a1"})
    assert len(resp.json) == 1
    resp = client.simulate_get('/t', headers={"Range": "10-29"})
    assert len(resp.json) == 20
    resp = client.simulate_get('/t', params={"limit": 5})
    assert len(resp.json) == 5
    resp = client.simulate_get('/t', params={"offset": 80})
    assert len(resp.json) == n - 80
    resp = client.simulate_get('/t', headers={"Range": "10-29"}, params={"offset": 0, "limit": 1})
    assert len(resp.json) == 1


def test_datetime(client):
    now = "2011-11-11 11:11:11"
    now = str(pendulum.now())
    client.simulate_post('/t', json={"s": "dt", "dt": now})
    resp = client.simulate_get('/t', params={"dt": f"eq.{quote(now)}"})
    assert len(resp.json) == 1
    assert resp.json[0]["dt"][:len(now)] == now
