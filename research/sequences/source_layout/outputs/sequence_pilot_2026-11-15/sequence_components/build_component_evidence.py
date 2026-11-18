"""Describe existing algorithmic components; do not fit or rerun a classifier.

Post-review exploratory response to SEQ02. Each NPZ field is read once and cached.
All outputs stay beside this script. Run with the existing scientific environment.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
ROOT = PILOT.parents[1]
ROLE_NAMES = ["isolated", "main", "associated"]
CASES = ["B_ssn", "C_ssn", "B_usgs", "C_usgs", "B_alaska_usgs"]
INPUTS: dict[str, dict] = {}


def read_bytes(path):
    data = path.read_bytes()
    INPUTS[path.relative_to(ROOT).as_posix()] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)
    }
    return data


def read_json(path):
    return json.loads(read_bytes(path).decode("utf-8-sig"))


def read_npz(path, fields):
    # Hash the archive, then load each selected array exactly once.
    read_bytes(path)
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in fields}


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False) + "\n", encoding="utf-8")


def write_csv(name, rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    with (HERE / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def adjusted_rand(a, b):
    """ARI from exact integer contingency counts, including singleton blocks.

    The rational expression avoids catastrophic cancellation in near-degenerate
    cases. Label values have no numerical or cross-partition identity semantics.
    """
    a, b = list(a), list(b)
    if len(a) != len(b):
        raise ValueError("ARI partitions must describe the same universe")
    n = len(a)
    if n < 2:
        return 1.0
    choose2 = lambda x: x * (x - 1) // 2
    cells = Counter(zip(a, b))
    left, right = Counter(a), Counter(b)
    same_both = sum(choose2(x) for x in cells.values())
    same_a = sum(choose2(x) for x in left.values())
    same_b = sum(choose2(x) for x in right.values())
    all_pairs = choose2(n)
    expected = Fraction(same_a * same_b, all_pairs)
    denominator = Fraction(same_a + same_b, 2) - expected
    return float((same_both - expected) / denominator) if denominator else 1.0


def gk_partition(ids, groups):
    # group==0 is a sentinel for ALL isolated records, not a component.
    return [("singleton", str(rid)) if int(group) == 0 else ("group", int(group))
            for rid, group in zip(ids, groups)]


def self_tests():
    assert adjusted_rand([0, 0, 1, 1], [2, 2, 8, 8]) == 1.0
    assert adjusted_rand([0, 0, 1, 1], [0, 1, 0, 1]) == -0.5
    assert adjusted_rand([0, 1, 2], [8, 9, 7]) == 1.0
    assert adjusted_rand([0, 0, 0], [2, 2, 2]) == 1.0
    assert adjusted_rand([], []) == 1.0
    assert adjusted_rand([0, 0, 1, 2], [9, 9, 9, 8]) == adjusted_rand(
        [9, 9, 9, 8], [0, 0, 1, 2])
    labels = gk_partition(["a", "b", "c", "d"], [0, 0, 1, 1])
    assert labels[0] != labels[1] and labels[2] == labels[3]
    # A component joined via an omitted context node keeps its original block.
    full = np.array([0, 0, 0])
    assert adjusted_rand(full[[0, 2]], [5, 5]) == 1.0
    # Test the actual descriptor path: NN root zero remains a real component.
    nn_summary, nn_blocks = component_stats(["a", "b", "c"], np.array([0, 0, 2]),
        np.array([0., 86400., 172800.]), "NN")
    assert nn_summary["n_nonunit_components"] == 1
    assert nn_blocks[0] == {"size": 2, "observed_duration_days": 1.0}
    gk_summary, gk_blocks = component_stats(["a", "b", "c", "d"], np.array([0, 0, 1, 1]),
        np.array([0., 1., 86400., 172800.]), "GK")
    assert gk_summary["n_singleton_components"] == 2 and 0 not in gk_blocks
    try:
        adjusted_rand([0], [])
    except ValueError:
        pass
    else:
        raise AssertionError("Different universes must fail")
    return {"known_crossed_toy_ARI": -0.5, "label_permutation_invariance": True,
            "singletons_and_degenerate_partitions": True, "symmetry": True,
            "unequal_universe_rejected": True, "GK_zero_is_per_record_singleton": True,
            "NN_zero_is_valid_group": True, "full_partition_labels_preserved_on_projection": True}


def utc_seconds(token):
    return datetime.fromisoformat(token.replace("Z", "+00:00")).timestamp()


def describe(values):
    values = np.asarray(values)
    if not len(values):
        return {key: None for key in ["median", "q25", "q75", "iqr", "max"]}
    q25, median, q75 = np.quantile(values, [0.25, 0.5, 0.75], method="linear")
    return {"median": float(median), "q25": float(q25), "q75": float(q75),
            "iqr": float(q75 - q25), "max": float(np.max(values))}


def mean_range(values):
    values = np.asarray(values, dtype=float)
    return {"mean": float(values.mean()), "min": float(values.min()),
            "max": float(values.max())}


def component_stats(ids, raw_groups, times, method):
    # Isolated GK group zeros are omitted from non-unitary component descriptors.
    include = raw_groups > 0 if method == "GK" else np.ones(len(ids), dtype=bool)
    unique, inverse, counts = np.unique(raw_groups[include], return_inverse=True,
                                        return_counts=True)
    minimum = np.full(len(unique), np.inf)
    maximum = np.full(len(unique), -np.inf)
    np.minimum.at(minimum, inverse, times[include])
    np.maximum.at(maximum, inverse, times[include])
    durations = (maximum - minimum) / 86400.0
    non_unitary = counts > 1
    groups = {int(group): {"size": int(count), "observed_duration_days": float(duration)}
              for group, count, duration in zip(unique, counts, durations)}
    n_nonunit = int(non_unitary.sum())
    n_nonunit_members = int(counts[non_unitary].sum())
    summary = {"n_records": len(ids), "n_nonunit_components": n_nonunit,
               "n_singleton_components": len(ids) - n_nonunit_members,
               "n_total_components": n_nonunit + len(ids) - n_nonunit_members,
               "n_records_in_nonunit_components": n_nonunit_members}
    for prefix, values in [("size", counts[non_unitary]),
                           ("observed_duration_days", durations[non_unitary])]:
        summary.update({f"{prefix}_{key}": value for key, value in describe(values).items()})
    return summary, groups


def record_descriptor(case, index, draw=0):
    group = int(case["groups"][draw, index])
    if case["method"] == "GK" and group == 0:
        return {"original_group": 0, "component_size": 1, "observed_duration_days": 0.0}
    descriptor = case["group_maps"][draw][group]
    return {"original_group": group, "component_size": descriptor["size"],
            "observed_duration_days": descriptor["observed_duration_days"]}


def main():
    started = time.perf_counter()
    tests = self_tests()
    source_rows, lookups = {}, {}
    for source in ["ssn", "usgs", "alaska_usgs"]:
        path = PILOT / "inputs" / f"{source}.csv"
        read_bytes(path)
        with path.open(encoding="utf-8", newline="") as stream:
            source_rows[source] = list(csv.DictReader(stream))
        lookups[source] = {row["record_id"]: row for row in source_rows[source]}
        assert len(lookups[source]) == len(source_rows[source])
    pairs = read_json(ROOT / "outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json")
    pair_indices = {(pair["ssn_record_id"], pair["usgs_record_id"]): i for i, pair in enumerate(pairs)}
    assert len(pairs) == 2989
    assert all(len({pair[f"{s}_record_id"] for pair in pairs}) == len(pairs)
               for s in ["ssn", "usgs"])
    data, by_field, all_components, compact = {}, [], [], []
    for method in ["GK", "NN"]:
        for name in CASES:
            regime, source = name.split("_", 1)
            if method == "GK":
                arrays = read_npz(PILOT / "results/gk" / name / "classification.npz",
                                  ["ids", "group", "roles", "native_flag"])
                ids = list(map(str, arrays["ids"]))
                groups = arrays["group"][None, :]
                roles = arrays["roles"][None, :]
                seeds = [None]
                parents_defined = np.ones(len(ids), dtype=bool)
                native = None
            else:
                directory = PILOT / "comparators/nearest_neighbor/results" / name
                ids = read_json(directory / "ids.json")
                native = read_npz(directory / "arrays.npz",
                                  ["parent_defined_mask", "parent_index", "p_background"])
                arrays = read_npz(PILOT / "results/nn_independent" / name / "draws.npz",
                                  ["component_ids", "derived_roles", "seeds"])
                groups = arrays["component_ids"]
                roles = np.asarray(ROLE_NAMES)[arrays["derived_roles"]]
                seeds = list(map(int, arrays["seeds"]))
                parents_defined = native["parent_defined_mask"]
                assert groups.shape == roles.shape == (20, len(ids))
                assert seeds == list(range(20261115, 20261135))
            assert len(ids) == len(set(ids))
            times = np.array([utc_seconds(lookups[source][rid]["time_utc"]) for rid in ids])
            case = {"method": method, "regime": regime, "source": source,
                    "ids": ids, "index": {rid: i for i, rid in enumerate(ids)},
                    "groups": groups, "roles": roles, "seeds": seeds,
                    "parent_defined": parents_defined, "native": native,
                    "group_maps": [], "field_statistics": []}
            for draw, (labels, seed) in enumerate(zip(groups, seeds)):
                summary, mapping = component_stats(ids, labels, times, method)
                for role in ROLE_NAMES:
                    summary[f"n_role_{role}"] = int(np.sum(roles[draw] == role))
                assert summary["n_role_isolated"] == summary["n_singleton_components"]
                assert summary["n_role_main"] == summary["n_nonunit_components"]
                case["group_maps"].append(mapping)
                case["field_statistics"].append(summary)
                by_field.append({"method": method, "case": name, "seed": seed, **summary})
                for group, info in mapping.items():
                    if info["size"] > 1:
                        all_components.append({"method": method, "case": name, "seed": seed,
                                               "original_component_id": group, **info})
            case["summary"] = (case["field_statistics"][0] if method == "GK" else
                {key: mean_range([summary[key] for summary in case["field_statistics"]])
                 for key in case["field_statistics"][0]})
            data[method, name] = case
            row = {"method": method, "case": name, "n_records": len(ids), "n_fields": len(seeds)}
            for key in ["n_nonunit_components", "size_median", "size_q25", "size_q75",
                        "size_iqr", "size_max", "observed_duration_days_median",
                        "observed_duration_days_q25", "observed_duration_days_q75",
                        "observed_duration_days_iqr", "observed_duration_days_max"]:
                value = case["summary"][key]
                for statistic, number in (value.items() if method == "NN" else [("value", value)]):
                    row[f"{key}_{statistic}"] = number
            compact.append(row)

    # Fix the same pair-ID universe across both sources AND B/C for each method.
    universes, partition_report, projection_rows, ari_rows, universe_rows = {}, {}, [], [], []
    for method in ["GK", "NN"]:
        kept = [pair for pair in pairs if all(
            pair[f"{source}_record_id"] in data[method, f"{regime}_{source}"]["index"]
            and data[method, f"{regime}_{source}"]["parent_defined"][
                data[method, f"{regime}_{source}"]["index"][pair[f"{source}_record_id"]]]
            for regime in ["B", "C"] for source in ["ssn", "usgs"])]
        assert len(kept) == (2459 if method == "GK" else 2458)
        universes[method] = kept
        universe_rows.extend({"method": method, "pair_index_in_original_2989":
            pair_indices[pair["ssn_record_id"], pair["usgs_record_id"]], **pair} for pair in kept)
        projected, projected_roles = {}, {}
        for name in ["B_ssn", "C_ssn", "B_usgs", "C_usgs"]:
            case = data[method, name]
            source = case["source"]
            ix = np.array([case["index"][pair[f"{source}_record_id"]] for pair in kept])
            projected[ name ] = []
            projected_roles[name] = case["roles"][:, ix]
            for draw, labels in enumerate(case["groups"]):
                full_labels = gk_partition(case["ids"], labels) if method == "GK" else labels.tolist()
                projected[name].append([full_labels[i] for i in ix])
                for pair_i, full_i in enumerate(ix):
                    projection_rows.append({"method": method, "case": name, "seed": case["seeds"][draw],
                        "pair_index_in_original_2989": pair_indices[kept[pair_i]["ssn_record_id"], kept[pair_i]["usgs_record_id"]],
                        "original_full_source_group": int(labels[full_i]),
                        "GK_per_record_singleton": bool(method == "GK" and labels[full_i] == 0),
                        "role": str(case["roles"][draw, full_i])})
        report = {"n_same_candidate_pairs": len(kept), "comparisons": {}}
        for left, right in [("B_ssn", "B_usgs"), ("C_ssn", "C_usgs"),
                            ("B_ssn", "C_ssn"), ("B_usgs", "C_usgs")]:
            scores = [adjusted_rand(a, b) for a, b in zip(projected[left], projected[right])]
            role_agreement = np.mean(projected_roles[left] == projected_roles[right], axis=1)
            key = left + "__" + right
            report["comparisons"][key] = {"ARI": scores[0] if method == "GK" else mean_range(scores),
                "role_agreement": float(role_agreement[0]) if method == "GK" else mean_range(role_agreement),
                "all_field_ARI": scores, "all_field_role_agreement": role_agreement.tolist()}
            for seed, score, agreement in zip(data[method, left]["seeds"], scores, role_agreement):
                ari_rows.append({"method": method, "comparison": key, "seed": seed,
                                 "n_same_pairs": len(kept), "adjusted_rand_index": score,
                                 "role_agreement": float(agreement)})
        partition_report[method] = report

    # Deterministic posterior descriptive audit; no minimal-cause attribution.
    b, c = data["GK", "B_ssn"], data["GK", "C_ssn"]
    changed = [pair["ssn_record_id"] for pair in universes["GK"] if
               b["roles"][0, b["index"][pair["ssn_record_id"]]] !=
               c["roles"][0, c["index"][pair["ssn_record_id"]]]]
    chosen = min(changed, key=lambda rid: (lookups["ssn"][rid]["time_utc"], rid))
    trace = {"rule": "First (UTC, SSN record_id) of the 2459 common candidate pairs with a GK role change B to C",
             "selection_status": "Post-review exploratory descriptive audit; not preregistered validation",
             "n_changed_roles_in_2459": len(changed), "chosen_record": lookups["ssn"][chosen],
             "regimes": {}, "limitation": "Many context records are removed simultaneously; no unique cause or minimality is established."}
    member_lists, trace_rows = {}, []
    for name, case in [("B", b), ("C", c)]:
        i = case["index"][chosen]
        group = int(case["groups"][0, i])
        members = ([chosen] if group == 0 else
                   [rid for rid, label in zip(case["ids"], case["groups"][0]) if label == group])
        members.sort(key=lambda rid: (lookups["ssn"][rid]["time_utc"], rid))
        reference = min(members, key=lambda rid: (-Decimal(lookups["ssn"][rid]["magnitude"]),
                                                  lookups["ssn"][rid]["time_utc"], rid))
        member_lists[name] = members
        trace["regimes"][name] = {"role": str(case["roles"][0, i]),
            **record_descriptor(case, i), "reference_max_reported_M_tie_UTC_ID": lookups["ssn"][reference],
            "member_record_ids": members}
    removed = [rid for rid in member_lists["B"] if rid not in c["index"]]
    trace["removed_B_component_members_by_intervention"] = [lookups["ssn"][rid] for rid in removed]
    trace["n_context_records_removed_in_all_SSN"] = len(b["ids"]) - len(c["ids"])
    trace["retained_B_component_members_outside_new_C_component"] = [rid for rid in member_lists["B"]
        if rid in c["index"] and rid not in set(member_lists["C"])]
    for rid in sorted(set(member_lists["B"]) | set(member_lists["C"]),
                      key=lambda rid: (lookups["ssn"][rid]["time_utc"], rid)):
        trace_rows.append({**lookups["ssn"][rid], "member_of_chosen_B_component": rid in member_lists["B"],
            "member_of_chosen_C_component": rid in member_lists["C"], "present_in_C_cohort": rid in c["index"],
            "removed_from_B_context": rid not in c["index"]})

    # Exhaustive symmetric exploratory threshold across ALL original pairs.
    large = [pair for pair in pairs if any(Decimal(lookups[s][pair[f"{s}_record_id"]]["magnitude"]) >= Decimal("6.0")
                                             for s in ["ssn", "usgs"])]
    high_rows, high_summary, high_metadata = [], [], []
    for pair in large:
        pair_index = pair_indices[pair["ssn_record_id"], pair["usgs_record_id"]]
        metadata = {"pair_index_in_original_2989": pair_index, **pair}
        for source in ["ssn", "usgs"]:
            row = lookups[source][pair[f"{source}_record_id"]]
            metadata.update({f"{source}_{key}": row[key] for key in ["time_utc", "magnitude", "magnitude_type"]})
        high_metadata.append(metadata)
        for method in ["GK", "NN"]:
            for name in ["B_ssn", "C_ssn", "B_usgs", "C_usgs"]:
                case = data[method, name]
                rid = pair[f"{case['source']}_record_id"]
                if rid not in case["index"]:
                    high_summary.append({"pair_index": pair_index, "method": method, "case": name,
                                         "record_id": rid, "retained": False})
                    continue
                index = case["index"][rid]
                details = []
                for draw, seed in enumerate(case["seeds"]):
                    detail = {"pair_index": pair_index, "method": method, "case": name,
                        "record_id": rid, "seed": seed, "role": str(case["roles"][draw, index]),
                        "parent_defined": bool(case["parent_defined"][index]),
                        **record_descriptor(case, index, draw)}
                    if method == "NN":
                        parent = int(case["native"]["parent_index"][index])
                        detail.update(parent_record_id=case["ids"][parent] if parent >= 0 else "",
                                      p_background=float(case["native"]["p_background"][index]))
                    high_rows.append(detail)
                    details.append(detail)
                aggregate = {"pair_index": pair_index, "method": method, "case": name,
                    "record_id": rid, "retained": True, "n_fields": len(details),
                    "parent_defined": bool(case["parent_defined"][index])}
                aggregate.update({f"n_role_{role}": sum(item["role"] == role for item in details)
                                  for role in ROLE_NAMES})
                for key in ["component_size", "observed_duration_days"]:
                    aggregate.update({f"{key}_{statistic}": value for statistic, value in
                        mean_range([item[key] for item in details]).items()})
                high_summary.append(aggregate)

    definitions = {
        "analysis_status": "Post-review exploratory descriptive response to SEQ02; original cohorts, parameters and primary analyses unchanged.",
        "component": "A non-unitary algorithmic block of the existing full-source GK/NN partition; these are not validated physical earthquake families.",
        "duration": "Maximum minus minimum observed UTC within the full-source block, in days; finite catalogue span and filtering censor duration.",
        "quantiles": "NumPy linear interpolation at .25/.5/.75; IQR=q75-q25; unweighted across non-unitary blocks within each field.",
        "NN_aggregation": "Compute each statistic separately in each of 20 source/ID-independent fields; report arithmetic mean and min/max across fields, never pooled component quantiles. Fields use the same listed seed by source, with distinct source namespaces and stable IDs between B/C; they are not 20 independent catalogues.",
        "ARI_universe": "Same original candidate-pair IDs retained by BOTH sources in BOTH B and C; GK 2459; NN 2458 after requiring native parent_defined_mask in every source/regime. Pair correspondences remain unvalidated candidates.",
        "ARI_projection": "Restrict the ORIGINAL full-source component labels to those pair IDs. Do not rerun connectivity, delete intermediary edges or regroup the projected records. All isolated GK records are unique singleton labels; NN group zero is valid. Block labels are nominal and source-specific.",
        "ARI_formula": "[sum_ij C(nij,2)-sum_i C(ai,2)sum_j C(bj,2)/C(n,2)] / [(sum_i C(ai,2)+sum_j C(bj,2))/2-sum_i C(ai,2)sum_j C(bj,2)/C(n,2)]. Degenerate identical partitions have ARI=1.",
        "NN_undefined": "Undefined native parents are flagged per record. They remain in full-source component summaries but are excluded from pair-level ARI comparisons; no component-ID sentinel test is used.",
        "high_magnitude_rule": "All original 2989 candidate pairs with native reported M >=6.0 in either source, symmetric Decimal comparison; all qualifying pairs exported, no named-event selection.",
        "interpretation": "ARI is conditional partition concordance, not physical sequence accuracy or topology/edge agreement. Role agreement and partition concordance measure different properties. Within-source B/C measures context sensitivity, not causal isolation."
    }
    report = {"definitions": definitions, "input_source_rows": {s: len(r) for s, r in source_rows.items()},
        "component_summaries": {f"{method}_{name}": case["summary"] for (method, name), case in data.items()},
        "partition_concordance": partition_report,
        "exploratory_high_magnitude_pairs": {"n": len(large), "metadata": high_metadata},
        "deterministic_GK_trace": trace}
    write_json("COMPONENT_EVIDENCE.json", report)
    write_json("GK_TRACE.json", trace)
    write_csv("component_summary_compact.csv", compact)
    write_csv("component_summary_by_field.csv", by_field)
    write_csv("nonunit_components_by_field.csv", all_components)
    write_csv("projected_original_labels.csv", projection_rows)
    write_csv("common_candidate_universes.csv", universe_rows)
    write_csv("partition_ARI_by_field.csv", ari_rows)
    write_csv("GK_trace_members.csv", trace_rows)
    write_csv("high_magnitude_candidate_pairs.csv", high_metadata)
    write_csv("high_magnitude_component_summary.csv", high_summary)
    write_csv("high_magnitude_components_by_field.csv", high_rows)
    output_names = ["COMPONENT_EVIDENCE.json", "GK_TRACE.json", "component_summary_compact.csv",
        "component_summary_by_field.csv", "nonunit_components_by_field.csv", "projected_original_labels.csv",
        "common_candidate_universes.csv", "partition_ARI_by_field.csv", "GK_trace_members.csv",
        "high_magnitude_candidate_pairs.csv", "high_magnitude_component_summary.csv",
        "high_magnitude_components_by_field.csv"]
    receipt = {"status": "PASS", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"executable": sys.executable, "python": platform.python_version(),
                    "numpy": np.__version__, "elapsed_seconds": time.perf_counter()-started},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": INPUTS, "tests": tests,
        "invariants": {"n_original_pairs": 2989, "GK_same_pair_universe": len(universes["GK"]),
                       "NN_same_defined_pair_universe": len(universes["NN"]), "no_clustering_or_fitting_rerun": True},
        "outputs": {path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "bytes": path.stat().st_size}
                    for path in [HERE/name for name in sorted(output_names)]}}
    write_json("COMPONENT_RECEIPT.json", receipt)
    print(json.dumps({"seconds": receipt["runtime"]["elapsed_seconds"],
        "partition_concordance": partition_report, "high_M_pairs": len(large),
        "trace": {"record_id": chosen, "regimes": {r: {key: value for key, value in item.items()
            if key not in ["member_record_ids", "reference_max_reported_M_tie_UTC_ID"]}
            for r, item in trace["regimes"].items()}}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
