"""Behavioural tests using explicitly synthetic GeoJSON and no network access."""

from copy import deepcopy
from datetime import datetime
import hashlib
from itertools import permutations
import json
import unittest

from scripts.evidence_contract import (
    REQUIRED_ASSUMPTIONS,
    historical_catalog_not_identifiable,
    retained_projection_conditional,
    snapshot_observed,
    synthetic_nonidentifiability_witnesses,
    validate_synthetic_witness,
)


def epoch(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def product(when, magnitude, *, source="us", code="synthetic-A", status="UPDATE", author="us"):
    return {
        "source": source, "type": "origin", "code": code,
        "id": f"synthetic:{source}:origin:{code}:{epoch(when)}",
        "updateTime": epoch(when), "status": status, "preferredWeight": 1,
        "properties": {
            "eventtime": "2020-01-01T00:00:00Z", "magnitude": str(magnitude),
            "magnitude-type": "mw", "latitude": "16", "longitude": "-96",
            "depth": "10", "origin-source": author, "event-type": "earthquake",
        },
    }


def event(*products, identifier="synthetic-A", magnitude=5.6):
    return {
        "type": "Feature", "id": identifier,
        "geometry": {"type": "Point", "coordinates": [-96, 16, 10]},
        "properties": {
            "time": epoch("2020-01-01T00:00:00Z"), "mag": magnitude,
            "magType": "mw", "type": "earthquake", "net": "us",
            "updated": epoch("2026-01-01T00:00:00Z"),
            "products": {"origin": list(products)},
        },
    }


def blob(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


ACK = list(REQUIRED_ASSUMPTIONS)
RETRIEVED = "2026-11-05T18:00:00Z"
CUTOFF = "2020-01-02T00:00:00Z"


class ObservedSnapshotTests(unittest.TestCase):
    def test_current_summary_is_not_replaced_with_retained_origin(self):
        raw = blob(event(product("2020-01-01T00:01:00Z", 4.0), magnitude=5.6))
        result = snapshot_observed(raw, RETRIEVED, {"min_magnitude": 5.5})
        self.assertEqual(result["contract"], "snapshot_observed")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["records"][0]["magnitude"], 5.6)
        self.assertFalse(result["historical_publication_reconstructed"])
        self.assertEqual(result["retrieved_at_utc"], RETRIEVED)

    def test_hash_covers_original_bytes_and_verification_fails_on_change(self):
        raw = blob(event())
        digest = hashlib.sha256(raw).hexdigest()
        result = snapshot_observed(raw, RETRIEVED, expected_sha256=digest)
        self.assertEqual(result["evidence_sha256"], digest)
        with self.assertRaises(ValueError):
            snapshot_observed(raw + b" ", RETRIEVED, expected_sha256=digest)
        with self.assertRaises(TypeError):
            snapshot_observed(event(), RETRIEVED)

    def test_query_interval_is_half_open(self):
        raw = blob(event())
        at_start = {"start_time_utc": "2020-01-01T00:00:00Z", "end_time_utc": "2020-01-02T00:00:00Z"}
        at_end = {"start_time_utc": "2019-12-31T00:00:00Z", "end_time_utc": "2020-01-01T00:00:00Z"}
        self.assertEqual(snapshot_observed(raw, RETRIEVED, at_start)["count"], 1)
        self.assertEqual(snapshot_observed(raw, RETRIEVED, at_end)["count"], 0)

    def test_missing_magnitude_stays_unknown(self):
        raw = blob(event(magnitude=None))
        unfiltered = snapshot_observed(raw, RETRIEVED)
        self.assertIsNone(unfiltered["records"][0]["magnitude"])
        self.assertEqual(snapshot_observed(raw, RETRIEVED, {"min_magnitude": 0})["count"], 0)

    def test_mag_type_is_never_silently_homogenized(self):
        payload = event()
        payload["properties"]["magType"] = "mb"
        result = snapshot_observed(blob(payload), RETRIEVED, {"magnitude_types": ["mw"]})
        self.assertEqual(result["count"], 0)

    def test_bad_query_and_unzoned_time_fail(self):
        for query in ({"asofdate": CUTOFF}, {"min_magnitude": True}, {"min_longitude": 170, "max_longitude": -170}):
            with self.assertRaises(ValueError):
                snapshot_observed(blob(event()), RETRIEVED, query)
        with self.assertRaises(ValueError):
            snapshot_observed(blob(event()), "2026-11-05T12:00:00")

    def test_duplicate_event_id_is_not_counted_twice(self):
        payload = {"type": "FeatureCollection", "features": [event(), event()]}
        with self.assertRaises(ValueError):
            snapshot_observed(blob(payload), RETRIEVED)

    def test_nonstandard_nan_is_rejected(self):
        raw = blob(event()).replace(b'"mag": 5.6', b'"mag": NaN')
        with self.assertRaises(ValueError):
            snapshot_observed(raw, RETRIEVED)


class ConditionalProjectionTests(unittest.TestCase):
    def test_latest_retained_version_is_selected_before_filtering(self):
        raw = blob(event(
            product("2020-01-01T00:01:00Z", 6.0),
            product("2020-01-01T01:00:00Z", 4.0),
            product("2020-01-03T00:00:00Z", 7.0),
        ))
        result = retained_projection_conditional(raw, CUTOFF, ACK, query={"min_magnitude": 5.5})
        self.assertEqual(result["active_lineage_count_before_query"], 1)
        self.assertEqual(result["selected_lineage_count"], 0)
        self.assertFalse(result["preferred_origin_reconstructed"])

    def test_version_at_cutoff_is_included(self):
        raw = blob(event(product(CUTOFF, 5.6)))
        result = retained_projection_conditional(raw, CUTOFF, ACK)
        self.assertEqual(result["selected_lineage_count"], 1)

    def test_multiple_sources_remain_multiple_lineages(self):
        raw = blob(event(
            product("2020-01-01T01:00:00Z", 5.6),
            product("2020-01-01T01:00:00Z", 5.2, source="other", author="other"),
        ))
        result = retained_projection_conditional(raw, CUTOFF, ACK)
        self.assertEqual(result["selected_lineage_count"], 2)
        self.assertEqual(result["count_unit"], "retained_product_lineages_not_unique_earthquakes")
        self.assertNotIn("count", result)

    def test_product_distributor_is_separate_from_origin_author(self):
        raw = blob(event(product("2020-01-01T01:00:00Z", 5.6, author="iscgem")))
        row = retained_projection_conditional(raw, CUTOFF, ACK)["records"][0]
        self.assertEqual(row["lineage"]["product_source"], "us")
        self.assertEqual(row["origin_source"], "iscgem")

    def test_latest_delete_does_not_resurrect_previous_version(self):
        deleted = product("2020-01-01T02:00:00Z", 5.6, status="DELETE")
        deleted["properties"] = {}
        raw = blob(event(product("2020-01-01T01:00:00Z", 5.6), deleted))
        result = retained_projection_conditional(raw, CUTOFF, ACK)
        self.assertEqual(result["active_lineage_count_before_query"], 0)
        self.assertEqual(len(result["retained_deletions"]), 1)

    def test_projection_requires_all_explicit_assumptions(self):
        for assumptions in ([], ACK[:-1], [*ACK, "independent_sources"], "yes"):
            with self.assertRaises(ValueError):
                retained_projection_conditional(blob(event()), CUTOFF, assumptions)

    def test_conflicting_same_version_fails_without_tiebreak(self):
        first = product("2020-01-01T01:00:00Z", 5.6)
        second = deepcopy(first)
        second["properties"]["magnitude"] = "5.7"
        with self.assertRaises(ValueError):
            retained_projection_conditional(blob(event(first, second)), CUTOFF, ACK)

    def test_superseded_conflicting_version_fails_for_every_product_order(self):
        old_a = product("2020-01-01T01:00:00Z", 5.6)
        old_b = deepcopy(old_a)
        old_b["properties"]["magnitude"] = "5.7"
        newer = product("2020-01-01T02:00:00Z", 6.0)
        for order in permutations([old_a, newer, old_b]):
            with self.subTest(order=[p["properties"]["magnitude"] for p in order]):
                with self.assertRaisesRegex(ValueError, "Conflicting retained bytes"):
                    retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_superseded_identical_copies_are_order_independent(self):
        old = product("2020-01-01T01:00:00Z", 5.6)
        newer = product("2020-01-01T02:00:00Z", 6.0)
        expected = None
        for order in permutations([old, newer, deepcopy(old)]):
            result = retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)
            self.assertEqual(result["retained_versions_considered"], 3)
            self.assertEqual(result["records"][0]["magnitude"], 6.0)
            if expected is None:
                expected = result["records"]
            self.assertEqual(result["records"], expected)

    def test_full_product_conflict_is_not_reduced_to_projected_measurements(self):
        old_a = product("2020-01-01T01:00:00Z", 5.6)
        newer = product("2020-01-01T02:00:00Z", 6.0)
        for field in ("equivalent_numeric_spelling", "unused_metadata"):
            old_b = deepcopy(old_a)
            if field == "equivalent_numeric_spelling":
                old_b["properties"]["magnitude"] = "5.60"
            else:
                old_b["preferredWeight"] = 2
            for order in permutations([old_a, newer, old_b]):
                with self.subTest(field=field, order=[p["id"] for p in order]):
                    with self.assertRaisesRegex(ValueError, "Conflicting retained bytes"):
                        retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_conflicts_after_cutoff_are_validated_before_temporal_selection(self):
        earlier = product("2020-01-01T01:00:00Z", 5.6)
        future_a = product("2020-01-03T01:00:00Z", 6.0)
        future_b = deepcopy(future_a)
        future_b["properties"]["magnitude"] = "6.1"
        for order in permutations([earlier, future_a, future_b]):
            with self.subTest(order=[p["properties"]["magnitude"] for p in order]):
                with self.assertRaisesRegex(ValueError, "Conflicting retained bytes"):
                    retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_missing_version_time_cannot_be_hidden_by_newer_product_order(self):
        missing = product("2020-01-01T01:00:00Z", 5.6)
        newer = product("2020-01-01T02:00:00Z", 6.0)
        for absent in (False, True):
            bad = deepcopy(missing)
            if absent:
                del bad["updateTime"]
            else:
                bad["updateTime"] = None
            for order in permutations([bad, newer]):
                with self.subTest(absent=absent, missing_first=order[0] is bad):
                    with self.assertRaisesRegex(ValueError, "Missing product updateTime"):
                        retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_equal_version_update_delete_conflict_fails_in_every_order(self):
        update = product("2020-01-01T01:00:00Z", 5.6)
        deleted = deepcopy(update)
        deleted["status"] = "DELETE"
        deleted["properties"] = {}
        newer = product("2020-01-01T02:00:00Z", 6.0)
        for order in permutations([update, newer, deleted]):
            with self.subTest(order=[p["status"] for p in order]):
                with self.assertRaisesRegex(ValueError, "Conflicting retained bytes"):
                    retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_duplicate_delete_retains_authentic_payload_without_resurrection(self):
        old = product("2020-01-01T01:00:00Z", 5.6)
        deleted = product("2020-01-01T02:00:00Z", 5.7, status="DELETE")
        # Existing output semantics preserve supplied DELETE properties as evidence.
        for order in permutations([old, deleted, deepcopy(deleted)]):
            result = retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)
            self.assertEqual(result["records"], [])
            self.assertEqual(len(result["retained_deletions"]), 1)
            self.assertEqual(result["retained_deletions"][0]["magnitude"], 5.7)

    def test_delete_payload_difference_is_not_normalized_away(self):
        first = product("2020-01-01T01:00:00Z", 5.6, status="DELETE")
        second = deepcopy(first)
        second["properties"]["magnitude"] = "5.7"
        newer = product("2020-01-01T02:00:00Z", 6.0)
        for order in permutations([first, newer, second]):
            with self.subTest(order=[p["properties"]["magnitude"] for p in order]):
                with self.assertRaisesRegex(ValueError, "Conflicting retained bytes"):
                    retained_projection_conditional(blob(event(*order)), CUTOFF, ACK)

    def test_future_cross_event_association_is_not_hidden_by_cutoff_or_event_order(self):
        earlier = product("2020-01-01T01:00:00Z", 5.6)
        future = product("2020-01-03T01:00:00Z", 6.0)
        for features in permutations([event(earlier), event(future, identifier="synthetic-B")]):
            with self.subTest(event_order=[e["id"] for e in features]):
                raw = blob({"type": "FeatureCollection", "features": features})
                with self.assertRaisesRegex(ValueError, "multiple captured event IDs"):
                    retained_projection_conditional(raw, CUTOFF, ACK)

    def test_product_under_two_event_ids_requires_association_resolution(self):
        same = product("2020-01-01T01:00:00Z", 5.6)
        raw = blob({"type": "FeatureCollection", "features": [event(same), event(same, identifier="synthetic-B")]})
        with self.assertRaises(ValueError):
            retained_projection_conditional(raw, CUTOFF, ACK)

    def test_unknown_status_is_not_assumed_active(self):
        incomplete = product("2020-01-01T01:00:00Z", 5.6)
        del incomplete["status"]
        with self.assertRaises(ValueError):
            retained_projection_conditional(blob(event(incomplete)), CUTOFF, ACK)
        unrecognized = product("2020-01-01T01:00:00Z", 5.6, status="UNRECOGNIZED")
        with self.assertRaises(ValueError):
            retained_projection_conditional(blob(event(unrecognized)), CUTOFF, ACK)


