"""Tests for the Flask web GUI."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # CSRF is exercised in the browser; disable it here so tests can POST
    # directly without minting tokens.
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


@pytest.fixture
def connected_client(client):
    client.post("/connect", data={
        "base_url": "https://api.example.com",
        "api_key": "testkey",
        "api_key_id": "1",
    })
    return client


class TestIndex:
    def test_renders_disconnected(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Not connected" in resp.data

    def test_renders_connected(self, connected_client):
        resp = connected_client.get("/")
        assert resp.status_code == 200
        assert b"api.example.com" in resp.data


class TestConnect:
    def test_connect_stores_session(self, client):
        resp = client.post("/connect", data={
            "base_url": "https://api.example.com",
            "api_key": "mykey",
            "api_key_id": "42",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"api.example.com" in resp.data

    def test_disconnect_clears_session(self, connected_client):
        resp = connected_client.post("/disconnect", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Not connected" in resp.data


class TestApiModules:
    def test_requires_connection(self, client):
        resp = client.get("/api/modules")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Not connected"

    def test_returns_modules(self, connected_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "reply": [{"module_id": 2, "title": "Malware Protection", "platforms": ["windows"]}]
        }
        with patch("app.get_modules", return_value=mock_resp.json.return_value):
            resp = connected_client.get("/api/modules")
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["module_id"] == 2


class TestApiFetch:
    def test_requires_connection(self, client):
        resp = client.get("/api/fetch")
        assert resp.status_code == 400

    def test_returns_rules(self, connected_client):
        reply = {"data": [{"NAME": "Rule A", "RULE_ID": 1}], "total_count": 1}
        with patch("app.fetch_exceptions", return_value={"reply": reply}):
            resp = connected_client.get("/api/fetch")
        data = resp.get_json()
        assert len(data["data"]) == 1
        assert data["data"][0]["NAME"] == "Rule A"

    def test_passes_name_filter(self, connected_client):
        with patch("app.fetch_exceptions", return_value={"reply": {"data": []}}) as mock:
            connected_client.get("/api/fetch?name=Defender&offset=5&limit=10")
            _, kwargs = mock.call_args
            assert kwargs["filters"] == [{"field": "NAME", "operator": "contains", "value": "Defender"}]
            assert kwargs["search_from"] == 5
            assert kwargs["search_to"] == 15


class TestApiUpload:
    def test_requires_connection(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 400

    def test_requires_file(self, connected_client):
        resp = connected_client.post("/api/upload")
        data = resp.get_json()
        assert data["error"] == "No CSV file provided"

    def _upload(self, client, csv_text, dry_run="true", validate="false"):
        return client.post("/api/upload", data={
            "csv_file": (io.BytesIO(csv_text.encode()), "test.csv"),
            "dry_run": dry_run,
            "validate": validate,
        }, content_type="multipart/form-data")

    def test_dry_run(self, connected_client):
        csv = "NAME,DESCRIPTION,PLATFORM,PATHS,MODULES,SCOPE,PROFILE_IDS,STATUS\nTest,desc,AGENT_OS_WINDOWS,C:\\foo,2,TENANT,,ENABLED\n"
        resp = self._upload(connected_client, csv, dry_run="true")
        result = resp.get_json()
        assert result["dry_run"] is True
        assert result["total"] == 1
        assert result["results"][0]["status"] == "DRY"

    def test_module_validation_failure_blocks_upload(self, connected_client):
        csv = "NAME,PATHS,MODULES\nTest,C:\\foo,99\n"
        mod_result = {
            "valid_ids": set(),
            "invalid_ids": {99},
            "available_modules": [{"module_id": 2, "pretty_name": "Exploit", "platforms": ["windows"]}],
            "affected_rows": {99: [{"row": 1, "name": "Test"}]},
            "suggestions": {99: [{"module_id": 2, "pretty_name": "Exploit"}]},
        }
        with patch("app.validate_modules", return_value=mod_result):
            resp = self._upload(connected_client, csv, dry_run="false")
        data = resp.get_json()
        assert resp.status_code == 400
        assert "1 module" in data["error"]
        assert data["invalid_modules"] == [99]
        assert len(data["available_modules"]) == 1
        assert data["affected_rows"]["99"][0]["name"] == "Test"
        assert data["suggestions"]["99"][0]["module_id"] == 2

    def test_upload_success(self, connected_client):
        csv = "NAME,DESCRIPTION,PLATFORM,PATHS,MODULES,SCOPE,PROFILE_IDS,STATUS\nTest,desc,AGENT_OS_WINDOWS,C:\\foo,2,TENANT,,ENABLED\n"
        mod_result = {
            "valid_ids": {2},
            "invalid_ids": set(),
            "available_modules": [],
            "affected_rows": {},
            "suggestions": {},
        }
        with patch("app.validate_modules", return_value=mod_result), \
             patch("app.upload_exception", return_value={"reply": {"id": 1}}):
            resp = self._upload(connected_client, csv, dry_run="false")
        result = resp.get_json()
        assert result["results"][0]["status"] == "OK"


class TestApiDelete:
    def test_requires_connection(self, client):
        resp = client.post("/api/delete", json={"rule_ids": [1]})
        assert resp.status_code == 400

    def test_requires_rule_ids(self, connected_client):
        resp = connected_client.post("/api/delete",
                                     json={"rule_ids": []},
                                     content_type="application/json")
        assert resp.status_code == 400

    def test_deletes_rules(self, connected_client):
        with patch("app.delete_exceptions", return_value={"reply": True}):
            resp = connected_client.post("/api/delete",
                                         json={"rule_ids": [1, 2]},
                                         content_type="application/json")
        assert resp.get_json()["reply"] is True
