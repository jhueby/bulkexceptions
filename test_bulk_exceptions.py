"""Validation tests for bulk_exceptions.py."""

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from bulk_exceptions import (
    build_exception_payload,
    build_headers,
    delete_exceptions,
    fetch_exceptions,
    get_modules,
    load_config,
    suggest_modules,
    upload_exception,
    validate_modules,
    validate_uploaded_rules,
)


# --- build_exception_payload ---


class TestBuildExceptionPayload:
    def _row(self, **overrides):
        base = {
            "NAME": "Test Exception",
            "DESCRIPTION": "A test rule",
            "PLATFORM": "AGENT_OS_WINDOWS",
            "PATHS": r"C:\foo\bar;C:\baz",
            "MODULES": "2",
            "SCOPE": "TENANT",
            "PROFILE_IDS": "",
            "STATUS": "ENABLED",
        }
        base.update(overrides)
        return base

    def test_basic_payload_structure(self):
        payload = build_exception_payload(self._row())
        data = payload["new_exception_data"]
        assert data["TYPE"] == "LEGACY_EXCEPTIONS"
        assert data["NAME"] == "Test Exception"
        assert data["DESCRIPTION"] == "A test rule"
        assert data["PLATFORM"] == "AGENT_OS_WINDOWS"
        assert data["SCOPE"] == "TENANT"
        assert data["STATUS"] == "ENABLED"

    def test_paths_split_on_semicolon(self):
        payload = build_exception_payload(self._row(PATHS=r"C:\a;C:\b;C:\c"))
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert folders == [r"C:\a", r"C:\b", r"C:\c"]

    def test_paths_strips_whitespace(self):
        payload = build_exception_payload(self._row(PATHS=" /a ; /b "))
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert folders == ["/a", "/b"]

    def test_empty_path_segments_skipped(self):
        payload = build_exception_payload(self._row(PATHS=";;/a;;;/b;;"))
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert folders == ["/a", "/b"]

    def test_single_path(self):
        payload = build_exception_payload(self._row(PATHS="/only/one"))
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert folders == ["/only/one"]

    def test_modules_parsed_as_ints(self):
        payload = build_exception_payload(self._row(MODULES="2,3,5"))
        assert payload["new_exception_data"]["MODULES"] == [2, 3, 5]

    def test_single_module(self):
        payload = build_exception_payload(self._row(MODULES="2"))
        assert payload["new_exception_data"]["MODULES"] == [2]

    def test_modules_strips_whitespace(self):
        payload = build_exception_payload(self._row(MODULES=" 2 , 3 "))
        assert payload["new_exception_data"]["MODULES"] == [2, 3]

    def test_profile_scope_includes_profile_ids(self):
        payload = build_exception_payload(self._row(SCOPE="PROFILE", PROFILE_IDS="48,99"))
        data = payload["new_exception_data"]
        assert data["SCOPE"] == "PROFILE"
        assert data["PROFILE_IDS"] == [48, 99]

    def test_tenant_scope_omits_profile_ids(self):
        payload = build_exception_payload(self._row(SCOPE="TENANT", PROFILE_IDS="48"))
        assert "PROFILE_IDS" not in payload["new_exception_data"]

    def test_profile_scope_without_profile_ids_omits_key(self):
        payload = build_exception_payload(self._row(SCOPE="PROFILE", PROFILE_IDS=""))
        assert "PROFILE_IDS" not in payload["new_exception_data"]

    def test_defaults_when_optional_fields_missing(self):
        row = {"NAME": "Minimal", "PATHS": "/a", "MODULES": "2"}
        payload = build_exception_payload(row)
        data = payload["new_exception_data"]
        assert data["DESCRIPTION"] == ""
        assert data["PLATFORM"] == "AGENT_OS_WINDOWS"
        assert data["SCOPE"] == "TENANT"
        assert data["STATUS"] == "ENABLED"

    def test_missing_name_raises(self):
        row = {"PATHS": "/a", "MODULES": "2"}
        with pytest.raises(KeyError):
            build_exception_payload(row)

    def test_missing_paths_raises(self):
        row = {"NAME": "No paths", "MODULES": "2"}
        with pytest.raises(KeyError):
            build_exception_payload(row)

    def test_missing_modules_raises(self):
        row = {"NAME": "No modules", "PATHS": "/a"}
        with pytest.raises(KeyError):
            build_exception_payload(row)

    def test_non_numeric_module_raises(self):
        with pytest.raises(ValueError):
            build_exception_payload(self._row(MODULES="abc"))

    def test_non_numeric_profile_id_raises(self):
        with pytest.raises(ValueError):
            build_exception_payload(self._row(SCOPE="PROFILE", PROFILE_IDS="abc"))

    def test_linux_platform(self):
        payload = build_exception_payload(self._row(PLATFORM="AGENT_OS_LINUX"))
        assert payload["new_exception_data"]["PLATFORM"] == "AGENT_OS_LINUX"

    def test_macos_platform(self):
        payload = build_exception_payload(self._row(PLATFORM="AGENT_OS_MACOS"))
        assert payload["new_exception_data"]["PLATFORM"] == "AGENT_OS_MACOS"

    def test_disabled_status(self):
        payload = build_exception_payload(self._row(STATUS="DISABLED"))
        assert payload["new_exception_data"]["STATUS"] == "DISABLED"


