"""Catalogue link policies tested with temporary synthetic data and no HTTP."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_links


class CatalogueLinkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="seismic-link-policy-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.dist = self.root / "system/dist"
        self.dist.mkdir(parents=True)
        self.catalogs = []
        self.usgs = self.catalog("usgs-fixture", "usgs", ["us-fixture-1"])
        self.canada = self.catalog("nrcan-fixture", "nrcan", ["nrcan-local-0123456789abcdef01234567-1", "nrcan-local-0123456789abcdef01234567-2"], derived=True)
        self.registry()
        self.app = self.dist / "app.js"
        self.app.write_text("", encoding="utf-8")
        for name, value in [("ROOT", self.root), ("DIST", self.dist)]:
            replacement = patch.object(check_links, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        source_paths = patch.object(check_links, "source_paths", return_value=[self.app])
        source_paths.start()
        self.addCleanup(source_paths.stop)
        self.http = patch.object(check_links, "urlopen", side_effect=AssertionError("No real HTTP is allowed in these tests"))
        self.urlopen = self.http.start()
        self.addCleanup(self.http.stop)

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        path.write_bytes(raw)
        return check_links.digest(raw)

    def catalog(self, name, provider, identifiers, derived=False):
        directory = self.dist / "data/catalogs" / name
        data = {"fields": ["id", "file", "net", "time"],
                "rows": [[identifier, "input.csv", "", "2000-01-01T00:00:00Z"] for identifier in identifiers]}
        events_hash = self.write_json(directory / "events.json", data)
        manifest = {"files": [{"path": "input.csv", "url": "https://example.test/original.csv"}],
                    "derived_asset_sha256": events_hash}
        catalog = {"id": name, "provider": provider,
                   "events_url": f"data/catalogs/{name}/events.json",
                   "manifest_url": f"data/catalogs/{name}/manifest.json", "sha256": events_hash}
        if derived:
            catalog["identifier_kind"] = manifest["identifier_kind"] = "derived_row_key"
        catalog["manifest_sha256"] = self.write_json(directory / "manifest.json", manifest)
        self.catalogs.append(catalog)
        return catalog

    def registry(self):
        self.write_json(self.dist / "data/catalogs.json", {"catalogs": self.catalogs, "default_catalog_id": self.usgs["id"]})

    def test_loopback_preview_examples_do_not_exempt_application_navigation(self):
        readme = self.root / "README.md"
        readme.write_text("Local preview: http://127.0.0.1:8787/\n", encoding="utf-8")
        self.app.write_text("const wrongPublicLink='http://127.0.0.1:8787/';", encoding="utf-8")
        with patch.object(check_links, "source_paths", return_value=[readme, self.app]):
            external, _, _, _, notes = check_links.collect_links("all")
        self.assertEqual(external["http://127.0.0.1:8787/"], {"system/dist/app.js"})
        self.assertEqual([entry["source"] for entry in notes], ["README.md"])

    def test_parameterized_reverse_lookup_is_a_template_without_service_validation(self):
        tools = self.dist / "map-tools.js"
        tools.write_text("const url=new URL('https://nominatim.openstreetmap.org/reverse');"
                         "url.search=new URLSearchParams({format:'jsonv2',lat:String(p.lat),"
                         "lon:String(((p.lng+180)%360+360)%360-180),zoom:'10',"
                         "'accept-language':en()?'en':'es'});", encoding="utf-8")
        with patch.object(check_links, "source_paths", return_value=[tools]):
            external, _, templates, _, _ = check_links.collect_links("artifact")
        self.assertNotIn("https://nominatim.openstreetmap.org/reverse", external)
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["classification"], "template_reverse_geocoder")
        self.assertEqual(templates[0]["required_parameters"], ["format", "lat", "lon", "zoom"])
        self.assertIn("does not verify service availability", templates[0]["status"])
        self.urlopen.assert_not_called()

    def test_reverse_template_does_not_exempt_literal_links_other_paths_or_missing_parameters(self):
        base = "https://nominatim.openstreetmap.org/reverse"
        readme = self.root / "README.md"
        readme.write_text("Service link: " + base, encoding="utf-8")
        tools = self.dist / "map-tools.js"
        tools.write_text("\n".join([
            "const literal='" + base + "';",
            "const url=new URL('" + base + "');url.search=new URLSearchParams({format:'jsonv2',zoom:'10'});",
            "const url=new URL('" + base + "-other');url.search=new URLSearchParams({format:'jsonv2',lat:String(p.lat),lon:String(((p.lng+180)%360+360)%360-180),zoom:'10','accept-language':en()?'en':'es'});",
        ]), encoding="utf-8")
        other_source = self.dist / "unrelated-map-tools.js"
        other_source.write_text("const url=new URL('" + base + "');url.search=new URLSearchParams({format:'jsonv2',lat:String(p.lat),lon:String(((p.lng+180)%360+360)%360-180),zoom:'10','accept-language':en()?'en':'es'});", encoding="utf-8")
        with patch.object(check_links, "source_paths", return_value=[tools, readme, other_source]):
            external, _, templates, _, _ = check_links.collect_links("all")
        self.assertEqual(external[base], {"README.md", "system/dist/map-tools.js", "system/dist/unrelated-map-tools.js"})
        self.assertEqual(external[base + "-other"], {"system/dist/map-tools.js"})
        self.assertEqual(templates, [])
        self.urlopen.assert_not_called()

    def test_canadian_derived_keys_never_generate_usgs_routes_in_any_mode(self):
        for mode in ["none", "sample", "all"]:
            with self.subTest(mode=mode):
                inventory, routes = check_links.event_routes(mode)
                self.assertEqual(inventory["malformed_event_ids"], [])
                canadian = next(c for c in inventory["catalogues"] if c["provider"] == "nrcan")
                self.assertEqual(canadian["records"], 2)
                self.assertEqual(canadian["sampled_or_selected_event_routes"], 0)
                self.assertFalse(any("nrcan-local" in route for route in routes))
                self.assertEqual(routes, [] if mode == "none" else ["https://earthquake.usgs.gov/earthquakes/eventpage/us-fixture-1"])
        self.urlopen.assert_not_called()

    def test_derived_identity_blocks_routes_even_if_provider_is_mislabelled(self):
        # A provider-label mistake cannot turn a local record key into an agency ID.
        self.canada["provider"] = "usgs"
        self.registry()
        _, routes = check_links.event_routes("all")
        self.assertEqual(routes, ["https://earthquake.usgs.gov/earthquakes/eventpage/us-fixture-1"])

    def test_native_ssn_observed_http_landing_is_provenance_not_an_event_route(self):
        ssn = self.catalog("ssn-fixture", "ssn", ["ssn-local-0123456789abcdef01234567-1"], derived=True)
        path = self.dist / ssn["manifest_url"]
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["files"][0].update(url="http://www2.ssn.unam.mx:8080/catalogo/", url_kind="catalogue_landing")
        manifest["files"][0]["public_copy_path"] = "research-data/catalogs/ssn-mx/input.csv"
        self.write_json(path, manifest); self.registry()
        self.app.write_text("const publicRawURL = publicCopy ? 'https://github.com/gabrielhuav/Seismic_Data_Geosciences/blob/main/'+publicCopy.split('/').map(encodeURIComponent).join('/') : '';", encoding="utf-8")
        external, *_ = check_links.collect_links("artifact")
        self.assertNotIn("https://github.com/gabrielhuav/Seismic_Data_Geosciences/blob/main/", external)
        self.assertIn("https://github.com/gabrielhuav/Seismic_Data_Geosciences/blob/main/research-data/catalogs/ssn-mx/input.csv", external)
        inventory, routes = check_links.event_routes("all")
        self.assertEqual(inventory["unmapped_raw_csv_files"], [])
        self.assertFalse(any("ssn-local" in route for route in routes))
        # Other HTTP URLs or missing identity/landing classifications are not
        # accepted by this narrow source-specific provenance rule.
        manifest["files"][0]["url"] = "http://example.test/unverified.csv"
        self.write_json(path, manifest)
        inventory, _ = check_links.event_routes("all")
        self.assertIn("ssn-fixture:input.csv", inventory["unmapped_raw_csv_files"])

    def test_manifest_derived_identity_also_blocks_routes_without_registry_flag(self):
        self.canada["provider"] = "usgs"
        del self.canada["identifier_kind"]
        self.registry()
        _, routes = check_links.event_routes("all")
        self.assertEqual(routes, ["https://earthquake.usgs.gov/earthquakes/eventpage/us-fixture-1"])

    def test_registry_integrity_detects_changed_event_and_manifest_bytes(self):
        before = check_links.privacy_and_integrity()
        self.assertEqual(before["privacy_failures"], [])
        self.assertTrue(all(c["ok"] for c in before["integrity_checks"]))
        for path_key in ["events_url", "manifest_url"]:
            with self.subTest(asset=path_key):
                target = self.dist / self.canada[path_key]
                original = target.read_bytes()
                target.write_bytes(original + b"\n")
                checked = check_links.privacy_and_integrity()
                failed = [c["check"] for c in checked["integrity_checks"] if not c["ok"]]
                self.assertIn(self.canada["id"] + ": " + path_key, failed)
                target.write_bytes(original)
        self.urlopen.assert_not_called()

    def test_tile_and_event_templates_are_inventoried_without_bulk_http(self):
        self.app.write_text("\n".join([
            "const osm='https://tile.openstreetmap.org/{z}/{x}/{y}.png';",
            "const tiles=`https://example.test/tiles/${z}/${x}/${y}.png`;",
            "const event=`https://earthquake.usgs.gov/earthquakes/eventpage/${event_id}`;",
            "const current='https://earthquake.usgs.gov/earthquakes/eventpage/' + encodeURIComponent(e.id);",
            "const policy='https://example.test/policy';",
        ]), encoding="utf-8")
        checked = []

        def check(url):
            checked.append(url)
            return {"url": url, "ok": True, "status": 200}

        with patch.object(check_links, "check_url", side_effect=check), patch("sys.argv", ["check_links.py", "--network", "--scope", "artifact", "--dynamic-events", "none"]), redirect_stdout(io.StringIO()):
            self.assertEqual(check_links.main(), 0)
        report = json.loads((self.root / "outputs/links/report_network.json").read_text(encoding="utf-8"))
        self.assertEqual(checked, ["https://example.test/policy"])
        self.assertEqual(len(report["url_templates"]), 4)
        self.assertEqual(report["dynamic_events"]["route_count"], 0)
        self.assertFalse(report["generated_event_links_exhaustively_checked"])
        self.urlopen.assert_not_called()


class AdditionalManuscriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="seismic-article-links-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.dist = self.root / "system/dist"
        self.dist.mkdir(parents=True)
        self.app = self.dist / "app.js"
        self.app.write_text("const source='https://example.test/system';", encoding="utf-8")
        self.old = self.root / "paper/drafts/manuscript.md"
        self.old.parent.mkdir(parents=True)
        self.old.write_text("Original: https://example.test/v0\n", encoding="utf-8")
        self.current = self.root / "outputs/reviewed_revision/manuscript.md"
        self.current.parent.mkdir(parents=True)
        self.current.write_text("Current: https://example.test/revised\n[Figure](case.svg)\n", encoding="utf-8")
        (self.current.parent / "case.svg").write_text("<svg/>", encoding="utf-8")
        for name, value in [("ROOT", self.root), ("DIST", self.dist)]:
            replacement = patch.object(check_links, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        http = patch.object(check_links, "urlopen", side_effect=AssertionError("No real HTTP is allowed in these tests"))
        self.urlopen = http.start()
        self.addCleanup(http.stop)

    def test_current_article_adds_urls_bytes_and_hash_without_replacing_default_sources(self):
        selected = check_links.source_paths("all", [self.current])
        self.assertIn(self.old, selected)
        self.assertIn(self.app, selected)
        self.assertIn(self.current, selected)
        external, local, _, sources, _ = check_links.collect_links("all", [self.current])
        self.assertIn("https://example.test/v0", external)
        self.assertIn("https://example.test/system", external)
        self.assertEqual(external["https://example.test/revised"], {"outputs/reviewed_revision/manuscript.md"})
        entry = next(item for item in sources if item["path"] == "outputs/reviewed_revision/manuscript.md")
        raw = self.current.read_bytes()
        self.assertEqual(entry["bytes"], len(raw))
        self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIn({"source": entry["path"], "link": "case.svg", "ok": True, "reason": "exists"}, local)
        self.urlopen.assert_not_called()

    def test_repeatable_cli_records_each_explicit_article_and_checks_uppercase_markdown(self):
        second = self.current.parent / "second.MD"
        second.write_text("[Missing case](missing.svg)\nhttps://example.test/second\n", encoding="utf-8")
        argv = ["check_links.py", "--scope", "all", "--manuscript", str(self.current.relative_to(self.root)),
                "--manuscript", str(second), "--manuscript", str(self.current)]
        artifact = {"inventory": [], "privacy_failures": [], "integrity_checks": []}
        dynamic = {"malformed_event_ids": [], "unmapped_raw_csv_files": []}
        with patch("sys.argv", argv), patch.object(check_links, "privacy_and_integrity", return_value=artifact), \
                patch.object(check_links, "event_routes", return_value=(dynamic, [])), redirect_stdout(io.StringIO()):
            self.assertEqual(check_links.main(), 1)  # Extra sources cannot hide a local failure.
        report = json.loads((self.root / "outputs/links/report_local.json").read_text(encoding="utf-8"))
        self.assertEqual(report["additional_manuscripts"], ["outputs/reviewed_revision/manuscript.md", "outputs/reviewed_revision/second.MD"])
        self.assertEqual(report["failed_local"], 1)
        self.assertIn("https://example.test/v0", {item["url"] for item in report["literal_external_inventory"]})
        self.assertIn("https://example.test/second", {item["url"] for item in report["literal_external_inventory"]})
        self.assertFalse(report["network_checked"])
        self.urlopen.assert_not_called()

    def test_outside_existing_article_is_rejected_before_collection_or_network(self):
        outside_directory = tempfile.TemporaryDirectory(prefix="seismic-other-workspace-")
        self.addCleanup(outside_directory.cleanup)
        outside = Path(outside_directory.name) / "unrelated.md"
        outside.write_text("This belongs to another workspace.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside this repository"):
            check_links.source_paths("all", [outside])
        with patch("sys.argv", ["check_links.py", "--network", "--manuscript", str(outside)]), \
                patch.object(check_links, "collect_links") as collect, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as error:
            check_links.main()
        self.assertEqual(error.exception.code, 2)
        collect.assert_not_called()
        self.urlopen.assert_not_called()

    def test_missing_non_markdown_and_directory_arguments_cannot_be_silently_dropped(self):
        wrong_suffix = self.current.with_suffix(".txt")
        wrong_suffix.write_text("Not an article Markdown", encoding="utf-8")
        directory = self.current.parent / "folder.md"
        directory.mkdir()
        for path in [self.current.parent / "missing.md", wrong_suffix, directory]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "existing Markdown"):
                check_links.source_paths("artifact", [self.current, path])
        self.urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
