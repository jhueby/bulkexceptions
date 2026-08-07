"""Flask web GUI for managing Cortex XDR/XSIAM legacy exceptions."""

import csv
import io
import json
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from bulk_exceptions import (
    build_exception_payload,
    build_headers,
    delete_exceptions,
    fetch_exceptions,
    get_modules,
    upload_exception,
    validate_modules,
    validate_uploaded_rules,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))


def get_config():
    base_url = session.get("base_url", "")
    api_key = session.get("api_key", "")
    api_key_id = session.get("api_key_id", "")
    if not all([base_url, api_key, api_key_id]):
        return None
    return {
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
        "api_key_id": api_key_id,
    }


@app.route("/")
def index():
    config = get_config()
    connected = config is not None
    return render_template("index.html", connected=connected, config=config or {})


@app.route("/connect", methods=["POST"])
def connect():
    session["base_url"] = request.form.get("base_url", "").strip()
    session["api_key"] = request.form.get("api_key", "").strip()
    session["api_key_id"] = request.form.get("api_key_id", "").strip()
    flash("Connected to tenant.", "success")
    return redirect(url_for("index"))


@app.route("/disconnect", methods=["POST"])
def disconnect():
    session.clear()
    flash("Disconnected.", "info")
    return redirect(url_for("index"))


@app.route("/api/modules", methods=["GET"])
def api_modules():
    config = get_config()
    if not config:
        return jsonify({"error": "Not connected"}), 400
    try:
        headers = build_headers(config)
        result = get_modules(config["base_url"], headers)
        return jsonify(result.get("reply", []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fetch", methods=["GET"])
def api_fetch():
    config = get_config()
    if not config:
        return jsonify({"error": "Not connected"}), 400
    try:
        headers = build_headers(config)
        name_filter = request.args.get("name", "").strip()
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 100))
        filters = None
        if name_filter:
            filters = [{"field": "NAME", "operator": "contains", "value": name_filter}]
        result = fetch_exceptions(config["base_url"], headers,
                                  search_from=offset,
                                  search_to=offset + limit,
                                  filters=filters)
        return jsonify(result.get("reply", {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    config = get_config()
    if not config:
        return jsonify({"error": "Not connected"}), 400

    file = request.files.get("csv_file")
    if not file or not file.filename:
        return jsonify({"error": "No CSV file provided"}), 400

    dry_run = request.form.get("dry_run") == "true"
    validate = request.form.get("validate") == "true"

    try:
        content = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV: {e}"}), 400

    if not rows:
        return jsonify({"error": "CSV file is empty"}), 400

    headers = build_headers(config)
    results = []

    if not dry_run:
        try:
            mod_result = validate_modules(config["base_url"], headers, rows)
            if mod_result["invalid_ids"]:
                available_summary = [
                    {"module_id": m.get("module_id"),
                     "name": m.get("pretty_name", m.get("title", "Unknown")),
                     "platforms": m.get("platforms", [])}
                    for m in mod_result["available_modules"]
                ]
                suggestions = {
                    str(mid): [
                        {"module_id": s.get("module_id"),
                         "name": s.get("pretty_name", s.get("title", "Unknown"))}
                        for s in slist
                    ]
                    for mid, slist in mod_result["suggestions"].items()
                }
                affected = {
                    str(mid): rows_list
                    for mid, rows_list in mod_result["affected_rows"].items()
                }
                return jsonify({
                    "error": f"{len(mod_result['invalid_ids'])} module(s) not available on this tenant.",
                    "valid_modules": sorted(mod_result["valid_ids"]),
                    "invalid_modules": sorted(mod_result["invalid_ids"]),
                    "available_modules": available_summary,
                    "affected_rows": affected,
                    "suggestions": suggestions,
                }), 400
        except Exception as e:
            return jsonify({"error": f"Module validation failed: {e}"}), 500

    for i, row in enumerate(rows, 1):
        name = row.get("NAME", f"row {i}")
        entry = {"row": i, "name": name}
        try:
            payload = build_exception_payload(row)
        except (KeyError, ValueError) as e:
            entry["status"] = "SKIP"
            entry["detail"] = f"Bad row data: {e}"
            results.append(entry)
            continue

        if dry_run:
            entry["status"] = "DRY"
            entry["payload"] = payload
            results.append(entry)
            continue

        try:
            resp = upload_exception(config["base_url"], headers, payload)
            entry["status"] = "OK"
            entry["detail"] = resp
        except Exception as e:
            entry["status"] = "FAIL"
            entry["detail"] = str(e)
        results.append(entry)

    response = {
        "total": len(rows),
        "results": results,
        "dry_run": dry_run,
    }

    if validate and not dry_run:
        uploaded_names = [r["name"] for r in results if r["status"] == "OK"]
        if uploaded_names:
            try:
                found, missing = validate_uploaded_rules(
                    config["base_url"], headers, uploaded_names)
                response["validation"] = {"found": found, "missing": missing}
            except Exception as e:
                response["validation"] = {"error": str(e)}

    return jsonify(response)


@app.route("/api/delete", methods=["POST"])
def api_delete():
    config = get_config()
    if not config:
        return jsonify({"error": "Not connected"}), 400
    try:
        data = request.get_json()
        rule_ids = data.get("rule_ids", [])
        if not rule_ids:
            return jsonify({"error": "No rule IDs provided"}), 400
        rule_ids = [int(r) for r in rule_ids]
        headers = build_headers(config)
        result = delete_exceptions(config["base_url"], headers, rule_ids)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