# --- build_headers ---


class TestBuildHeaders:
    def test_builds_correct_headers(self):
        config = {"api_key": "mykey", "api_key_id": 42}
        headers = build_headers(config)
        assert headers["Authorization"] == "mykey"
        assert headers["x-xdr-auth-id"] == "42"
        assert headers["Content-Type"] == "application/json"

    def test_coerces_key_id_to_string(self):
        headers = build_headers({"api_key": "k", "api_key_id": 7})
        assert isinstance(headers["x-xdr-auth-id"], str)


# --- load_config ---


class TestLoadConfig:
    def test_loads_valid_config(self):
        data = {"base_url": "https://api.example.com", "api_key": "k", "api_key_id": "1"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            result = load_config(f.name)
        assert result == data

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json{{{")
            f.flush()
            with pytest.raises(json.JSONDecodeError):
                load_config(f.name)


# --- upload_exception ---


class TestUploadException:
    def test_posts_to_correct_url(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": True}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            upload_exception("https://api.example.com", {"Authorization": "k"}, {"data": 1})
            mock_post.assert_called_once_with(
                "https://api.example.com/public_api/v1/legacy_exceptions/add",
                headers={"Authorization": "k"},
                json={"data": 1},
                timeout=30,
            )

    def test_returns_json_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"id": 42}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            result = upload_exception("https://api.example.com", {}, {})
        assert result == {"reply": {"id": 42}}

    def test_raises_on_http_error(self):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                upload_exception("https://api.example.com", {}, {})


# --- fetch_exceptions ---


class TestFetchExceptions:
    def test_posts_to_correct_url(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": [], "total_count": 0}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            fetch_exceptions("https://api.example.com", {"Authorization": "k"})
            mock_post.assert_called_once_with(
                "https://api.example.com/public_api/v1/legacy_exceptions/fetch",
                headers={"Authorization": "k"},
                json={"request_data": {"search_from": 0, "search_to": 100}},
                timeout=30,
            )

    def test_passes_pagination(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": []}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            fetch_exceptions("https://api.example.com", {}, search_from=10, search_to=20)
            body = mock_post.call_args[1]["json"]
            assert body["request_data"]["search_from"] == 10
            assert body["request_data"]["search_to"] == 20

    def test_passes_sort(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": []}}
        sort = {"field": "module", "keyword": "asc"}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            fetch_exceptions("https://api.example.com", {}, sort=sort)
            body = mock_post.call_args[1]["json"]
            assert body["request_data"]["sort"] == sort

    def test_passes_filters(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": []}}
        filters = [{"field": "NAME", "operator": "contains", "value": "test"}]
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            fetch_exceptions("https://api.example.com", {}, filters=filters)
            body = mock_post.call_args[1]["json"]
            assert body["request_data"]["filters"] == filters

    def test_omits_sort_and_filters_when_none(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": []}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            fetch_exceptions("https://api.example.com", {})
            body = mock_post.call_args[1]["json"]
            assert "sort" not in body["request_data"]
            assert "filters" not in body["request_data"]

    def test_returns_json_response(self):
        mock_resp = MagicMock()
        expected = {"reply": {"data": [{"NAME": "rule1"}], "total_count": 1, "filter_count": 1}}
        mock_resp.json.return_value = expected
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            result = fetch_exceptions("https://api.example.com", {})
        assert result == expected

    def test_raises_on_http_error(self):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                fetch_exceptions("https://api.example.com", {})


# --- delete_exceptions ---


class TestDeleteExceptions:
    def test_posts_to_correct_url_with_rule_ids(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": True}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            delete_exceptions("https://api.example.com", {"Authorization": "k"}, [1, 2, 3])
            mock_post.assert_called_once_with(
                "https://api.example.com/public_api/v1/legacy_exceptions/delete",
                headers={"Authorization": "k"},
                json={"request_data": {"rule_ids": [1, 2, 3]}},
                timeout=30,
            )

    def test_single_rule_id(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": True}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            delete_exceptions("https://api.example.com", {}, [42])
            body = mock_post.call_args[1]["json"]
            assert body["request_data"]["rule_ids"] == [42]

    def test_returns_json_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": True}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            result = delete_exceptions("https://api.example.com", {}, [1])
        assert result == {"reply": True}

    def test_raises_on_http_error(self):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                delete_exceptions("https://api.example.com", {}, [1])


# --- get_modules ---


class TestGetModules:
    def test_posts_to_correct_url_with_empty_body(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": []}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp) as mock_post:
            get_modules("https://api.example.com", {"Authorization": "k"})
            mock_post.assert_called_once_with(
                "https://api.example.com/public_api/v1/legacy_exceptions/get_modules",
                headers={"Authorization": "k"},
                json={},
                timeout=30,
            )

    def test_returns_module_list(self):
        mock_resp = MagicMock()
        modules = {"reply": [
            {"module_id": 1, "title": "Malware Protection", "platforms": ["windows", "linux"]},
            {"module_id": 2, "title": "Exploit Protection", "platforms": ["windows"]},
        ]}
        mock_resp.json.return_value = modules
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            result = get_modules("https://api.example.com", {})
        assert len(result["reply"]) == 2
        assert result["reply"][0]["module_id"] == 1

    def test_raises_on_http_error(self):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                get_modules("https://api.example.com", {})


# --- validate_uploaded_rules ---


class TestValidateUploadedRules:
    def test_all_found(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "reply": {"data": [{"NAME": "Rule A"}, {"NAME": "Rule B"}]}
        }
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            found, missing = validate_uploaded_rules(
                "https://api.example.com", {}, ["Rule A", "Rule B"])
        assert found == ["Rule A", "Rule B"]
        assert missing == []

    def test_some_missing(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "reply": {"data": [{"NAME": "Rule A"}]}
        }
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            found, missing = validate_uploaded_rules(
                "https://api.example.com", {}, ["Rule A", "Rule B"])
        assert found == ["Rule A"]
        assert missing == ["Rule B"]

    def test_none_found(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": []}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            found, missing = validate_uploaded_rules(
                "https://api.example.com", {}, ["Rule A"])
        assert found == []
        assert missing == ["Rule A"]

    def test_empty_expected_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {"data": [{"NAME": "Rule A"}]}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            found, missing = validate_uploaded_rules(
                "https://api.example.com", {}, [])
        assert found == []
        assert missing == []

    def test_handles_empty_reply(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"reply": {}}
        with patch("bulk_exceptions.requests.post", return_value=mock_resp):
            found, missing = validate_uploaded_rules(
                "https://api.example.com", {}, ["Rule A"])
        assert found == []
        assert missing == ["Rule A"]


# --- validate_modules ---


class TestValidateModules:
    def _mock_modules(self, modules):
        """Accept a list of ints (IDs only) or dicts (full module objects)."""
        mock_resp = MagicMock()
        reply = []
        for m in modules:
            if isinstance(m, int):
                reply.append({"module_id": m})
            else:
                reply.append(m)
        mock_resp.json.return_value = {"reply": reply}
        return mock_resp

    def test_all_modules_valid(self):
        rows = [{"MODULES": "2"}, {"MODULES": "4"}, {"MODULES": "5"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([1, 2, 3, 4, 5])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == {2, 4, 5}
        assert result["invalid_ids"] == set()
        assert result["affected_rows"] == {}

    def test_some_modules_invalid(self):
        rows = [{"MODULES": "2"}, {"MODULES": "99"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([1, 2, 3])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == {2}
        assert result["invalid_ids"] == {99}

    def test_all_modules_invalid(self):
        rows = [{"MODULES": "8"}, {"MODULES": "9"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([1, 2])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == set()
        assert result["invalid_ids"] == {8, 9}

    def test_multi_module_row(self):
        rows = [{"MODULES": "2,4"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([2, 4])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == {2, 4}
        assert result["invalid_ids"] == set()

    def test_deduplicates_across_rows(self):
        rows = [{"MODULES": "2"}, {"MODULES": "2"}, {"MODULES": "2"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([2])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == {2}
        assert result["invalid_ids"] == set()

    def test_empty_tenant_modules(self):
        rows = [{"MODULES": "2"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert result["valid_ids"] == set()
        assert result["invalid_ids"] == {2}

    def test_affected_rows_maps_invalid_to_rows(self):
        rows = [
            {"NAME": "Rule A", "MODULES": "2"},
            {"NAME": "Rule B", "MODULES": "99"},
            {"NAME": "Rule C", "MODULES": "99,2"},
        ]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules([1, 2, 3])):
            result = validate_modules("https://api.example.com", {}, rows)
        assert 99 in result["affected_rows"]
        affected = result["affected_rows"][99]
        assert len(affected) == 2
        assert affected[0] == {"row": 2, "name": "Rule B"}
        assert affected[1] == {"row": 3, "name": "Rule C"}

    def test_suggestions_returns_closest_modules(self):
        modules = [
            {"module_id": 1, "pretty_name": "Malware"},
            {"module_id": 2, "pretty_name": "Exploit"},
            {"module_id": 5, "pretty_name": "Restrictions"},
        ]
        rows = [{"NAME": "Rule A", "MODULES": "4"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules(modules)):
            result = validate_modules("https://api.example.com", {}, rows)
        assert 4 in result["suggestions"]
        suggested_ids = [s["module_id"] for s in result["suggestions"][4]]
        assert suggested_ids[0] == 5

    def test_available_modules_returned(self):
        modules = [
            {"module_id": 1, "pretty_name": "Malware"},
            {"module_id": 2, "pretty_name": "Exploit"},
        ]
        rows = [{"NAME": "Rule A", "MODULES": "99"}]
        with patch("bulk_exceptions.requests.post",
                   return_value=self._mock_modules(modules)):
            result = validate_modules("https://api.example.com", {}, rows)
        assert len(result["available_modules"]) == 2
        assert result["available_modules"][0]["module_id"] == 1


class TestSuggestModules:
    def test_returns_closest_by_id(self):
        modules = [
            {"module_id": 1}, {"module_id": 3}, {"module_id": 10},
        ]
        result = suggest_modules(4, modules, n=2)
        assert [m["module_id"] for m in result] == [3, 1]

    def test_returns_empty_for_no_modules(self):
        assert suggest_modules(5, []) == []

    def test_limits_to_n(self):
        modules = [{"module_id": i} for i in range(1, 20)]
        result = suggest_modules(10, modules, n=3)
        assert len(result) == 3

    def test_exact_match_comes_first(self):
        modules = [{"module_id": 1}, {"module_id": 5}, {"module_id": 10}]
        result = suggest_modules(5, modules)
        assert result[0]["module_id"] == 5


# --- suggested-exceptions.csv integration ---


class TestSuggestedExceptionsCSV:
    """Verify suggested-exceptions.csv parses into valid payloads."""

    @pytest.fixture(autouse=True)
    def load_rows(self):
        import csv
        from pathlib import Path

        csv_path = Path(__file__).parent / "suggested-exceptions.csv"
        with open(csv_path, newline="", encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))

    def test_csv_has_eight_rules(self):
        assert len(self.rows) == 8

    def test_all_rows_build_valid_payloads(self):
        for row in self.rows:
            payload = build_exception_payload(row)
            data = payload["new_exception_data"]
            assert data["TYPE"] == "LEGACY_EXCEPTIONS"
            assert data["NAME"]
            assert data["PLATFORM"] == "AGENT_OS_WINDOWS"
            assert data["SCOPE"] == "TENANT"
            assert data["STATUS"] == "ENABLED"
            assert len(data["CONDITIONS"]["whitelistFolders"]) > 0
            assert len(data["MODULES"]) > 0

    def test_btp_rules_use_module_4(self):
        btp_rows = [r for r in self.rows if r["NAME"].startswith("BTP")]
        assert len(btp_rows) == 4
        for row in btp_rows:
            payload = build_exception_payload(row)
            assert payload["new_exception_data"]["MODULES"] == [4]

    def test_operational_rules_use_module_5(self):
        op_rows = [r for r in self.rows if r["NAME"].startswith("Operational")]
        assert len(op_rows) == 3
        for row in op_rows:
            payload = build_exception_payload(row)
            assert payload["new_exception_data"]["MODULES"] == [5]

    def test_scanning_rule_uses_module_2(self):
        scan_rows = [r for r in self.rows if r["NAME"].startswith("Scanning")]
        assert len(scan_rows) == 1
        payload = build_exception_payload(scan_rows[0])
        assert payload["new_exception_data"]["MODULES"] == [2]

    def test_defender_av_has_eight_paths(self):
        row = next(r for r in self.rows if r["NAME"] == "BTP Defender AV")
        payload = build_exception_payload(row)
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert len(folders) == 8
        assert any("MsMpEng.exe" in p for p in folders)

    def test_rapid7_has_ten_paths(self):
        row = next(r for r in self.rows if r["NAME"] == "BTP Rapid7")
        payload = build_exception_payload(row)
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert len(folders) == 10
        assert any("velociraptor" in p for p in folders)

    def test_beyondtrust_btp_has_two_paths(self):
        row = next(r for r in self.rows if r["NAME"] == "BTP BeyondTrust")
        payload = build_exception_payload(row)
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert len(folders) == 2

    def test_management_agents_has_four_paths(self):
        row = next(r for r in self.rows if r["NAME"] == "BTP Management Agents")
        payload = build_exception_payload(row)
        folders = payload["new_exception_data"]["CONDITIONS"]["whitelistFolders"]
        assert len(folders) == 4
        assert any("ccmexec" in p for p in folders)
        assert any("IntuneWindowsAgent" in p for p in folders)

    def test_no_profile_ids_on_tenant_scope(self):
        for row in self.rows:
            payload = build_exception_payload(row)
            assert "PROFILE_IDS" not in payload["new_exception_data"]

    def test_rule_names_are_unique(self):
        names = [r["NAME"] for r in self.rows]
        assert len(names) == len(set(names))
