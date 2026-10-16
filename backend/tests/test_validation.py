import pytest


@pytest.mark.parametrize('patch', [
    {'name': '   '}, {'quantity': None}, {'name': None}, {'category': None},
    {'unit': None}, {'min_quantity': None}, {'location': None}, {'notes': None},
    {'quantity': '100000000'}, {'quantity': '0.001'}, {'quantity': 'NaN'},
    {'unexpected': True},
])
def test_invalid_update_returns_validation_error(client, patch):
    item = client.post('/api/items', json={'name': 'Rice'}).json()
    assert client.put(f"/api/items/{item['id']}", json=patch).status_code == 422
    assert client.get(f"/api/items/{item['id']}").json()['name'] == 'Rice'


def test_trim_and_clear_expiry(client):
    item = client.post('/api/items', json={'name': ' Rice ', 'expires_on': '2026-11-01'}).json()
    assert item['name'] == 'Rice'
    assert client.put(f"/api/items/{item['id']}", json={'expires_on': None}).json()['expires_on'] is None


@pytest.mark.parametrize('amount', ['0.001', 'NaN', 0, -1, '100000000'])
def test_invalid_consume_amount(client, amount):
    assert client.post('/api/items/1/consume', json={'amount': amount}).status_code == 422
