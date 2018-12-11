from urllib.parse import quote

import falcon
import pendulum


def test_query(client):
    for i in range(100):
        client.simulate_post('/t', json={"s": f"a{i}"})
    resp = client.simulate_get('/t', params={"s": "like.a%"})
    assert len(resp.json) == 100
    resp = client.simulate_get('/t', params={"s": "like.a_"})
    assert len(resp.json) == 10
    resp = client.simulate_get('/t', params={"s": "eq.a1"})
    assert len(resp.json) == 1
    resp = client.simulate_get('/t', headers={"Range": "10-29"})
    assert len(resp.json) == 20


def test_datetime(client):
    now = "2011-11-11 11:11:11"
    now = str(pendulum.now())
    client.simulate_post('/t', json={"s": "dt", "dt": now})
    resp = client.simulate_get('/t', params={"dt": f"eq.{quote(now)}"})
    assert len(resp.json) == 1
    assert resp.json[0]["dt"][:len(now)] == now
