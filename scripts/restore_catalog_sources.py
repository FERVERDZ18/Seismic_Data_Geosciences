"""Restore only the original CSVs required by the frozen catalogue checks.

The Mexico and North America manifests pin an immutable upstream Git revision,
byte counts, SHA-256 and Git blob IDs. Missing CSVs are downloaded only with
--download. Existing evidence is verified and never replaced. No catalogue is
rebuilt, no live service is queried and no public artifact is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Actronix09/fuentes-alternas"
COMMIT = "8fe055ffe635875f7290906d45f70562a7896621"
BASE_URL = f"https://raw.githubusercontent.com/Actronix09/fuentes-alternas/{COMMIT}/"
SOURCES = [
    ("data/source_manifest.json", "system/dist/data/manifest.json",
     "sismos-usgs/datos/usgs/mexico", "data/raw/usgs"),
    ("data/north_source_manifest.json", "system/dist/data/catalogs/usgs-na/manifest.json",
     "sismos-usgs/datos/usgs/norteamerica", "data/raw/catalogs/usgs-na"),
]


def checked_path(base, relative):
    name = PurePosixPath(relative)
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or name.is_absolute() or ".." in name.parts
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", relative)
            or name.suffix != ".csv" or name.as_posix() != relative):
        raise ValueError(f"Unexpected original CSV path: {relative}")
    target = (base / relative).resolve()
    target.relative_to(base.resolve())
    return target


def source_specs(root=ROOT):
    """Check the restore inventory against the already packaged source files."""
    specs = []
    seen = set()
    for source_path, package_path, upstream, destination in SOURCES:
        manifest = json.loads((root / source_path).read_bytes())
        if (manifest["snapshot_repository"] != REPOSITORY
                or manifest["snapshot_commit"] != COMMIT):
            raise ValueError("Only the declared immutable upstream revision may be restored")
        package = json.loads((root / package_path).read_bytes())
        packaged = {item["path"]: item for item in package["files"]}
        if len(packaged) != len(package["files"]):
            raise ValueError("Repeated packaged source CSV")
        original_paths = set()
        for item in manifest["files"]:
            relative = item["path"]
            target = checked_path(root / destination, relative)
            if target in seen or relative in original_paths:
                raise ValueError("Repeated original source CSV")
            seen.add(target)
            original_paths.add(relative)
            if (item["upstream_path"] != upstream + "/" + relative
                    or item["url"] != BASE_URL + item["upstream_path"]):
                raise ValueError("Unexpected original CSV download URL")
            if (type(item["bytes"]) is not int or item["bytes"] <= 0
                    or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                    or not re.fullmatch(r"[0-9a-f]{40}", item["git_blob_sha"])):
                raise ValueError("Missing original CSV size or checksum")
            retained = packaged.get(relative)
            if retained is None or any(retained.get(key) != item[key]
                                       for key in ["bytes", "sha256", "git_blob_sha", "url"]):
                raise ValueError("Original CSV manifest disagrees with the packaged catalogue")
            specs.append((target, item))
        if original_paths != set(packaged) or not original_paths:
            raise ValueError("Original CSV inventory differs from the packaged catalogue")
    return specs


def verify_bytes(raw, spec):
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if (len(raw) != spec["bytes"] or hashlib.sha256(raw).hexdigest() != spec["sha256"]
            or blob != spec["git_blob_sha"]):
        raise ValueError(f"Original CSV size or checksum mismatch: {spec['path']}")


def restore(root=ROOT, *, download=False):
    specs = source_specs(root)
    missing = []
    # Reject any changed existing input before contacting the network or writing.
    for target, spec in specs:
        if target.exists():
            verify_bytes(target.read_bytes(), spec)
        else:
            missing.append((target, spec))
    if missing and not download:
        raise FileNotFoundError(f"Missing {len(missing)} pinned CSVs; use --download to restore them")
    pending = []
    for target, spec in missing:
        request = Request(spec["url"], headers={"User-Agent": "SeismicDataGeosciences-Restore/1"})
        with urlopen(request, timeout=45) as response:
            if response.geturl() != spec["url"]:
                raise ValueError("Original CSV request redirected away from its immutable URL")
            raw = response.read(spec["bytes"] + 1)
        verify_bytes(raw, spec)
        pending.append((target, raw))
    # Validate every response before the first write; never replace evidence.
    for target, raw in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as stream:
                stream.write(raw)
        except FileExistsError:
            if target.read_bytes() != raw:
                raise ValueError(f"Refusing to replace different existing evidence: {target}")
    return {"snapshot_commit": COMMIT, "verified_csvs": len(specs),
            "restored_csvs": len(pending), "source_bytes": sum(item["bytes"] for _, item in specs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Restore missing CSVs from the pinned upstream revision")
    args = parser.parse_args()
    print(json.dumps(restore(download=args.download)))


if __name__ == "__main__":
    main()
