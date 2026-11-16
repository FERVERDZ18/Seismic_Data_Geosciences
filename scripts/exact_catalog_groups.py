"""Prove exact source-record copies offline; never infer physical-event identity.

Original CSV cells (including precision and empty strings) define equality. The
browser packages omit source columns, so their normalized values alone cannot
establish equality. This deterministic sidecar binds the full-cell proof to the
original files and all packaged input bytes. No network or source writes occur.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "system/dist"
TARGET = DIST / "data/exact-record-groups.json"
SCHEMA = "seismic-exact-source-evidence/1"
USGS_FIELDS = ["time", "latitude", "longitude", "depth", "mag", "magType", "nst", "gap",
               "dmin", "rms", "net", "id", "updated", "place", "type", "horizontalError",
               "depthError", "magError", "magNst", "status", "locationSource", "magSource"]
NRCAN_FIELDS = ["date", "latitude", "longitude", "depth", "magnitude", "magnitude type", "place", "", ""]
NUMERIC = {"latitude", "longitude", "depth", "mag", "horizontalError", "depthError", "magError"}
RULES = {
    "usgs-comcat": {"provider": "usgs", "rule": "same_provider_id_and_all_22_original_cells", "fields": USGS_FIELDS},
    "nrcan-earthquakes-canada": {"provider": "nrcan", "rule": "all_9_original_cells_no_source_event_id", "fields": NRCAN_FIELDS},
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def signature(namespace, fields, cells):
    if namespace not in RULES or fields != RULES[namespace]["fields"]:
        raise ValueError("Unsupported source schema/namespace")
    if len(cells) != len(fields) or any(not isinstance(cell, str) for cell in cells):
        raise ValueError("Every original cell must be a string, including missing cells")
    if namespace == "usgs-comcat" and not cells[USGS_FIELDS.index("id")]:
        raise ValueError("USGS source event ID is required")
    return sha(compact([namespace, fields, cells]))


def number(cell):
    if cell == "":
        return None
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", cell.strip(), flags=re.ASCII):
        raise ValueError("Non-numeric source measurement")
    result = float(cell)
    if not math.isfinite(result):
        raise ValueError("Non-finite source measurement")
    return result


def group_members(records):
    """Pure exact grouping oracle; input records include complete original cells."""
    buckets = {}
    seen = set()
    for record in records:
        namespace, cells = record["provider_namespace"], record["source_cells"]
        if namespace not in RULES:
            raise ValueError("Unsupported provider namespace")
        fields = RULES[namespace]["fields"]
        digest = signature(namespace, fields, cells)
        member = record["member"]
        if member["record_key"] in seen:
            raise ValueError("Repeated qualified source record")
        seen.add(member["record_key"])
        key = "exact:" + namespace + ":" + digest
        group = buckets.setdefault(key, {"group_key": key, "rule": RULES[namespace]["rule"],
            "provider_namespace": namespace, "signature": digest, "source_fields": fields[:],
            "source_cells": cells[:], "members": []})
        if group["source_cells"] != cells:
            raise ValueError("SHA-256 collision")
        group["members"].append({**member, "signature": digest})
    return [{**group, "members": sorted(group["members"], key=lambda item: item["record_key"])}
            for _, group in sorted(buckets.items()) if len(group["members"]) > 1]


def checked_file(path, spec):
    raw = path.read_bytes()
    if len(raw) != spec["bytes"] or sha(raw) != spec["sha256"]:
        raise ValueError(f"Original source checksum mismatch: {path}")
    return raw


def check_package_record(row, source, fields, source_file, provider):
    """Reproduce every retained raw-dependent field, never compare rounded floats."""
    expected = {}
    if provider == "usgs":
        original = dict(zip(USGS_FIELDS, source, strict=True))
        for field in fields:
            if field == "file":
                expected[field] = source_file
            elif field == "event_type":
                expected[field] = original["type"]
            elif field == "event_url":
                expected[field] = ""
            elif field in original:
                expected[field] = number(original[field]) if field in NUMERIC else original[field]
            else:
                raise ValueError(f"Unrecognized packaged source column: {field}")
    else:
        instant = datetime.strptime(source[0], "%Y-%m-%dT%H:%M:%S%z")
        if instant.utcoffset().total_seconds() != 0:
            raise ValueError("NRCan source date must be explicitly UTC")
        expected = dict(time=instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            latitude=number(source[1]), longitude=number(source[2]), depth=None, mag=number(source[4]),
            magType=source[5], raw_depth=source[3], place=", ".join(cell for cell in source[6:] if cell),
            file=source_file, net="", locationSource="", magSource="", horizontalError=None,
            depthError=None, magError=None, updated="", status="", event_type="")
    for field, value in expected.items():
        if row.get(field) != value:
            raise ValueError(f"Raw/package disagreement: {row['id']} {field}")


def build_evidence(root=ROOT):
    dist = root / "system/dist"
    registry = json.loads((dist / "data/catalogs.json").read_text(encoding="utf-8"))
    inputs, source_files, records = {}, [], []
    total = 0
    for catalog in sorted(registry["catalogs"], key=lambda item: item["id"]):
        cid, provider = catalog["id"], catalog["provider"]
        event_bytes = (dist / catalog["events_url"]).read_bytes()
        manifest_bytes = (dist / catalog["manifest_url"]).read_bytes()
        event_hash, manifest_hash = sha(event_bytes), sha(manifest_bytes)
        package, manifest = json.loads(event_bytes), json.loads(manifest_bytes)
        if (event_hash != catalog["sha256"] or manifest_hash != catalog["manifest_sha256"]
                or manifest["derived_asset_sha256"] != event_hash):
            raise ValueError(f"Packaged input checksum mismatch: {cid}")
        rows = {row[0]: dict(zip(package["fields"], row, strict=True)) for row in package["rows"]}
        if len(rows) != len(package["rows"]) or len(rows) != catalog["event_count"]:
            raise ValueError(f"Repeated or missing packaged records: {cid}")
        inputs[cid] = {"provider": provider, "events_sha256": event_hash,
                       "manifest_sha256": manifest_hash, "record_count": len(rows)}
        total += len(rows)
        covered, occurrences = set(), Counter()
        for spec in manifest["files"]:
            if cid == "usgs-mx-historical":
                path = root / "data/raw/usgs" / spec["path"]
            elif cid == "usgs-na-2020-2025":
                path = root / "data/raw/catalogs/usgs-na" / spec["path"]
            elif provider in {"nrcan", "ssn"}:
                path = root / "research-data/catalogs" / ("nrcan-ca" if provider == "nrcan" else "ssn-mx") / spec["path"]
            else:
                raise ValueError(f"No exact-copy source adapter: {cid}")
            raw = checked_file(path, spec)
            source_files.append({"catalog_id": cid, "path": spec["path"], "sha256": spec["sha256"], "bytes": len(raw)})
            if provider == "ssn":
                continue  # SSN stays ungrouped; no cross-provider identity is inferred.
            reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            fields = next(reader)
            expected_fields = USGS_FIELDS if provider == "usgs" else NRCAN_FIELDS
            if fields != expected_fields:
                raise ValueError(f"Original CSV schema mismatch: {cid} {spec['path']}")
            for source_row, cells in enumerate(reader, start=2):
                if len(cells) != len(fields):
                    raise ValueError("Unexpected original CSV width")
                if provider == "usgs":
                    identifier = cells[USGS_FIELDS.index("id")]
                    namespace = "usgs-comcat"
                else:
                    raw_digest = sha(compact(cells))
                    occurrences[raw_digest] += 1
                    identifier = f"nrcan-local-{raw_digest[:24]}-{occurrences[raw_digest]}"
                    namespace = "nrcan-earthquakes-canada"
                if identifier not in rows:
                    continue
                if identifier in covered:
                    raise ValueError("Repeated source ID cannot establish one packaged record")
                row = rows[identifier]
                check_package_record(row, cells, package["fields"], spec["path"], provider)
                covered.add(identifier)
                records.append({"provider_namespace": namespace, "source_cells": cells,
                    "member": {"catalog_id": cid, "source_event_id": identifier,
                        "record_key": cid + "~" + identifier, "source_file": spec["path"],
                        "source_file_sha256": spec["sha256"], "source_row": source_row}})
        if provider != "ssn" and len(covered) != len(rows):
            raise ValueError(f"Missing original-cell proof for packaged records: {cid}")
    groups = group_members(records)
    collapsed = sum(len(group["members"]) - 1 for group in groups)
    by_namespace = Counter()
    for group in groups:
        by_namespace[group["provider_namespace"]] += len(group["members"]) - 1
    return {"schema": SCHEMA, "signature_encoding": "sha256(UTF-8 JSON([provider_namespace,source_fields,source_cells])); compact separators; preserve every string cell",
        "count_unit": "exact_source_record_groups", "inputs": inputs,
        "source_files": sorted(source_files, key=lambda item: (item["catalog_id"], item["path"])),
        "rules": RULES, "groups": groups,
        "stats": {"input_records": total, "group_count": total - collapsed,
                  "collapsed_records": collapsed, "multi_member_groups": len(groups),
                  "multi_member_records": sum(len(group["members"]) for group in groups),
                  "collapsed_by_namespace": dict(sorted(by_namespace.items()))},
        "limits": ["These are exact source-record groups, not unique physical earthquakes.",
                   "No cross-provider event matching, revision merging, magnitude conversion or missing-value imputation.",
                   "Different original string precision, missing cells or any changed original field remain distinct.",
                   "NRCan has no original event ID; equality covers all nine original cells, not agency identity."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Recompute and compare; never write")
    args = parser.parse_args()
    evidence = build_evidence()
    raw = compact(evidence)
    if args.verify_only:
        if TARGET.read_bytes() != raw:
            raise ValueError("Exact-record sidecar differs from recomputed source evidence")
    else:
        TARGET.write_bytes(raw)
    print(json.dumps({**evidence["stats"], "source_files": len(evidence["source_files"]),
                      "sidecar_sha256": sha(raw), "verified_only": args.verify_only}))


if __name__ == "__main__":
    main()
