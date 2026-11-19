"""Recalculate role kappa and partition ARI from sealed native classifications."""

import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np


SOURCES = ("ssn", "usgs")
CLASSES = ("isolated", "representative", "associated")
LOW = 1.0905428994843476
HIGH = 1.3265675928192793
WEIGHTS = (0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, LOW, HIGH)
REFIT_GRID = [(w, w) for w in WEIGHTS] + [(LOW, HIGH), (HIGH, LOW)]
LABEL_KEYS = ("roles", "component_root_index", "retained_parent_index", "strong_link_mask")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(path.read_bytes())


def families_loader(path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("retained_families", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.families_from_cut


def checked(path, expected, receipt, key):
    actual = digest(path)
    if expected is not None and actual != expected:
        raise ValueError(f"Unexpected SHA-256: {key}")
    receipt[key] = actual
    return path


def load_case(path, refit, families, receipt, manifest=None, root=None):
    key = f"{'catalog' if manifest is not None else 'v3'}/{path.name}"

    def retained_file(name):
        file = path / name
        expected = manifest[file.relative_to(root).as_posix()] if manifest is not None else None
        return checked(file, expected, receipt, f"{key}/{name}")

    meta = read_json(retained_file("metadata.json"))
    ids = read_json(retained_file("ids.json"))
    rows = read_json(retained_file("rows.json"))
    if ids != [row["record_id"] for row in rows] or len(ids) != len(set(ids)):
        raise ValueError(f"Endpoint IDs do not match native ordered rows: {key}")
    arrays_path = retained_file("arrays.npz")
    assert receipt[f"{key}/arrays.npz"] == meta["arrays_sha256"]
    if "ids_sha256" in meta:
        assert receipt[f"{key}/ids.json"] == meta["ids_sha256"]
    with np.load(arrays_path, allow_pickle=False) as archive:
        arrays = dict(archive.items())
    with np.errstate(divide="ignore", invalid="ignore"):
        score = np.log10(arrays["TN"]) + np.log10(arrays["RN"])

    def classify(cut):
        return families(arrays["parent_index"], score, arrays["reported_magnitude"],
                        arrays["t_year"], ids, cut, inclusive=True)

    cutoff = meta["fit"]["threshold_log10"]
    for field, values in classify(cutoff).items():
        if field in LABEL_KEYS:
            assert np.array_equal(values, arrays[refit + field]), (key, field)
    mode_count = meta.get("diagnostics", meta.get("mixture_diagnostics"))["mode_count"]
    return dict(ids=ids, meta=meta, cutoff=cutoff, modes=mode_count, classify=classify)


def choose_two(n):
    return n * (n - 1) // 2


def metrics(roles_a, roles_b, groups_a, groups_b):
    n = len(roles_a)
    assert n == len(roles_b) == len(groups_a) == len(groups_b) and n > 1
    matrix = np.bincount(3 * roles_a.astype(int) + roles_b.astype(int), minlength=9).reshape(3, 3)
    first = matrix.sum(axis=1)
    second = matrix.sum(axis=0)
    matches = int(np.trace(matrix))
    agreement = matches / n
    chance_matches = int(first @ second)
    chance_agreement = chance_matches / (n * n)
    kappa = (matches * n - chance_matches) / (n * n - chance_matches) if chance_agreement != 1.0 else None

    first_pairs = sum(choose_two(k) for k in Counter(groups_a).values())
    second_pairs = sum(choose_two(k) for k in Counter(groups_b).values())
    shared_pairs = sum(choose_two(k) for k in Counter(zip(groups_a, groups_b)).values())
    total = choose_two(n)
    chance_pairs = first_pairs * second_pairs
    denominator = (first_pairs + second_pairs) * total - 2 * chance_pairs
    ari = 2 * (shared_pairs * total - chance_pairs) / denominator if denominator else 1.0
    return dict(n=n, matches=matches, agreement=agreement, chance_role_agreement=chance_agreement,
                cohen_kappa=kappa, adjusted_rand_index=ari,
                matrix_ssn_rows_comcat_columns=matrix.tolist(),
                ssn_role_counts=dict(zip(CLASSES, first.tolist())),
                comcat_role_counts=dict(zip(CLASSES, second.tolist())),
                family_pair_counts=dict(ssn=first_pairs, comcat=second_pairs, both=shared_pairs))


def weight_label(weight):
    return {LOW: "low", HIGH: "high"}.get(weight, f"{weight:g}")


def write_table(path, label, rows, include_modes):
    header = "| " + label + " | All (%) | All κ / ARI | Temporal (%) | Temporal κ / ARI | Largest SSN / ComCat |"
    if include_modes:
        header += " SSN modes |"
    lines = [header, "|" + " --- |" * (7 if include_modes else 6)]
    for name, result in rows:
        full, held = (result[period] for period in ("full", "temporal"))
        largest = result["largest_native_families"]
        line = f"| {name} | {full['agreement']:.2%} | {full['cohen_kappa']:.3f} / {full['adjusted_rand_index']:.3f} | "
        line += f"{held['agreement']:.2%} | {held['cohen_kappa']:.3f} / {held['adjusted_rand_index']:.3f} | {largest['ssn']} / {largest['comcat']} |"
        if include_modes:
            line += f" {result['ssn_fit_modes']} |"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-run", type=Path, required=True)
    parser.add_argument("--families-module", type=Path, required=True)
    parser.add_argument("--native-v3", type=Path, required=True)
    parser.add_argument("--retained-sweep", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.catalog_run
    receipt = {"role_sensitivity.py": digest(Path(__file__)), "families_module": digest(args.families_module)}
    families = families_loader(args.families_module)
    manifest = read_json(checked(root / "MANIFEST.json", None, receipt, "catalog/MANIFEST.json"))
    assert manifest["status"] == "PASS"
    expected = {item["path"]: item["sha256"] for item in manifest["output_files"]}
    pairs = csv_rows(checked(root / "PAIRED_ENDPOINTS.csv", expected["PAIRED_ENDPOINTS.csv"], receipt,
                             "catalog/PAIRED_ENDPOINTS.csv"))
    held = np.array(["2021" <= row["year"] <= "2025" for row in pairs])
    assert len(pairs) == 889 and int(held.sum()) == 382
    cases = {}
    for path in sorted((root / "cases").iterdir()):
        case = load_case(path, "delta_0_", families, receipt, expected, root)
        meta = case["meta"]
        assert meta["d"] == 1.6 and meta["q"] == 0.5
        cases[meta["source"], meta["w"]] = case
    assert set(cases) == {(source, w) for source in SOURCES for w in WEIGHTS}
    cuts_w1 = [cases[source, 1.0]["cutoff"] for source in SOURCES]
    indices = []
    for source in SOURCES:
        ids = cases[source, 1.0]["ids"]
        assert all(cases[source, w]["ids"] == ids for w in WEIGHTS)
        by_id = {key: j for j, key in enumerate(ids)}
        chosen = [by_id[row[f"{source}_record_id"]] for row in pairs]
        assert len(set(chosen)) == len(pairs)
        indices.append(np.array(chosen))

    def evaluate(two_cases, cuts):
        labels = [case["classify"](cut) for case, cut in zip(two_cases, cuts)]
        picked = tuple(tuple(label[field][idx] for label, idx in zip(labels, indices))
                       for field in ("roles", "component_root_index"))
        a, b, ga, gb = (*picked[0], *picked[1])
        largest = [int(np.bincount(label["component_root_index"]).max()) for label in labels]
        return dict(full=metrics(a, b, ga, gb), temporal=metrics(a[held], b[held], ga[held], gb[held]),
                    largest_native_families=dict(zip(("ssn", "comcat"), largest)),
                    native_total=dict(zip(("ssn", "comcat"), (len(c["ids"]) for c in two_cases))),
                    caps_log10=dict(zip(("ssn", "comcat"), cuts)), ssn_fit_modes=two_cases[0]["modes"])

    def native(weights, cuts=None):
        two_cases = [cases[source, weight] for source, weight in zip(SOURCES, weights)]
        return evaluate(two_cases, cuts if cuts is not None else [case["cutoff"] for case in two_cases])

    refit = [dict(ssn_weight=a, comcat_weight=b, **native((a, b))) for a, b in REFIT_GRID]
    retained = csv_rows(checked(root / "WEIGHT_THRESHOLD_METRICS.csv", expected["WEIGHT_THRESHOLD_METRICS.csv"], receipt,
                                "catalog/WEIGHT_THRESHOLD_METRICS.csv"))
    map_periods = {"full": "full_2016_2025", "temporal": "evaluation_2021_2025"}
    retained = {(float(row["w_ssn"]), float(row["w_usgs"]), row["period"]): row for row in retained if float(row["delta"]) == 0}
    for row in refit:
        for period, key in map_periods.items():
            check = retained[row["ssn_weight"], row["comcat_weight"], key]
            z = row[period]
            assert z["n"] == int(check["n"])
            for rebuilt, prior in (("agreement", "agreement"), ("cohen_kappa", "kappa"), ("adjusted_rand_index", "ARI")):
                assert math.isclose(z[rebuilt], float(check[prior]), rel_tol=0.0, abs_tol=1e-12), (period, key, rebuilt)

    sweep = {}
    for w in WEIGHTS:
        sweep[w, "refit"] = native((w, w))
        sweep[w, "fixed_w1"] = native((w, w), cuts_w1)
        sweep[w, "centered_at_floor"] = native((w, w), [cut - 4.5 * (w - 1.0) for cut in cuts_w1])
    for w in (1.2, 1.3):
        for cut_weight in (1.2, 1.3):
            cuts = [cases[source, cut_weight]["cutoff"] for source in SOURCES]
            sweep[w, f"w{cut_weight:g}"] = native((w, w), cuts)

    sweep_matches = 0
    if args.retained_sweep:
        sweep_reference = csv_rows(checked(args.retained_sweep, None, receipt, "r3/WEIGHT_CUT_SWEEP.csv"))
        assert len(sweep_reference) == len(sweep)
        for prior in sweep_reference:
            key = float(prior["weight"]), prior["cut_mode"]
            result = sweep[key]
            for field, old in (("full", "full"), ("temporal", "evaluation")):
                assert result[field]["matches"] == int(prior[f"{old}_matches"]), (key, field)
                assert result[field]["n"] == int(prior[f"{old}_n"]), (key, field)
            assert result["largest_native_families"] == dict(ssn=int(prior["ssn_largest"]), comcat=int(prior["usgs_largest"]))
            assert result["caps_log10"] == dict(ssn=float(prior["ssn_threshold"]), comcat=float(prior["usgs_threshold"]))
            sweep_matches += 1

    retained_v3 = args.native_v3
    v3_manifest = read_json(checked(retained_v3 / "MANIFEST.json", None, receipt, "v3/MANIFEST.json"))
    alternate_cases = []
    for source in SOURCES:
        name = f"M4p5_{source}_native_d1p5"
        case = load_case(retained_v3 / "cases" / name, "", families, receipt)
        case_receipt = next(entry for entry in v3_manifest["cases"] if entry["case"] == name)
        assert case_receipt["directory"] == f"cases/{name}" and case_receipt["events"] == len(case["ids"])
        assert case["meta"]["d"] == 1.5 and case["meta"]["w"] == 1.0 and case["ids"] == cases[source, 1.0]["ids"]
        alternate_cases.append(case)
    distance = dict(refit=evaluate(alternate_cases, [case["cutoff"] for case in alternate_cases]),
                    fixed_d1p6=evaluate(alternate_cases, cuts_w1))
    assert [(z["full"]["matches"], z["temporal"]["matches"]) for z in distance.values()] == [(786, 328), (777, 324)]

    cut_rows = []
    mode_labels = {"fixed_w1": "w = 1 boundary", "centered_at_floor": "Centred at M 4.5", "w1.2": "w = 1.2 boundary", "w1.3": "w = 1.3 boundary"}
    for w in (1.2, 1.3):
        for mode in mode_labels:
            if mode != f"w{w:g}":
                cut_rows.append((f"{w:g}, {mode_labels[mode]}", sweep[w, mode]))
    cut_rows.extend((("d = 1.5, refit", distance["refit"]), ("d = 1.5, d = 1.6 boundary", distance["fixed_d1p6"])))

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    write_table(output / "TABLE_3.md", "SSN / ComCat w", ((f"{weight_label(a)} / {weight_label(b)}", row)
                for (a, b), row in zip(REFIT_GRID, refit)), include_modes=True)
    write_table(output / "CUT_VARIANTS.md", "Sensitivity setting", cut_rows, include_modes=False)
    data = dict(status="PASS", definitions={
        "kappa": "Cohen's kappa for three operational roles on paired endpoints",
        "ari": "Adjusted Rand index for partition membership restricted to paired endpoints",
        "largest": "Largest family in each complete native input after the given cutoff",
        "full": "2016–2025, both reported M ≥ 4.5, 889 matched candidate pairs",
        "temporal": "2021–2025 subset, 382 matched candidate pairs",
    }, inputs_sha256=receipt, refit_grid=refit,
        weight_cut_grid=[dict(weight=w, cut_mode=mode, **result) for (w, mode), result in sweep.items()],
        distance_variants=distance,
        checks=dict(refit_rows_agree_with_independent_retained_metrics=len(refit),
                    weight_cut_rows_agree_with_retained_sweep=sweep_matches, distance_count_pairs_agree=2))
    (output / "RESULTS.json").write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(refit)} refit rows, {len(sweep)} cutoff rows, {len(distance)} distance rows")


if __name__ == "__main__":
    main()
