"""Recompute the additional article analyses from the materialized science package."""
import argparse
import csv
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path[:0] = [str(HERE), str(PACKAGE)]
from package_io import inside, manifest, sha_file


CATALOG = "outputs/claude_round2_2026-11-17/science/catalog"
TWINS = "outputs/claude_round2_2026-11-17/science/twins"
METHODS = "outputs/claude_response_2026-11-16"
BENCH = "outputs/claude_round2_2026-11-17/science/compute/native_benchmark_01"
PILOT = "outputs/sequence_pilot_2026-11-15"
INPUT_FILES = {
    f"source_layout/{CATALOG}/INPUTS.json",
    f"source_layout/{CATALOG}/vendor/deterministic_families.py",
    f"source_layout/{TWINS}/PROTOCOL_TWINS_V1.json",
    f"source_layout/{TWINS}/run_twins_v1.py",
    f"source_layout/{TWINS}/vendor/pilot_catalog_reconciliation.py",
    f"source_layout/{METHODS}/index/spherical_weighted_v2.py",
    f"source_layout/{METHODS}/methods/author_normalmix_port.py",
    f"source_layout/{METHODS}/methods/deterministic_families.py",
    f"source_layout/{METHODS}/methods/run_deterministic_study_v3.py",
    f"source_layout/{METHODS}/methods/deterministic_study_v3/PAIRED_METRICS.json",
    f"source_layout/{METHODS}/methods/deterministic_study_v3/MEASUREMENT_FACTORIAL.json",
    f"source_layout/{PILOT}/inputs/ssn.csv",
    f"source_layout/{PILOT}/inputs/usgs.csv",
    f"source_layout/{PILOT}/gardner_knopoff.py",
    f"source_layout/{PILOT}/comparators/nearest_neighbor/bruces_reference.py",
    "source_layout/outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json",
    "source_layout/system/dist/sequences/data/inputs_3_5.json",
    f"expected/{CATALOG}/runs/run_01/MANIFEST.json",
    f"expected/{CATALOG}/runs/run_01/PAIRED_ENDPOINTS.csv",
    f"expected/{CATALOG}/runs/run_01/WEIGHT_THRESHOLD_METRICS.csv",
    f"expected/{TWINS}/run_v1/CALIBRATION.json",
    f"expected/{BENCH}/MANIFEST.json",
    f"expected/{BENCH}/SUMMARY.json",
}


def required_input(name):
    return (name in INPUT_FILES
            or name.startswith(f"expected/{CATALOG}/runs/run_01/cases/")
            or (name.startswith(f"expected/{TWINS}/run_v1/test_") and
                name.endswith(("/latent_truth.json", "/observation_ledger.json")))
            or (name.startswith(f"expected/{BENCH}/") and name.endswith("/receipt.json")))


def read(path):
    return json.loads(path.read_bytes())


def compare_numeric(expected, actual, key=""):
    """Permit rounding only in floating-point arithmetic, with no integer slack."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        assert expected.keys() == actual.keys(), key
        for name, value in expected.items():
            compare_numeric(value, actual[name], f"{key}/{name}")
    elif isinstance(expected, list) and isinstance(actual, list):
        assert len(expected) == len(actual), key
        for index, (a, b) in enumerate(zip(expected, actual, strict=True)):
            compare_numeric(a, b, f"{key}/{index}")
    elif isinstance(expected, float) and isinstance(actual, float):
        assert math.isclose(expected, actual, rel_tol=1e-13, abs_tol=1e-13), (key, expected, actual)
    else:
        assert type(expected) is type(actual) and expected == actual, (key, expected, actual)


def compare_csv(expected, actual):
    def records(path):
        with path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    left, right = records(expected), records(actual)
    assert len(left) == len(right)
    for index, (a, b) in enumerate(zip(left, right, strict=True)):
        assert a.keys() == b.keys()
        for key in a:
            if a[key] != b[key]:
                # Scientific identifiers, integers and booleans must be exact.
                try:
                    if any(c in a[key] for c in (".", "e")) and any(c in b[key] for c in (".", "e")):
                        close = math.isclose(float(a[key]), float(b[key]), rel_tol=1e-13, abs_tol=1e-13)
                    else:
                        close = False
                except ValueError:
                    close = False
                assert close, (expected.name, index, key, a[key], b[key])


def check_result_dir(actual, expected):
    checked = []
    for path in sorted(expected.iterdir()):
        if path.suffix == ".json":
            compare_numeric(read(path), read(actual / path.name), path.name)
        elif path.suffix == ".csv":
            compare_csv(path, actual / path.name)
        else:
            assert (actual / path.name).read_bytes() == path.read_bytes(), path.name
        checked.append(path.name)
    return checked


def main():
    if not __debug__:
        raise RuntimeError("Run with assertions enabled for numerical verification")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True,
                        help="Independent workspace from replay.py --materialize-only")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    materialization = read(workspace / "MATERIALIZATION.json")
    assert materialization["manifest_sha256"] == sha_file(PACKAGE / "MANIFEST.json")
    assert not (workspace / "source_layout/.git").exists()
    spec = manifest(PACKAGE)
    for entry in spec["package_files"]:
        if entry["path"].startswith("r3/"):
            package_file = inside(PACKAGE, entry["path"])
            assert sha_file(package_file) == entry["sha256"], entry["path"]
    validated = 0
    for entry in spec["files"]:
        logical_path = entry["logical_path"]
        if required_input(logical_path):
            assert sha_file(inside(workspace, logical_path)) == entry["sha256"], logical_path
            validated += 1
    config = read(PACKAGE / "science_pipeline.json")
    for name, expected in config["dependency_versions"].items():
        assert version(name) == expected, (name, expected, version(name))
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMBA_NUM_THREADS="1")
    output = workspace / "r3-results"
    output.mkdir(exist_ok=False)
    for folder in ("weights", "twins", "benchmark"):
        (output / folder).mkdir()

    import benchmark_projection
    import common_member_sensitivity
    import weight_contrasts
    import weight_strata

    weight_contrasts.configure(workspace, output / "weights")
    weight_contrasts.main()
    weight_strata.main(workspace, output / "weights")
    common_member_sensitivity.configure(workspace, output / "twins")
    common_member_sensitivity.main()
    benchmark_projection.main(workspace, output / "benchmark")
    catalog_source = workspace / "source_layout" / CATALOG
    roles_args = [str(HERE / "role_sensitivity.py"), "--catalog-run", str(workspace / "expected" / CATALOG / "runs/run_01"),
                  "--families-module", str(catalog_source / "vendor/deterministic_families.py"), "--native-v3", str(HERE / "inputs/d1p5"),
                  "--retained-sweep", str(HERE / "reference/weights/WEIGHT_CUT_SWEEP.csv"), "--output-dir", str(output / "roles")]
    subprocess.run([sys.executable, "-I", "-B", *roles_args], check=True)
    checks = {name: check_result_dir(output / name, HERE / "reference" / name) for name in ("weights", "twins", "roles")}
    benchmark = "performance-matched-data.json"
    assert sha_file(output / "benchmark" / benchmark) == sha_file(HERE / "reference" / benchmark)
    checks["benchmark"] = [benchmark]
    receipt = dict(status="PASS", validated_workspace_files=validated, matching_outputs=checks,
                   synthetic_histories=60, synthetic_history_cells=960, benchmark_receipts=81,
                   benchmark_groups=27, timings_remeasured=False)
    (output / "REPLAY_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
