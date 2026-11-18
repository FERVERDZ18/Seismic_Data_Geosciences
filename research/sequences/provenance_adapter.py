"""Bind public scientific projections in a NEW consumer workspace only.

Original numerical sources and original project evidence are never edited.
The excluded internal aggregate was only hash-listed, never read by R2 science.
Only the exact sensitivity table is projected from the older association report.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CATALOG = "outputs/claude_round2_2026-11-17/science/catalog"
OMITTED_AUDIT = "outputs/claude_response_2026-11-16/catalog_design/CATALOG_DESIGN_AUDIT.json"
OLD_MATCH_REPORT = "outputs/ssn_usgs_pilot_2026-11-15/pilot_results.json"
PUBLIC_MATCH_REFERENCE = "research/sequences/references/association_window_reference.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind(project: Path) -> dict:
    project = project.resolve()
    receipt_path = project.parent / "PROVENANCE_REPLAY_RECEIPT.json"
    if receipt_path.exists():
        return json.loads(receipt_path.read_text(encoding="utf-8"))
    reference = project / PUBLIC_MATCH_REFERENCE
    if not reference.exists():
        return dict(status="NOT_NEEDED", hash_aliases={})
    reference_value = json.loads(reference.read_text(encoding="utf-8"))
    if set(reference_value) != {"sensitivity"}:
        raise ValueError("Public association reference must contain only the scientific sensitivity table")
    compatibility = project / OLD_MATCH_REPORT
    compatibility.parent.mkdir(parents=True, exist_ok=True)
    if compatibility.exists():
        raise FileExistsError("Original private matching report must not be materialized")
    compatibility.write_bytes(reference.read_bytes())
    changes, aliases = [], {}

    def replace_metadata(path, update):
        before = sha(path)
        value = json.loads(path.read_text(encoding="utf-8"))
        update(value)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        after = sha(path)
        if before != after:
            aliases[after] = before
            changes.append(dict(project_path=path.relative_to(project).as_posix(),
                                original_metadata_sha256=before, consumer_metadata_sha256=after))

    inputs = project / CATALOG / "INPUTS.json"
    omitted = []
    def input_update(value):
        for row in list(value):
            if row["path"] == OMITTED_AUDIT:
                value.remove(row)
                omitted.append(dict(path=row["path"], historical_sha256=row["sha256"],
                                    reason="Internal aggregate only hash-listed by R2; not an observed or numerical input"))
            elif row["path"] == OLD_MATCH_REPORT:
                row.update(bytes=compatibility.stat().st_size, sha256=sha(compatibility))
    replace_metadata(inputs, input_update)
    seal = project / CATALOG / "SEAL.json"
    replace_metadata(seal, lambda value: value["files"].update({"INPUTS.json": sha(inputs)}))
    south = project / CATALOG / "south_control/ANALYSIS_SEAL.json"
    if south.exists():
        def south_update(value):
            for name, old_hash in list(value["frozen_files"].items()):
                target = (south.parent / name).resolve()
                target.relative_to(project)
                actual = sha(target)
                if actual != old_hash:
                    if aliases.get(actual) != old_hash:
                        raise ValueError("Unexpected change beyond the declared public metadata adapter")
                    value["frozen_files"][name] = actual
        replace_metadata(south, south_update)
    receipt = dict(schema="public-scientific-provenance-adapter/1", status="BOUND_PUBLIC_PROJECTION",
                   numerical_sources_modified=False, observed_rows_modified=False,
                   public_reference=PUBLIC_MATCH_REFERENCE, public_reference_sha256=sha(reference),
                   compatibility_path=OLD_MATCH_REPORT, omitted_internal_aggregates=omitted,
                   metadata_changes=changes, hash_aliases=aliases,
                   scope="Only provenance-routing/checksum metadata in this new workspace; historical originals remain untouched")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def bind_validated_generated_inputs(project: Path, stage: str):
    """Route zero diagnostics to independently validated newly generated cases."""
    if stage != "zero_distance":
        return
    project = project.resolve()
    path = project/"outputs/claude_round2_2026-11-17/science/zero_distance/PROTOCOL.json"
    protocol = json.loads(path.read_text(encoding="utf-8"))
    report_path = project.parent/"CATALOG_MANIFEST_COMPARISON.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["status"] != "ALL_LISTED_SCIENTIFIC_OUTPUTS_EQUAL":
        raise ValueError("Generated diagnostic inputs require the complete catalogue comparison first")
    root = project/CATALOG/"runs/run_01"
    expected_root = project.parent/"expected"/CATALOG/"runs/run_01"
    if sha(root/"MANIFEST.json") != report["actual_manifest_sha256"] or sha(expected_root/"MANIFEST.json") != report["expected_manifest_sha256"]:
        raise ValueError("Validated catalogue inventory changed")
    old_files = {x["path"]:x for x in json.loads((expected_root/"MANIFEST.json").read_text())["output_files"]}
    new_files = {x["path"]:x for x in json.loads((root/"MANIFEST.json").read_text())["output_files"]}
    covered = {x["path"] for x in report["checks"] if x["equal"]}
    changes = []
    prefix = CATALOG+"/runs/run_01/"
    for item in protocol["inputs"]:
        source = project/item["path"]
        actual_hash = sha(source)
        if actual_hash == item["sha256"]:
            continue
        if not item["path"].startswith(prefix):
            raise ValueError("Unexplained non-catalogue input difference")
        relative = item["path"][len(prefix):]
        if relative not in covered or old_files[relative]["sha256"] != item["sha256"] or new_files[relative]["sha256"] != actual_hash:
            raise ValueError("Changed diagnostic input lacks a complete exact scientific comparison")
        changes.append(dict(path=item["path"], historical_sha256=item["sha256"], consumer_sha256=actual_hash,
                            scientific_comparison_report_sha256=sha(report_path)))
        item.update(sha256=actual_hash, bytes=source.stat().st_size)
    if not changes:
        return
    original = sha(path)
    path.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    seal = path.parent/"ANALYSIS_SEAL.json"
    original_seal = sha(seal)
    value = json.loads(seal.read_text(encoding="utf-8")); value["protocol_sha256"] = sha(path)
    seal.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt_path = project.parent/"PROVENANCE_REPLAY_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["hash_aliases"].update({sha(path):original,sha(seal):original_seal})
    receipt["validated_generated_input_rebindings"] = changes
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
