"""Apply corrected, frozen family detector to preserved generator truth."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import csv
import hashlib
import json
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
sys.path.insert(0,str(HERE))
from run_deterministic_study_v3 import np,calculate,make_labels,author_normalmix,mixture_diagnostics,comparison,partition_comparison,dump,sha,set_num_threads
sys.path.insert(0,str(PILOT))
from gardner_knopoff import classify


def child_scores(true,predicted):
    a,b=np.asarray(true,dtype=bool),np.asarray(predicted,dtype=bool)
    tp=int(np.sum(a&b));fp=int(np.sum(~a&b));fn=int(np.sum(a&~b));tn=int(np.sum(~a&~b))
    den=2*tp+fp+fn
    return dict(n=len(a),TP=tp,FP=fp,FN=fn,TN=tn,
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                F1=2*tp/den if den else None,false_positive_fraction_among_true_immigrants=fp/(fp+tn) if fp+tn else None,
                accuracy=(tp+tn)/len(a) if len(a) else None)


def truth_arrays(rows,truth):
    root_ids=[truth[r['record_id']]['root_id'] for r in rows]
    codes={key:i for i,key in enumerate(sorted(set(root_ids)))}
    group=np.asarray([codes[key] for key in root_ids],dtype=int)
    counts=np.bincount(group)
    best={}
    for i,r in enumerate(rows):
        key=(-float(r['magnitude']),r['time_utc'],r['record_id'])
        g=group[i]
        if g not in best or key<best[g][0]:best[g]=(key,i)
    role=np.full(len(rows),2,dtype=np.int8)
    for g,(_,i) in best.items():role[i]=0 if counts[g]==1 else 1
    child=np.asarray([truth[r['record_id']]['is_immigrant']=='0' for r in rows])
    evaluation=np.asarray([truth[r['record_id']]['is_eval']=='1' for r in rows])
    return group,role,child,evaluation


def summary(rows):
    result={}
    for key in ['NN','GK']:
        result[key]={}
        for scenario in ['etas','n0','n1']:
            subset=[r[key] for r in rows if r['scenario']==scenario and r[key] is not None]
            out={}
            for name,getter in [('child_F1',lambda r:r['generated_child']['F1']),
                                ('immigrant_FPR',lambda r:r['generated_child']['false_positive_fraction_among_true_immigrants']),
                                ('family_ARI',lambda r:r['roles_and_families']['partition']['ARI']),
                                ('three_role_agreement',lambda r:r['roles_and_families']['agreement']),
                                ('fraction_in_a_family',lambda r:r['fraction_in_a_family'])]:
                values=[getter(r) for r in subset if getter(r) is not None]
                out[name]={'n_cases':len(values),'mean':float(np.mean(values)) if values else None,
                           'minimum':min(values) if values else None,'maximum':max(values) if values else None}
            result[key][scenario]=out
    return result


def main():
    target=HERE/'synthetic_2013_validation_v3'
    if target.exists():raise FileExistsError('Never overwrite prior scientific evidence')
    target.mkdir()
    set_num_threads(1);started=time.perf_counter()
    all_rows=[];fits=[]
    for cut,d in [(3.5,1.6),(4.1,1.6),(4.5,1.6),(4.5,2.)]:
        trainpath=PILOT/'synthetic/training/etas_20261000/events.csv'
        with trainpath.open(encoding='utf-8-sig',newline='') as f:training=[r for r in csv.DictReader(f) if Decimal(r['magnitude'])>=Decimal(str(cut))]
        prepared,pred=calculate(training,d,1.)
        fit=author_normalmix(pred['eta_log10'])
        diag=mixture_diagnostics(fit,pred['eta_log10'])
        fits.append(dict(cut=cut,d=d,fit=fit,diagnostics=diag,input_sha256=sha(trainpath)))
        for seed in range(20261120,20261130):
            for scenario in ['etas','n0','n1']:
                folder=PILOT/'synthetic/test'/f'{scenario}_{seed}'
                with (folder/'events.csv').open(encoding='utf-8-sig',newline='') as f:rows=[r for r in csv.DictReader(f) if Decimal(r['magnitude'])>=Decimal(str(cut))]
                with (folder/'truth.csv').open(encoding='utf-8-sig',newline='') as f:truth={r['record_id']:r for r in csv.DictReader(f)}
                prepared,result=calculate(rows,d,1.)
                rows=prepared['source_rows']
                truth_group,truth_role,true_child,evaluation=truth_arrays(rows,truth)
                gk=classify(prepared['t_year']*365.25,prepared['lat_deg'],prepared['lon_deg'],prepared['m'])
                gk_role=np.asarray([{'isolated':0,'main':1,'associated':2}[str(v)] for v in gk['roles']],dtype=np.int8)
                gk_group=np.where(gk['group']>0,gk['group'],-np.arange(len(rows))-1)
                true_group_eval=truth_group[evaluation];truth_role_eval=truth_role[evaluation];child_eval=true_child[evaluation]
                gk_item=dict(generated_child=child_scores(child_eval,gk_role[evaluation]==2),
                    roles_and_families=comparison(truth_role_eval,gk_role[evaluation],true_group_eval,gk_group[evaluation]),
                    fraction_in_a_family=float(np.mean(gk['group'][evaluation]>0)),
                    true_immigrant_in_a_family_fraction=float(np.mean((gk['group'][evaluation]>0)[~child_eval])) if np.any(~child_eval) else None,
                    prediction_semantics='associated relative to maximum in GK window, not a generated immigrant label')
                labels=make_labels(prepared,result,fit['threshold_log10']) if fit['status']=='estimable' else None
                nn_item=None
                if labels is not None:
                    nn_item=dict(generated_child=child_scores(child_eval,labels['strong_link_mask'][evaluation]),
                        roles_and_families=comparison(truth_role_eval,labels['roles'][evaluation],true_group_eval,labels['component_root_index'][evaluation]),
                        fraction_in_a_family=float(np.mean(labels['component_size'][evaluation]>1)),
                        true_immigrant_in_a_family_fraction=float(np.mean((labels['component_size'][evaluation]>1)[~child_eval])) if np.any(~child_eval) else None,
                        prediction_semantics='strong parent link for generated-child score; maximum-retained family role evaluated separately')
                baseline=dict(always_child=child_scores(child_eval,np.ones(len(child_eval),dtype=bool)),
                    always_immigrant=child_scores(child_eval,np.zeros(len(child_eval),dtype=bool)),
                    all_one_family=partition_comparison(true_group_eval,np.zeros(len(child_eval),dtype=int)),
                    all_singletons=partition_comparison(true_group_eval,np.arange(len(child_eval))))
                name=f'{scenario}_{seed}_M{cut}_d{d}'
                casepath=target/name;casepath.mkdir()
                fields=dict(parent_index=result['parent_index'],eta_log10=result['eta_log10'],true_group=truth_group,
                    true_operational_role=truth_role,true_generated_child=true_child,evaluated=evaluation,
                    GK_role=gk_role,GK_group=gk_group)
                if labels is not None:fields.update(NN_group=labels['component_root_index'],NN_role=labels['roles'],NN_strong_link=labels['strong_link_mask'])
                np.savez_compressed(casepath/'arrays.npz',**fields)
                dump(casepath/'ids.json',prepared['ids'])
                item=dict(case=name,scenario=scenario,seed=seed,cut=cut,d=d,synthetic=True,events=len(rows),evaluated=int(evaluation.sum()),
                          NN=nn_item,GK=gk_item,trivial_baselines=baseline,
                          event_input_sha256=sha(folder/'events.csv'),truth_input_sha256=sha(folder/'truth.csv'),
                          array_output_sha256=sha(casepath/'arrays.npz'),fit_status=fit['status'])
                dump(casepath/'metrics.json',item);all_rows.append(item)
        print(json.dumps(dict(cut=cut,d=d,fit_status=fit['status'],threshold=fit.get('threshold_log10'))),flush=True)
    summaries={}
    for cut,d in [(3.5,1.6),(4.1,1.6),(4.5,1.6),(4.5,2.)]:
        summaries[f'M{cut}_d{d}']=summary([r for r in all_rows if r['cut']==cut and r['d']==d])
    report=dict(schema='post-review-synthetic-2013-validation/1',synthetic=True,
        protocol_sha256=sha(HERE/'SYNTHETIC_2013_PROTOCOL.md'),script_sha256=sha(__file__),fits=fits,
        results=all_rows,summaries=summaries,elapsed_seconds=time.perf_counter()-started,
        limitations=['Not empirical Mexico fit or real event-family validation.',
                     'N0/N1 share immigrant rate, not ideal ETAS total rate; the adverse dense regime is preserved.',
                     'Paired scenarios within a seed are dependent; summaries are descriptive.',
                     'GK associated vs immigrant and NN maximum-retained vs generated-child are different labels and reported separately.'])
    dump(target/'RESULTS.json',report)
    print(json.dumps(dict(cases=len(all_rows),seconds=report['elapsed_seconds'],summaries=summaries),indent=2))


if __name__=='__main__':main()
