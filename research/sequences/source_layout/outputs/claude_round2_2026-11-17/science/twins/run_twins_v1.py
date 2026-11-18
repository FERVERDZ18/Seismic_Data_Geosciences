"""Private post-review paired synthetic validation. No public data or Git writes."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import gzip
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = ROOT/'outputs/claude_response_2026-11-16'
PILOT = ROOT/'outputs/sequence_pilot_2026-11-15'
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = str(HERE/'cache/numba')
os.environ['MPLCONFIGDIR'] = str(HERE/'cache/matplotlib')
sys.path.insert(0, str(OLD/'methods'))
from run_deterministic_study_v3 import np, calculate, make_labels, author_normalmix, mixture_diagnostics, comparison, partition_comparison, set_num_threads
sys.path.insert(0, str(PILOT))
from gardner_knopoff import classify
import pyproj
import scipy
import numba
from scipy.stats import t as student_t

PROTOCOL = json.loads((HERE/'PROTOCOL_TWINS_V1.json').read_text(encoding='utf-8'))
P = PROTOCOL['latent']
EPOCH = datetime.fromisoformat(P['epoch_utc'].replace('Z', '+00:00'))
TRANSFORM = pyproj.Transformer.from_crs(P['projection'], 'EPSG:4326', always_xy=True)
CELLS = PROTOCOL['observations']['B_cells']
spec = importlib.util.spec_from_file_location('twins_frozen_actual_matcher', HERE/'vendor/pilot_catalog_reconciliation.py')
matcher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = matcher
spec.loader.exec_module(matcher)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def dump_gzip(path, value):
    # Complete derived inputs remain replayable; fixed gzip timestamp avoids
    # wall-clock metadata in otherwise identical scientific content.
    with Path(path).open('wb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
            compressed.write((json.dumps(value, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8'))


def verify_protocol():
    seal = json.loads((HERE/'PROTOCOL_SHA256.json').read_text(encoding='utf-8-sig'))
    for name, value in seal['files'].items():
        assert sha(HERE/name) == value['sha256'], 'Sealed protocol changed: '+name
    return sha(HERE/'PROTOCOL_TWINS_V1.json')


def rng(seed, block, stream):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, block, stream])))


def magnitude_sample(generator, count):
    beta = P['b']*math.log(10)
    return P['M0']-np.log1p(-generator.random(count)*(-math.expm1(-beta*(P['Mmax']-P['M0']))))/beta


def generate(seed, branching):
    """Truth derives from branching only, with no detector calls."""
    rt, rs, rm = (rng(seed, 100, i) for i in (1, 2, 3))
    n = int(rt.poisson(P['immigrants_per_365_days']*(P['end_exclusive_days']-P['start_days'])/365))
    times = np.sort(rt.uniform(P['start_days'], P['end_exclusive_days'], n))
    xy = rs.normal(0, P['background_sd_km'], (n, 2))
    xy[:, 0] += np.where(rs.random(n)<.5, -40., 40.)
    events = [dict(t=float(t), x=float(x), y=float(y), m=float(m), parent=None, root=i, generation=0)
              for i, (t, (x, y), m) in enumerate(zip(times, xy, magnitude_sample(rm, n)))]
    if n>P['count_abort_guard']:
        raise RuntimeError('Initial immigrant count guard; no truncation or reseeding')
    expected = P['b']/(P['b']-P['productivity_alpha'])*(1-10**(-(P['b']-P['productivity_alpha'])*(P['Mmax']-P['M0'])))/(1-10**(-P['b']*(P['Mmax']-P['M0'])))
    productivity = branching/expected
    rc, rt, rm, rs = (rng(seed, 200, i) for i in (1, 2, 3, 4))
    i = 0
    while branching and i<len(events):
        parent = events[i]
        if parent['generation']>=P['generation_abort_guard']:
            raise RuntimeError('Generation guard; no truncation or reseeding')
        horizon = P['end_exclusive_days']-parent['t']
        cdf = -math.expm1(P['omori_theta']*(math.log(P['omori_c_days'])-math.log(P['omori_c_days']+horizon)))
        n = int(rc.poisson(productivity*10**(P['productivity_alpha']*(parent['m']-P['M0']))*cdf))
        if len(events)+n>P['count_abort_guard']:
            raise RuntimeError('Count guard; no truncation or reseeding')
        delays = P['omori_c_days']*np.expm1(-np.log1p(-rt.random(n)*cdf)/P['omori_theta'])
        for delay, m, (dx, dy) in zip(delays, magnitude_sample(rm, n), rs.normal(0, P['offspring_gaussian_sd_km'], (n, 2))):
            events.append(dict(t=parent['t']+float(delay), x=parent['x']+float(dx), y=parent['y']+float(dy), m=float(m), parent=i, root=parent['root'], generation=parent['generation']+1))
        i += 1
    for i, event in enumerate(events):
        event['latent_id'] = hashlib.sha256(f'{seed}:{i}'.encode()).hexdigest()[:24]
        event['is_eval'] = 0<=event['t']<P['end_exclusive_days']
        assert P['start_days']<=event['t']<P['end_exclusive_days']
        if event['parent'] is not None:
            parent = events[event['parent']]
            assert parent['t']<event['t'] and parent['root']==event['root']
            assert event['generation']==parent['generation']+1
            assert events[event['root']]['parent'] is None
        else:
            assert event['root']==i and event['generation']==0
    return events


def round_m(value):
    return float(Decimal(str(value)).quantize(Decimal('.1'), rounding=ROUND_HALF_UP))


def make_ledger(events, seed):
    n = len(events)
    detection = rng(seed, 300, 1).random(n)
    magnitude = rng(seed, 300, 2).normal(0, .15, n)+.15
    position = rng(seed, 300, 3).normal(0, 5, (n, 2))+np.asarray([2, -2])
    clock = rng(seed, 300, 4).normal(0, 2, n)+2
    return [dict(latent_id=e['latent_id'], detection_uniform=float(detection[i]),
                 detection_probability=.65+.30*float(np.clip((e['m']-3.5)/1.5, 0, 1)),
                 delta_m=float(magnitude[i]), delta_x_km=float(position[i, 0]), delta_y_km=float(position[i, 1]), delta_seconds=float(clock[i])) for i, e in enumerate(events)]


def observe(events, ledger, cell, source):
    d, m, x, t = map(int, cell)
    rows, truth, states = [], {}, {}
    for i, (event, error) in enumerate(zip(events, ledger)):
        assert event['latent_id']==error['latent_id']
        latent_id = event['latent_id']
        if d and error['detection_uniform']>=error['detection_probability']:
            states[latent_id] = 'missing'
            continue
        mag = round_m(round_m(event['m'])+(error['delta_m'] if m else 0))
        lon, lat = TRANSFORM.transform((event['x']+(error['delta_x_km'] if x else 0))*1000, (event['y']+(error['delta_y_km'] if x else 0))*1000)
        clean_time = EPOCH+timedelta(days=event['t'])
        timestamp = (clean_time+timedelta(seconds=error['delta_seconds'] if t else 0)).isoformat(timespec='microseconds').replace('+00:00', 'Z')
        record_id = source+'-'+latent_id
        rows.append(dict(record_id=record_id, source='synthetic_'+source, event_id=record_id, time_utc=timestamp, latitude=float(lat), longitude=float(lon), depth_km=10., magnitude=mag, magnitude_type='synthetic_reported', source_file='shared_latent', source_record=i, package_row=i))
        truth[record_id] = dict(latent_id=latent_id, root=event['root'], parent=event['parent'], is_eval=event['is_eval'])
        states[latent_id] = 'retained' if Decimal(str(mag))>=Decimal('4.5') else 'below_cut'
    return rows, truth, states


def retained(rows):
    return [row for row in rows if Decimal(str(row['magnitude']))>=Decimal('4.5')]


def truth_arrays(rows, truth):
    groups = np.asarray([truth[r['record_id']]['root'] for r in rows], dtype=np.int64)
    counts = Counter(map(int, groups))
    representatives = {}
    for i, row in enumerate(rows):
        key = (-float(row['magnitude']), row['time_utc'], row['record_id'])
        group = int(groups[i])
        if group not in representatives or key<representatives[group][0]:
            representatives[group] = (key, i)
    roles = np.full(len(rows), 2, dtype=np.int8)
    for group, (_, i) in representatives.items():
        roles[i] = 0 if counts[group]==1 else 1
    child = np.asarray([truth[r['record_id']]['parent'] is not None for r in rows], dtype=bool)
    evaluation = np.asarray([truth[r['record_id']]['is_eval'] for r in rows], dtype=bool)
    return groups, roles, child, evaluation


def binary_scores(true, predicted):
    a, b = np.asarray(true, dtype=bool), np.asarray(predicted, dtype=bool)
    tp, fp, fn, tn = (int(v) for v in (np.sum(a&b), np.sum(~a&b), np.sum(a&~b), np.sum(~a&~b)))
    return dict(n=len(a), TP=tp, FP=fp, FN=fn, TN=tn,
                precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
                F1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                false_positive_fraction_among_negatives=fp/(fp+tn) if fp+tn else None,
                accuracy=(tp+tn)/len(a) if len(a) else None)


def role_scores(true, predicted, gt, gp):
    result = safe_comparison(true, predicted, gt, gp)
    result['partition']['interpretation'] = 'Accuracy against independent generated latent-root truth on the evaluated retained records'
    result['per_class'] = {str(k): binary_scores(np.asarray(true)==k, np.asarray(predicted)==k) for k in range(3)}
    return result


def safe_comparison(a, b, ga, gb):
    result = comparison(a, b, ga, gb)
    if not len(a):
        result['partition']['ARI'] = None
    return result


def infer(rows):
    rows = retained(rows)
    if len(rows)<2:
        raise ValueError('Fewer than two retained events; record failure, do not reseed')
    prepared, result = calculate(rows, 1.6, 1.)
    gk = classify(prepared['t_year']*365.25, prepared['lat_deg'], prepared['lon_deg'], prepared['m'])
    gk_role = np.asarray([{'isolated': 0, 'main': 1, 'associated': 2}[str(v)] for v in gk['roles']], dtype=np.int8)
    gk_group = np.where(gk['group']>0, gk['group'], -np.arange(len(rows))-1)
    return dict(prepared=prepared, result=result, GK=dict(roles=gk_role, groups=gk_group, child=gk_role==2))


def nn_labels(inferred, fit):
    if fit['status']!='estimable':
        return None
    labels = make_labels(inferred['prepared'], inferred['result'], fit['threshold_log10'])
    return dict(roles=labels['roles'], groups=labels['component_root_index'], child=labels['strong_link_mask'])


def accuracy(inferred, truth, prediction):
    if prediction is None:
        return dict(status='unavailable_cut')
    groups, roles, child, evaluation = truth_arrays(inferred['prepared']['source_rows'], truth)
    child_result = binary_scores(child[evaluation], prediction['child'][evaluation])
    child_result['true_immigrant_false_positive_fraction'] = child_result['false_positive_fraction_among_negatives']
    return dict(status='computed', evaluated=int(evaluation.sum()),
                observed_families_and_roles=role_scores(roles[evaluation], prediction['roles'][evaluation], groups[evaluation], prediction['groups'][evaluation]),
                generated_child=child_result)


def baselines(inferred, truth):
    groups, roles, child, evaluation = truth_arrays(inferred['prepared']['source_rows'], truth)
    n = len(groups)
    one_roles = np.full(n, 2, dtype=np.int8)
    one_roles[min(range(n), key=lambda i: (-inferred['prepared']['m'][i], inferred['prepared']['source_rows'][i]['time_utc'], inferred['prepared']['ids'][i]))] = 1 if n>1 else 0
    return dict(always_child=binary_scores(child[evaluation], np.ones(evaluation.sum(), dtype=bool)),
                always_immigrant=binary_scores(child[evaluation], np.zeros(evaluation.sum(), dtype=bool)),
                all_singletons=role_scores(roles[evaluation], np.zeros(n, dtype=np.int8)[evaluation], groups[evaluation], np.arange(n)[evaluation]),
                all_one_family=role_scores(roles[evaluation], one_roles[evaluation], groups[evaluation], np.zeros(n, dtype=int)[evaluation]),
                constant_roles={str(k): role_scores(roles[evaluation], np.full(evaluation.sum(), k), groups[evaluation], np.arange(evaluation.sum())) for k in range(3)})


def known_comparison(a, b, truth_a, truth_b, states_b, prediction_a, prediction_b):
    ia = {truth_a[rid]['latent_id']: i for i, rid in enumerate(a['prepared']['ids']) if truth_a[rid]['is_eval']}
    ib = {truth_b[rid]['latent_id']: i for i, rid in enumerate(b['prepared']['ids'])}
    keys = sorted(ia)
    both = [key for key in keys if key in ib]
    counts = Counter(states_b[key] for key in keys)
    out = dict(fixed_clean_A_evaluation_keys=len(keys), B_missing=counts['missing'], B_below_cut=counts['below_cut'], retained_both=len(both),
               B_only_evaluation_entrants=sum(truth_b[rid]['is_eval'] and truth_b[rid]['latent_id'] not in ia for rid in b['prepared']['ids']))
    if prediction_a is None or prediction_b is None:
        return dict(**out, status='unavailable_cut')
    ai = np.asarray([ia[key] for key in both], dtype=int)
    bi = np.asarray([ib[key] for key in both], dtype=int)
    conditional = safe_comparison(prediction_a['roles'][ai], prediction_b['roles'][bi], prediction_a['groups'][ai], prediction_b['groups'][bi])
    changed = int(np.sum(prediction_a['roles'][ai]!=prediction_b['roles'][bi]))
    denominator = len(keys)
    return dict(**out, status='computed', conditional_retained=conditional,
                retained_role_changes=changed, inclusion_losses=denominator-len(both),
                retained_role_change_fraction_fixed_A=changed/denominator if denominator else None,
                inclusion_loss_fraction_fixed_A=(denominator-len(both))/denominator if denominator else None,
                total_state_disagreement_fraction_fixed_A=(changed+denominator-len(both))/denominator if denominator else None)


def actual_matching(a, b, truth_a, truth_b, predictions_a, predictions_b):
    def records(inferred, source):
        return [matcher.Record(r['record_id'], source, r['event_id'], r['time_utc'], matcher.utc_nanoseconds(r['time_utc']), float(r['latitude']), float(r['longitude']), 10., float(r['magnitude']), 'synthetic_reported') for r in inferred['prepared']['source_rows']]
    edges = matcher.candidate_edges(records(a, 'ssn'), records(b, 'usgs'), 30., 50.)
    pairs = sorted(matcher.optimal_assignment(edges, 30., 50.))
    retained_a, retained_b = set(a['prepared']['ids']), set(b['prepared']['ids'])
    latent_a = {v['latent_id']: k for k, v in truth_a.items() if k in retained_a}
    latent_b = {v['latent_id']: k for k, v in truth_b.items() if k in retained_b}
    true_pairs = {(latent_a[k], latent_b[k]) for k in latent_a.keys() & latent_b.keys()}
    chosen = set(pairs)
    correct = chosen & true_pairs
    possible_eval = {pair for pair in true_pairs if truth_a[pair[0]]['is_eval']}
    chosen_eval = {pair for pair in chosen if truth_a[pair[0]]['is_eval']}
    correct_eval = chosen_eval & possible_eval
    def counts(selected, valid, possible):
        return dict(assigned=len(selected), correct=len(valid), possible_true_pairs=len(possible), precision=len(valid)/len(selected) if selected else None, recall=len(valid)/len(possible) if possible else None)
    out = dict(all_history=counts(chosen, correct, true_pairs), evaluation_by_latent_A_time=counts(chosen_eval, correct_eval, possible_eval))
    ia = {rid: i for i, rid in enumerate(a['prepared']['ids'])}
    ib = {rid: i for i, rid in enumerate(b['prepared']['ids'])}
    out['roles_on_actual_assigned_evaluation_pairs'] = {}
    for method in predictions_a:
        pa, pb = predictions_a[method], predictions_b[method]
        if pa is None or pb is None:
            out['roles_on_actual_assigned_evaluation_pairs'][method] = None
            continue
        ordered = sorted(chosen_eval)
        ai, bi = np.asarray([ia[x] for x, _ in ordered], dtype=int), np.asarray([ib[y] for _, y in ordered], dtype=int)
        out['roles_on_actual_assigned_evaluation_pairs'][method] = safe_comparison(pa['roles'][ai], pb['roles'][bi], pa['groups'][ai], pb['groups'][bi])
    return out, dict(edges=[dict(A=e.ssn, B=e.usgs, delta_ns=e.delta_ns, distance_km=e.distance_km) for e in edges], assignments=[dict(A=x, B=y, known_identity_correct=(x, y) in true_pairs) for x, y in pairs])


def save_inferred(path, inferred, truth, fits):
    path.mkdir()
    dump(path/'retained_rows.json', inferred['prepared']['source_rows'])
    groups, roles, child, evaluation = truth_arrays(inferred['prepared']['source_rows'], truth)
    fields = {k: inferred['result'][k] for k in ('parent_index', 'eta_log10', 'eta_log10_sum', 'TN', 'RN', 'T_log10', 'R_log10', 'parent_dt_years', 'parent_distance_km')}
    fields.update(true_root=groups, true_observed_role=roles, true_generated_child=child, evaluation=evaluation, GK_role=inferred['GK']['roles'], GK_group=inferred['GK']['groups'])
    for label, fit in fits.items():
        pred = nn_labels(inferred, fit)
        if pred is not None:
            fields.update({label+'_'+key: value for key, value in pred.items()})
    np.savez_compressed(path/'arrays.npz', **fields)
    dump(path/'kernel_metadata.json', inferred['result']['metadata'])


def calibrate(destination):
    pools = {cell: [] for cell in CELLS}
    for seed in PROTOCOL['randomness']['development_seeds_branching_0p6']:
        folder = destination/f'development_{seed}'
        folder.mkdir()
        events = generate(seed, .6)
        ledger = make_ledger(events, seed)
        dump(folder/'latent_truth.json', events)
        dump(folder/'observation_ledger.json', ledger)
        for cell in CELLS:
            rows, truth, states = observe(events, ledger, cell, 'B')
            inferred = infer(rows)
            values = inferred['result']['eta_log10']
            pools[cell].extend(values[np.isfinite(values)].tolist())
            folder_cell = folder/cell
            folder_cell.mkdir()
            dump_gzip(folder_cell/'observed_rows.json.gz', rows)
            dump(folder_cell/'observation_state.json', states)
            np.savez_compressed(folder_cell/'calibration_scores.npz', eta_log10=values, parent_index=inferred['result']['parent_index'])
    fits = {}
    for cell, values in pools.items():
        values = np.asarray(values)
        fit = author_normalmix(values)
        fits[cell] = dict(fit=fit, diagnostics=mixture_diagnostics(fit, values), finite_score_count=len(values))
    dump(destination/'CALIBRATION.json', fits)
    return fits


def interactions(metrics):
    outputs = {}
    for method in ('GK', 'NN_fixed_A_cut', 'NN_cell_development_cut'):
        outputs[method] = {}
        for response in ('inclusion_loss_fraction_fixed_A', 'retained_role_change_fraction_fixed_A', 'total_state_disagreement_fraction_fixed_A'):
            cell_values = {cell: metrics[cell]['known_identity'][method].get(response) for cell in CELLS}
            if any(value is None for value in cell_values.values()):
                outputs[method][response] = dict(status='unavailable_cell', values=cell_values)
                continue
            terms = {}
            for cell in CELLS:
                mask = int(cell, 2)
                terms[cell] = sum((-1)**(mask.bit_count()-sub.bit_count())*cell_values[f'{sub:04b}'] for sub in range(16) if sub & ~mask == 0)
            outputs[method][response] = dict(status='computed', cell_values=cell_values, mobius_interactions=terms,
                                            reconstruction_max_abs_error=max(abs(sum(terms[f'{sub:04b}'] for sub in range(16) if sub & ~int(cell, 2) == 0)-cell_values[cell]) for cell in CELLS))
    return outputs


def one_test(destination, seed, branching, fits):
    folder = destination/f'test_b{branching}_{seed}'
    folder.mkdir()
    events = generate(seed, branching)
    ledger = make_ledger(events, seed)
    dump(folder/'latent_truth.json', events)
    dump(folder/'observation_ledger.json', ledger)
    rows_a, truth_a, states_a = observe(events, ledger, '0000', 'A')
    dump(folder/'A_observed_rows.json', rows_a)
    dump(folder/'A_truth_identity.json', truth_a)
    dump(folder/'A_observation_states.json', states_a)
    a = infer(rows_a)
    cut_a = fits['0000']['fit']
    pred_a_nn = nn_labels(a, cut_a)
    predictions_a = dict(GK=a['GK'], NN_fixed_A_cut=pred_a_nn, NN_cell_development_cut=pred_a_nn)
    save_inferred(folder/'A', a, truth_a, {'NN_fixed_A_cut': cut_a})
    metrics = {}
    for cell in CELLS:
        rows_b, truth_b, states_b = observe(events, ledger, cell, 'B')
        b = infer(rows_b)
        predictions_b = dict(GK=b['GK'], NN_fixed_A_cut=nn_labels(b, cut_a), NN_cell_development_cut=nn_labels(b, fits[cell]['fit']))
        cell_folder = folder/cell
        cell_folder.mkdir()
        dump_gzip(cell_folder/'B_observed_rows.json.gz', rows_b)
        dump(cell_folder/'B_truth_identity.json', truth_b)
        dump(cell_folder/'B_observation_states.json', states_b)
        save_inferred(cell_folder/'B', b, truth_b, {'NN_fixed_A_cut': cut_a, 'NN_cell_development_cut': fits[cell]['fit']})
        matching_metrics, matching_ledger = actual_matching(a, b, truth_a, truth_b, predictions_a, predictions_b)
        dump(cell_folder/'matching_ledger.json', matching_ledger)
        metrics[cell] = dict(cell=cell, seed=seed, branching=branching, latent_events=len(events),
                             observed_B=len(rows_b), retained_B=len(b['prepared']['ids']),
                             A_recovery={key: accuracy(a, truth_a, value) for key, value in predictions_a.items()},
                             B_recovery={key: accuracy(b, truth_b, value) for key, value in predictions_b.items()},
                             A_trivial_baselines=baselines(a, truth_a), B_trivial_baselines=baselines(b, truth_b),
                             known_identity={key: known_comparison(a, b, truth_a, truth_b, states_b, predictions_a[key], predictions_b[key]) for key in predictions_a},
                             actual_matching=matching_metrics)
        dump(cell_folder/'metrics.json', metrics[cell])
    contrasts = interactions(metrics)
    dump(folder/'FACTORIAL_INTERACTIONS.json', contrasts)
    return dict(seed=seed, branching=branching, path=folder.name, metrics=metrics, interactions=contrasts)


def numeric_leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from numeric_leaves(child, path+(key,))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from numeric_leaves(child, path+(str(i),))
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        yield '.'.join(path), float(value)


def summarize(results):
    summary = {}
    for branching in (0., .6):
        histories = [r for r in results if r['branching']==branching]
        output = {}
        for cell in CELLS:
            values = {}
            for history in histories:
                for key, value in numeric_leaves(history['metrics'][cell]):
                    if key not in ('seed', 'branching'):
                        values.setdefault(key, []).append(value)
            output[cell] = {key: mc_summary(v) for key, v in values.items()}
        contrast_values = {}
        for history in histories:
            for key, value in numeric_leaves(history['interactions']):
                contrast_values.setdefault(key, []).append(value)
        summary[str(branching)] = dict(successful_histories=len(histories), cells=output, factorial={key: mc_summary(v) for key, v in contrast_values.items()})
    return summary


def mc_summary(values):
    n = len(values)
    mean = float(np.mean(values)) if n else None
    sd = float(np.std(values, ddof=1)) if n>1 else None
    se = sd/math.sqrt(n) if n>1 else None
    half = float(student_t.ppf(.975, n-1))*se if n>1 else None
    return dict(n_histories=n, mean=mean, SD=sd, SE=se, MC95_t=[mean-half, mean+half] if n>1 else None, pooled_sum=sum(values), minimum=min(values) if n else None, maximum=max(values) if n else None)


def source_manifest():
    sources = [Path(__file__), HERE/'vendor/pilot_catalog_reconciliation.py', OLD/'methods/run_deterministic_study_v3.py', OLD/'index/spherical_weighted_v2.py', OLD/'methods/author_normalmix_port.py', OLD/'methods/deterministic_families.py', PILOT/'gardner_knopoff.py']
    return {str(path.relative_to(ROOT)): dict(sha256=sha(path), bytes=path.stat().st_size) for path in sources}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-reviewed-batch', action='store_true')
    parser.add_argument('--cpu-gate', type=Path, required=True)
    args = parser.parse_args()
    if not args.run_reviewed_batch:
        parser.error('Execution requires explicit reviewed-batch flag')
    gate = json.loads(args.cpu_gate.read_text(encoding='utf-8-sig'))
    protocol_sha = verify_protocol()
    assert gate.get('twins_protocol_sha256')==protocol_sha and gate.get('twins_scientific_cpu_authorized') is True, 'Root master-protocol/CPU gate required'
    destination = HERE/'run_v1'
    destination.mkdir(exist_ok=False)
    set_num_threads(1)
    start = time.perf_counter()
    sources = source_manifest()
    dump(destination/'RUN_START.json', dict(protocol_sha256=protocol_sha, gate=gate, sources=sources, python=sys.version, platform=platform.platform(), numpy=np.__version__, scipy=scipy.__version__, numba=numba.__version__, pyproj=pyproj.__version__, started_utc=datetime.now(timezone.utc).isoformat(), argv=sys.argv))
    results, failures = [], []
    try:
        fits = calibrate(destination)
    except Exception:
        dump(destination/'CALIBRATION_FAILURE.json', dict(error=traceback.format_exc(), no_reseeding=True))
        raise
    for branching, seeds in ((0., PROTOCOL['randomness']['test_seeds_branching_0']), (.6, PROTOCOL['randomness']['test_seeds_branching_0p6'])):
        for seed in seeds:
            try:
                result = one_test(destination, seed, branching, fits)
                results.append(result)
                print(json.dumps(dict(seed=seed, branching=branching, status='completed', elapsed=time.perf_counter()-start)), flush=True)
            except Exception:
                failure = dict(seed=seed, branching=branching, error=traceback.format_exc(), no_reseeding=True)
                failures.append(failure)
                dump(destination/f'FAILURE_{seed}.json', failure)
                print(json.dumps(dict(seed=seed, branching=branching, status='failed_no_reseed')), flush=True)
    assert sources==source_manifest(), 'Source changed during execution; retain evidence and invalidate replay'
    dump(destination/'RESULTS.json', dict(schema='shared-latent-twin-validation/1', synthetic=True, protocol_sha256=protocol_sha, sources=sources, elapsed_seconds=time.perf_counter()-start, planned_histories=60, completed_histories=len(results), failures=failures, results=results, summaries=summarize(results), limitations=PROTOCOL['limitations']))
    manifest = {str(path.relative_to(destination)): dict(sha256=sha(path), bytes=path.stat().st_size) for path in destination.rglob('*') if path.is_file()}
    dump(destination/'OUTPUT_MANIFEST.json', manifest)
    print(json.dumps(dict(completed_histories=len(results), failures=len(failures), results=str(destination/'RESULTS.json'), seconds=time.perf_counter()-start)), flush=True)


if __name__=='__main__':
    main()
