"""Fixed-protocol computational interventions, never physical event labels."""
from __future__ import annotations
import argparse
import csv
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
import json
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/'outputs/sequence_pilot_2026-11-15'
MATCH=ROOT/'outputs/ssn_usgs_pilot_2026-11-15'
sys.path.insert(0,str(OLD))
sys.path.insert(0,str(ROOT/'scripts'))
from gardner_knopoff import classify
from pilot_catalog_reconciliation import Record,candidate_edges,optimal_assignment,utc_nanoseconds,epicentral_distance
from audit_catalog_design import read_csv,json_read,sha,dump,csv_write


def get():
    rows={s:read_csv(OLD/'inputs'/f'{s}.csv') for s in ['ssn','usgs']}
    lookup={s:{r['record_id']:r for r in rr} for s,rr in rows.items()}
    pairs=json_read(MATCH/'graph_candidate_pairs.json')
    return rows,lookup,pairs


def days(r):
    return utc_nanoseconds(r['time_utc'])/(86400*1e9)


def classify_rows(rows, tie_column='record_id'):
    ordered=sorted(rows,key=lambda r:(utc_nanoseconds(r['time_utc']),r[tie_column]))
    got=classify([days(r) for r in ordered],*[np.array([float(r[k]) for r in ordered]) for k in ['latitude','longitude','magnitude']])
    return {r['pair_id'] if 'pair_id' in r else r['record_id']:str(role) for r,role in zip(ordered,got['roles'])}


def table(a,b):
    labels=['isolated','main','associated']
    matrix=[[sum(x==la and y==lb for x,y in zip(a,b)) for lb in labels] for la in labels]
    n=len(a)
    return {'n':n,'changed':sum(x!=y for x,y in zip(a,b)),'agreement':sum(x==y for x,y in zip(a,b))/n,'labels':labels,'matrix':matrix}


def selected_pairs(pairs,lookup,cut):
    return sorted([p for p in pairs if all(Decimal(lookup[s][p[s+'_record_id']]['magnitude'])>=Decimal(cut) for s in ['ssn','usgs'])],key=lambda p:(p['ssn_record_id'],p['usgs_record_id']))


def stamp(task):
    receipt={'task':task,'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(HERE/'PROTOCOL_CATALOG_DESIGN.md'),
             'script_sha256':sha(Path(__file__)),'inputs':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [OLD/'inputs/ssn.csv',OLD/'inputs/usgs.csv',MATCH/'graph_candidate_pairs.json',OLD/'gardner_knopoff.py',ROOT/'scripts/pilot_catalog_reconciliation.py']},
             'classification':'transported counterfactual inputs or controlled thinning; not earthquake observations; no earthquake identity truth; no physical magnitude calibration'}
    dump(task+'_started_receipt.json',receipt)
    return receipt


def factorial():
    receipt=stamp('factorial')
    rows,lookup,pairs=get()
    output={}
    allroles=[]
    alledges=[]
    for cut in ['4.5','4.1']:
        keep=selected_pairs(pairs,lookup,cut)
        ids=[p['ssn_record_id']+'|'+p['usgs_record_id'] for p in keep]
        results={}
        for m,xy,t in product([0,1],repeat=3):
            bits=f'{m}{xy}{t}'
            transported=[]
            for p,pid in zip(keep,ids):
                rr=[lookup[s][p[s+'_record_id']] for s in ['ssn','usgs']]
                transported.append({'pair_id':pid,'ssn_id':rr[0]['record_id'],'usgs_id':rr[1]['record_id'],
                                    'magnitude':rr[m]['magnitude'],'latitude':rr[xy]['latitude'],'longitude':rr[xy]['longitude'],'time_utc':rr[t]['time_utc']})
            for tie in ['ssn_id','usgs_id','pair_id']:
                got=classify_rows(transported,tie)
                results[bits,tie]=[got[pid] for pid in ids]
        for i,p in enumerate(keep):
            allroles.append({'cut':cut,**p,**{f'MXYT_{bits}_{tie}':v[i] for (bits,tie),v in results.items()}})
        summary={'n':len(ids),'bit_definition':'reported magnitude, epicentre, UTC; 0 SSN, 1 ComCat',
                 'native_tie_endpoint':table(results['000','ssn_id'],results['111','usgs_id']),
                 'common_pair_key_endpoint':table(results['000','pair_id'],results['111','pair_id']),
                 'tie_controls':{},'all_factor_edges':[]}
        for bits in [f'{m}{xy}{t}' for m,xy,t in product([0,1],repeat=3)]:
            summary['tie_controls'][bits]=table(results[bits,'ssn_id'],results[bits,'usgs_id'])
            for factor,name in enumerate(['magnitude','epicentre','UTC']):
                if bits[factor]=='0':
                    target=bits[:factor]+'1'+bits[factor+1:]
                    for tie in ['ssn_id','usgs_id','pair_id']:
                        record={'cut':cut,'from':bits,'to':target,'factor':name,'tie':tie,**table(results[bits,tie],results[target,tie])}
                        alledges.append({k:v for k,v in record.items() if k not in ['labels','matrix']})
                        summary['all_factor_edges'].append(record)
        projected={}
        for source,bit,tie in [('ssn','000','ssn_id'),('usgs','111','usgs_id')]:
            for regime in ['A','B','C','D45']:
                data=np.load(OLD/'results/gk'/f'{regime}_{source}'/'classification.npz')
                roles={str(rid):str(role) for rid,role in zip(data['ids'],data['roles'])}
                if all(p[source+'_record_id'] in roles for p in keep):
                    value=[roles[p[source+'_record_id']] for p in keep]
                    projected[source+'_'+regime]=value
                    summary['native_projection_'+source+'_'+regime]=table(value,results[bit,tie])
                    if cut=='4.1' and regime=='C':
                        assert value==results[bit,tie],('C endpoint failed to reproduce',source)
        native_regime='D45' if cut=='4.5' else 'B'
        summary['native_context_cross_source']=table(projected['ssn_'+native_regime],projected['usgs_'+native_regime])
        output[cut]=summary
    csv_write('factorial_pair_roles.csv',allroles)
    csv_write('factorial_all_edges.csv',alledges)
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat()
    receipt['results']=output
    dump('FACTORIAL_GK.json',receipt)
    print(json.dumps({cut:{k:v for k,v in obj.items() if k in ['n','native_tie_endpoint','common_pair_key_endpoint','tie_controls','native_context_cross_source']} for cut,obj in output.items()},indent=2))


