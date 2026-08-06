# Bulk Exceptions for Cortex XDR/XSIAM

CLI tool for managing legacy exception rules in Cortex XDR/XSIAM via the public API.

## Features

- **Upload** exception rules in bulk from a CSV file
- **Module validation** — automatically verifies CSV module IDs exist on the tenant before uploading
- **Post-upload validation** — fetches rules after upload to confirm they were created
- **Fetch** existing exception rules with filtering and pagination
- **Delete** exception rules by ID
- **Get Modules** to list available exception modules and their schemas

## Setup

```bash
pip install requests
```

Copy `config.json.example` to `config.json` and fill in your credentials:

```json
{
    "base_url": "https://api-yourfqdn",
    "api_key": "YOUR_API_KEY",
    "api_key_id": "YOUR_API_KEY_ID"
}
```

## Usage

### Upload exceptions from CSV

```bash
python3 bulk_exceptions.py upload exceptions.csv
python3 bulk_exceptions.py upload exceptions.csv --dry-run
python3 bulk_exceptions.py upload exceptions.csv --validate
python3 bulk_exceptions.py upload exceptions.csv --delay 1.0
```

Before uploading, the tool calls `get-modules` to verify that all module IDs in the CSV exist on the tenant. If any module ID is invalid, the upload is aborted with an error. The `--validate` flag additionally fetches rules after upload to confirm they were created.

### Fetch exception rules

```bash
python3 bulk_exceptions.py fetch
python3 bulk_exceptions.py fetch --name "Windows Defender"
python3 bulk_exceptions.py fetch --offset 0 --limit 50
```

### Delete exception rules

```bash
python3 bulk_exceptions.py delete 101,102,103
```

### List available modules

```bash
python3 bulk_exceptions.py get-modules
python3 bulk_exceptions.py get-modules --json
```

## Included Exception Sets

- **`exceptions.csv.example`** — Template with sample rules
- **`suggested-exceptions.csv`** — 8 rules for endpoint NICE-5CG40406JD to resolve cross-scanning loop between Cortex XDR, Defender AV, Rapid7, BeyondTrust, and Sysmon (sourced from `suggested-exceptions.md`)

## CSV Format

See `exceptions.csv.example` for a template. Required columns:

| Column | Required | Description |
|---|---|---|
| NAME | Yes | Exception rule name |
| PATHS | Yes | Semicolon-separated paths for whitelistFolders |
| MODULES | Yes | Comma-separated module IDs |
| DESCRIPTION | No | Free-text description |
| PLATFORM | No | `AGENT_OS_WINDOWS` (default), `AGENT_OS_LINUX`, `AGENT_OS_MACOS` |
| SCOPE | No | `TENANT` (default) or `PROFILE` |
| PROFILE_IDS | No | Comma-separated profile IDs (required when SCOPE=PROFILE) |
| STATUS | No | `ENABLED` (default) or `DISABLED` |

## Tests

```bash
python3 -m pytest test_bulk_exceptions.py -v
```
