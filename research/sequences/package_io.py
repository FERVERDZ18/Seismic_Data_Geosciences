"""Bounded, hash-checked package verification and new-workspace materialization.

This module uses only the Python standard library. It never contacts a network,
installs dependencies, imports numerical engines, or writes to a source checkout.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

SCHEMA = "seismic-science-package/1"
MAX_ARCHIVE_BYTES = 95_000_000  # strictly below the requested decimal100 MB
MAX_CHUNK_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")
SAFE = re.compile(r"[A-Za-z0-9_./-]+\Z")
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_name(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or not SAFE.fullmatch(value):
        raise ValueError(f"Unsafe package path: {value!r}")
    item = PurePosixPath(value)
    if item.is_absolute() or item.as_posix() != value or any(p in {".", "..", ""} for p in item.parts):
        raise ValueError(f"Non-canonical package path: {value!r}")
    for part in item.parts:
        if part.endswith((".", " ")) or part.split(".", 1)[0].upper() in RESERVED:
            raise ValueError(f"Unsupported portable filename: {value!r}")
    return item


def inside(base: Path, relative: str) -> Path:
    item = relative_name(relative)
    base = base.resolve()
    target = base.joinpath(*item.parts)
    # Refuse existing symlink parents even when they happen to point inward.
    cursor = base
    for part in item.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Symlink in package/materialization path: {relative}")
    target.resolve().relative_to(base)
    return target


def manifest(package: Path, *, allow_private_partial=False) -> dict:
    path = package / "MANIFEST.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    permitted = {"SEALED", "SEALED_PRIVATE_PARTIAL"} if allow_private_partial else {"SEALED"}
    if value.get("schema") != SCHEMA or value.get("status") not in permitted:
        raise ValueError("Package is not sealed. Private draft staging is not a scientific release.")
    if not isinstance(value.get("files"), list) or not isinstance(value.get("blobs"), dict):
        raise ValueError("Incomplete package manifest")
    names, portable_names, total = set(), set(), 0
    for record in value["files"]:
        name = relative_name(record["logical_path"]).as_posix()
        if not name.startswith(("source_layout/", "expected/")):
            raise ValueError("Logical inputs must be source_layout/ or expected/")
        if name in names or name.casefold() in portable_names:
            raise ValueError(f"Duplicate or case-ambiguous logical path: {name}")
        names.add(name); portable_names.add(name.casefold())
        if type(record.get("bytes")) is not int or record["bytes"] < 0 or not HEX.fullmatch(record.get("sha256", "")):
            raise ValueError("Invalid file size/hash")
        total += record["bytes"]
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Package exceeds the reviewed default materialization budget")
        kind = record.get("storage")
        if kind == "plain":
            relative_name(record["package_path"])
        elif kind == "blob":
            if record.get("blob") != record["sha256"] or record["blob"] not in value["blobs"]:
                raise ValueError("Missing content-addressed blob")
        else:
            raise ValueError("Unknown storage mode")
    return value


def _chunk(package: Path, spec: dict) -> bytes:
    if type(spec.get("bytes")) is not int or not 0 <= spec["bytes"] <= MAX_CHUNK_BYTES:
        raise ValueError("Unbounded data chunk")
    if not HEX.fullmatch(spec.get("sha256", "")):
        raise ValueError("Invalid chunk hash")
    archive = inside(package, spec["archive"])
    if not archive.is_file() or archive.stat().st_size >= MAX_ARCHIVE_BYTES:
        raise ValueError("Missing or oversized data archive")
    member = relative_name(spec["member"]).as_posix()
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        if len({x.filename for x in infos}) != len(infos):
            raise ValueError("Duplicate ZIP members")
        info = source.getinfo(member)
        if stat.S_ISLNK(info.external_attr >> 16) or info.file_size != spec["bytes"]:
            raise ValueError("Unexpected ZIP member type/size")
        with source.open(info) as stream:
            raw = stream.read(spec["bytes"] + 1)
    if len(raw) != spec["bytes"] or hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        raise ValueError("Frozen data chunk failed verification")
    return raw


def file_blocks(package: Path, value: dict, record: dict):
    if record["storage"] == "plain":
        path = inside(package, record["package_path"])
        if not path.is_file() or path.stat().st_size != record["bytes"]:
            raise ValueError(f"Missing/changed readable source: {record['logical_path']}")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                yield block
    else:
        spec = value["blobs"][record["blob"]]
        if spec.get("bytes") != record["bytes"]:
            raise ValueError("Blob/file size disagrees")
        for part in spec["chunks"]:
            yield _chunk(package, part)


def verify(package: Path, *, allow_private_partial=False) -> dict:
    package = package.resolve()
    value = manifest(package, allow_private_partial=allow_private_partial)
    allowed = {"MANIFEST.json"}
    allowed.update(r["package_path"] for r in value["files"] if r["storage"] == "plain")
    allowed.update(r["path"] for r in value.get("package_files", []))
    for record in value.get("archives", []):
        path = inside(package, record["path"])
        allowed.add(record["path"])
        if not path.is_file() or path.stat().st_size != record["bytes"] or path.stat().st_size >= MAX_ARCHIVE_BYTES or sha_file(path) != record["sha256"]:
            raise ValueError("Missing, changed or oversized frozen data archive")
    for path in package.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are excluded from the reviewed package")
        if path.is_file() and path.relative_to(package).as_posix() not in allowed:
            raise ValueError("Unlisted file in reviewed package: " + path.relative_to(package).as_posix())
    checked = set()
    for record in value["files"]:
        # One hash per identical content blob; readable duplicates are checked too.
        identity = (record["storage"], record.get("package_path", record["sha256"]))
        if identity in checked:
            continue
        digest, count = hashlib.sha256(), 0
        for block in file_blocks(package, value, record):
            digest.update(block); count += len(block)
        if count != record["bytes"] or digest.hexdigest() != record["sha256"]:
            raise ValueError(f"File verification failed: {record['logical_path']}")
        checked.add(identity)
    for record in value.get("package_files", []):
        path = inside(package, record["path"])
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha_file(path) != record["sha256"]:
            raise ValueError(f"Package helper changed: {record['path']}")
    return value


def new_workspace(package: Path, target: Path) -> Path:
    package, target = package.resolve(), target.resolve()
    if target.exists():
        raise FileExistsError("A new workspace path is required; existing folders are never reused or deleted")
    if target == package or target.is_relative_to(package) or package.is_relative_to(target):
        raise ValueError("Workspace must be independent of the package source tree")
    for ancestor in (target.parent, *target.parents):
        if (ancestor / ".git").exists():
            raise ValueError("Materialization inside a Git checkout is refused")
    target.mkdir(parents=True, exist_ok=False)
    return target


def materialize(package: Path, target: Path, *, omit_groups=(), omit_prefixes=(), allow_private_partial=False) -> dict:
    value = verify(package, allow_private_partial=allow_private_partial)
    target = new_workspace(package, target)
    omitted, written = [], []
    for record in value["files"]:
        if (set(record.get("groups", [])) & set(omit_groups)
                or any(record["logical_path"].startswith(prefix) for prefix in omit_prefixes)):
            omitted.append(record["logical_path"]); continue
        destination = inside(target, record["logical_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest, count = hashlib.sha256(), 0
        with destination.open("xb") as stream:
            for block in file_blocks(package, value, record):
                stream.write(block); digest.update(block); count += len(block)
        if digest.hexdigest() != record["sha256"] or count != record["bytes"]:
            raise ValueError("Materialized content changed")
        written.append(record["logical_path"])
    project = target / "source_layout"
    project.mkdir(exist_ok=True)
    # Compatibility sentinel only in this newly created independent workspace.
    # No real AGENTS/context content is copied or served.
    (project / "AGENTS.md").write_text(
        "# Generated scientific replay sentinel\n"
        "This new workspace uses this empty-content routing marker only.\n"
        "It contains no project instructions, private context or publication permission.\n",
        encoding="utf-8")
    receipt = dict(schema="science-materialization/1", manifest_sha256=sha_file(package / "MANIFEST.json"),
                   written=written, omitted=omitted, generated_sentinel="source_layout/AGENTS.md",
                   private_original_checkout_required=False)
    (target / "MATERIALIZATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
