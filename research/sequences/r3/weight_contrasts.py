"""Recalculate the weight and cutoff contrasts from the retained numerical arrays."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import csv
import hashlib
import json
import math
import sys

import numpy as np

PACKAGE = Path(__file__).resolve().parent
CATALOG_SUBPATH = Path("outputs/claude_round2_2026-11-17/science/catalog")
CASES_SUBPATH = Path("outputs/claude_response_2026-11-16/methods/deterministic_study_v3")


def configure(workspace, output):
    global ROOT, CAT, RUN, V3, HERE, families_from_cut
    ROOT = workspace / "source_layout"
    CAT = ROOT / CATALOG_SUBPATH
    RUN = workspace / "expected" / CATALOG_SUBPATH / "runs/run_01"
    V3 = ROOT / CASES_SUBPATH
    HERE = output
    sys.path.insert(0, str(CAT / "vendor"))
    from deterministic_families import families_from_cut


def read_json(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put_json(path, data):
    with path.open('x', encoding='utf-8') as out:
        out.write(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + '\n')


def put_csv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as source:
        return list(csv.DictReader(source))


def classify(case, cut):
    parent, eta, m, t, ids = (case[x] for x in ['parent_index', 'cut_score', 'reported_magnitude', 't_year', 'ids'])
    return families_from_cut(parent, eta, m, t, ids, cut, inclusive=True)


def case_arrays(path):
    ids, rows, metadata = (read_json(path / name) for name in ['ids.json', 'rows.json', 'metadata.json'])
    with np.load(path / 'arrays.npz', allow_pickle=False) as archive:
        arrays = dict(archive.items())
    assert ids == [row['record_id'] for row in rows]
    assert sha(path / 'arrays.npz') == metadata['arrays_sha256']
    with np.errstate(divide='ignore', invalid='ignore'):
        score = np.log10(arrays['TN']) + np.log10(arrays['RN'])
    arrays.update(ids=ids, rows=rows, metadata=metadata, cut_score=score)
    return arrays


def stats(data):
    if not len(data):
        return None
    p = np.quantile(data, [0., .25, .5, .75, .95, 1.])
    return dict(zip(('min', 'q25', 'median', 'q75', 'q95', 'max'), map(float, p)))


def biggest(labels):
    sizes = np.bincount(labels['component_root_index'])
    return int(np.argmax(sizes)), int(np.max(sizes))


def pct(i, n):
    return round(100 * i / n, 8) if n else None


input_hashes = {}
def track(path, expected=None):
    digest = sha(path)
    if expected is not None:
        assert digest == expected, path
    input_hashes[path] = digest


def main():
    assert not (HERE / 'RESULTS.json').exists()
    manifest = read_json(RUN / 'MANIFEST.json')
    assert manifest['status'] == 'PASS'
    track(RUN / 'MANIFEST.json')
    track(CAT / 'vendor/deterministic_families.py')
    track(RUN / 'PAIRED_ENDPOINTS.csv')
    expected_outputs = {e['path']: e['sha256'] for e in manifest['output_files']}
    track(RUN / 'PAIRED_ENDPOINTS.csv', expected_outputs['PAIRED_ENDPOINTS.csv'])
    case_dirs = sorted((RUN / 'cases').iterdir())
    assert len(case_dirs) == 18
    cases = {}
    for case_dir in case_dirs:
        for filename in ['arrays.npz', 'rows.json', 'ids.json', 'metadata.json']:
            rel = (case_dir / filename).relative_to(RUN).as_posix()
            track(case_dir / filename, expected_outputs[rel])
        case = case_arrays(case_dir)
        meta = case['metadata']
        assert meta['d'] == 1.6 and meta['q'] == .5
        labels = classify(case, meta['fit']['threshold_log10'])
        for field in ['roles', 'component_root_index', 'retained_parent_index', 'strong_link_mask']:
            assert np.array_equal(labels[field], case['delta_0_' + field]), (case_dir, field)
        cases[meta['source'], float(meta['w'])] = case
    original = {source: cases[source, 1.] for source in ['ssn','usgs']}
    idx = {s: {key: i for i,key in enumerate(original[s]['ids'])} for s in original}
    pairs = read_csv(RUN / 'PAIRED_ENDPOINTS.csv')
    selection = {s: np.array([idx[s][p[s+'_record_id']] for p in pairs]) for s in original}
    evaluation = np.array([p['year'] >= '2021' for p in pairs])
    assert len(pairs) == 889 and evaluation.sum() == 382
    for (s,_), case in cases.items():
        assert case['ids'] == original[s]['ids']

    def compare(labels, include=None):
        keep = np.ones(len(pairs), bool) if include is None else include
        a,b = [labels[s]['roles'][selection[s]] for s in original]
        n, matches = int(keep.sum()), int((keep & (a == b)).sum())
        return dict(n=n, equal=matches, percent=pct(matches,n))

    def cut(source, w, mode):
        if mode == 'refit':
            return cases[source,w]['metadata']['fit']['threshold_log10']
        c1 = original[source]['metadata']['fit']['threshold_log10']
        if mode == 'fixed_w1':
            return c1
        if mode == 'centered_at_floor':
            return c1 - 4.5 * (w - 1.)
        return cases[source,float(mode.removeprefix('w'))]['metadata']['fit']['threshold_log10']

    def evaluate(w, mode):
        z = {s: classify(cases[s,w], cut(s,w,mode)) for s in original}
        full, held = compare(z), compare(z,evaluation)
        results = dict(weight=w, cut_mode=mode, full_matches=full['equal'], full_n=full['n'], full_pct=full['percent'],
                       evaluation_matches=held['equal'], evaluation_n=held['n'], evaluation_pct=held['percent'])
        for s in original:
            results.update({s+'_threshold':cut(s,w,mode),s+'_largest':biggest(z[s])[1], s+'_native_total':len(original[s]['ids']),
                            s+'_retained_edges':int(z[s]['strong_link_mask'].sum()),
                            s+'_mode_count_refit':cases[s,w]['metadata']['diagnostics']['mode_count']})
        return results,z

    sweep = [evaluate(w,mode)[0] for w in sorted({w for _,w in cases}) for mode in ['refit','fixed_w1','centered_at_floor']]
    cross = [evaluate(w,mode)[0] for w in [1.2,1.3] for mode in ['w1.2','w1.3']]
    _, labels_before = evaluate(1.2,'refit')
    _, labels_after = evaluate(1.3,'refit')
    before, after = labels_before['ssn'], labels_after['ssn']
    largest_root, largest_n = biggest(after)
    component = after['component_root_index'] == largest_root
    s = cases['ssn',1.3]
    old_par = cases['ssn',1.2]['parent_index']
    edge_rows = []
    for i in np.flatnonzero(component & after['strong_link_mask']):
        j = s['parent_index'][i]
        edge_rows.append(dict(child_id=s['ids'][i], parent_id=s['ids'][j], child_utc=s['rows'][i]['time_utc'], parent_utc=s['rows'][j]['time_utc'],
                              child_M=float(s['reported_magnitude'][i]), parent_M=float(s['reported_magnitude'][j]),
                              distance_km=float(s['parent_distance_km'][i]), lag_days=float((s['t_year'][i]-s['t_year'][j])*365.25),
                              both_same_w12_component=bool(before['component_root_index'][i]==before['component_root_index'][j]),
                              previously_retained_same_edge=bool(before['retained_parent_index'][i]==j), parent_changed=bool(old_par[i]!=j)))
    assert len(edge_rows) == largest_n-1
    bridge = [e for e in edge_rows if not e['both_same_w12_component']]
    assert bridge and not any(e['previously_retained_same_edge'] for e in bridge)
    prior_components = Counter(before['component_root_index'][component])
    parent_counts = Counter(e['parent_id'] for e in edge_rows)
    def edge_summary(edges):
        return dict(n=len(edges), parent_M=stats([e['parent_M'] for e in edges]),
                    distance_km=stats([e['distance_km'] for e in edges]),lag_days=stats([e['lag_days'] for e in edges]),
                    parent_changes=sum(e['parent_changed'] for e in edges),
                    parent_M7_or_higher=sum(e['parent_M']>=7. for e in edges))
    influential = []
    for rid,count in parent_counts.most_common(8):
        i=idx['ssn'][rid]
        es = [e for e in edge_rows if e['parent_id']==rid]
        influential.append(dict(parent_id=rid,utc=s['rows'][i]['time_utc'],M=float(s['reported_magnitude'][i]),direct_children=count,
                                direct_children_at_w12=int(np.count_nonzero(before['retained_parent_index']==i)),
                                bridge_summary=edge_summary([e for e in es if not e['both_same_w12_component']]), all_edges=edge_summary(es)))
    biggest_members = np.flatnonzero(component)
    main = int(np.flatnonzero(component & (after['roles']==1))[0])
    component_result = dict(records=largest_n, source_total=len(s['ids']), root=dict(id=s['ids'][largest_root], M=float(s['reported_magnitude'][largest_root]),
                            utc=s['rows'][largest_root]['time_utc']), representative=dict(id=s['ids'][main],M=float(s['reported_magnitude'][main]),
                            utc=s['rows'][main]['time_utc']), time_span_days=float((s['t_year'][biggest_members[-1]]-s['t_year'][biggest_members[0]])*365.25),
                            number_of_intersecting_w12_components=len(prior_components),largest_intersections=sorted(prior_components.values(),reverse=True)[:8],
                            all_retained_edges=edge_summary(edge_rows), bridging_edges=edge_summary(bridge), largest_direct_parents=influential)

    inputs = {e['path']:e['sha256'] for e in read_json(CAT/'INPUTS.json')}
    lookup = {}
    for s in original:
        raw = f'outputs/sequence_pilot_2026-11-15/inputs/{s}.csv'
        track(ROOT/raw,inputs[raw]);lookup[s]={row['record_id']:row for row in read_csv(ROOT/raw)}
    pair_path = ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json'
    track(pair_path,inputs[pair_path.relative_to(ROOT).as_posix()]);matched = read_json(pair_path);assert len(matched)==2989
    m_a = np.array([Decimal(lookup['ssn'][p['ssn_record_id']]['magnitude']) for p in matched],object)
    m_b = np.array([Decimal(lookup['usgs'][p['usgs_record_id']]['magnitude']) for p in matched],object)
    difference = np.asarray(m_a-m_b,float)
    large_a = m_a>Decimal('5.2');large_b = m_b>Decimal('5.2')
    base = evaluate(1.,'refit')[1]
    role_masks = {
        'SSN M<=5.2':np.array([Decimal(original['ssn']['rows'][i]['magnitude'])<=Decimal('5.2') for i in selection['ssn']]),
        'SSN M>5.2':np.array([Decimal(original['ssn']['rows'][i]['magnitude'])>Decimal('5.2') for i in selection['ssn']]),
        'opposite sides':np.array([(Decimal(original['ssn']['rows'][i]['magnitude'])>Decimal('5.2')) != (Decimal(original['usgs']['rows'][j]['magnitude'])>Decimal('5.2')) for i,j in zip(selection['ssn'],selection['usgs'])]),
    }
    strata = []
    for name, mask in [('SSN M<=5.2',~large_a),('SSN M>5.2',large_a),('opposite sides',large_a!=large_b)]:
        types = Counter(lookup['usgs'][matched[i]['usgs_record_id']]['magnitude_type'] for i in np.flatnonzero(mask))
        strata.append(dict(stratum=name,pair_n=int(mask.sum()),signed_SSN_minus_ComCat=stats(difference[mask]),
                           absolute_difference=stats(abs(difference[mask])),absolute_difference_ge_0_3=int((abs(difference[mask])>=.3).sum()),
                           observed_ComCat_type_counts=dict(types),roles_on_both_M_ge_4_5=compare(base,role_masks[name]),
                           roles_on_both_M_ge_4_5_evaluation=compare(base,role_masks[name]&evaluation)))

    track(V3/'PAIRED_METRICS.json')
    d_alt, d_fixed = {},{}
    parent_changes = {}
    for source in original:
        case_path=PACKAGE/'inputs/d1p5/cases'/f'M4p5_{source}_native_d1p5'
        for name in ['arrays.npz','rows.json','ids.json','metadata.json']:
            track(case_path/name)
        case = case_arrays(case_path)
        assert case['metadata']['d']==1.5 and case['metadata']['w']==1. and case['ids']==original[source]['ids']
        assert sha(case_path/'ids.json')==case['metadata']['ids_sha256']
        if 'reported_magnitude' not in case:
            case['reported_magnitude'] = original[source]['reported_magnitude']
        if 't_year' not in case:
            case['t_year'] = original[source]['t_year']
        d_alt[source] = classify(case, case['metadata']['fit']['threshold_log10'])
        d_fixed[source] = classify(case, cut(source,1.,'refit'))
        assert np.array_equal(d_alt[source]['roles'],case['roles'])
        p, p0 = case['parent_index'],original[source]['parent_index']
        eligible=(p>=0)&(p0>=0)
        parent_changes[source]=dict(changed=int(((p!=p0)&eligible).sum()),both_defined=int(eligible.sum()),
                                    d1p5_threshold=case['metadata']['fit']['threshold_log10'],
                                    d1p5_fit_modes=case['metadata']['mixture_diagnostics']['mode_count'])
    prior = read_json(V3/'PAIRED_METRICS.json')['M4p5_native_d1p5']
    assert abs(compare(d_alt)['percent']-prior['full_descriptive']['agreement']*100)<1e-7
    assert abs(compare(d_alt,evaluation)['percent']-prior['held_out_2021_2025']['agreement']*100)<1e-7
    assert compare(base)['equal']==772
    _, b_cross_labels = evaluate(1.0905428994843476,'refit')
    d_result=dict(d_1_5_refit=compare(d_alt),d_1_5_refit_evaluation=compare(d_alt,evaluation),
                  d_1_5_original_d_1_6_cut=compare(d_fixed),d_1_5_original_d_1_6_cut_evaluation=compare(d_fixed,evaluation),
                  d_1_6_w_1_refit=compare(base),d_1_6_w_1_refit_evaluation=compare(base,evaluation),
                  d_1_6_low_low_apparent_b=compare(b_cross_labels),d_1_6_low_low_apparent_b_evaluation=compare(b_cross_labels,evaluation),
                  change_in_parent_choices=parent_changes)
    assert d_result['d_1_5_refit']['equal']==d_result['d_1_6_low_low_apparent_b']['equal']==786

    split2017 = np.array([p['year']=='2017' for p in pairs])
    anchor2017 = np.array([p['excluded_fixed_2017']=='True' for p in pairs])
    year2017 = dict(all_2017=compare(base,split2017),anchor_union_2017=compare(base, split2017&anchor2017),
                    outside_anchor_union_2017=compare(base,split2017&~anchor2017))
    floor_m = math.acos(math.nextafter(1.0,0.0))*6367300.0
    assert all(sha(p) == h for p, h in input_hashes.items())
    put_csv(HERE/'WEIGHT_CUT_SWEEP.csv',sweep+cross)
    put_csv(HERE/'SSN_W13_LARGEST_COMPONENT_EDGES.csv',edge_rows)
    put_json(HERE/'RESULTS.json',dict(status='PASS_RETAINED_RECLASSIFICATION_AND_RECALCULATED_STRATA',
             sweep=sweep,local_weight_by_cut=cross,
             largest_ssn_component_w13_refit=component_result,reported_magnitude_strata=strata,d_sensitivity=d_result,
             annual_2017_anchor_context=year2017,cosine_law_floor_m=floor_m,
             source_geometry_changed=False,large_cohort_colocation_ablation=False))
    print(json.dumps(dict(status='PASS',d_sensitivity=d_result,cosine_law_floor_m=floor_m,
                          weights=[r for r in sweep if r['weight'] in [1.2,1.3]],largest_component=component_result,
                          reported_magnitude_strata=strata,annual_2017_anchor_context=year2017), indent=2))

