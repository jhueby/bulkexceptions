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


def main():
    parser = argparse.ArgumentParser(description="Bulk upload legacy exceptions to Cortex XDR/XSIAM")
    parser.add_argument("csv_file", help="Path to CSV file containing exception rules")
    parser.add_argument("--config", default="config.json", help="Path to config JSON (default: config.json)")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without uploading")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls (default: 0.5)")
    args = parser.parse_args()

    config = load_config(args.config)
    base_url = config["base_url"].rstrip("/")
    headers = {
        "Authorization": config["api_key"],
        "x-xdr-auth-id": str(config["api_key_id"]),
        "Content-Type": "application/json",
    }

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
            result = upload_exception(base_url, headers, payload)
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
        if i < len(rows):
            time.sleep(args.delay)

    print(f"\nDone. {success} succeeded, {failed} failed out of {len(rows)} total.")


if __name__ == "__main__":
    main()
