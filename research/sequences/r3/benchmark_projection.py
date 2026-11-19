"""Rebuild the published measurements from the retained one-thread receipts."""
from pathlib import Path
import json
import statistics

from package_io import sha_file


PACKAGE = Path(__file__).resolve().parent
RESULT_PATH = Path("expected/outputs/claude_round2_2026-11-17/science/compute/native_benchmark_01")
CELL_KEYS = ("dataset", "n", "backend", "rep")
PHASES = ("preparation_seconds", "tree_seconds", "kernel_seconds", "postprocess_seconds", "total_seconds")


def read(path):
    return json.loads(path.read_bytes())


def main(workspace, output):
    # The retained receipts preserve measurements, but redact local runtime paths.
    transformations = {row["logical_path"]: row for row in
                       read(PACKAGE.parent / "METADATA_TRANSFORMATIONS.json")["transformations"]}

    def retained(logical_path):
        path = workspace / logical_path
        record = transformations[logical_path.as_posix()]
        assert sha_file(path) == record["public_sha256"], logical_path
        return read(path), record["original_source_sha256"]

    manifest, original_manifest = retained(RESULT_PATH / "MANIFEST.json")
    summary_path = workspace / RESULT_PATH / "SUMMARY.json"
    summary = read(summary_path)
    assert manifest["status"] == "PASS" and manifest["threads_all"] == 1 and manifest["repetitions"] == 3
    assert len(manifest["cells"]) == 81 and len(summary) == 27
    measurements = []
    for cell in manifest["cells"]:
        path = RESULT_PATH / Path(cell["path"]).name / "receipt.json"
        receipt, original_receipt = retained(path)
        assert cell["all_arrays_equal"] and original_receipt == cell["receipt_sha256"]
        assert all(receipt[key] == cell[key] for key in CELL_KEYS)
        assert receipt["status"] == "PASS" and receipt["threads_configured"] == 1
        assert receipt["measurement"]["total_seconds"] == cell["total_seconds"]
        assert receipt["after_measurement_memory"]["peak_working_set_bytes"] == cell["peak_working_set_bytes"]
        measurements.append({key: cell[key] for key in CELL_KEYS}
                            | {key: receipt["measurement"][key] for key in PHASES}
                            | {key: cell[key] for key in ("peak_working_set_bytes", "receipt_sha256")})

    for group in summary:
        rows = [row for row in measurements if all(row[key] == group[key] for key in CELL_KEYS[:3])]
        seconds = [row["total_seconds"] for row in rows]
        assert len(seconds) == 3
        assert [statistics.median(seconds), min(seconds), max(seconds)] == [group[key] for key in
                                                                             ("median_seconds", "min_seconds", "max_seconds")]
        assert [row["peak_working_set_bytes"] for row in rows] == group["peak_working_set_bytes"]

    published = read(PACKAGE / "reference/performance-matched-data.json")
    assert published["source"] == {"manifest_sha256": original_manifest, "summary_sha256": sha_file(summary_path)}
    assert published["threads"] == manifest["threads_all"] and published["repetitions"] == manifest["repetitions"]
    assert published["measurements"] == measurements
    published["measurements"] = measurements
    with (output / "performance-matched-data.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(published, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS: 81 one-thread cells and 27 retained summaries")
