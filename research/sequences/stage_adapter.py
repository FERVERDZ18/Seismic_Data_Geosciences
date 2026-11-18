"""Process-local routing/runtime adapter; numerical source bytes are unchanged."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance_adapter import bind, bind_validated_generated_inputs


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def executable(value, label):
    found = shutil.which(value) if value else None
    path = Path(found or value or "").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Provide a real {label} executable")
    return path


def numerical_dependency_origins():
    """Observe already-imported modules without importing numerical packages."""
    observed = {}
    environment = Path(sys.prefix).resolve()
    for name in ["numpy", "scipy", "numba", "llvmlite", "pyproj", "bruces", "matplotlib", "utm"]:
        module = sys.modules.get(name)
        filename = getattr(module, "__file__", None) if module else None
        if filename:
            path = Path(filename).resolve()
            if not path.is_relative_to(environment):
                raise RuntimeError("Numerical dependency escaped the new isolated environment: " + name)
            observed[name] = "NEW_VIRTUAL_ENVIRONMENT"
    return observed


def comparator_replay_seal(project, octave):
    """Create a consumer seal in the new workspace, retaining the historical seal.

    The author runtime is obtained separately. Runtime provenance is checked and
    recorded here instead of pretending a new user's binary has the old hash.
    Scientific input/source entries retain their original hashes unchanged.
    """
    base = project / "outputs/claude_round2_2026-11-17/science/compute"
    path = base / "COMPARATOR_EXECUTION_SEAL.json"
    original = path.read_bytes()
    value = json.loads(original)
    historical = base / "HISTORICAL_COMPARATOR_EXECUTION_SEAL.json"
    if historical.exists():
        raise FileExistsError("A fresh comparator workspace is required")
    runtime_entries, scientific = [], []
    for item in value["entries"]:
        if "/runtime/octave-" in item["path"].replace("\\", "/"):
            runtime_entries.append(item)
        else:
            source = (project / item["path"]).resolve()
            source.relative_to(project)
            if not source.is_file() or sha(source) != item["sha256"]:
                raise ValueError("Historical scientific comparator source changed")
            scientific.append(item)
    result = subprocess.run([str(octave), "--version"], capture_output=True,
                            text=True, timeout=30, check=True)
    text = result.stdout + result.stderr
    if "11.3.0" not in text:
        raise ValueError("This author-reference profile requires GNU Octave11.3.0")
    historical.write_bytes(original)
    value.update(status="CONSUMER_REPLAY_SEAL", entries=scientific,
                 historical_seal_sha256=hashlib.sha256(original).hexdigest(),
                 runtime=dict(kind="separately_obtained_GNU_Octave", version_output=text,
                              executable_sha256=sha(octave), historical_runtime_entries=runtime_entries),
                 note="Runtime pin replaced explicitly for this consumer replay; original scientific sources unchanged")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--step", type=int, default=0)
    parser.add_argument("--node", default="node")
    parser.add_argument("--octave", default="octave-cli")
    args = parser.parse_args()
    project = args.project.resolve()
    if not (project / "AGENTS.md").is_file() or (project / ".git").exists():
        raise ValueError("Use only the generated independent scientific workspace")
    config = json.loads(args.recipe.read_text(encoding="utf-8"))
    stage = next(x for x in config["stages"] if x["name"] == args.stage)
    step = stage["steps"][args.step]
    if "package_script" in step:
        source = (Path(__file__).resolve().parent / step["package_script"]).resolve()
        source.relative_to(Path(__file__).resolve().parent)
    else:
        source = (project / step["script"]).resolve()
        source.relative_to(project)
    if not source.is_file():
        raise FileNotFoundError(source)
    node = executable(args.node, "Node") if stage.get("requires_node") else None
    octave = executable(args.octave, "Octave") if stage.get("requires_octave") else None
    node_version = None
    if node is not None:
        node_version = subprocess.run([str(node), "--version"], capture_output=True,
                                      text=True, timeout=30, check=True).stdout.strip()
        expected_node = config.get("specific_runtime_versions", {}).get("node")
        if expected_node and node_version.removeprefix("v") != expected_node.removeprefix("v"):
            raise ValueError("Node version differs from the finalized replay profile")
    if stage.get("consumer_comparator_seal"):
        comparator_replay_seal(project, octave)
    public_provenance = bind(project)
    bind_validated_generated_inputs(project, args.stage)
    gate = project / "consumer_twins_cpu_gate.json"
    argv = [str(project) if x == "{PROJECT}" else x for x in step.get("argv", [])]
    if stage.get("consumer_twins_gate"):
        protocol = project / "outputs/claude_round2_2026-11-17/science/twins/PROTOCOL_TWINS_V1.json"
        gate.write_text(json.dumps(dict(twins_protocol_sha256=sha(protocol),
            twins_scientific_cpu_authorized=True,
            scope="Consumer-requested local scientific replay only; no Git/publication or original author approval"), indent=2) + "\n", encoding="utf-8")
        argv = [str(gate) if x == "{TWINS_GATE}" else x for x in argv]
    os.chdir(project)
    sys.path.insert(0, str(source.parent))
    name = "scientific_stage_" + hashlib.sha256(str(source).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # Change runtime handles in memory, never a scientific source file.
    overrides = {}
    if node is not None and hasattr(module, "NODE"):
        module.NODE = node; overrides["NODE"] = str(node)
    if octave is not None and hasattr(module, "OCTAVE"):
        module.OCTAVE = octave; overrides["OCTAVE"] = str(octave)
    sys.argv = [str(source), *argv]
    call_args = [str(project) if x == "{PROJECT}" else str(node) if x == "{NODE}" else x for x in step.get("call_args", [])]
    getattr(module, step.get("call", "main"))(*call_args)
    receipt = dict(stage=args.stage, step=args.step, source_sha256=sha(source),
                   numerical_source_edited=False, runtime_overrides=overrides,
                   node_version=node_version,
                   public_provenance_adapter_status=public_provenance["status"],
                   numerical_dependency_origins=numerical_dependency_origins(),
                   python=sys.version, user_site_disabled=bool(sys.flags.no_user_site),
                   dependency_versions={name: importlib.metadata.version(name) for name in config["dependency_versions"]})
    target = project.parent / "adapter_receipts"
    target.mkdir(exist_ok=True)
    (target / f"{args.stage}_{args.step}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
