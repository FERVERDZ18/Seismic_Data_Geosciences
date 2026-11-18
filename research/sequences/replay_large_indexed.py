"""Recompute36 indexed observed-parent cases and Node parity, no timing study.

The frozen exhaustive/reference results remain expected evidence. This controller
reuses the unchanged indexed workers and original summary implementation; it
does not rerun the eight full170880-event exhaustive weight controls.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


def main(project, node):
    project = Path(project).resolve()
    base = project / "outputs/claude_round2_2026-11-17/science/compute"
    sys.path.insert(0, str(base))
    source = base / "run_large_parent_study.py"
    name = "unchanged_large_parent_scientific_driver"
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.NODE = Path(node).resolve()
    module.verify_seal()
    out = base / "large_indexed_replay_01"
    out.mkdir(exist_ok=False)
    selected = {}
    for dataset in ["ssn_native", "usgs_native", "ssn_common", "usgs_common"]:
        for label, weight in module.WEIGHTS:
            native = module.execute_native(out, dataset, label, weight, "kd", 1)
            module.node_parity(out, dataset, label, weight, native)
            selected[dataset + "_" + label] = str(native)
            print(json.dumps(dict(dataset=dataset, weight=weight, status="INDEXED_AND_NODE_RECOMPUTED",
                                  exhaustive_reexecuted=False)), flush=True)
    module.summarize(out, selected)
    (out / "SCIENTIFIC_REPLAY_SCOPE.json").write_text(json.dumps(dict(
        status="INDEXED_SCIENCE_RECOMPUTED", planned_cases=36, completed_cases=len(selected),
        numerical_implementations_edited=False, exhaustive_reexecuted=False, benchmark_reexecuted=False,
        comparison="Decoded arrays checked against retained complete exhaustive results by the package wrapper"), indent=2) + "\n", encoding="utf-8")
