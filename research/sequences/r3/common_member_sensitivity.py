"""Replay the common-member synthetic sensitivity on the retained latent histories."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import product
import json
import math
import os
from pathlib import Path
import sys

import importlib.util

import numpy as np
import pyproj
from scipy.stats import t

from package_io import sha_file

PACKAGE = Path(__file__).resolve().parent


def configure(workspace, output):
    global HERE, ROOT, METHODS, TWINS, TWINS_RUN, DATA, observe
    global calculate, make_labels, comparison, partition_comparison, set_num_threads
    HERE = output
    ROOT = workspace / "source_layout"
    METHODS = ROOT / "outputs/claude_response_2026-11-16/methods"
    twins_path = Path("outputs/claude_round2_2026-11-17/science/twins")
    TWINS = ROOT / twins_path
    TWINS_RUN = workspace / "expected" / twins_path / "run_v1"
    DATA = ROOT / "system/dist/sequences/data"
    os.environ["NUMBA_CACHE_DIR"] = str(output / "cache")
    sys.path.insert(0, str(METHODS))
    from run_deterministic_study_v3 import (
        calculate, make_labels, comparison, partition_comparison, set_num_threads,
    )

    spec = importlib.util.spec_from_file_location("frozen_twin_observations", TWINS / "run_twins_v1.py")
    twin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(twin)
    observe = twin.observe


GEOD = pyproj.Geod(ellps='WGS84')
FIELDS = (('time_utc',), ('latitude', 'longitude'), ('magnitude',))
CELLS = [''.join(flags) for flags in product('01', repeat=3)]
def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def magnitude_delta(row_a, row_b):
    return Decimal(str(row_b['magnitude'])) - Decimal(str(row_a['magnitude']))


def measurements(rows_a, rows_b):
    arrays = [np.asarray([row[key] for row in rows], dtype=float)
              for rows in [rows_a, rows_b] for key in ['longitude', 'latitude']]
    azimuth, _, radial_m = GEOD.inv(*arrays)
    return [dict(dm=magnitude_delta(a, b), dt=(dt(b['time_utc']) - dt(a['time_utc'])).total_seconds(),
                 bearing=float(az), distance_km=float(radial / 1000))
            for a, b, az, radial in zip(rows_a, rows_b, azimuth, radial_m, strict=True)]


def descriptive(vectors):
    return dict(count=len(vectors),
                magnitudes_abs_ge_0p3=sum(abs(x['dm']) >= Decimal('.3') for x in vectors),
                mean_signed_m=float(np.mean([float(x['dm']) for x in vectors])),
                median_abs_m=float(np.median([float(abs(x['dm'])) for x in vectors])),
                median_abs_time_seconds=float(np.median([abs(x['dt']) for x in vectors])),
                median_geodesic_km=float(np.median([x['distance_km'] for x in vectors])))


def observed_pool():
    pairs = load(PACKAGE / 'inputs/candidates_3_5.json')['pairs']
    observed = load(DATA / 'inputs_3_5.json')['sources']
    assert len(pairs) == len({p['ssn'] for p in pairs}) == len({p['usgs'] for p in pairs}) == 2989
    maps = {key: {row['record_id']: row for row in rows} for key, rows in observed.items()}
    rows_a = [maps['ssn'][p['ssn']] for p in pairs]
    rows_b = [maps['usgs'][p['usgs']] for p in pairs]
    vectors = measurements(rows_a, rows_b)
    for p, v in zip(pairs, vectors, strict=True):
        assert v['dm'] == -Decimal(p['delta_m'])
        assert math.isclose(v['dt'], -p['delta_seconds'], abs_tol=1e-7)
        # Radius/ellipsoid differ. The matching limits apply to the archived values.
        assert abs(p['distance_km'] - v['distance_km']) < .5
        assert abs(p['delta_seconds']) <= 30 and 0 <= p['distance_km'] <= 50
    selected = [i for i, (a, b) in enumerate(zip(rows_a, rows_b, strict=True))
                if min(a['magnitude'], b['magnitude']) >= 4.5]
    assert len(selected) == 889
    stats = dict(all=descriptive(vectors), selected_4p5_both=descriptive([vectors[i] for i in selected]),
                 recorded_spherical_distance_median_km=float(np.median([p['distance_km'] for p in pairs])))
    return vectors, stats, [rows_a[i] for i in selected], [rows_b[i] for i in selected]


def mixed_rows(base_rows, replacements, cell):
    rows = []
    for clean, changed in zip(base_rows, replacements, strict=True):
        row = dict(clean)
        for flag, fields in zip(cell, FIELDS, strict=True):
            if flag == '1':
                row.update({field: changed[field] for field in fields})
        rows.append(row)
    return rows


def aligned_predictions(rows, cut, ordered_ids):
    prepared, arrays = calculate(rows, 1.6, 1.)
    labels = make_labels(prepared, arrays, cut)
    index = {value: i for i, value in enumerate(prepared['ids'])}
    order = np.asarray([index[rid] for rid in ordered_ids], dtype=int)
    return (labels['roles'][order], labels['component_root_index'][order],
            labels['strong_link_mask'][order])


def replay_observed(rows_a, rows_b):
    calibration = load(PACKAGE / 'inputs/calibration.json')
    historic = load(METHODS / 'deterministic_study_v3/MEASUREMENT_FACTORIAL.json')
    peer = {(p['cut_source'], ''.join(map(str, p['measurement_flags_time_location_magnitude']))): p
            for p in historic}
    order = [a['record_id'] for a in rows_a]
    holdout = np.array([r['time_utc'] >= '2021-01-01' for r in rows_a])
    assert int(holdout.sum()) == 382
    outputs = []
    for name in ('ssn', 'usgs'):
        cut = float(peer[(name, '000')]['fixed_cut'])
        archived_cut = calibration['cuts']['4.5'][name]['threshold_log10']
        assert abs(archived_cut - cut) < 1e-12
        ra, ga, _ = aligned_predictions(rows_a, cut, order)
        for cell in CELLS:
            rb, gb, _ = aligned_predictions(mixed_rows(rows_a, rows_b, cell), cut, order)
            for label, indices in [('all', slice(None)), ('held_out_2021_2025', holdout)]:
                value = comparison(ra[indices], rb[indices], ga[indices], gb[indices])
                previous = peer[(name, cell)][label]
                assert value['n'] == previous['n']
                assert value['matrix_first_rows_second_columns'] == previous['matrix_first_rows_second_columns']
                assert abs(value['partition']['ARI'] - previous['partition']['ARI']) < 1e-12
                outputs.append(dict(cut_source=name, cell=cell, cohort=label, stats=value))
    return outputs


def sample_fields(rows, vectors, seed):
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, 20261118, 404])))
    draw = rng.integers(len(vectors), size=len(rows))
    perturbations = [vectors[i] for i in draw]
    lon, lat, _ = GEOD.fwd([r['longitude'] for r in rows], [r['latitude'] for r in rows],
                           [v['bearing'] for v in perturbations], [1000*v['distance_km'] for v in perturbations])
    fields = [dict(record_id=row['record_id'], longitude=float(x), latitude=float(y),
                   magnitude=float(Decimal(str(row['magnitude'])) + vector['dm']),
                   time_utc=(dt(row['time_utc']) + timedelta(microseconds=round(vector['dt']*1e6)))
                   .isoformat(timespec='microseconds').replace('+00:00', 'Z'))
              for row, x, y, vector in zip(rows, lon, lat, perturbations, strict=True)]
    return fields, draw


def synthetic_one(folder, seed, branch, vectors, cut):
    events = load(folder / 'latent_truth.json')
    ledger = load(folder / 'observation_ledger.json')
    clean, truth, _ = observe(events, ledger, '0000', 'A')
    whole_gaussian, _, _ = observe(events, ledger, '0111', 'B')
    _, detected_gaussian, _ = observe(events, ledger, '1111', 'B')
    all_latent = [truth[row['record_id']]['latent_id'] for row in clean]
    assert len(clean) == len(whole_gaussian) == len(truth) == len(set(all_latent))
    assert [row['record_id'] for row in whole_gaussian] == ['B-'+v for v in all_latent]
    empirical, draw = sample_fields(clean, vectors, seed)
    selected = [i for i, (a, b, c) in enumerate(zip(clean, whole_gaussian, empirical, strict=True))
                if b['record_id'] in detected_gaussian and min(a['magnitude'], b['magnitude'], c['magnitude']) >= 4.5]
    baseline = [clean[i] for i in selected]
    order = [r['record_id'] for r in baseline]
    eval_mask = np.array([truth[rid]['is_eval'] for rid in order])
    true_groups = np.array([truth[rid]['root'] for rid in order])[eval_mask]
    true_child = np.array([truth[rid]['parent'] is not None for rid in order])[eval_mask]
    assert int(eval_mask.sum()) > 1
    clean_roles, clean_groups, clean_children = aligned_predictions(baseline, cut, order)
    values = []
    for scenario, changed in [('gaussian', whole_gaussian), ('candidate_resampling', empirical)]:
        replacements = [changed[i] for i in selected]
        for cell in CELLS:
            if cell == '000':
                roles, groups, children = clean_roles, clean_groups, clean_children
            else:
                inp = mixed_rows(baseline, replacements, cell)
                assert all(row['magnitude'] >= 4.5 for row in inp)
                roles, groups, children = aligned_predictions(inp, cut, order)
            new_groups = groups[eval_mask]
            inferred_child = children[eval_mask]
            tp = int(np.sum(true_child & inferred_child))
            denominator = int(np.sum(true_child) + np.sum(inferred_child))
            values.append(dict(branching=branch, seed=seed, scenario=scenario, cell=cell,
                               common_context=len(selected), evaluation=int(eval_mask.sum()),
                               changed_roles=int(np.sum(clean_roles[eval_mask] != roles[eval_mask])),
                               partition_ARI_between_views=partition_comparison(clean_groups[eval_mask], new_groups)['ARI'],
                               partition_ARI_against_truth=partition_comparison(true_groups, new_groups)['ARI'],
                               generated_child_F1=2*tp/denominator if denominator else None))
    gaussian_vectors = measurements(clean, whole_gaussian)
    gaussian_all_eval = [v for r, v in zip(clean, gaussian_vectors, strict=True) if truth[r['record_id']]['is_eval']]
    gaussian_4p5_eval = [v for a, b, v in zip(clean, whole_gaussian, gaussian_vectors, strict=True)
                         if truth[a['record_id']]['is_eval'] and min(a['magnitude'], b['magnitude']) >= 4.5]
    return values, (gaussian_all_eval, gaussian_4p5_eval), draw.tolist()


def mean_ci(values):
    v = np.asarray([x for x in values if x is not None], dtype=float)
    if len(v) < 2:
        return dict(n=len(v), mean=float(v[0]) if len(v) else None, CI95_MC=None)
    mean = float(v.mean())
    half = float(t.ppf(.975, len(v)-1) * v.std(ddof=1) / np.sqrt(len(v)))
    return dict(n=len(v), mean=mean, CI95_MC=[mean-half, mean+half])


def main():
    capabilities = load(TWINS / 'PROTOCOL_TWINS_V1.json')['randomness']
    threshold = load(TWINS_RUN / 'CALIBRATION.json')['0000']['fit']['threshold_log10']
    set_num_threads(1)
    vectors, observed, rows_a, rows_b = observed_pool()
    factorial_observed = replay_observed(rows_a, rows_b)
    print('Observed pools and sixteen factorial cells verified.', flush=True)
    histories, draws, gaussian_all_eval, gaussian_4p5_eval = [], {}, [], []
    for branch, stream in [(0.0, 'test_seeds_branching_0'), (0.6, 'test_seeds_branching_0p6')]:
        for seed in capabilities[stream]:
            path = TWINS_RUN / f'test_b{branch}_{seed}'
            result, gaussian, draw = synthetic_one(path, seed, branch, vectors, threshold)
            histories.extend(result)
            gaussian_all_eval += gaussian[0]
            gaussian_4p5_eval += gaussian[1]
            draws[str(seed)] = draw
        print(f'Branch {branch}: thirty histories complete.', flush=True)
    assert len(histories) == 960 and len(draws) == 60
    assert all(x['changed_roles'] == 0 and x['partition_ARI_between_views'] == 1 for x in histories if x['cell'] == '000')
    summary = []
    for branch, scenario, cell in product((0.0, 0.6), ('gaussian', 'candidate_resampling'), CELLS):
        group = [x for x in histories if (x['branching'], x['scenario'], x['cell']) == (branch, scenario, cell)]
        assert len(group) == 30
        summary.append(dict(branching=branch, scenario=scenario, cell=cell,
                            evaluation_keys=sum(x['evaluation'] for x in group),
                            evaluation_key_range=[min(x['evaluation'] for x in group), max(x['evaluation'] for x in group)],
                            role_change_fraction=mean_ci([x['changed_roles']/x['evaluation'] for x in group]),
                            partition_ARI_between_views=mean_ci([x['partition_ARI_between_views'] for x in group]),
                            partition_ARI_against_truth=mean_ci([x['partition_ARI_against_truth'] for x in group]),
                            generated_child_F1=mean_ci([x['generated_child_F1'] for x in group])))
    with (HERE / 'HISTORY_CELL_METRICS.csv').open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(histories[0]))
        writer.writeheader()
        writer.writerows(histories)
    save(HERE / 'SAMPLED_PAIR_INDICES.json', draws)
    result = dict(status='PASS_REPLAY_AND_COMMON_MEMBER_SENSITIVITY',
                  threads=1, threshold_log10=threshold,
                  parent_kernel_sha256=sha_file(METHODS.parent / "index/spherical_weighted_v2.py"),
                  detector_sha256=sha_file(METHODS / "deterministic_families.py"),
                  observed_pool=observed, observed_factorial=factorial_observed,
                  gaussian_as_applied=dict(all_evaluation=descriptive(gaussian_all_eval),
                                           m4p5_both_evaluation=descriptive(gaussian_4p5_eval)),
                  synthetic_factorial=summary)
    save(HERE / 'RESULTS.json', result)
    print('PASS. See RESULTS.json and HISTORY_CELL_METRICS.csv.', flush=True)

