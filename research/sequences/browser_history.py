"""Validate persisted public V3 scientific arrays without rerunning a browser."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


def main(project):
    project = Path(project).resolve()
    relative = "outputs/claude_round2_2026-11-17/science/compute"
    base = project/relative
    observed = project.parent/"expected"/relative/"browser_actual_v3_01/observed.json"
    sys.path.insert(0,str(base))
    source = base/"validate_browser_results_v3.py"
    name = "preserved_browser_v3_numerical_validator"
    spec = importlib.util.spec_from_file_location(name,source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    sys.argv = [str(source),"--observed",str(observed),"--folder","browser_public_check_01"]
    module.main()
    path = base/"browser_public_check_01/VERIFICATION.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    # The original/private POST byte digest is retained separately in the public
    # transformation ledger. Scientific arrays/cells/criteria are unchanged.
    report.pop("download")
    (path.parent/"SCIENTIFIC_VERIFICATION.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
