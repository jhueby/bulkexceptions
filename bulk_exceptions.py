#!/usr/bin/env python3
"""Bulk upload legacy exception rules to Cortex XDR/XSIAM."""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import requests


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return json.load(f)


def build_headers(config: dict) -> dict:
    return {
        "Authorization": config["api_key"],
        "x-xdr-auth-id": str(config["api_key_id"]),
        "Content-Type": "application/json",
    }


def build_exception_payload(row: dict) -> dict:
    """Build an API payload from a CSV row.

    Expected CSV columns:
      NAME          - Exception rule name (required)
      DESCRIPTION   - Free-text description
      PLATFORM      - e.g. AGENT_OS_WINDOWS, AGENT_OS_LINUX, AGENT_OS_MACOS
      PATHS         - Semicolon-separated list of paths for whitelistFolders
      MODULES       - Comma-separated module IDs (e.g. "2" or "2,3")
      SCOPE         - PROFILE or TENANT
      PROFILE_IDS   - Comma-separated profile IDs (required when SCOPE=PROFILE)
      STATUS        - ENABLED or DISABLED
    """
    paths = [p.strip() for p in row["PATHS"].split(";") if p.strip()]
    modules = [int(m.strip()) for m in row["MODULES"].split(",") if m.strip()]

    payload = {
        "new_exception_data": {
            "TYPE": "LEGACY_EXCEPTIONS",
            "NAME": row["NAME"],
            "DESCRIPTION": row.get("DESCRIPTION", ""),
            "PLATFORM": row.get("PLATFORM", "AGENT_OS_WINDOWS"),
            "CONDITIONS": {
                "whitelistFolders": paths,
            },
            "MODULES": modules,
            "SCOPE": row.get("SCOPE", "TENANT"),
            "STATUS": row.get("STATUS", "ENABLED"),
        }
    }

    if row.get("SCOPE", "TENANT") == "PROFILE" and row.get("PROFILE_IDS"):
        profile_ids = [int(p.strip()) for p in row["PROFILE_IDS"].split(",") if p.strip()]
        payload["new_exception_data"]["PROFILE_IDS"] = profile_ids

    return payload