class NonidentifiabilityTests(unittest.TestCase):
    def test_superseded_versions_do_not_authorize_past_catalogue_claim(self):
        raw = blob(event(product("2020-01-01T01:00:00Z", 5.6), product("2021-01-01T00:00:00Z", 5.7)))
        result = historical_catalog_not_identifiable(raw, CUTOFF)
        self.assertEqual(result["contract"], "historical_catalog_not_identifiable")
        self.assertIsNone(result["result"])
        self.assertFalse(result["historical_publication_reconstructed"])
        self.assertEqual(len(result["unestablished_requirements"]), 5)

    def test_synthetic_witnesses_preserve_current_evidence_but_change_past_answer(self):
        examples = synthetic_nonidentifiability_witnesses()
        self.assertEqual(len(examples), 3)
        for case in examples:
            self.assertTrue(case["synthetic"])
            self.assertEqual(case["history_a_evidence_sha256"], case["history_b_evidence_sha256"])
            current = json.dumps(case["evidence_at_capture"], sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(current).hexdigest(), case["history_a_evidence_sha256"])
            replayed = validate_synthetic_witness(case)
            self.assertTrue(replayed["valid_counterexample"])
            self.assertNotEqual(replayed["past_answer_a"], replayed["past_answer_b"])

    def test_witness_validator_catches_histories_that_no_longer_share_evidence(self):
        case = deepcopy(synthetic_nonidentifiability_witnesses()[0])
        case["history_b"]["versions"][0]["magnitude"] = 6.0
        result = validate_synthetic_witness(case)
        self.assertFalse(result["same_current_evidence"])
        self.assertFalse(result["valid_counterexample"])

    def test_witness_validator_catches_identical_past_answers(self):
        case = deepcopy(synthetic_nonidentifiability_witnesses()[0])
        case["history_b"]["versions"][0]["published"] = "T0"
        result = validate_synthetic_witness(case)
        self.assertTrue(result["same_current_evidence"])
        self.assertFalse(result["different_past_answers"])
        self.assertFalse(result["valid_counterexample"])


if __name__ == "__main__":
    unittest.main()