def thinning(cut):
    receipt=stamp('thinning_'+cut.replace('.','_'))
    rows,lookup,pairs=get()
    keep=selected_pairs(pairs,lookup,cut)
    fixed={s:{p[s+'_record_id'] for p in keep} for s in ['ssn','usgs']}
    core=[r for r in rows['ssn'] if r['record_id'] in fixed['ssn']]
    context=sorted([r for r in rows['ssn'] if Decimal(r['magnitude'])>=Decimal(cut) and r['record_id'] not in fixed['ssn']],key=lambda r:r['record_id'])
    native_comcat=[r for r in rows['usgs'] if Decimal(r['magnitude'])>=Decimal(cut)]
    native_target=classify_rows(native_comcat)
    common_target=classify_rows([r for r in native_comcat if r['record_id'] in fixed['usgs']])
    native_ssn=classify_rows(core+context)
    ids=[p['ssn_record_id'] for p in keep]
    comcatids=[p['usgs_record_id'] for p in keep]
    records=[]
    rolecounts={rid:Counter() for rid in ids}
    for fraction in [0,.25,.5,.75,1]:
        size=int(np.floor(len(context)*fraction))
        seeds=[2026111600] if fraction in [0,1] else range(2026111600,2026111620)
        for seed in seeds:
            rng=np.random.default_rng(seed)
            selected=np.sort(rng.choice(len(context),size,replace=False)) if size else []
            got=classify_rows(core+[context[i] for i in selected])
            roles=[got[rid] for rid in ids]
            rec={'cut':cut,'context_fraction':fraction,'seed':seed,'n_core':len(core),'n_context':size,'n_total':len(core)+size,
                 'changed_vs_native_ssn':sum(got[rid]!=native_ssn[rid] for rid in ids),
                 'agreement_vs_native_comcat':sum(got[rid]==native_target[bid] for rid,bid in zip(ids,comcatids))/len(ids),
                 'agreement_vs_common_comcat':sum(got[rid]==common_target[bid] for rid,bid in zip(ids,comcatids))/len(ids)}
            records.append(rec)
    csv_write('thinning_'+cut.replace('.','_')+'.csv',records)
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat()
    receipt['results']=records
    dump('THINNING_'+cut.replace('.','_')+'.json',receipt)
    print(json.dumps({'cut':cut,'n_core':len(core),'full_context':len(context),'runs':len(records),
                      'summary':[{ 'fraction':f,**{v:{'min':min(r[v] for r in records if r['context_fraction']==f),'median':float(np.median([r[v] for r in records if r['context_fraction']==f])),'max':max(r[v] for r in records if r['context_fraction']==f)} for v in ['changed_vs_native_ssn','agreement_vs_native_comcat','agreement_vs_common_comcat']}} for f in [0,.25,.5,.75,1]]},indent=2))


def matching_null():
    receipt=stamp('matching_timeshift')
    rows,lookup,pairs=get()
    def record(s,r):
        return Record(r['record_id'],s,r.get('event_id') or None,r['time_utc'],utc_nanoseconds(r['time_utc']),float(r['latitude']),float(r['longitude']),float(r['depth_km']) if r['depth_km'] else None,float(r['magnitude']),r['magnitude_type'] or None)
    ssn=[record('ssn',r) for r in rows['ssn']]
    usgs=[record('usgs',r) for r in rows['usgs']]
    start=utc_nanoseconds('2016-01-01T00:00:00Z'); stop=utc_nanoseconds('2026-01-01T00:00:00Z')
    output=[]
    for shift in [0,-90,-60,-30,-14,-7,7,14,30,60,90]:
        shifted=[replace(r,time_ns=start+(r.time_ns-start+shift*86400*10**9)%(stop-start)) for r in usgs]
        edges=candidate_edges(ssn,shifted,30,50)
        assigned=optimal_assignment(edges,30,50)
        if shift==0:
            assert assigned=={(p['ssn_record_id'],p['usgs_record_id']) for p in pairs}
        output.append({'shift_days':shift,'edges':len(edges),'assignments':len(assigned),'ssn_with_candidates':len({e.ssn for e in edges}),'usgs_with_candidates':len({e.usgs for e in edges})})
    csv_write('matching_timeshift_negative_control.csv',output)
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat()
    receipt['results']=output
    receipt['warning']='Computational negative control; not a false-positive rate or empirical identity precision. Sequences and edge density are altered; cyclic boundary is artificial.'
    dump('MATCHING_TIMESHIFT.json',receipt)
    print(json.dumps(output,indent=2))


if __name__=='__main__':
    from collections import Counter
    parser=argparse.ArgumentParser()
    parser.add_argument('task',choices=['factorial','thinning','matching_null'])
    parser.add_argument('--cut',choices=['4.5','4.1'],default='4.5')
    args=parser.parse_args()
    {'factorial':factorial,'matching_null':matching_null,'thinning':lambda:thinning(args.cut)}[args.task]()
