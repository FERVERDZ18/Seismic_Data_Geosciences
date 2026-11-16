"""Exact-source equality, not event matching; no input/output files are changed."""
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest

from scripts import exact_catalog_groups as exact


def usgs(identifier="shared", **updates):
    values = dict(time="2020-01-01T00:00:00Z", latitude="20.00", longitude="-100.00",
                  depth="", mag="4.0", magType="mw", nst="12", id=identifier,
                  type="earthquake", place="México")
    values.update(updates)
    return [values.get(field, "") for field in exact.USGS_FIELDS]


def record(catalog, identifier, cells, namespace="usgs-comcat"):
    return {"provider_namespace": namespace, "source_cells": cells[:],
            "member": {"catalog_id": catalog, "source_event_id": identifier,
                       "record_key": catalog + "~" + identifier, "source_file": "native.csv",
                       "source_file_sha256": exact.sha(b"native"), "source_row": 2}}


class ExactSourceGroups(unittest.TestCase):
    def test_exact_content_keys_and_members_are_order_independent(self):
        rows = [record("na", "shared", usgs()), record("mx", "shared", usgs())]
        before = deepcopy(rows)
        groups = exact.group_members(rows)
        self.assertEqual(groups, exact.group_members(list(reversed(rows))))
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["members"]), 2)
        self.assertEqual(len(groups[0]["signature"]), 64)
        self.assertEqual(rows, before)

    def test_same_id_changed_revision_or_omitted_column_is_not_exact(self):
        for change in [{"mag": "4.1"}, {"updated": "2026-11-15T00:00:00Z"},
                       {"nst": "13"}, {"gap": "90"}, {"dmin": "0.1"},
                       {"rms": "0.12"}, {"magNst": "8"}, {"place": "Elsewhere"}]:
            with self.subTest(change=change):
                self.assertEqual(exact.group_members([record("a", "shared", usgs()),
                    record("b", "shared", usgs(**change))]), [])

    def test_precision_missing_zero_and_unknown_are_distinct_strings(self):
        for change in [{"latitude": "20.0"}, {"mag": "4.00"}, {"depth": "0"},
                       {"depth": "unknown"}, {"nst": ""}]:
            with self.subTest(change=change):
                self.assertEqual(exact.group_members([record("a", "shared", usgs()),
                    record("b", "shared", usgs(**change))]), [])
        for token in ["unknown", "NaN", "Infinity", "0x10", "1_0"]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                exact.check_package_record({"id": "shared", "depth": None}, usgs(depth=token),
                                           ["id", "depth"], "native.csv", "usgs")
        self.assertIsNone(exact.number(""))
        self.assertEqual(exact.number("0"), 0)

    def test_different_source_ids_are_distinct_even_at_equal_time_and_position(self):
        self.assertEqual(exact.group_members([record("a", "first", usgs("first")),
            record("b", "second", usgs("second"))]), [])
        cells = usgs()
        self.assertNotEqual(exact.sha(exact.compact(["usgs-comcat", exact.USGS_FIELDS, cells])),
                            exact.sha(exact.compact(["ssn", exact.USGS_FIELDS, cells])))

    def test_native_nrcan_complete_cells_define_repeats_without_claiming_an_event_id(self):
        cells = ["1985-01-07T22:51:14+0000", "65.265", "-133.537", "18", "3.5", "ML", "AFTERSHOCK", "", ""]
        rows = [record("ca", "derived-1", cells, "nrcan-earthquakes-canada"),
                record("ca", "derived-2", cells, "nrcan-earthquakes-canada")]
        self.assertEqual(len(exact.group_members(rows)), 1)
        for index in [3, 7, 8]:
            changed = deepcopy(rows)
            changed[1]["source_cells"][index] += "x"
            self.assertEqual(exact.group_members(changed), [])

    def test_malformed_missing_and_duplicate_record_proof_fail_closed(self):
        for cells in [usgs()[:-1], [None] + usgs()[1:], usgs(identifier="")]:
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                exact.signature("usgs-comcat", exact.USGS_FIELDS, cells)
        with self.assertRaises(ValueError):
            exact.signature("ssn", exact.USGS_FIELDS, usgs())
        row = record("a", "shared", usgs())
        with self.assertRaises(ValueError):
            exact.group_members([row, row])

    def test_checksum_and_original_package_disagreement_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            path.write_bytes(b"native")
            spec = {"bytes": 6, "sha256": exact.sha(b"native")}
            self.assertEqual(exact.checked_file(path, spec), b"native")
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                exact.checked_file(path, spec)
        with self.assertRaisesRegex(ValueError, "Raw/package disagreement"):
            exact.check_package_record({"id": "shared", "mag": 4.5}, usgs(), ["id", "mag"], "native.csv", "usgs")

    def test_all_original_files_reproduce_the_sidecar_and_exact_totals(self):
        evidence = exact.build_evidence()
        self.assertEqual(exact.TARGET.read_bytes(), exact.compact(evidence))
        self.assertEqual(len(evidence["source_files"]), 60)
        self.assertEqual(evidence["stats"], {"input_records": 287936, "group_count": 285768,
            "collapsed_records": 2168, "multi_member_groups": 2168, "multi_member_records": 4336,
            "collapsed_by_namespace": {"nrcan-earthquakes-canada": 5, "usgs-comcat": 2163}})
        self.assertTrue(all(len(group["source_cells"]) == (22 if group["provider_namespace"] == "usgs-comcat" else 9)
                            for group in evidence["groups"]))


if __name__ == "__main__":
    unittest.main()
