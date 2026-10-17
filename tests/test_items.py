def test_items_crud(client):
    # Create
    resp = client.post("/items", json={"name": "Cuenta ahorro", "description": "Producto base"})
    assert resp.status_code == 201
    item = resp.json()
    assert item["name"] == "Cuenta ahorro"
    assert item["is_active"] is True
    item_id = item["id"]

    # Read
    resp = client.get(f"/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["description"] == "Producto base"

    # List
    client.post("/items", json={"name": "Tarjeta"})
    resp = client.get("/items")
    assert resp.status_code == 200
    assert [i["name"] for i in resp.json()] == ["Cuenta ahorro", "Tarjeta"]

    # Update parcial
    resp = client.patch(f"/items/{item_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["name"] == "Cuenta ahorro"

    # Delete
    resp = client.delete(f"/items/{item_id}")
    assert resp.status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404


def test_item_not_found(client):
    assert client.get("/items/999").status_code == 404
    assert client.patch("/items/999", json={"name": "x"}).status_code == 404
    assert client.delete("/items/999").status_code == 404


def test_item_validation(client):
    assert client.post("/items", json={"name": ""}).status_code == 422
    assert client.post("/items", json={}).status_code == 422
    item_id = client.post("/items", json={"name": "x"}).json()["id"]
    assert client.patch(f"/items/{item_id}", json={"name": None}).status_code == 422
    assert client.patch(f"/items/{item_id}", json={"is_active": None}).status_code == 422


def test_delete_item_removes_its_files(client, bucket_keys):
    item_id = client.post("/items", json={"name": "Cliente"}).json()["id"]
    for name in ("dni.pdf", "contrato.pdf"):
        client.post("/files", data={"item_id": str(item_id)}, files={"file": (name, b"pdf", "application/pdf")})
    unlinked = client.post("/files", files={"file": ("suelto.txt", b"x", "text/plain")}).json()
    assert len(bucket_keys()) == 3

    assert client.delete(f"/items/{item_id}").status_code == 204
    assert client.get(f"/items/{item_id}/files").status_code == 404
    assert [f["id"] for f in client.get("/files").json()] == [unlinked["id"]]
    assert bucket_keys() == [unlinked["s3_key"]]
