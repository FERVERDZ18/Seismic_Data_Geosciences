"""Post-review deterministic catalogue comparisons, not physical truth labels."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from collections import Counter
import csv
import hashlib
import itertools
import json
import math
import os
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
INDEX=HERE.parent/'index'
os.environ.setdefault('NUMBA_CACHE_DIR',str(INDEX/'numba_gc_cache'))
sys.dont_write_bytecode=True
sys.path[:0]=[str(HERE),str(INDEX),str(PILOT/'comparators/nearest_neighbor/_deps'),str(PILOT/'comparators/carluccio/_deps')]
from spherical_weighted_v2 import np,prepare_rows,run_arrays,set_num_threads,utc_microseconds
from deterministic_families import families_from_cut
from author_normalmix_port import author_normalmix


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,value):Path(p).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def label_number(x):return f'{x:.12g}'.replace('.','p')


def partition_comparison(a,b):
    """ARI and pairwise overlap of two partitions; neither is declared truth."""
    choose=lambda k:k*(k-1)//2
    ca,cb,cab=Counter(map(int,a)),Counter(map(int,b)),Counter(zip(map(int,a),map(int,b)))
    na,nb,joint=sum(map(choose,ca.values())),sum(map(choose,cb.values())),sum(map(choose,cab.values()))
    n=len(a);total=choose(n)
    expected=na*nb/total if total else 0.;maximum=(na+nb)/2.
    return dict(ARI=(joint-expected)/(maximum-expected) if maximum!=expected else 1.,
        n=n,coassigned_pairs_first=na,coassigned_pairs_second=nb,coassigned_pairs_both=joint,
        overlap_fraction_of_first=joint/na if na else None,
        overlap_fraction_of_second=joint/nb if nb else None,
        interpretation='Partition agreement on retained candidate endpoints, not accuracy or validated event identity')


def comparison(a,b,groups_a,groups_b):
    a,b=np.asarray(a),np.asarray(b)
    matrix=np.asarray([[int(np.sum((a==i)&(b==j))) for j in range(3)] for i in range(3)])
    n=int(matrix.sum())
    observed=float(np.trace(matrix)/n) if n else None
    expected=float(np.dot(matrix.sum(axis=0),matrix.sum(axis=1))/n**2) if n else None
    return dict(n=n,agreement=observed,kappa=(observed-expected)/(1-expected) if n and expected<1 else None,
        labels=['isolated','operational main','associated'],matrix_first_rows_second_columns=matrix.tolist(),
        first_marginal=matrix.sum(axis=1).tolist(),second_marginal=matrix.sum(axis=0).tolist(),
        partition=partition_comparison(groups_a,groups_b))


def mixture_diagnostics(fit,values):
    x=np.asarray(values);x=x[np.isfinite(x)]
    if fit['status']!='estimable':return dict(status='not_estimable',reason=fit.get('reason'))
    means=np.asarray(fit['means']);sigmas=np.asarray(fit['sigmas']);weights=np.asarray(fit['weights'])
    grid=np.linspace(min(np.min(x),np.min(means-6*sigmas)),max(np.max(x),np.max(means+6*sigmas)),16385)
    density=sum(weights[k]/(sigmas[k]*np.sqrt(2*np.pi))*np.exp(-.5*((grid-means[k])/sigmas[k])**2) for k in range(2))
    peaks=np.flatnonzero((density[1:-1]>density[:-2])&(density[1:-1]>density[2:]))+1
    likelihood2=float(np.sum(np.log(sum(weights[k]/(sigmas[k]*np.sqrt(2*np.pi))*np.exp(-.5*((x-means[k])/sigmas[k])**2) for k in range(2)))))
    variance=float(np.var(x));likelihood1=float(np.sum(-.5*(math.log(2*np.pi*variance)+(x-float(np.mean(x)))**2/variance)))
    bic1=2*math.log(len(x))-2*likelihood1;bic2=5*math.log(len(x))-2*likelihood2
    return dict(status='diagnosed',mode_count=int(len(peaks)),mode_locations=grid[peaks].tolist(),
        BIC_one=bic1,BIC_two=bic2,two_mode_BIC_guard_passed=bool(len(peaks)==2 and bic2<bic1),
        guard_does_not_change_author_cut_or_hide_operational_output=True)


def development_mask(rows):return np.asarray([r['time_utc']<'2021-01-01' for r in rows],dtype=bool)


def empirical_reported_b(rows,cut):
    mags=[float(Decimal(r['magnitude']).quantize(Decimal('.1'),rounding=ROUND_HALF_UP)) for r in rows if r['time_utc']<'2021-01-01']
    return math.log10(math.e)/(float(np.mean(mags))-(cut-.05))


def calculate(rows,d,w):
    prepared=prepare_rows(rows)
    result=run_arrays(prepared['t_year'],prepared['lat_deg'],prepared['lon_deg'],prepared['m'],d=d,w=w,backend='kd')
    return prepared,result


def make_labels(prepared,result,cut):
    with np.errstate(divide='ignore',invalid='ignore'):
        score=np.log10(result['TN'])+np.log10(result['RN'])
    return families_from_cut(result['parent_index'],score,prepared['m'],prepared['t_year'],prepared['ids'],cut,inclusive=True)


def save_case(destination,prepared,result,fit,diagnostics,labels,metadata):
    destination.mkdir(parents=True)
    dump(destination/'ids.json',prepared['ids']);dump(destination/'rows.json',prepared['source_rows'])
    fields={k:result[k] for k in ('parent_index','eta_native_seconds_metres','eta_log10','eta_log10_sum','T_log10','R_log10','TN','RN','parent_dt_years','parent_distance_km')}
    fields.update(t_year=prepared['t_year'],latitude=prepared['lat_deg'],longitude=prepared['lon_deg'],reported_magnitude=prepared['m'])
    if labels is not None:fields.update({k:v for k,v in labels.items() if isinstance(v,np.ndarray)})
    np.savez_compressed(destination/'arrays.npz',**fields)
    metadata.update(events=len(prepared['ids']),fit=fit,mixture_diagnostics=diagnostics,kernel_metadata=result['metadata'],
                    role_counts={str(i):int(np.sum(labels['roles']==i)) for i in range(3)} if labels is not None else None,
                    arrays_sha256=sha(destination/'arrays.npz'),ids_sha256=sha(destination/'ids.json'),
                    interpretation='Operational statistical families; no physical truth or calibrated magnitude equivalence')
    dump(destination/'metadata.json',metadata)


def pair_metrics(a,b,pairs,lookup):
    ia={v:i for i,v in enumerate(a['prepared']['ids'])};ib={v:i for i,v in enumerate(b['prepared']['ids'])}
    retained=[p for p in pairs if p['ssn_record_id'] in ia and p['usgs_record_id'] in ib]
    if a['labels'] is None or b['labels'] is None:return dict(status='not_estimable',retained=len(retained))
    si=np.asarray([ia[p['ssn_record_id']] for p in retained],dtype=int)
    ui=np.asarray([ib[p['usgs_record_id']] for p in retained],dtype=int)
    years=np.asarray([lookup['ssn'][p['ssn_record_id']]['time_utc'][:4] for p in retained])
    def at(mask):
        s,u=si[mask],ui[mask]
        return comparison(a['labels']['roles'][s],b['labels']['roles'][u],a['labels']['component_root_index'][s],b['labels']['component_root_index'][u])
    counts=Counter('both' if p['ssn_record_id'] in ia and p['usgs_record_id'] in ib else 'ssn_only' if p['ssn_record_id'] in ia else 'usgs_only' if p['usgs_record_id'] in ib else 'neither' for p in pairs)
    return dict(status='computed',retention=dict(counts),full_descriptive=at(np.ones(len(si),dtype=bool)),
                held_out_2021_2025=at(years>='2021'),development_2016_2020=at(years<'2021'),
                by_year={y:at(years==y) for y in sorted(set(years))},candidate_identity_not_validated=True)


def main():
    target=HERE/'deterministic_study_v3'
    if target.exists():raise FileExistsError('Never overwrite completed or failed study evidence')
    target.mkdir()
    set_num_threads(1)
    started=time.perf_counter()
    original={}
    for source in ['ssn','usgs']:
        with (PILOT/'inputs'/f'{source}.csv').open(encoding='utf-8-sig',newline='') as f:original[source]=list(csv.DictReader(f))
    lookup={s:{r['record_id']:r for r in rows} for s,rows in original.items()}
    pair_path=ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json'
    pairs=json.loads(pair_path.read_text(encoding='utf-8'))
    cases={};metrics={};case_manifest=[]
    for cut in [4.5,4.4,4.1]:
        selected={s:[r for r in rows if Decimal(r['magnitude'])>=Decimal(str(cut))] for s,rows in original.items()}
        membership={s:{r['record_id'] for r in rows} for s,rows in selected.items()}
        common_pairs=[p for p in pairs if p['ssn_record_id'] in membership['ssn'] and p['usgs_record_id'] in membership['usgs']]
        common_ids={s:{p[f'{s}_record_id'] for p in common_pairs} for s in original}
        for mode in ['author','d1p5','w_reported_b']:
            for source in ['ssn','usgs']:
                d=1.5 if mode=='d1p5' else 1.6
                w=empirical_reported_b(selected[source],cut) if mode=='w_reported_b' else 1.
                native_fit=None;native_diagnostics=None
                for cohort in ['native','common']:
                    rows=selected[source] if cohort=='native' else [r for r in selected[source] if r['record_id'] in common_ids[source]]
                    name=f'M{label_number(cut)}_{source}_{cohort}_{mode}'
                    prepared,result=calculate(rows,d,w)
                    train=development_mask(prepared['source_rows'])
                    local_fit=author_normalmix(result['eta_log10'][train])
                    diagnostics=mixture_diagnostics(local_fit,result['eta_log10'][train])
                    if cohort=='native':native_fit=local_fit;native_diagnostics=diagnostics
                    used=native_fit
                    labels=make_labels(prepared,result,used['threshold_log10']) if used['status']=='estimable' else None
                    case=dict(prepared=prepared,result=result,labels=labels,fit=used,local_fit=local_fit)
                    cases[name]=case
                    metadata=dict(name=name,cut=cut,source=source,cohort=cohort,parameter_mode=mode,d=d,w=w,
                                  calibration='native-development cutoff frozen; common membership alone does not refit',
                                  local_fit_if_refit_development=local_fit,local_fit_diagnostics=diagnostics,
                                  protocol_sha256=sha(HERE/'DETERMINISTIC_STUDY_PROTOCOL.md'))
                    save_case(target/'cases'/name,prepared,result,used,native_diagnostics,labels,metadata)
                    case_manifest.append(dict(case=name,directory=f'cases/{name}',events=len(rows),cut=cut,source=source,cohort=cohort,d=d,w=w))
                    if cohort=='common' and local_fit['status']=='estimable':
                        name_refit=name+'_refit'
                        refit_labels=make_labels(prepared,result,local_fit['threshold_log10'])
                        cases[name_refit]={**case,'labels':refit_labels,'fit':local_fit}
                        save_case(target/'cases'/name_refit,prepared,result,local_fit,diagnostics,refit_labels,
                                  {**metadata,'name':name_refit,'calibration':'common-development cutoff refit, then frozen'})
            for cohort in ['native','common','common_refit']:
                left=f'M{label_number(cut)}_ssn_{cohort.replace("_refit","")}_{mode}'+('_refit' if cohort.endswith('_refit') else '')
                right=left.replace('_ssn_','_usgs_')
                if left in cases and right in cases:metrics[f'M{label_number(cut)}_{cohort}_{mode}']=pair_metrics(cases[left],cases[right],pairs,lookup)
        print(json.dumps(dict(cut=cut,source_counts={s:len(v) for s,v in selected.items()},common_candidate_pairs=len(common_pairs))),flush=True)
    # Controlled measurement factorial at the primary common membership.
    common=cases['M4p5_ssn_common_author']
    cp=[p for p in pairs if p['ssn_record_id'] in set(common['prepared']['ids']) and p['usgs_record_id'] in set(cases['M4p5_usgs_common_author']['prepared']['ids'])]
    pair_for={p['ssn_record_id']:p for p in cp}
    baseline_ids=common['prepared']['ids'];baseline_rows=common['prepared']['source_rows']
    eval_mask=np.asarray([r['time_utc']>='2021-01-01' for r in baseline_rows])
    factorial=[]
    for flags in itertools.product([0,1],repeat=3):
        hybrids=[]
        for row in baseline_rows:
            replacement=lookup['usgs'][pair_for[row['record_id']]['usgs_record_id']]
            mixed=dict(row)
            for flag,fields in zip(flags,[['time_utc'],['latitude','longitude'],['magnitude']]):
                if flag:
                    for field in fields:mixed[field]=replacement[field]
            mixed['source']='computational_intervention';hybrids.append(mixed)
        prepared,result=calculate(hybrids,1.6,1.)
        positions={v:i for i,v in enumerate(prepared['ids'])}
        canonical=np.asarray([positions[v] for v in baseline_ids])
        name=''.join(map(str,flags))
        for cut_source in ['ssn','usgs']:
            fitted=cases[f'M4p5_{cut_source}_native_author']['fit']
            if fitted['status']!='estimable':continue
            labels=make_labels(prepared,result,fitted['threshold_log10'])
            baseline=make_labels(common['prepared'],common['result'],fitted['threshold_log10'])
            a,b=baseline['roles'],labels['roles'][canonical]
            ga,gb=baseline['component_root_index'],labels['component_root_index'][canonical]
            item=dict(measurement_flags_time_location_magnitude=list(flags),cut_source=cut_source,
                      fixed_cut=fitted['threshold_log10'],all=comparison(a,b,ga,gb),
                      held_out_2021_2025=comparison(a[eval_mask],b[eval_mask],ga[eval_mask],gb[eval_mask]),
                      synthetic_intervention_not_new_observed_catalogue=True)
            factorial.append(item)
            save_case(target/'factorial'/f'{name}_cut_{cut_source}',prepared,result,fitted,{},labels,item.copy())
    dump(target/'PAIRED_METRICS.json',metrics)
    dump(target/'MEASUREMENT_FACTORIAL.json',factorial)
    calibration={'schema':'deterministic-family-development-calibration/1','cuts':{},
                 'd':1.6,'w':1.,'fit_score':'log10(TN*RN)','edge_cut_score':'log10(TN)+log10(RN)',
                 'keep_edge_when':'score <= threshold_log10','time_origin_utc':'2016-01-01T00:00:00Z',
                 'magnitude_policy':'reported M; no Mw harmonization or physical b calibration',
                 'protocol_sha256':sha(HERE/'DETERMINISTIC_STUDY_PROTOCOL.md')}
    with (PILOT/'inputs/alaska_usgs.csv').open(encoding='utf-8-sig',newline='') as f:alaska=list(csv.DictReader(f))
    for cut in [4.5,4.4,4.1,3.5]:
        output={}
        for source in ['ssn','usgs','alaska']:
            end='2023-01-01' if source=='alaska' else '2021-01-01'
            if source!='alaska' and cut!=3.5:
                case=cases[f'M{label_number(cut)}_{source}_native_author']
                prepared,result=case['prepared'],case['result']
                mask=np.asarray([r['time_utc']<end for r in prepared['source_rows']])
                fit=case['fit'];diagnostics=mixture_diagnostics(fit,result['eta_log10'][mask])
            else:
                rows=alaska if source=='alaska' else original[source]
                rows=[r for r in rows if Decimal(r['magnitude'])>=Decimal(str(cut)) and r['time_utc']<end]
                prepared,result=calculate(rows,1.6,1.)
                fit=author_normalmix(result['eta_log10']);diagnostics=mixture_diagnostics(fit,result['eta_log10'])
                mask=np.ones(len(rows),dtype=bool)
                destination=target/'calibration_inputs'/f'M{label_number(cut)}_{source}'
                labels=make_labels(prepared,result,fit['threshold_log10']) if fit['status']=='estimable' else None
                save_case(destination,prepared,result,fit,diagnostics,labels,
                          dict(name=f'calibration_M{cut}_{source}',training_end_exclusive=end))
            output[source]={**fit,'diagnostics':diagnostics,'training_events':int(mask.sum()),
                            'training_end_exclusive':end,'source':'alaska_usgs' if source=='alaska' else source,
                            'threshold_log10':fit.get('threshold_log10')}
        calibration['cuts'][str(cut)]=output
    dump(HERE/'calibration_v3.json',calibration)
    metadata=dict(schema='post-review-deterministic-sequence-comparison/1',protocol_sha256=sha(HERE/'DETERMINISTIC_STUDY_PROTOCOL.md'),
                  source_inputs={s:sha(PILOT/'inputs'/f'{s}.csv') for s in original},pairs_sha256=sha(pair_path),
                  script_sha256=sha(__file__),index_script_sha256=sha(INDEX/'spherical_weighted_v2.py'),
                  EM_port_sha256=sha(HERE/'author_normalmix_port.py'),cases=case_manifest,
                  full_descriptive_period='2016-2025',fit_only='2016-2020',held_out='2021-2025',
                  physical_event_identity_validated=False,physical_family_truth_validated=False,
                  elapsed_seconds=time.perf_counter()-started,case_count=len(cases),factorial_cells=len(factorial))
    dump(target/'MANIFEST.json',metadata)
    print(json.dumps(dict(status='computed',cases=len(cases),factorial_cells=len(factorial),seconds=metadata['elapsed_seconds'],
                         primary=metrics.get('M4p5_native_author')),indent=2))


if __name__=='__main__':main()
