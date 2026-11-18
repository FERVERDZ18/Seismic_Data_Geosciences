"""Compare selected scientific contents, excluding only declared runtime fields."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

# These key names are recorded in EXPECTED_COMPARISON_CONTRACT.json. Scientific
# lag_seconds, time windows, denominators, source hashes and fitted values stay.
VOLATILE = {
    "started_utc", "completed_utc", "created_utc", "elapsed_seconds", "pid",
    "preparation_seconds", "tree_seconds", "kernel_seconds", "postprocess_seconds",
    "total_seconds", "process_wall_seconds", "warmup_seconds", "input_load_seconds",
    "outer_measurement_seconds", "process_cpu_seconds", "serialization_seconds_excluded",
    "arrays_sha256", "output_sha256", "receipt_sha256", "python_executable", "argv",
}


def normalize(value, hash_aliases=None):
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if k in VOLATILE:
                continue
            if k.endswith("sha256") and isinstance(v, str) and v in (hash_aliases or {}):
                v = hash_aliases[v]
            result[k] = normalize(v, hash_aliases)
        return result
    if isinstance(value, list):
        return [normalize(x, hash_aliases) for x in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite__": "nan" if math.isnan(value) else "inf" if value > 0 else "-inf"}
    return value


def compare(expected: Path, actual: Path, *, hash_aliases=None) -> dict:
    if not expected.is_file() or not actual.is_file():
        raise FileNotFoundError(f"Missing scientific comparison member: {expected.name}")
    suffix = expected.suffix.lower()
    if suffix == ".npz":
        # Imported only during an explicitly requested scientific comparison.
        import numpy as np
        fields = []
        with np.load(expected, allow_pickle=False) as first, np.load(actual, allow_pickle=False) as second:
            if set(first.files) != set(second.files):
                raise AssertionError(f"Array field set differs: {expected.name}")
            for name in sorted(first.files):
                a, b = first[name], second[name]
                if a.dtype != b.dtype or a.shape != b.shape:
                    raise AssertionError(f"Scientific array dtype/shape differs: {expected.name}:{name}")
                same_values = np.array_equal(a, b, equal_nan=True) if a.dtype.kind in "fc" else np.array_equal(a, b)
                if not same_values:
                    raise AssertionError(f"Scientific array differs: {expected.name}:{name}")
                fields.append(dict(name=name, dtype=str(a.dtype), shape=list(a.shape)))
        return dict(kind="decoded_npz", equal=True, fields=fields)
    if suffix == ".json":
        a = normalize(json.loads(expected.read_text(encoding="utf-8-sig")), hash_aliases)
        b = normalize(json.loads(actual.read_text(encoding="utf-8-sig")), hash_aliases)
        if a != b:
            raise AssertionError(f"Normalized scientific JSON differs: {expected.name}")
        return dict(kind="normalized_json", equal=True)
    if suffix == ".csv":
        with expected.open(encoding="utf-8-sig", newline="") as f:
            a = list(csv.reader(f))
        with actual.open(encoding="utf-8-sig", newline="") as f:
            b = list(csv.reader(f))
        if a != b:
            raise AssertionError(f"Scientific CSV cells differ: {expected.name}")
        return dict(kind="csv_cells", equal=True, rows=len(a))
    if expected.read_bytes() != actual.read_bytes():
        raise AssertionError(f"Scientific bytes differ: {expected.name}")
    return dict(kind="bytes", equal=True)


def validated_manifest_alias(expected: Path, actual: Path, *, hash_aliases=None):
    """Alias a runtime-created manifest ONLY after every listed output matches.

    Each manifest first validates its own path/size/byte-hash inventory. Then
    every paired data file is compared scientifically with the same strict
    rules as the main replay. Transport sizes/hashes are replaced by those
    successful comparisons solely for comparing the manifest's other fields.
    A changed array, fitted value, CSV cell, path set or source contract fails.
    """
    from package_io import inside, sha_file
    first = json.loads(expected.read_text(encoding="utf-8"))
    second = json.loads(actual.read_text(encoding="utf-8"))
    a = {x["path"]: x for x in first["output_files"]}
    b = {x["path"]: x for x in second["output_files"]}
    if len(a) != len(first["output_files"]) or len(b) != len(second["output_files"]) or set(a) != set(b):
        raise AssertionError("Scientific output manifest path set differs")
    checks = []
    for name in sorted(a):
        p, q = inside(expected.parent, name), inside(actual.parent, name)
        for path, record in [(p, a[name]), (q, b[name])]:
            if path.stat().st_size != record["bytes"] or sha_file(path) != record["sha256"]:
                raise AssertionError("Output manifest does not authenticate its own listed file")
        checks.append(dict(path=name, **compare(p, q, hash_aliases=hash_aliases)))
    first = dict(first); second = dict(second)
    common = [{"path": x["path"], "scientific_comparison": "EXACT_NORMALIZED"} for x in checks]
    first["output_files"] = common; second["output_files"] = common
    if normalize(first, hash_aliases) != normalize(second, hash_aliases):
        raise AssertionError("Non-runtime scientific manifest fields differ")
    return dict(schema="validated-scientific-output-manifest-alias/1", status="ALL_LISTED_SCIENTIFIC_OUTPUTS_EQUAL",
                expected_manifest_sha256=sha_file(expected), actual_manifest_sha256=sha_file(actual),
                listed_outputs=len(checks), checks=checks,
                normalized_other_manifest_fields_equal=True,
                not_a_global_volatile_hash_exclusion=True)
