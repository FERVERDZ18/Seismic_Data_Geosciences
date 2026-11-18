"""Post-review diagnostic crossing of two fixed numerical magnitude weights."""
from pathlib import Path
import json
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from run_deterministic_study_v3 import np,calculate,make_labels,author_normalmix,mixture_diagnostics,save_case,pair_metrics,dump,sha,set_num_threads

LOW=1.0905428994843476
HIGH=1.3265675928192793


def load_existing(source,cohort):
    folder=HERE/'deterministic_study_v3/cases'/f'M4p5_{source}_{cohort}_w_reported_b'
    rows=json.loads((folder/'rows.json').read_text(encoding='utf-8'))
    ids=json.loads((folder/'ids.json').read_text(encoding='utf-8'))
    data=dict(np.load(folder/'arrays.npz'))
    metadata=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    prepared=dict(ids=ids,source_rows=rows,m=data['reported_magnitude'],t_year=data['t_year'])
    result={k:data[k] for k in ['parent_index','eta_log10','eta_log10_sum','TN','RN']}
    labels=make_labels(prepared,result,metadata['fit']['threshold_log10']) if metadata['fit']['status']=='estimable' else None
    return dict(prepared=prepared,result=result,labels=labels,fit=metadata['fit'],metadata=metadata,
                preserved_existing_directory=str(folder),input_arrays_sha256=sha(folder/'arrays.npz'))


def main():
    target=HERE/'weight_cross_2x2_v3'
    if target.exists():raise FileExistsError('Never overwrite completed/failed diagnostic evidence')
    target.mkdir();set_num_threads(1);started=time.perf_counter()
    old={s:{cohort:load_existing(s,cohort) for cohort in ['native','common']} for s in ['ssn','usgs']}
    pairs_path=ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json'
    pairs=json.loads(pairs_path.read_text(encoding='utf-8'))
    lookup={s:{r['record_id']:r for r in old[s]['native']['prepared']['source_rows']} for s in old}
    cases={}
    cases['ssn','high','native']=old['ssn']['native'];cases['ssn','high','common']=old['ssn']['common']
    cases['usgs','low','native']=old['usgs']['native'];cases['usgs','low','common']=old['usgs']['common']
    new_diagnostics=[]
    for source,level,w in [('ssn','low',LOW),('usgs','high',HIGH)]:
        native_fit=None;native_diag=None
        for cohort in ['native','common']:
            rows=old[source][cohort]['prepared']['source_rows']
            prepared,result=calculate(rows,1.6,w)
            if cohort=='native':
                train=np.array([r['time_utc']<'2021-01-01' for r in prepared['source_rows']])
                native_fit=author_normalmix(result['eta_log10'][train])
                native_diag=mixture_diagnostics(native_fit,result['eta_log10'][train])
            labels=make_labels(prepared,result,native_fit['threshold_log10']) if native_fit['status']=='estimable' else None
            name=f'M4p5_{source}_{cohort}_w_{level}'
            metadata=dict(name=name,source=source,cohort=cohort,d=1.6,w=w,weight_level=level,
                magnitude_policy='Reported M; numerical coefficient transported, not Mw harmonization',
                calibration='own-source native-development fit frozen; no common-membership refit',
                protocol_sha256=sha(HERE/'WEIGHT_CROSS_2X2_V2_PROTOCOL.md'),
                source_existing_array_sha256=old[source][cohort]['input_arrays_sha256'])
            save_case(target/'cases'/name,prepared,result,native_fit,native_diag,labels,metadata)
            cases[source,level,cohort]=dict(prepared=prepared,result=result,labels=labels,fit=native_fit,metadata=metadata)
            if cohort=='native':new_diagnostics.append(dict(source=source,weight_level=level,w=w,fit=native_fit,diagnostics=native_diag))
    comparisons={}
    for cohort in ['native','common']:
        comparisons[cohort]={}
        for left in ['low','high']:
            for right in ['low','high']:
                value=pair_metrics(cases['ssn',left,cohort],cases['usgs',right,cohort],pairs,lookup)
                comparisons[cohort][f'ssn_{left}__usgs_{right}']=dict(ssn_weight=LOW if left=='low' else HIGH,
                    usgs_weight=LOW if right=='low' else HIGH,metrics=value,
                    fit_diagnostics={s:cases[s,lev,cohort]['metadata'].get('mixture_diagnostics') or
                        cases[s,lev,cohort]['metadata'].get('local_fit_diagnostics') for s,lev in [('ssn',left),('usgs',right)]})
    main=json.loads((HERE/'deterministic_study_v3/PAIRED_METRICS.json').read_text(encoding='utf-8'))
    result=dict(schema='post-review-reported-weight-cross-2x2/1',protocol_sha256=sha(HERE/'WEIGHT_CROSS_2X2_V2_PROTOCOL.md'),
                script_sha256=sha(__file__),main_unchanged_w1=main['M4p5_native_author'],
                levels=dict(low=LOW,high=HIGH),new_source_weight_fits=new_diagnostics,
                comparisons=comparisons,pairs_sha256=sha(pairs_path),elapsed_seconds=time.perf_counter()-started,
                interpretation='Post-review sensitivity diagnostic; agreement is not accuracy, no weight selected by best outcome')
    dump(target/'RESULTS.json',result)
    for cohort,values in comparisons.items():
        print(cohort)
        for name,item in values.items():
            m=item['metrics']
            if m['status']=='computed':print(name,m['full_descriptive']['agreement'],m['held_out_2021_2025']['agreement'],m['held_out_2021_2025']['partition']['ARI'])
            else:print(name,m)
    print(json.dumps(dict(new_source_fits=new_diagnostics,seconds=result['elapsed_seconds']),indent=2))


if __name__=='__main__':main()
