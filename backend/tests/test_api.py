from datetime import date, timedelta


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_checks_the_database(client):
    assert client.get("/ready").json() == {"status": "ready"}


def test_add_item_returns_201_with_defaults(client):
    r = client.post("/api/items", json={"name": "Basmati rice", "quantity": 2, "unit": "kg", "category": "grains"})
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1 and body["location"] == "" and body["expires_on"] is None


def test_rejects_unknown_category_and_negative_quantity(client):
    assert client.post("/api/items", json={"name": "x", "category": "snacks"}).status_code == 422
    assert client.post("/api/items", json={"name": "x", "quantity": -1}).status_code == 422


def test_list_filters(client):
    soon = (date.today() + timedelta(days=3)).isoformat()
    client.post("/api/items", json={"name": "Milk", "category": "dairy", "quantity": 1, "unit": "l", "expires_on": soon})
    client.post("/api/items", json={"name": "Salt", "category": "spices", "quantity": 0, "min_quantity": 1})
    assert len(client.get("/api/items").json()) == 2
    assert [i["name"] for i in client.get("/api/items", params={"category": "dairy"}).json()] == ["Milk"]
    assert [i["name"] for i in client.get("/api/items", params={"low_stock": "true"}).json()] == ["Salt"]
    assert [i["name"] for i in client.get("/api/items", params={"expiring": "true"}).json()] == ["Milk"]


def test_update_and_delete(client):
    item_id = client.post("/api/items", json={"name": "Eggs", "quantity": 12}).json()["id"]
    r = client.put(f"/api/items/{item_id}", json={"location": "fridge door", "min_quantity": 6})
    assert r.status_code == 200 and r.json()["location"] == "fridge door"
    assert client.delete(f"/api/items/{item_id}").status_code == 204
    assert client.get(f"/api/items/{item_id}").status_code == 404


def test_consume_reduces_stock_and_refuses_overdraw(client):
    item_id = client.post("/api/items", json={"name": "Flour", "quantity": 1.5, "unit": "kg"}).json()["id"]
    r = client.post(f"/api/items/{item_id}/consume", json={"amount": 0.5})
    assert r.status_code == 200 and float(r.json()["quantity"]) == 1.0
    assert client.post(f"/api/items/{item_id}/consume", json={"amount": 5}).status_code == 409


def test_stats(client):
    today = date.today()
    client.post("/api/items", json={"name": "Yogurt", "category": "dairy", "quantity": 2, "expires_on": (today + timedelta(days=2)).isoformat()})
    client.post("/api/items", json={"name": "Bread", "category": "grains", "quantity": 1, "expires_on": (today - timedelta(days=1)).isoformat()})
    client.post("/api/items", json={"name": "Cumin", "category": "spices", "quantity": 0, "min_quantity": 1})
    s = client.get("/api/items/stats").json()
    assert s["total_items"] == 3
    assert s["by_category"]["dairy"] == 1 and s["by_category"]["produce"] == 0
    assert s["expiring_soon"] == 1 and s["expired"] == 1 and s["low_stock"] == 1


def _metric(body, name):
    return float(next(l for l in body.splitlines() if l.startswith(name + " ")).split()[-1])


def test_metrics_endpoint(client):
    before = _metric(client.get("/metrics").text, "pantry_items_added_total")
    client.post("/api/items", json={"name": "Butter", "quantity": 1})
    body = client.get("/metrics").text
    assert _metric(body, "pantry_items_added_total") == before + 1
    assert 'pantry_http_requests_total{method="POST",route="/api/items",status="201"}' in body


def test_expiry_filters_match_stats(client):
    today = date.today()
    for name, days, quantity in [('today', 0, 1), ('week', 7, 1), ('old', -1, 1), ('empty', 2, 0)]:
        client.post('/api/items', json={'name': name, 'quantity': quantity,
            'expires_on': (today + timedelta(days=days)).isoformat()})
    assert [x['name'] for x in client.get('/api/items?expiring=true').json()] == ['today', 'week']
    assert [x['name'] for x in client.get('/api/items?expired=true').json()] == ['old']
    assert client.get('/api/items/stats').json()['expiring_soon'] == 2
    assert client.get('/api/items?category=invalid').status_code == 422
