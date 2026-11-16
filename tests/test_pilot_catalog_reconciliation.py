"""Scientific-contract checks for offline candidate association, without labels."""
from pathlib import Path
import csv
import itertools
import json
import math
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import pilot_catalog_reconciliation as P


def record(key, source='ssn', time='2020-01-01T00:00:00Z', lat=0., lon=0., mag=4., kind=None):
    return P.Record(key, source, key if source == 'usgs' else None, time, P.utc_nanoseconds(time),
                    lat, lon, None, mag, kind)


def exhaustive_optimum(edges, seconds=30, km=50):
    """Independent exhaustive subsets, feasible only for small test graphs."""
    best = (0, 0)
    for mask in range(1 << len(edges)):
        chosen = [e for i, e in enumerate(edges) if mask & (1 << i)]
        if len({e.ssn for e in chosen}) != len(chosen) or len({e.usgs for e in chosen}) != len(chosen):
            continue
        objective = (-len(chosen), sum(round((abs(e.delta_ns)/(seconds*10**9)+e.distance_km/km)*10**9) for e in chosen))
        best = min(best, objective)
    return best


class TimestampAndCandidateTests(unittest.TestCase):
    def test_explicit_utc_keeps_nanoseconds_and_rejects_invalid_dates(self):
        base = P.utc_nanoseconds('2020-02-29T00:00:00Z')
        self.assertEqual(P.utc_nanoseconds('2020-02-29T00:00:00.000000001+00:00'), base+1)
        self.assertEqual(P.utc_nanoseconds('2020-02-29T00:00:00.100000000Z'), base+100_000_000)
        for value in ['2020-02-30T00:00:00Z', '2020-01-01T00:00:00', '2020-01-01T00:00:00-06:00',
                      '2020-01-01T00:00:00.0000000001Z', '2020-01-01T24:00:00Z']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                P.utc_nanoseconds(value)

    def test_temporal_window_is_inclusive_before_rounding(self):
        b = record('u', 'usgs')
        exact = record('exact', time='2020-01-01T00:00:30Z')
        outside = record('outside', time='2020-01-01T00:00:30.000000001Z')
        before = record('before', time='2019-12-31T23:59:30Z')
        pairs = {e.pair for e in P.candidate_edges([exact, outside, before], [b], 30, 50)}
        self.assertEqual(pairs, {('exact', 'u'), ('before', 'u')})

    def test_distance_window_and_antimeridian(self):
        b = record('u', 'usgs')
        longitude = lambda km: math.degrees(km/P.EARTH_RADIUS_KM)
        exact = record('exact', lon=longitude(50))
        outside = record('outside', lon=longitude(50.000001))
        self.assertAlmostEqual(P.epicentral_distance(exact, b), 50, places=9)
        self.assertEqual({e.ssn for e in P.candidate_edges([exact, outside], [b], 30, 50)}, {'exact'})
        west, east = record('a', lon=179.9), record('b', 'usgs', lon=-179.9)
        self.assertAlmostEqual(P.epicentral_distance(west, east), 22.2390160467, places=7)

    def test_unknown_types_depths_and_magnitude_difference_are_not_match_constraints(self):
        a, b = record('s', mag=3.5), record('u', 'usgs', mag=8.2, kind='mww')
        self.assertEqual(len(P.candidate_edges([a], [b], 30, 50)), 1)
        self.assertIsNone(a.event_id)
        self.assertIsNone(a.depth_km)
        self.assertIsNone(a.magnitude_type)

    def test_duplicate_keys_and_wrong_bipartite_sources_fail(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            P.candidate_edges([record('x'), record('x')], [], 30, 50)
        with self.assertRaisesRegex(ValueError, 'Bipartite'):
            P.candidate_edges([record('x', 'usgs')], [], 30, 50)


class AssignmentTests(unittest.TestCase):
    def test_alternating_path_recovers_cardinality_lost_by_greedy(self):
        edges = [P.Edge('a', '1', 0, 1), P.Edge('a', '2', 0, 2), P.Edge('b', '1', 0, 3)]
        self.assertEqual(len(P.greedy_assignment(edges, 30, 50)), 1)
        self.assertEqual(P.optimal_assignment(edges, 30, 50), {('a', '2'), ('b', '1')})

    def test_optimum_minimizes_cost_after_cardinality(self):
        edges = [P.Edge('a', '1', 0, 1), P.Edge('a', '2', 0, 3),
                 P.Edge('b', '1', 0, 1), P.Edge('b', '2', 0, 40)]
        self.assertEqual(P.optimal_assignment(edges, 30, 50), {('a', '2'), ('b', '1')})

    def test_small_graphs_agree_with_exhaustive_feasible_assignments(self):
        rng = random.Random(417319)
        universe = list(itertools.product(['a', 'b', 'c'], ['1', '2', '3']))
        for _ in range(50):
            edges = [P.Edge(a, b, rng.randrange(0, 30_000_000_001), rng.randrange(0, 50001)/1000)
                     for a, b in universe if rng.random() < .6]
            result = P.optimal_assignment(edges, 30, 50)
            actual = (-len(result), sum(P.cost_units(e, 30, 50) for e in edges if e.pair in result))
            self.assertEqual(actual, exhaustive_optimum(edges))
            self.assertEqual(len({p[0] for p in result}), len(result))
            self.assertEqual(len({p[1] for p in result}), len(result))

    def test_ties_are_stable_under_edge_input_order(self):
        edges = [P.Edge(a, b, 0, 0) for a, b in itertools.product(['a', 'b'], ['1', '2'])]
        expected = P.optimal_assignment(edges, 30, 50)
        for order in itertools.permutations(edges):
            self.assertEqual(P.optimal_assignment(list(order), 30, 50), expected)

    def test_chained_component_is_explicitly_ambiguous_and_not_collapsed(self):
        edges = [P.Edge('a', '1', 0, 0), P.Edge('a', '2', 0, 0), P.Edge('b', '2', 0, 0)]
        summary, assignments, _ = P.summarize(edges, 2, 2, 30, 50)
        self.assertEqual(summary['ambiguous_components'], 1)
        self.assertEqual(summary['isolated_one_edge_components'], 0)
        self.assertEqual(len(assignments), 2)
        self.assertEqual(len(edges), 3)
        self.assertEqual(P.concordance(set(), set())['jaccard'], None)
        with self.assertRaisesRegex(ValueError, 'Duplicate candidate'):
            P.optimal_assignment(edges + [edges[0]], 30, 50)


class EvidenceAndBlindingTests(unittest.TestCase):
    def test_checksum_failure_rejects_input_before_recording_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'example.csv'
            path.write_bytes(b'unexpected')
            evidence = []
            with self.assertRaisesRegex(ValueError, 'checksum'):
                P.verified_read(path, '0'*64, evidence, root)
            self.assertEqual(evidence, [])

    def test_blind_strata_are_deterministic_disjoint_and_keep_shortages(self):
        strata = {'first': {('a', '1'), ('b', '2')}, 'second': {('a', '1'), ('c', '3')}}
        cases, counts = P.blind_cases(strata, limit=2)
        self.assertEqual(cases, P.blind_cases(strata, limit=2)[0])
        self.assertEqual(len(cases), 3)
        self.assertEqual(counts['second']['shortfall'], 1)
        self.assertEqual(len({c['case_id'] for c in cases}), 3)

    def test_blinded_table_has_no_algorithm_labels_scores_or_automatic_judgements(self):
        cases, _ = P.blind_cases({'isolated': {('s', 'u')}})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            P.export_blind_cases(cases, {'s': record('s'), 'u': record('u', 'usgs')}, output)
            with (output/'adjudication_blinded.csv').open(encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                self.assertTrue({'stratum', 'score', 'graph_candidate_assignment', 'ssn_record_id'}.isdisjoint(reader.fieldnames))
            self.assertEqual(len(rows), 1)
            for field in ['human_judgement', 'independent_evidence', 'reviewer']:
                self.assertEqual(rows[0][field], '')
            lookup = json.loads((output/'adjudication_source_lookup.json').read_text(encoding='utf-8'))['cases'][0]
            self.assertTrue({'stratum', 'cost', 'graph_candidate_assignment'}.isdisjoint(lookup))
            self.assertEqual({lookup['a']['record_id'], lookup['b']['record_id']}, {'s', 'u'})

    def test_gem_pair_cannot_reference_outside_cohort_or_reversed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'gem.json'
            P.write_json(path, [{'ssn_record_id': 'u', 'usgs_record_id': 's'}])
            with self.assertRaisesRegex(ValueError, 'frozen cohort'):
                P.read_gem_pairs(path, {'s': record('s'), 'u': record('u', 'usgs')})

    def test_gem_diagnostic_distinguishes_strict_boundary_and_clock_precision(self):
        a = record('s', time='2020-01-01T00:00:30Z')
        b = record('u', 'usgs')
        edges = P.candidate_edges([a], [b], 60, 100)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'gem.json'
            P.write_json(path, [])
            result = P.gem_diagnostics(path, {'s': a, 'u': b}, edges, edges, {('s', 'u')}, set())
        self.assertEqual(result['primary_only_eligible_pairs'], 1)
        self.assertEqual(result['gem_model_only_eligible_pairs'], 0)
        self.assertEqual(result['source_rows_with_nonzero_submicroseconds'], 0)
        self.assertEqual(result['gem_strict_model_graph_assignments'], 0)

    def test_gem_comparator_rejects_other_thresholds_or_input_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for source in ['ssn', 'usgs']:
                (output/(source+'_cohort.csv')).write_text(source, encoding='utf-8')
            baseline = {'status': 'executed_official_GEM', 'time_seconds': 30, 'distance_km': 50,
                        'host_source': 'SSN', 'guest_source': 'USGS', 'use_kms': True, 'use_ids': False,
                        'gem_commit': P.GEM_COMMIT, 'host_input': 0, 'guest_input': 0,
                        'inputs': [{'path': source+'_cohort.csv', 'sha256': P.sha256(source.encode())} for source in ['ssn', 'usgs']]}
            P.write_json(output/'run.json', baseline)
            (output/'pairs.json').write_text('[]', encoding='utf-8')
            (output/'protocol_v1_frozen.md').write_text('protocol', encoding='utf-8')
            manifest = {'status': 'PASS', 'gem_commit': P.GEM_COMMIT, 'protocol_sha256': P.sha256(b'protocol'),
                        'files': [{'path': name, 'sha256': P.sha256((output/name).read_bytes()), 'bytes': (output/name).stat().st_size}
                                  for name in ['run.json', 'pairs.json']]}
            P.write_json(output/'GEM_RESULT_MANIFEST.json', manifest)
            cohorts = {'ssn': [], 'usgs': []}
            P.validate_gem_run(output/'pairs.json', cohorts, output)
            P.write_json(output/'run.json', {**baseline, 'time_seconds': 60})
            with self.assertRaisesRegex(ValueError, 'comparator'):
                P.validate_gem_run(output/'pairs.json', cohorts, output)
            P.write_json(output/'run.json', baseline)
            (output/'ssn_cohort.csv').write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CSV hashes'):
                P.validate_gem_run(output/'pairs.json', cohorts, output)
            (output/'ssn_cohort.csv').write_text('ssn', encoding='utf-8')
            (output/'pairs.json').write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                P.validate_gem_run(output/'pairs.json', cohorts, output)

    def test_rerun_preserves_human_adjudication(self):
        cases, _ = P.blind_cases({'isolated': {('s', 'u')}})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            target = output/'adjudication_blinded.csv'
            target.write_text('case_id,human_judgement,independent_evidence,reviewer\nexample,uncertain,,human\n', encoding='utf-8')
            original = target.read_bytes()
            with self.assertRaisesRegex(ValueError, 'human work'):
                P.export_blind_cases(cases, {'s': record('s'), 'u': record('u', 'usgs')}, output)
            self.assertEqual(target.read_bytes(), original)

    def test_real_frozen_cohort_is_source_selected_with_unknowns_preserved(self):
        cohorts, inputs, profile = P.load_cohorts(ROOT)
        self.assertEqual({k: len(v) for k, v in cohorts.items()}, {'ssn': 170880, 'usgs': 3945})
        self.assertEqual(len({r.record_id for rows in cohorts.values() for r in rows}), 174825)
        self.assertTrue(all(r.event_id is None and r.magnitude_type is None for r in cohorts['ssn']))
        for rows in cohorts.values():
            self.assertTrue(all(2016 <= int(r.time_utc[:4]) <= 2025 and 14 <= r.latitude <= 33
                                and -118 <= r.longitude <= -86 and r.magnitude >= 3.5 for r in rows))
        self.assertTrue(all(len(e['sha256']) == 64 for e in inputs))
        self.assertEqual(profile['ssn']['official_event_ids'], 0)


if __name__ == '__main__':
    unittest.main()