def upload_exception(base_url: str, headers: dict, payload: dict) -> dict:
    url = f"{base_url}/public_api/v1/legacy_exceptions/add"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_exceptions(base_url: str, headers: dict, search_from: int = 0,
                     search_to: int = 100, sort: dict = None,
                     filters: list = None) -> dict:
    url = f"{base_url}/public_api/v1/legacy_exceptions/fetch"
    request_data = {
        "search_from": search_from,
        "search_to": search_to,
    }
    if sort:
        request_data["sort"] = sort
    if filters:
        request_data["filters"] = filters
    resp = requests.post(url, headers=headers,
                         json={"request_data": request_data}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def delete_exceptions(base_url: str, headers: dict, rule_ids: list) -> dict:
    url = f"{base_url}/public_api/v1/legacy_exceptions/delete"
    resp = requests.post(url, headers=headers,
                         json={"request_data": {"rule_ids": rule_ids}},
                         timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_modules(base_url: str, headers: dict) -> dict:
    url = f"{base_url}/public_api/v1/legacy_exceptions/get_modules"
    resp = requests.post(url, headers=headers, json={}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def validate_uploaded_rules(base_url: str, headers: dict,
                            expected_names: list) -> list:
    """Fetch all rules and return which expected names are present."""
    result = fetch_exceptions(base_url, headers, search_from=0,
                              search_to=500)
    remote_names = {r.get("NAME") for r in result.get("reply", {}).get("data", [])}
    found = []
    missing = []
    for name in expected_names:
        if name in remote_names:
            found.append(name)
        else:
            missing.append(name)
    return found, missing


def cmd_upload(args):
    config = load_config(args.config)
    base_url = config["base_url"].rstrip("/")
    headers = build_headers(config)

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} exception(s) from {csv_path}")

    success = 0
    failed = 0
    uploaded_names = []

    for i, row in enumerate(rows, 1):
        name = row.get("NAME", f"row {i}")
        try:
            payload = build_exception_payload(row)
        except (KeyError, ValueError) as e:
            print(f"[{i}/{len(rows)}] SKIP  {name} — bad row data: {e}")
            failed += 1
            continue

        if args.dry_run:
            print(f"[{i}/{len(rows)}] DRY   {name}")
            print(json.dumps(payload, indent=2))
            continue

        try:
            upload_exception(base_url, headers, payload)
            print(f"[{i}/{len(rows)}] OK    {name}")
        except requests.HTTPError as e:
            print(f"[{i}/{len(rows)}] FAIL  {name} — {e.response.status_code}: {e.response.text}")
            failed += 1
            continue
        except requests.RequestException as e:
            print(f"[{i}/{len(rows)}] FAIL  {name} — {e}")
            failed += 1
            continue

        success += 1
        uploaded_names.append(name)
        if i < len(rows):
            time.sleep(args.delay)

    print(f"\nDone. {success} succeeded, {failed} failed out of {len(rows)} total.")

    if args.validate and uploaded_names and not args.dry_run:
        print("\nValidating uploaded rules...")
        time.sleep(2)
        try:
            found, missing = validate_uploaded_rules(base_url, headers, uploaded_names)
            for n in found:
                print(f"  VERIFIED  {n}")
            for n in missing:
                print(f"  MISSING   {n}")
            print(f"\nValidation: {len(found)}/{len(uploaded_names)} confirmed on tenant.")
        except requests.RequestException as e:
            print(f"  Validation failed: {e}", file=sys.stderr)


def cmd_fetch(args):
    config = load_config(args.config)
    base_url = config["base_url"].rstrip("/")
    headers = build_headers(config)

    filters = None
    if args.name:
        filters = [{"field": "NAME", "operator": "contains", "value": args.name}]

    result = fetch_exceptions(base_url, headers,
                              search_from=args.offset,
                              search_to=args.offset + args.limit,
                              filters=filters)

    reply = result.get("reply", {})
    rules = reply.get("data", [])
    print(f"Showing {len(rules)} of {reply.get('total_count', '?')} total rules "
          f"(filtered: {reply.get('filter_count', '?')})\n")
    print(json.dumps(rules, indent=2))


def cmd_delete(args):
    config = load_config(args.config)
    base_url = config["base_url"].rstrip("/")
    headers = build_headers(config)

    rule_ids = [int(r.strip()) for r in args.rule_ids.split(",")]
    print(f"Deleting {len(rule_ids)} rule(s): {rule_ids}")
    result = delete_exceptions(base_url, headers, rule_ids)
    print(json.dumps(result, indent=2))


def cmd_get_modules(args):
    config = load_config(args.config)
    base_url = config["base_url"].rstrip("/")
    headers = build_headers(config)

    result = get_modules(base_url, headers)
    modules = result.get("reply", [])
    if args.json:
        print(json.dumps(modules, indent=2))
    else:
        for m in modules:
            platforms = ", ".join(m.get("platforms", []))
            print(f"  [{m.get('module_id')}] {m.get('pretty_name', m.get('title', 'Unknown'))}")
            print(f"       Platforms: {platforms}")
            conditions = list(m.get("conditions_definition", {}).keys())
            if conditions:
                print(f"       Conditions: {', '.join(conditions)}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Manage legacy exception rules in Cortex XDR/XSIAM")
    parser.add_argument("--config", default="config.json",
                        help="Path to config JSON (default: config.json)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # upload
    p_upload = subparsers.add_parser("upload", help="Bulk upload exceptions from CSV")
    p_upload.add_argument("csv_file", help="Path to CSV file containing exception rules")
    p_upload.add_argument("--dry-run", action="store_true",
                          help="Print payloads without uploading")
    p_upload.add_argument("--validate", action="store_true",
                          help="Fetch rules after upload to verify they exist on the tenant")
    p_upload.add_argument("--delay", type=float, default=0.5,
                          help="Seconds between API calls (default: 0.5)")
    p_upload.set_defaults(func=cmd_upload)

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch exception rules from tenant")
    p_fetch.add_argument("--name", help="Filter rules by name (contains match)")
    p_fetch.add_argument("--offset", type=int, default=0,
                         help="Pagination start index (default: 0)")
    p_fetch.add_argument("--limit", type=int, default=100,
                         help="Max rules to return (default: 100)")
    p_fetch.set_defaults(func=cmd_fetch)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete exception rules by ID")
    p_delete.add_argument("rule_ids",
                          help="Comma-separated rule IDs to delete")
    p_delete.set_defaults(func=cmd_delete)

    # get-modules
    p_modules = subparsers.add_parser("get-modules",
                                      help="List available exception modules and their schemas")
    p_modules.add_argument("--json", action="store_true",
                           help="Output raw JSON instead of formatted table")
    p_modules.set_defaults(func=cmd_get_modules)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
