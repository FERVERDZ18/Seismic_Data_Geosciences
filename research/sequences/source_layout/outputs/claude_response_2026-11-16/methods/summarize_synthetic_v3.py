"""Descriptive summaries of completed fixed-seed controls; no detector fitting."""
from pathlib import Path
import json
import statistics

HERE=Path(__file__).resolve().parent


def describe(values):
    a=[float(v) for v in values if v is not None]
    return dict(n=len(a),mean=statistics.mean(a) if a else None,minimum=min(a) if a else None,maximum=max(a) if a else None)


def main():
    output=HERE/'SYNTHETIC_DESCRIPTIVE_SUMMARY_v3.json'
    if output.exists():raise FileExistsError('Do not overwrite completed summary')
    old=json.loads((HERE/'synthetic_2013_validation_v3/RESULTS.json').read_text())
    anchored=json.loads((HERE/'anchored_synthetic_validation_v3/RESULTS.json').read_text())
    original=[]
    for cut,d in [(3.5,1.6),(4.1,1.6),(4.5,1.6),(4.5,2.)]:
        for scenario in ['etas','n0','n1']:
            cases=[r for r in old['results'] if r['cut']==cut and r['d']==d and r['scenario']==scenario]
            out=dict(cut=cut,d=d,scenario=scenario,n_cases=len(cases),models={})
            for method in ['NN','GK']:
                valid=[r for r in cases if r[method] is not None]
                out['models'][method]=dict(
                    family_role_accuracy=describe([r[method]['roles_and_families']['agreement'] for r in valid]),
                    best_constant_role_accuracy_using_truth_marginals=describe([max(r[method]['roles_and_families']['first_marginal'])/r['evaluated'] for r in valid]),
                    family_ARI=describe([r[method]['roles_and_families']['partition']['ARI'] for r in valid]),
                    generated_child_F1=describe([r[method]['generated_child']['F1'] for r in valid]),
                    always_child_F1=describe([r['trivial_baselines']['always_child']['F1'] for r in valid]),
                    immigrant_FPR=describe([r[method]['generated_child']['false_positive_fraction_among_true_immigrants'] for r in valid]),
                    in_family_fraction=describe([r[method]['fraction_in_a_family'] for r in valid]))
            original.append(out)
    extra=[]
    for source in ['ssn','usgs']:
        for branching in [0.,.3,.6,.8]:
            subset=[r for r in anchored['results'] if r['source']==source and r['branching']==branching]
            item=dict(source_anchor=source,branching=branching,n_cases=len(subset),models={})
            for method in ['observed_development','independent_synthetic_development','GK']:
                values=[r['GK'] if method=='GK' else r['NN'][method]['metrics'] for r in subset]
                values=[r for r in values if r is not None]
                item['models'][method]=dict(
                    family_role_accuracy=describe([r['roles_and_families']['agreement'] for r in values]),
                    best_constant_role_accuracy_using_truth_marginals=describe([max(r['roles_and_families']['first_marginal'])/r['roles_and_families']['n'] for r in values]),
                    family_ARI=describe([r['roles_and_families']['partition']['ARI'] for r in values]),
                    generated_child_F1=describe([r['generated_child']['F1'] for r in values]),
                    immigrant_FPR=describe([r['generated_child']['false_positive_fraction_among_true_immigrants'] for r in values]),
                    in_family_fraction=describe([r['fraction_in_a_family'] for r in values]))
            extra.append(item)
    result=dict(original_controls=original,descriptor_anchored_controls=extra,
                uncertainty='Fixed-seed descriptive ranges; no population confidence intervals or empirical Mexican validation',
                labels='Generated immigrant/child differs from family maximum/member; both retained, including adverse outcomes')
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Original ETAS M4.5,d1.6:')
    print(json.dumps(next(r for r in original if r['cut']==4.5 and r['d']==1.6 and r['scenario']=='etas'),indent=2))
    print('Anchored controls: source n [accuracy/ARI/FPR] observed-cut, synthetic-cut, GK')
    for item in extra:
        print(item['source_anchor'],item['branching'],{k:[round(v[m]['mean'],4) if v[m]['mean'] is not None else None for m in ['family_role_accuracy','family_ARI','immigrant_FPR']] for k,v in item['models'].items()})


if __name__=='__main__':main()
