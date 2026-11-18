"""One entry point for package verification and isolated scientific reproduction."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

# -I intentionally excludes the script directory; add this reviewed helper root.
PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE))
from package_io import inside, materialize, sha_file, verify


def environment_versions(expected):
    observed = {}
    for name, version in expected.items():
        found = importlib.metadata.version(name)
        if found != version:
            raise ValueError(f"Dependency mismatch for {name}: expected {version}, observed {found}")
        observed[name] = found
    return observed


def clean_environment():
    env = dict(os.environ)
    for key in ["PYTHONPATH", "PYTHONHOME"]:
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMBA_NUM_THREADS="1")
    return env


def run_stage(project, config, stage, args):
    logs = project.parent / "logs"
    logs.mkdir(exist_ok=True)
    records = []
    for i, step in enumerate(stage["steps"]):
        command = [sys.executable, "-I", "-B", str(PACKAGE / "stage_adapter.py"),
                   "--project", str(project), "--recipe", str(PACKAGE / "science_pipeline.json"),
                   "--stage", stage["name"], "--step", str(i), "--node", args.node, "--octave", args.octave]
        started = time.perf_counter()
        stem = f"{stage['name']}_{i}"
        attempt = 0
        while (logs/(stem+".stdout.txt")).exists() or (logs/(stem+".stderr.txt")).exists():
            attempt += 1
            stem = f"{stage['name']}_{i}_attempt{attempt:02d}"
        with (logs / (stem+".stdout.txt")).open("xb") as stdout, \
             (logs / (stem+".stderr.txt")).open("xb") as stderr:
            try:
                done = subprocess.run(command, cwd=project, env=clean_environment(),
                    stdout=stdout, stderr=stderr, timeout=stage["cap_seconds"], check=False)
            except subprocess.TimeoutExpired:
                records.append(dict(step=i, status="CENSORED", cap_seconds=stage["cap_seconds"]))
                raise RuntimeError(f"Stage cap reached; preserve logs: {stage['name']}")
        record = dict(step=i, returncode=done.returncode, wall_seconds=time.perf_counter()-started)
        records.append(record)
        if done.returncode:
            raise RuntimeError(f"Scientific stage failed; preserve logs: {stage['name']} step{i}")
    return records


def compare_stage(project, workspace, package_manifest, stage):
    from compare_science import compare, validated_manifest_alias
    checks = []
    adapter_receipt = project.parent / "PROVENANCE_REPLAY_RECEIPT.json"
    aliases = json.loads(adapter_receipt.read_text(encoding="utf-8")).get("hash_aliases", {}) if adapter_receipt.exists() else {}
    if stage["name"] == "catalog":
        relative = "outputs/claude_round2_2026-11-17/science/catalog/runs/run_01/MANIFEST.json"
        audit = validated_manifest_alias(workspace/"expected"/relative, project/relative, hash_aliases=aliases)
        aliases[audit["actual_manifest_sha256"]] = audit["expected_manifest_sha256"]
        (project.parent/"CATALOG_MANIFEST_COMPARISON.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    specifications = [x for x in package_manifest.get("comparisons", []) if x["stage"] == stage["name"]]
    if not specifications and stage.get("required_scientific_comparison"):
        raise ValueError(f"No sealed scientific comparisons for {stage['name']}")
    for spec in specifications:
        expected = inside(workspace, spec["expected_logical_path"])
        actual = inside(project, spec["actual_project_path"])
        if stage["name"] == "browser_history":
            from compare_science import normalize
            first = json.loads(expected.read_text(encoding="utf-8")); first.pop("download", None)
            second = json.loads(actual.read_text(encoding="utf-8"))
            if normalize(first, aliases) != normalize(second, aliases):
                raise AssertionError("Canonical browser scientific verification fields differ")
            outcome = dict(kind="browser_scientific_fields", equal=True,
                           excluded_transport_field="download", original_post_hash_preserved_in_transformation_ledger=True)
        else:
            outcome = compare(expected, actual, hash_aliases=aliases)
        checks.append(dict(expected=spec["expected_logical_path"], actual=spec["actual_project_path"], **outcome))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--materialize-only", action="store_true")
    mode.add_argument("--replay-science", action="store_true")
    mode.add_argument("--bench-native", action="store_true")
    mode.add_argument("--browser-manual", action="store_true")
    mode.add_argument("--author-reference", action="store_true")
    mode.add_argument("--verify-gem-history", action="store_true")
    mode.add_argument("--verify-browser-history", action="store_true")
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--node", default="node")
    parser.add_argument("--octave", default="octave-cli")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--allow-private-partial", action="store_true", help="Private QA only; never a complete/public reproduction claim")
    parser.add_argument("--stages", help="Explicit subset of science stages for private functional QA")
    parser.add_argument("--resume-verified-workspace", action="store_true", help="Private QA only; preserve and recheck completed calculations")
    args = parser.parse_args()
    value = verify(PACKAGE, allow_private_partial=args.allow_private_partial)
    config = json.loads((PACKAGE / "science_pipeline.json").read_text(encoding="utf-8"))
    if args.verify:
        print(json.dumps(dict(status="VERIFIED", files=len(value["files"]),
                              manifest_sha256=sha_file(PACKAGE / "MANIFEST.json")), indent=2))
        return
    if args.workdir is None:
        parser.error("--workdir must name a new independent folder outside a Git checkout")
    if not args.materialize_only and sys.prefix == sys.base_prefix:
        raise ValueError("Run scientific modes using the documented new local virtual environment")
    selected = "science" if args.replay_science else "native_benchmark" if args.bench_native else "gem_history" if args.verify_gem_history else "browser_history" if args.verify_browser_history else "author_reference"
    stages = [x for x in config["stages"] if x["profile"] == selected]
    if args.stages:
        if not args.replay_science or not args.allow_private_partial:
            parser.error("--stages is only available for explicitly private partial scientific QA")
        requested = args.stages.split(",")
        if len(set(requested)) != len(requested) or not set(requested) <= {x["name"] for x in stages}:
            parser.error("Unknown or duplicate scientific stage")
        stages = [x for x in stages if x["name"] in requested]
    if not args.materialize_only and not args.browser_manual:
        if not stages or any(x.get("status") != "READY_FOR_REPLAY" for x in stages):
            raise ValueError("Selected profile is not finalized in the scientific source/result map")
    observed = environment_versions(config["dependency_versions"]) if not args.materialize_only else {}
    workspace = args.workdir.resolve()
    if args.resume_verified_workspace:
        if not args.allow_private_partial or not workspace.is_dir():
            parser.error("Resume is restricted to an existing explicitly private QA workspace")
        materialization = json.loads((workspace/"MATERIALIZATION.json").read_text(encoding="utf-8"))
        accepted = {sha_file(PACKAGE/"MANIFEST.json"), *value.get("compatible_predecessor_manifest_sha256", [])}
        if materialization["manifest_sha256"] not in accepted or (workspace/"source_layout/.git").exists():
            raise ValueError("Workspace is not the verified private materialization of this data package")
    else:
        materialize(PACKAGE, args.workdir, allow_private_partial=args.allow_private_partial)
    project = workspace / "source_layout"
    if args.materialize_only:
        print(json.dumps(dict(status="MATERIALIZED", workspace=str(workspace)), indent=2)); return
    if args.browser_manual:
        from browser_consumer import main as browser_main
        browser_main(project)
        return
    receipt = dict(schema="independent-scientific-replay/1", status="IN_PROGRESS", profile=selected,
        started_utc=datetime.now(timezone.utc).isoformat(), manifest_sha256=sha_file(PACKAGE/"MANIFEST.json"),
        versions=observed, python=sys.version, source_numcode_edited=False,
        partial_scientific_scope=bool(args.allow_private_partial), stages=[])
    receipt_path = workspace / "REPLAY_RECEIPT.json"
    if args.resume_verified_workspace and receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
        history = workspace/"replay_history"
        history.mkdir(exist_ok=True)
        history_path = history/f"receipt_before_resume_{len(list(history.glob('*.json'))):02d}.json"
        history_path.write_text(json.dumps(previous, indent=2)+"\n", encoding="utf-8")
        receipt["prior_failure_preserved"] = history_path.name
    try:
        for stage in stages:
            actual_project = project
            if stage.get("independent_legacy_root"):
                legacy = workspace.parent / (workspace.name + "_legacy")
                if not args.resume_verified_workspace:
                    materialize(PACKAGE, legacy, omit_groups=["generated_checkpoints"], omit_prefixes=["expected/"],
                                allow_private_partial=args.allow_private_partial)
                actual_project = legacy / "source_layout"
            executed = []
            if args.resume_verified_workspace:
                existing = [actual_project.parent/"adapter_receipts"/f"{stage['name']}_{i}.json" for i in range(len(stage["steps"]))]
                if all(x.exists() for x in existing):
                    for path, step in zip(existing, stage["steps"]):
                        before = json.loads(path.read_text(encoding="utf-8"))
                        source = PACKAGE/step["package_script"] if "package_script" in step else actual_project/step["script"]
                        if before["source_sha256"] != sha_file(source):
                            raise ValueError("Completed scientific step source changed; use a fresh replay")
                        executed.append(dict(reused_actual_calculation_receipt=path.name,
                                             expected_outputs_not_copied_as_calculation=True))
            if not executed:
                executed = run_stage(actual_project, config, stage, args)
            record = dict(name=stage["name"], executions=executed)
            record["scientific_comparisons"] = compare_stage(actual_project, workspace, value, stage)
            receipt["stages"].append(record)
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt.update(status="PASS", completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        receipt.update(status="FAILED_OR_CENSORED", error=repr(error))
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=receipt["status"], receipt=str(receipt_path)), indent=2))


if __name__ == "__main__":
    main()
