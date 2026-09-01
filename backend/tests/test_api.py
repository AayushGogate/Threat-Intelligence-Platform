class TestAuth:
    def test_login_success(self, client):
        import os
        resp = client.post("/api/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        import os
        resp = client.post("/api/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": "wrong"})
        assert resp.status_code == 401

    def test_me_requires_auth(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_token(self, client, admin_token):
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["email"]


class TestIOCEndpoints:
    def test_list_iocs_requires_auth(self, client):
        resp = client.get("/api/iocs")
        assert resp.status_code == 401

    def test_list_iocs_demo_data_present(self, client, admin_token):
        resp = client.get("/api/iocs", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_create_ioc_valid(self, client, admin_token):
        resp = client.post(
            "/api/iocs",
            json={"type": "IPV4", "value": "203.0.113.99", "description": "test IOC"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["value"] == "203.0.113.99"

    def test_create_ioc_invalid_rejected(self, client, admin_token):
        resp = client.post(
            "/api/iocs",
            json={"type": "IPV4", "value": "not-an-ip"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_create_ioc_deduplicates(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        first = client.post("/api/iocs", json={"type": "IPV4", "value": "203.0.113.200"}, headers=headers)
        second = client.post("/api/iocs", json={"type": "IPV4", "value": "203.0.113.200"}, headers=headers)
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] == second.json()["id"]

    def test_get_ioc_detail(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        created = client.post("/api/iocs", json={"type": "DOMAIN", "value": "detail-test.invalid"}, headers=headers)
        ioc_id = created.json()["id"]
        detail = client.get(f"/api/iocs/{ioc_id}", headers=headers)
        assert detail.status_code == 200
        assert "score_breakdown" in detail.json()


class TestRBAC:
    def test_viewer_cannot_create_ioc(self, client, viewer_token):
        resp = client.post(
            "/api/iocs",
            json={"type": "IPV4", "value": "203.0.113.201"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_viewer_can_read_iocs(self, client, viewer_token):
        resp = client.get("/api/iocs", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 200

    def test_viewer_cannot_read_audit_logs(self, client, viewer_token):
        resp = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
