import falcon


def test_post(client):
    resp = client.simulate_post('/t', json={"s": "x"})
    resp = client.simulate_post('/t', json={"s": "x"})
    assert resp.status == falcon.HTTP_OK


def test_get(client, capsys):
    resp = client.simulate_get('/t')
    assert resp.status == falcon.HTTP_OK
    assert isinstance(resp.json, list)


def test_patch(client):
    params = {"id": "eq.1"}
    headers = {"Accept": "application/vnd.pgrst.object+json"}
    s_new = "xxx"
    resp = client.simulate_patch('/t', params=params, json={"s": s_new})
    assert resp.status == falcon.HTTP_OK
    resp = client.simulate_get('/t', params=params, headers=headers)
    assert resp.status == falcon.HTTP_OK
    assert isinstance(resp.json, dict)
    assert resp.json["s"] == s_new


def test_delete(client):
    resp = client.simulate_post('/t', json={"s": "to_delete"})
    assert resp.status == falcon.HTTP_OK
    resp = client.simulate_delete('/t', params={"s": "eq.to_delete"})
    assert resp.status == falcon.HTTP_OK
