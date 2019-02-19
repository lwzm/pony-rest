import falcon

def test_export_config(client, capsys):
    resp = client.simulate_get('/-1')
    assert resp.status == falcon.HTTP_OK
    assert isinstance(resp.json, list)
    for table in resp.json:
        assert "fs" in table
        assert "tableName" in table
    # with capsys.disabled():
        # print(resp.json)
