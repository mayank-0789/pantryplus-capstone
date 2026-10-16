from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal


def test_stock_ledger_survives_deletion(client):
    item = client.post('/api/items', json={'name': 'Rice', 'quantity': 2, 'unit': 'kg'}).json()
    path = f"/api/items/{item['id']}"
    assert client.post(path + '/restock', json={'amount': 3, 'note': 'weekly shop'}).status_code == 200
    assert client.post(path + '/consume', json={'amount': 1}).status_code == 200
    assert client.post(path + '/waste', json={'amount': '.25', 'note': 'spilled'}).status_code == 200
    assert Decimal(client.get(path).json()['quantity']) == Decimal('3.75')
    history = client.get('/api/activity').json()
    assert [x['kind'] for x in history] == ['waste', 'consume', 'restock', 'opening']
    assert sum(Decimal(x['amount']) for x in history) == Decimal('3.75')
    assert client.post(path + '/consume', json={'amount': 99}).status_code == 409
    assert len(client.get('/api/activity').json()) == 4
    assert client.delete(path).status_code == 204
    history = client.get('/api/activity').json()
    assert len(history) == 5 and all(x['item_id'] is None for x in history)
    assert sum(Decimal(x['amount']) for x in history) == 0


def test_concurrent_consumption_cannot_overdraw(client):
    item = client.post('/api/items', json={'name': 'Last egg', 'quantity': 1}).json()
    def consume(_):
        return client.post(f"/api/items/{item['id']}/consume", json={'amount': 1}).status_code
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(consume, range(5)))
    assert results.count(200) == 1
    assert results.count(409) == 4
    assert len(client.get('/api/activity').json()) == 2


def test_capacity_and_missing_item(client):
    item = client.post('/api/items', json={'name': 'Full', 'quantity': '99999999.99'}).json()
    assert client.post(f"/api/items/{item['id']}/restock", json={'amount': 1}).status_code == 409
    assert client.post('/api/items/999/restock', json={'amount': 1}).status_code == 404
    assert client.get('/api/activity?limit=201').status_code == 422
    assert client.put(f"/api/items/{item['id']}", json={'quantity': 3}).status_code == 422
