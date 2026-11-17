"""Refresh or check same-document sequence-workspace dependency cache keys.

The graph is acyclic: component bytes -> loader manifest -> loader bytes ->
application HTML. Scientific input manifests and source observations are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "system/dist"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def component(name: str) -> bytes:
    path = (DIST / name).resolve()
    if not path.is_relative_to(DIST.resolve()) or path.suffix not in {".js", ".css"}:
        raise ValueError("Invalid local component: " + name)
    return path.read_bytes()


def expected_files() -> dict[Path, bytes]:
    loader = DIST / "sequence-workbench.js"
    source = text(loader)
    match = re.search(r"const ASSETS=(\{.*?\});", source, re.S)
    if match is None:
        raise ValueError("The sequence-workspace dependency manifest is missing")
    assets = json.loads(match[1])
    for index, value in enumerate(assets["styles"]):
        name = value.split("?", 1)[0]
        assets["styles"][index] = name + "?v=" + digest(component(name))
    for value in assets["scripts"]:
        name = value[0].split("?", 1)[0]
        value[0] = name + "?v=" + digest(component(name))
    source = source[:match.start(1)] + json.dumps(assets, ensure_ascii=False, indent=2) + source[match.end(1):]
    planned = {loader: source.encode("utf-8")}

    compatibility = DIST / "sequences/index.html"
    source = text(compatibility)

    def legacy_key(match: re.Match) -> str:
        return match[1] + "?v=" + digest((compatibility.parent / match[1]).read_bytes())

    source, count = re.subn(r"([A-Za-z0-9_.-]+\.js)\?v=[a-f0-9]+", legacy_key, source)
    if count != 2:
        raise ValueError("Expected two historical-entry component references")
    planned[compatibility] = source.encode("utf-8")

    application = DIST / "index.html"
    source = text(application)
    loader_references = 0

    def application_key(match: re.Match) -> str:
        nonlocal loader_references
        prefix, name = match[1], match[2]
        if name.startswith("vendor/"):
            return match[0]  # Third-party provenance and pins are maintained separately.
        if name == "sequence-workbench.js":
            loader_references += 1
            data = planned[loader]
        else:
            data = component(name)
        return prefix + name + "?v=" + digest(data)

    source = re.sub(r"((?:src|href)=[\"'])([A-Za-z0-9_./-]+\.(?:js|css))(?:\?v=[a-f0-9]+)?(?=[\"'])",
                    application_key, source)
    if loader_references != 1:
        raise ValueError("Expected one sequence-workspace loader in the application")
    planned[application] = source.encode("utf-8")
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify current bytes without editing files")
    args = parser.parse_args()
    planned = expected_files()
    stale = [path for path, data in planned.items() if path.read_bytes() != data]
    if args.check:
        if stale:
            print("Stale sequence cache keys: " + ", ".join(path.relative_to(ROOT).as_posix() for path in stale))
            return 1
        print("PASS: sequence dependencies, compatibility entry and all application-owned JS/CSS cache keys; vendor references unchanged")
        return 0
    for path in stale:
        path.write_bytes(planned[path])
    print("Updated sequence cache references in " + str(len(stale)) + " file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
