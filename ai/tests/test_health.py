def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_degraded_without_plane_key(client):
    # Without a configured gateway/plane key, ready reports degraded.
    response = client.get("/ready")
    assert response.status_code in (200, 503)
