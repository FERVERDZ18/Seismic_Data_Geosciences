"""Tiny fixtures only; no scientific histories/seeds or performance measurement."""
import copy
from datetime import datetime, timezone
import sys
import math
import unittest
from pathlib import Path
import run_twins_v1 as t


def fixtures():
    # The unobserved immigrant is root0; observed child remains a true child.
    events = [dict(t=-1., x=0., y=0., m=4., parent=None, root=0, generation=0, latent_id='r0', is_eval=False),
              dict(t=.1, x=1., y=0., m=5.05, parent=0, root=0, generation=1, latent_id='c1', is_eval=True),
              dict(t=.2, x=2., y=0., m=4.45, parent=1, root=0, generation=2, latent_id='c2', is_eval=True),
              dict(t=50., x=100., y=100., m=4.55, parent=None, root=3, generation=0, latent_id='r3', is_eval=True),
              dict(t=51., x=101., y=100., m=3.9, parent=3, root=3, generation=1, latent_id='c4', is_eval=True)]
    ledger = [dict(latent_id=e['latent_id'], detection_uniform=.1, detection_probability=.8, delta_m=.2, delta_x_km=3., delta_y_km=-2., delta_seconds=2.) for e in events]
    return events, ledger


class TwinFixtures(unittest.TestCase):
    def test_seal_and_new_seed_sets(self):
        self.assertEqual(len(t.verify_protocol()), 64)
        r = t.PROTOCOL['randomness']
        development, null, cluster = (r[name] for name in ('development_seeds_branching_0p6', 'test_seeds_branching_0', 'test_seeds_branching_0p6'))
        self.assertEqual((len(development), len(null), len(cluster)), (3, 30, 30))
        self.assertEqual(len(set(development+null+cluster)), 63)
        self.assertTrue(set(development+null+cluster).isdisjoint(range(20261120, 20261130)))

    def test_exact_control_and_no_truth_input(self):
        events, ledger = fixtures()
        a, ta, sa = t.observe(events, ledger, '0000', 'A')
        b, tb, sb = t.observe(events, ledger, '0000', 'B')
        keys = ('time_utc', 'latitude', 'longitude', 'magnitude')
        self.assertEqual([[r[k] for k in keys] for r in a], [[r[k] for k in keys] for r in b])
        self.assertEqual(sa, sb)
        self.assertFalse({'root', 'parent', 'latent_id'} & set(a[0]))
        self.assertEqual(t.round_m(4.45), 4.5)
        self.assertEqual(t.round_m(5.05), 5.1)

    def test_analytic_productivity_and_tiny_generator_guard(self):
        p = t.P
        grid = t.np.linspace(p['M0'], p['Mmax'], 10001)
        density = p['b']*math.log(10)*t.np.exp(-p['b']*math.log(10)*(grid-p['M0']))/(1-10**(-p['b']*(p['Mmax']-p['M0'])))
        expected = p['b']/(p['b']-p['productivity_alpha'])*(1-10**(-(p['b']-p['productivity_alpha'])*(p['Mmax']-p['M0'])))/(1-10**(-p['b']*(p['Mmax']-p['M0'])))
        self.assertAlmostEqual(float(t.np.trapezoid(density, grid)), 1., places=6)
        self.assertAlmostEqual(float(t.np.trapezoid(density*.6/expected*10**(p['productivity_alpha']*(grid-p['M0'])), grid)), .6, places=6)
        # A non-scientific tiny fixture uses a two-day horizon, zero allowed
        # records and a fixed fixture seed; it must abort rather than truncate.
        saved = copy.deepcopy(t.P)
        try:
            t.P = dict(saved, start_days=-1, end_exclusive_days=1,
                       immigrants_per_365_days=36500, count_abort_guard=0)
            with self.assertRaisesRegex(RuntimeError, 'no truncation or reseeding'):
                t.generate(17, 0.)
        finally:
            t.P = saved

    def test_reused_errors_and_pure_operations(self):
        events, ledger = fixtures()
        clean, _, _ = t.observe(events, ledger, '0000', 'A')
        for i, bit in enumerate(('1000', '0100', '0010', '0001')):
            rows, _, _ = t.observe(events, ledger, bit, 'B')
            if i!=1:
                self.assertEqual([r['magnitude'] for r in rows], [r['magnitude'] for r in clean])
            if i!=2:
                self.assertEqual([r['latitude'] for r in rows], [r['latitude'] for r in clean])
            if i!=3:
                self.assertEqual([r['time_utc'] for r in rows], [r['time_utc'] for r in clean])
        combined, _, _ = t.observe(events, ledger, '0111', 'B')
        only_m, _, _ = t.observe(events, ledger, '0100', 'B')
        only_x, _, _ = t.observe(events, ledger, '0010', 'B')
        only_t, _, _ = t.observe(events, ledger, '0001', 'B')
        self.assertEqual([r['magnitude'] for r in combined], [r['magnitude'] for r in only_m])
        self.assertEqual([r['longitude'] for r in combined], [r['longitude'] for r in only_x])
        self.assertEqual([r['time_utc'] for r in combined], [r['time_utc'] for r in only_t])

    def test_hidden_parent_observed_family_roles(self):
        events, ledger = fixtures()
        rows, truth, _ = t.observe(events, ledger, '0000', 'A')
        rows = t.retained(rows)
        groups, roles, child, evaluate = t.truth_arrays(rows, truth)
        self.assertEqual(groups.tolist(), [0, 0, 3])
        self.assertEqual(roles.tolist(), [1, 2, 0])
        self.assertEqual(child.tolist(), [True, True, False])
        ledger[1]['detection_uniform'] = .9
        rows, truth, _ = t.observe(events, ledger, '1000', 'B')
        groups, roles, child, evaluate = t.truth_arrays(t.retained(rows), truth)
        self.assertEqual(roles.tolist(), [0, 0])
        self.assertTrue(child[0])

    def test_inclusion_cut_and_fixed_denominator(self):
        events, ledger = fixtures()
        rows_a, ta, sa = t.observe(events, ledger, '0000', 'A')
        ledger[1]['detection_uniform'] = .9  # Missing clean-A key.
        ledger[2]['delta_m'] = -.2           # Below-cut clean-A key.
        ledger[4]['delta_m'] = .7            # B-only entrant.
        rows_b, tb, sb = t.observe(events, ledger, '1100', 'B')
        a = dict(prepared=dict(ids=[r['record_id'] for r in t.retained(rows_a)]))
        b = dict(prepared=dict(ids=[r['record_id'] for r in t.retained(rows_b)]))
        pa = dict(roles=t.np.asarray([1, 2, 0]), groups=t.np.asarray([0, 0, 3]))
        pb = dict(roles=t.np.asarray([1, 2]), groups=t.np.asarray([3, 3]))
        result = t.known_comparison(a, b, ta, tb, sb, pa, pb)
        self.assertEqual((result['fixed_clean_A_evaluation_keys'], result['B_missing'], result['B_below_cut'], result['retained_both'], result['B_only_evaluation_entrants']), (3, 1, 1, 1, 1))
        self.assertAlmostEqual(result['total_state_disagreement_fraction_fixed_A'], 1.)
        self.assertAlmostEqual(result['inclusion_loss_fraction_fixed_A'], 2/3)

    def test_actual_matcher_not_ledger(self):
        events, ledger = fixtures()
        arows, ta, _ = t.observe(events, ledger, '0000', 'A')
        brows, tb, _ = t.observe(events, ledger, '0001', 'B')
        a = dict(prepared=dict(ids=[r['record_id'] for r in t.retained(arows)], source_rows=t.retained(arows)))
        b = dict(prepared=dict(ids=[r['record_id'] for r in t.retained(brows)], source_rows=t.retained(brows)))
        pa = dict(roles=t.np.asarray([1, 2, 0]), groups=t.np.asarray([0, 0, 3]))
        metrics, ledger_out = t.actual_matching(a, b, ta, tb, {'fixture': pa}, {'fixture': pa})
        self.assertEqual(metrics['all_history']['precision'], 1.)
        self.assertEqual(metrics['all_history']['recall'], 1.)
        self.assertEqual(len(ledger_out['assignments']), 3)
        # Reassign truth identities only: the actual matcher must return the
        # same endpoints; its reported accuracy, rather than choice, changes.
        wrong_truth = copy.deepcopy(tb)
        first, second = b['prepared']['ids'][:2]
        wrong_truth[first]['latent_id'], wrong_truth[second]['latent_id'] = wrong_truth[second]['latent_id'], wrong_truth[first]['latent_id']
        bad_metrics, bad_ledger = t.actual_matching(a, b, ta, wrong_truth, {'fixture': pa}, {'fixture': pa})
        self.assertEqual([(p['A'], p['B']) for p in ledger_out['assignments']], [(p['A'], p['B']) for p in bad_ledger['assignments']])
        self.assertEqual(bad_metrics['all_history']['correct'], 1)

    def test_boolean_factorial_interactions(self):
        values = {}
        for cell in t.CELLS:
            d, m, x, clock = map(int, cell)
            response = .1*d+.2*m+.05*d*m
            values[cell] = dict(known_identity={key: {response_key: response for response_key in ('inclusion_loss_fraction_fixed_A', 'retained_role_change_fraction_fixed_A', 'total_state_disagreement_fraction_fixed_A')} for key in ('GK', 'NN_fixed_A_cut', 'NN_cell_development_cut')})
        result = t.interactions(values)['GK']['total_state_disagreement_fraction_fixed_A']
        self.assertAlmostEqual(result['mobius_interactions']['1000'], .1)
        self.assertAlmostEqual(result['mobius_interactions']['0100'], .2)
        self.assertAlmostEqual(result['mobius_interactions']['1100'], .05)
        self.assertLess(result['reconstruction_max_abs_error'], 1e-12)

    def test_null_denominators_and_mc_units(self):
        self.assertIsNone(t.binary_scores([], [])['F1'])
        self.assertIsNone(t.safe_comparison([], [], [], [])['partition']['ARI'])
        out = t.mc_summary([1., 2., 3.])
        self.assertEqual(out['n_histories'], 3)
        self.assertEqual(out['mean'], 2.)
        self.assertEqual(out['SD'], 1.)
        self.assertGreater(out['MC95_t'][1], 3.)


if __name__=='__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TwinFixtures))
    t.dump(Path(__file__).with_name('FIXTURE_TEST_RECEIPT.json'), dict(
        schema='twins-tiny-software-fixtures/1', generated_scientific_histories=False,
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        status='PASS' if result.wasSuccessful() else 'FAIL',
        tests=[name for name in dir(TwinFixtures) if name.startswith('test_')],
        protocol_sha256=t.verify_protocol(), runner_sha256=t.sha(t.HERE/'run_twins_v1.py'),
        test_sha256=t.sha(__file__), executed_utc=datetime.now(timezone.utc).isoformat()))
    sys.exit(0 if result.wasSuccessful() else 1)
