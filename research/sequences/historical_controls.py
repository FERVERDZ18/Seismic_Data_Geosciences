"""Recheck retained GEM evidence and rerun the fixed ten-shift null control.

The GEM engine is NOT executed. Its original memberships/decisions and source
pin/license are supplied separately as identified historical evidence.
"""
from __future__ import annotations

import csv
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main(project):
    project = Path(project).resolve()
    matcher = load_module(project / "scripts/pilot_catalog_reconciliation.py", "retained_scientific_matcher")
    gem = project / "outputs/ssn_usgs_pilot_2026-11-15/gem_results/30s_50km"
    # The unmodified historical verifier reads only relative frozen input paths
    # in the explicitly projected public run receipt, then checks all memberships.
    original = load_module(gem / "verify_gem_result.py", "retained_gem_evidence_verifier")
    original.main()
    first = json.loads((gem / "pairs.json").read_text(encoding="utf-8"))
    second = json.loads((project / "outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json").read_text(encoding="utf-8"))
    pairset = lambda data: {(x["ssn_record_id"], x["usgs_record_id"]) for x in data}
    a, b = pairset(first), pairset(second)
    counts = dict(gem_assignments=len(a), graph_assignments=len(b), intersection=len(a & b),
                  gem_only=len(a - b), graph_only=len(b - a), symmetric_difference=len(a ^ b),
                  engine_rerun=False, original_engine_commit="d13e63bebedcc6788e0ec88e8632957b749d3b60")
    pilot = project / "outputs/sequence_pilot_2026-11-15"
    def records(source):
        return [matcher.Record(r["record_id"], source, r.get("event_id") or None, r["time_utc"],
                    matcher.utc_nanoseconds(r["time_utc"]), float(r["latitude"]), float(r["longitude"]),
                    float(r["depth_km"]) if r["depth_km"] else None, float(r["magnitude"]),
                    r.get("magnitude_type") or None) for r in rows(pilot / "inputs" / f"{source}.csv")]
    ssn, usgs = records("ssn"), records("usgs")
    start, stop = matcher.utc_nanoseconds("2016-01-01T00:00:00Z"), matcher.utc_nanoseconds("2026-01-01T00:00:00Z")
    shifts = []
    for days in [0, -90, -60, -30, -14, -7, 7, 14, 30, 60, 90]:
        changed = [replace(r, time_ns=start + (r.time_ns-start+days*86400*10**9) % (stop-start)) for r in usgs]
        edges = matcher.candidate_edges(ssn, changed, 30, 50)
        assigned = matcher.optimal_assignment(edges, 30, 50)
        if days == 0 and assigned != b:
            raise AssertionError("Unshifted assignment differs from the frozen graph association")
        shifts.append(dict(shift_days=days, edges=len(edges), assignments=len(assigned),
                           ssn_with_candidates=len({x.ssn for x in edges}), usgs_with_candidates=len({x.usgs for x in edges})))
    reference = json.loads((project / "research/sequences/references/historical_control_reference.json").read_text(encoding="utf-8"))
    if counts != reference["gem"] or shifts != reference["time_shifts"]:
        raise AssertionError("Retained GEM count or fixed ten-shift table differs")
    output = project / "research/sequences/replayed_controls"
    output.mkdir(parents=True, exist_ok=False)
    (output / "HISTORICAL_CONTROL_COUNTS.json").write_text(json.dumps(dict(gem=counts, time_shifts=shifts), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="HISTORICAL_EVIDENCE_AND_SHIFT_COUNTS_PASS", gem=counts,
                          nonzero_shifts=len(shifts)-1, engine_rerun=False)))
