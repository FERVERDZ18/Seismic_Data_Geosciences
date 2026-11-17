"""Restoration keeps frozen source bytes and fails before writing altered input."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import restore_catalog_sources as restore


class Response(io.BytesIO):
    def __init__(self, raw, url):
        super().__init__(raw)
        self.url = url

    def geturl(self):
        return self.url


class CatalogSourceRestoreTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="seismic-source-restore-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.content = {}
        for index, (source, package, upstream, _) in enumerate(restore.SOURCES):
            raw = b"id,place\r\n" + str(index).encode() + ",México\r\n".encode("utf-8")
            item = {"path": "original.csv", "upstream_path": upstream + "/original.csv",
                    "url": restore.BASE_URL + upstream + "/original.csv", "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "git_blob_sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
            manifest = {"snapshot_repository": restore.REPOSITORY,
                        "snapshot_commit": restore.COMMIT, "files": [item]}
            self.write_json(source, manifest)
            self.write_json(package, {"files": [item]})
            self.content[item["url"]] = raw

    def write_json(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")

    def mutate_manifest(self, callback, *, source=0, packaged=False):
        path = self.root / restore.SOURCES[source][1 if packaged else 0]
        value = json.loads(path.read_bytes())
        callback(value)
        self.write_json(path, value)

    def fetch(self, request, timeout):
        self.assertEqual(timeout, 45)
        return Response(self.content[request.full_url], request.full_url)

    def test_real_manifests_identify_every_missing_csv_from_one_immutable_revision(self):
        specs = restore.source_specs()
        self.assertEqual(len(specs), 58)
        self.assertEqual(sum(item["bytes"] for _, item in specs), 7049107)
        for path, item in specs:
            path.relative_to(restore.ROOT / "data/raw")
            self.assertTrue(item["url"].startswith(restore.BASE_URL))

    def test_clean_restore_is_byte_exact_and_second_pass_is_offline(self):
        with patch.object(restore, "urlopen", side_effect=self.fetch) as fetch:
            report = restore.restore(self.root, download=True)
            self.assertEqual(fetch.call_count, 2)
        self.assertEqual(report["restored_csvs"], 2)
        for target, item in restore.source_specs(self.root):
            self.assertEqual(target.read_bytes(), self.content[item["url"]])
        with patch.object(restore, "urlopen", side_effect=AssertionError("No HTTP")):
            self.assertEqual(restore.restore(self.root)["restored_csvs"], 0)

    def test_missing_csvs_require_explicit_download_without_writes(self):
        with patch.object(restore, "urlopen", side_effect=AssertionError("No HTTP")):
            with self.assertRaisesRegex(FileNotFoundError, "--download"):
                restore.restore(self.root)
        self.assertFalse((self.root / "data/raw").exists())

    def test_existing_altered_evidence_stops_before_network_and_is_preserved(self):
        target, _ = restore.source_specs(self.root)[1]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"human evidence")
        with patch.object(restore, "urlopen", side_effect=AssertionError("No HTTP")):
            with self.assertRaisesRegex(ValueError, "checksum"):
                restore.restore(self.root, download=True)
        self.assertEqual(target.read_bytes(), b"human evidence")
        self.assertFalse(restore.source_specs(self.root)[0][0].exists())

    def test_invalid_later_download_cannot_write_an_earlier_valid_csv(self):
        second = restore.source_specs(self.root)[1][1]
        self.content[second["url"]] += b"changed"
        with patch.object(restore, "urlopen", side_effect=self.fetch):
            with self.assertRaisesRegex(ValueError, "checksum"):
                restore.restore(self.root, download=True)
        self.assertFalse((self.root / "data/raw").exists())

    def test_a_different_redirect_cannot_supply_source_bytes(self):
        def redirected(request, timeout):
            return Response(self.content[request.full_url], "https://example.test/live.csv")
        with patch.object(restore, "urlopen", side_effect=redirected):
            with self.assertRaisesRegex(ValueError, "redirected"):
                restore.restore(self.root, download=True)
        self.assertFalse((self.root / "data/raw").exists())

    def test_unsafe_paths_moving_versions_and_inventory_drift_fail_closed(self):
        for path in ["../outside.csv", "/outside.csv", "C:/outside.csv", "a\\outside.csv", "a/../outside.csv"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                restore.checked_path(self.root, path)
        self.mutate_manifest(lambda value: value.update(snapshot_commit="main"))
        with self.assertRaisesRegex(ValueError, "immutable"):
            restore.source_specs(self.root)
        self.mutate_manifest(lambda value: value.update(snapshot_commit=restore.COMMIT))
        self.mutate_manifest(lambda value: value["files"][0].update(url="https://example.test/live.csv"))
        with self.assertRaisesRegex(ValueError, "URL"):
            restore.source_specs(self.root)

    def test_restore_inventory_must_match_packaged_scientific_input(self):
        self.mutate_manifest(lambda value: value["files"][0].update(sha256="0" * 64), packaged=True)
        with patch.object(restore, "urlopen", side_effect=AssertionError("No HTTP")):
            with self.assertRaisesRegex(ValueError, "disagrees"):
                restore.restore(self.root, download=True)


if __name__ == "__main__":
    unittest.main()
