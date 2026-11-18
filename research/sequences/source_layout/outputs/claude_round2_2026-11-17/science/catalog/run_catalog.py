"""Sealed second-review catalogue lane. Private, no input or public-file writes."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
METHODS=ROOT/'outputs/claude_response_2026-11-16/methods'
DESIGN=METHODS.parent/'catalog_design'
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
MATCH=ROOT/'outputs/ssn_usgs_pilot_2026-11-15'
sys.dont_write_bytecode=True
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[k]='1'
os.environ['NUMBA_CACHE_DIR']=str(HERE/'cache/numba')
os.environ['MPLCONFIGDIR']=str(HERE/'cache/matplotlib')
sys.path[:0]=[str(HERE/'vendor'),str(PILOT/'comparators/nearest_neighbor'),str(PILOT/'comparators/nearest_neighbor/_deps'),str(PILOT/'comparators/carluccio/_deps')]
from spherical_weighted_v2 import np,prepare_rows,run_arrays,set_num_threads,YEAR_SECONDS
from author_normalmix_port import author_normalmix
from deterministic_families import families_from_cut
from run_deterministic_study_v3 import comparison,mixture_diagnostics,empirical_reported_b
from gardner_knopoff import classify as gk_classify
from pilot_catalog_reconciliation import Record,candidate_edges,optimal_assignment,in_window,utc_nanoseconds

LABELS=['isolated','operational representative','associated']
ROLE_CODE={'isolated':0,'main':1,'associated':2}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readj(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,obj):Path(p).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with Path(p).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def wtag(w):return format(w,'.17g').replace('.','p')
def verify_frozen():
    seal=readj(HERE/'SEAL.json')
    for name,h in seal['files'].items():assert sha(HERE/name)==h,('seal',name)
    for r in readj(HERE/'INPUTS.json'):assert sha(ROOT/r['path'])==r['sha256'],('input_changed',r['path'])
    for r in readj(HERE/'VENDOR.json'):assert sha(HERE/r['copy'])==r['sha256'],('copy_changed',r['copy'])
    assert sha(HERE/'AMENDMENT_01.md')=='bb3a354cab0796620c15a3aad73709de28e989f206726b13b2056449638e57c3'

def metric(a,b,ga=None,gb=None):
    a,b=np.asarray(a,dtype=int),np.asarray(b,dtype=int)
    assert len(a)==len(b)
    if ga is None:ga=np.arange(len(a))
    if gb is None:gb=np.arange(len(b))
    m=comparison(a,b,ga,gb)
    m['labels']=LABELS
    z=np.asarray(m['matrix_first_rows_second_columns']);r=z.sum(axis=1);c=z.sum(axis=0)
    m['per_class']={LABELS[k]:dict(intersection=int(z[k,k]),first_count=int(r[k]),second_count=int(c[k]),
        union=int(r[k]+c[k]-z[k,k]),jaccard=float(z[k,k]/(r[k]+c[k]-z[k,k])) if r[k]+c[k]-z[k,k] else None,
        symmetric_F1=float(2*z[k,k]/(r[k]+c[k])) if r[k]+c[k] else None) for k in range(3)}
    m['symmetric_concordance_not_accuracy']=True
    if not len(a):m['partition']['ARI']=None
    return m

class Union:
    def __init__(self,n):self.p=list(range(n))
    def find(self,x):
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def join(self,a,b):
        a,b=self.find(int(a)),self.find(int(b))
        if a!=b:self.p[max(a,b)]=min(a,b)

def shared_units(labels_a,labels_b,si,ui):
    na=len(labels_a);u=Union(na+len(labels_b))
    for i,r in enumerate(labels_a):u.join(i,r)
    for i,r in enumerate(labels_b):u.join(na+i,na+r)
    for a,b in zip(si,ui):u.join(a,na+b)
    roots=[u.find(int(i)) for i in si]
    codes={v:i for i,v in enumerate(sorted(set(roots)))}
    out=np.array([codes[v] for v in roots],dtype=int)
    assert all(u.find(int(a))==u.find(na+int(b)) for a,b in zip(si,ui))
    return out

def bootstrap_plan(units,mask,replications,seed):
    restricted=units[mask]
    codes=np.unique(restricted)
    sizes=np.asarray([int(np.sum(restricted==g)) for g in codes])
    if not len(codes):return dict(status='not_estimable',reason='no_nonempty_units')
    draws=np.random.Generator(np.random.PCG64(seed)).multinomial(len(codes),np.repeat(1/len(codes),len(codes)),size=replications)
    frac=sizes/sizes.sum()
    return dict(status='computed',codes=codes,sizes=sizes,draws=draws,
        effective_units=float(1/np.sum(frac**2)),largest_pair_fraction=float(frac.max()),
        fragile=bool(len(codes)<10 or frac.max()>.5))

def bootstrap_values(a,b,units,mask,plan):
    if plan['status']!='computed':return None
    a,b,units=a[mask],b[mask],units[mask]
    counts=np.asarray([np.bincount(3*a[units==g]+b[units==g],minlength=9) for g in plan['codes']],dtype=float)
    z=(plan['draws']@counts).reshape((-1,3,3));n=z.sum(axis=(1,2))
    diag=np.diagonal(z,axis1=1,axis2=2);ra=z.sum(axis=2);cb=z.sum(axis=1)
    observed=diag.sum(axis=1)/n
    expected=(ra*cb).sum(axis=1)/n**2
    with np.errstate(divide='ignore',invalid='ignore'):
        kappa=(observed-expected)/(1-expected)
        j=diag/(ra+cb-diag);f=2*diag/(ra+cb)
    return dict(agreement=observed,kappa=kappa,**{f'Jaccard_{k}':j[:,k] for k in range(3)},**{f'F1_{k}':f[:,k] for k in range(3)})

def unit_spans(components,units):
    spans=[len(set(map(int,units[components==g]))) for g in np.unique(components)]
    return dict(families_represented=len(spans),families_spanning_multiple_baseline_units=sum(n>1 for n in spans),
                maximum_baseline_units_in_one_family=max(spans,default=0),baseline_resampling_does_not_capture_new_cross_unit_dependence=bool(any(n>1 for n in spans)))

def intervals(values,baseline=None):
    if values is None:return dict(status='not_estimable')
    out={}
    if baseline is not None:values={**values,'paired_agreement_difference_vs_w1_delta0':values['agreement']-baseline['agreement']}
    for k,v in values.items():
        finite=np.asarray(v)[np.isfinite(v)]
        out[k]=dict(valid_replicates=len(finite),percentile_2_5=float(np.quantile(finite,.025,method='linear')) if len(finite) else None,
                    percentile_97_5=float(np.quantile(finite,.975,method='linear')) if len(finite) else None)
    return dict(status='computed',intervals=out,interpretation='Conditional dependence-unit resampling sensitivity, not a nominal-coverage physical uncertainty interval')

def classify_case(prepared,result,c):
    with np.errstate(divide='ignore',invalid='ignore'):score=np.log10(result['TN'])+np.log10(result['RN'])
    return families_from_cut(result['parent_index'],score,prepared['m'],prepared['t_year'],prepared['ids'],c,inclusive=True)

def components_table(prepared,labels,source,w,delta):
    t=prepared['t_year']*YEAR_SECONDS/86400
    rows=[]
    for g in np.unique(labels['component_root_index']):
        ii=np.flatnonzero(labels['component_root_index']==g)
        if len(ii)<2:continue
        representative=int(ii[np.flatnonzero(labels['roles'][ii]==1)[0]])
        rows.append(dict(source=source,w=w,delta=delta,root_record_id=prepared['ids'][int(g)],
            representative_record_id=prepared['ids'][representative],n=len(ii),native_fraction=len(ii)/len(t),
            start_utc=prepared['source_rows'][int(ii[0])]['time_utc'],end_utc=prepared['source_rows'][int(ii[-1])]['time_utc'],
            duration_days=float(t[ii[-1]]-t[ii[0]]),max_consecutive_gap_days=float(np.diff(t[ii]).max())))
    return rows

def case_summary(prepared,labels):
    counts=Counter(map(int,labels['component_root_index']))
    maximum=max(counts.values()) if counts else 0
    return dict(events=len(prepared['ids']),role_counts={LABELS[i]:int(np.sum(labels['roles']==i)) for i in range(3)},
        components=len(counts),nonunit_components=sum(n>1 for n in counts.values()),largest_component=maximum,
        largest_component_fraction=maximum/len(prepared['ids']) if prepared['ids'] else None)

def make_weights(target,raw,config):
    cases={};all_components=[]
    for source in ['ssn','usgs']:
        rows=[r for r in raw[source] if Decimal(r['magnitude'])>=Decimal(config['magnitude_cut'])]
        prepared=prepare_rows(rows)
        exact_b=empirical_reported_b(rows,4.5)
        expected=1.3265675928192793 if source=='ssn' else 1.0905428994843476
        assert exact_b==expected,(source,exact_b,expected)
        for w in config['weights']:
            dest=target/'cases'/f'{source}_w{wtag(w)}';dest.mkdir(parents=True)
            started=time.perf_counter()
            result=run_arrays(prepared['t_year'],prepared['lat_deg'],prepared['lon_deg'],prepared['m'],d=1.6,w=w,q=.5,backend='kd')
            train=np.asarray([r['time_utc']<'2021-01-01' for r in prepared['source_rows']])
            fit=author_normalmix(result['eta_log10'][train])
            diagnostics=mixture_diagnostics(fit,result['eta_log10'][train])
            labels={}
            if fit['status']=='estimable':
                for delta in config['threshold_deltas']:
                    labels[delta]=classify_case(prepared,result,fit['threshold_log10']+delta)
                    all_components.extend(components_table(prepared,labels[delta],source,w,delta))
            fields={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
            fields.update(t_year=prepared['t_year'],latitude=prepared['lat_deg'],longitude=prepared['lon_deg'],reported_magnitude=prepared['m'])
            for delta,z in labels.items():fields.update({f'delta_{delta}_{k}':v for k,v in z.items() if isinstance(v,np.ndarray)})
            np.savez_compressed(dest/'arrays.npz',**fields)
            dump(dest/'ids.json',prepared['ids']);dump(dest/'rows.json',prepared['source_rows'])
            meta=dict(source=source,w=w,d=1.6,q=.5,fit=fit,diagnostics=diagnostics,kernel=result['metadata'],
                development_events=int(train.sum()),native_events=len(rows),empirical_reported_b=exact_b,
                classifications={str(delta):case_summary(prepared,z) for delta,z in labels.items()},elapsed_seconds=time.perf_counter()-started,
                arrays_sha256=sha(dest/'arrays.npz'))
            if w==1.:
                old=METHODS/'deterministic_study_v3/cases'/f'M4p5_{source}_native_author'
                olda=np.load(old/'arrays.npz');assert prepared['ids']==readj(old/'ids.json')
                checks={k:bool(np.array_equal(result[k],olda[k],equal_nan=True)) for k in ['parent_index','TN','RN','eta_log10']}
                if labels:checks['roles']=bool(np.array_equal(labels[0]['roles'],olda['roles']));checks['component_root_index']=bool(np.array_equal(labels[0]['component_root_index'],olda['component_root_index']))
                assert all(checks.values()),('baseline_replay',source,checks)
                meta['canonical_v3_replay']=checks
            dump(dest/'metadata.json',meta)
            cases[source,w]=dict(prepared=prepared,result=result,fit=fit,labels=labels,metadata=meta)
            print(json.dumps(dict(stage='weight',source=source,w=w,status=fit['status'],events=len(rows),seconds=meta['elapsed_seconds'])),flush=True)
    writecsv(target/'COMPONENTS.csv',all_components)
    return cases

def pair_analysis(target,cases,raw,pairs,config):
    primary={s:cases[s,1.] for s in ['ssn','usgs']}
    idx={s:{rid:i for i,rid in enumerate(c['prepared']['ids'])} for s,c in primary.items()}
    pp=sorted([p for p in pairs if p['ssn_record_id'] in idx['ssn'] and p['usgs_record_id'] in idx['usgs']],key=lambda p:(p['ssn_record_id'],p['usgs_record_id']))
    si=np.array([idx['ssn'][p['ssn_record_id']] for p in pp]);ui=np.array([idx['usgs'][p['usgs_record_id']] for p in pp])
    years=np.array([primary['ssn']['prepared']['source_rows'][i]['time_utc'][:4] for i in si])
    pa,pb=primary['ssn']['labels'][0],primary['usgs']['labels'][0]
    units=shared_units(pa['component_root_index'],pb['component_root_index'],si,ui)
    # The fixed predeclared 2017 anchor and union of its native principal families.
    anchor=sorted([r for r in raw['usgs'] if r['time_utc'].startswith('2017')],key=lambda r:(-Decimal(r['magnitude']),utc_nanoseconds(r['time_utc']),r['record_id']))[0]
    ap=next((p for p in pairs if p['usgs_record_id']==anchor['record_id']),None)
    anchor_ids={'usgs':anchor['record_id'],'ssn':ap['ssn_record_id'] if ap else None}
    excluded={}
    for s in ['ssn','usgs']:
        aid=anchor_ids[s];labels=primary[s]['labels'][0]
        excluded[s]=set() if aid not in idx[s] else {rid for rid,i in idx[s].items() if labels['component_root_index'][i]==labels['component_root_index'][idx[s][aid]]}
    no17=np.array([p['ssn_record_id'] not in excluded['ssn'] and p['usgs_record_id'] not in excluded['usgs'] for p in pp])
    masks={'full_2016_2025':np.ones(len(pp),dtype=bool),'development_2016_2020':years<'2021','evaluation_2021_2025':years>='2021',
           'full_without_fixed_2017_union':no17,'evaluation_without_fixed_2017_union':no17&(years>='2021')}
    masks.update({'year_'+str(y):years==str(y) for y in range(2016,2026)})
    plans={}
    for period in ['full_2016_2025','evaluation_2021_2025']:
        plan=bootstrap_plan(units,masks[period],config['bootstrap']['replications'],config['bootstrap']['seed']);plans[period]=plan
        np.savez_compressed(target/f'bootstrap_{period}.npz',unit_codes=plan.get('codes',[]),unit_sizes=plan.get('sizes',[]),unit_multiplicities=plan.get('draws',[]))
    dump(target/'DEPENDENCE_UNITS.json',dict(protocol='Principal w1 delta0 union, both full native partitions including unpaired context; then candidate endpoint links',
        plans={p:{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in z.items() if k!='draws'} for p,z in plans.items()},
        fixed_2017_anchor=anchor_ids,excluded_ids={s:sorted(v) for s,v in excluded.items()},
        excluded_pairs=int((~no17).sum()),masks={k:int(v.sum()) for k,v in masks.items()}))
    writecsv(target/'PAIRED_ENDPOINTS.csv',[dict(**p,year=years[i],fixed_unit=int(units[i]),excluded_fixed_2017=bool(not no17[i])) for i,p in enumerate(pp)])
    base_values={period:bootstrap_values(pa['roles'][si],pb['roles'][ui],units,masks[period],plan) for period,plan in plans.items()}
    results={};flat=[]
    combos=[(w,w,'same_w') for w in config['weights']]
    low,high=1.0905428994843476,1.3265675928192793
    combos.extend((a,b,'b_cross') for a in [low,high] for b in [low,high] if a!=b)
    for wa,wb,kind in combos:
        aa,bb=cases['ssn',wa],cases['usgs',wb]
        for delta in config['threshold_deltas']:
            name=f'{kind}_ssn{wtag(wa)}_usgs{wtag(wb)}_delta{delta}'
            if delta not in aa['labels'] or delta not in bb['labels']:
                results[name]=dict(status='not_estimable',ssn_fit=aa['fit'],usgs_fit=bb['fit']);continue
            a,b=aa['labels'][delta],bb['labels'][delta]
            entry=dict(status='computed',w_ssn=wa,w_usgs=wb,delta=delta,kind=kind,
                baseline_unit_fusion_diagnostics=dict(ssn=unit_spans(a['component_root_index'][si],units),usgs=unit_spans(b['component_root_index'][ui],units)),periods={})
            for period,mask in masks.items():
                z=metric(a['roles'][si[mask]],b['roles'][ui[mask]],a['component_root_index'][si[mask]],b['component_root_index'][ui[mask]])
                if period in plans:z['dependent_resampling']=intervals(bootstrap_values(a['roles'][si],b['roles'][ui],units,mask,plans[period]),base_values[period])
                entry['periods'][period]=z
                flat.append(dict(contrast=name,kind=kind,w_ssn=wa,w_usgs=wb,delta=delta,period=period,n=z['n'],agreement=z['agreement'],kappa=z['kappa'],ARI=z['partition']['ARI'],
                    **{f'Jaccard_{i}':z['per_class'][LABELS[i]]['jaccard'] for i in range(3)},**{f'F1_{i}':z['per_class'][LABELS[i]]['symmetric_F1'] for i in range(3)}))
            results[name]=entry
    dump(target/'WEIGHT_THRESHOLD_METRICS.json',results);writecsv(target/'WEIGHT_THRESHOLD_METRICS.csv',flat)
    return primary,idx,pp,si,ui,units,masks

def coverage_geography(target,raw,pairs,primary,idx):
    cindex=readj(ROOT/'system/dist/data/country-index.json')
    country={}
    for s in ['ssn','usgs']:
        cat='ssn-mx-historical' if s=='ssn' else 'usgs-mx-historical'
        labels=cindex['catalogs'][cat]['country_ids']
        country[s]={r['record_id']:labels[int(r['package_row'])-1] for r in raw[s]}
    pairlookup={s:{p[s+'_record_id']:p for p in pairs} for s in ['ssn','usgs']}
    states=Counter();rows=[];selected=[]
    for p in pairs:
        a=p['ssn_record_id'] in idx['ssn'];b=p['usgs_record_id'] in idx['usgs']
        states['both' if a and b else 'ssn_only' if a else 'usgs_only' if b else 'neither']+=1
    for s in ['ssn','usgs']:
        other='usgs' if s=='ssn' else 'ssn';counts=Counter();labels=primary[s]['labels'][0]
        for r in primary[s]['prepared']['source_rows']:
            rid=r['record_id'];p=pairlookup[s].get(rid)
            state='both_above_cut' if p and p[other+'_record_id'] in idx[other] else 'counterpart_below_cut' if p else 'unassigned'
            role=LABELS[int(labels['roles'][idx[s][rid]])]
            selected.append(dict(source=s,record_id=rid,year=r['time_utc'][:4],country_land_polygon=country[s][rid],candidate_state=state,role=role,
                magnitude_type=r['magnitude_type'] or 'not_supplied',reported_magnitude=r['magnitude']))
            for year in ['all',r['time_utc'][:4]]:
                counts[year,'all',country[s][rid]]+=1;counts[year,state,country[s][rid]]+=1
        for (year,state,co),n in sorted(counts.items()):rows.append(dict(source=s,year=year,state=state,country_land_polygon=co,n=n))
    writecsv(target/'SELECTED_ENDPOINT_STRATA.csv',selected);writecsv(target/'GEOGRAPHY_M4_5.csv',rows)
    dump(target/'COVERAGE.json',dict(candidate_assignments=len(pairs),candidate_cut_states=dict(states),
        native_selected={s:len(idx[s]) for s in idx},coverage_both_over_selected={s:states['both']/len(idx[s]) for s in idx},
        selected_endpoint_state_counts={s:dict(Counter(r['candidate_state'] for r in selected if r['source']==s)) for s in idx},
        caution='Land polygon label is context, not network or detection coverage. Candidate identity not validated. Neither/neither not added to agreement.'))

def edge_controls(target,primary,idx,pp):
    kept={s:{r['record_id']:r for r in primary[s]['prepared']['source_rows']} for s in idx}
    def within(r,interior=False):
        lat,lon=float(r['latitude']),float(r['longitude'])
        return 14.5<=lat<=32.5 and -117.5<=lon<=-86.5 if interior else lat>=14.5
    out={};lists=[]
    for name,interior in [('both_latitude_ge14p5',False),('both_interior_halfdegree',True)]:
        qq=[p for p in pp if all(within(kept[s][p[s+'_record_id']],interior) for s in idx)]
        a=np.array([idx['ssn'][p['ssn_record_id']] for p in qq],dtype=int);b=np.array([idx['usgs'][p['usgs_record_id']] for p in qq],dtype=int)
        za,zb=primary['ssn']['labels'][0],primary['usgs']['labels'][0]
        out[name]=metric(za['roles'][a],zb['roles'][b],za['component_root_index'][a],zb['component_root_index'][b])
        lists.extend(dict(control=name,**p) for p in qq)
    out['limitations']={'does_not_restore_truncated_context':True,'land_not_completeness':True,'new_data_needed_for_south_extension':True,
        'required_design':'Versioned expanded ComCat acquisition; same-snapshot restriction requery compared with original to separate revisions from geography; then rerun matching/NN/calibration. No downloads in this lane.'}
    dump(target/'EXISTING_EDGE_CONTROLS.json',out);writecsv(target/'EXISTING_EDGE_PAIRS.csv',lists)

def as_record(r):
    return Record(r['record_id'],r['source'],r['event_id'] or None,r['time_utc'],utc_nanoseconds(r['time_utc']),float(r['latitude']),float(r['longitude']),float(r['depth_km']) if r['depth_km'] else None,float(r['magnitude']),r['magnitude_type'] or None)

def matching(target,raw,primary,idx):
    expected=readj(MATCH/'pilot_results.json')['sensitivity']
    broad=candidate_edges([as_record(r) for r in raw['ssn']],[as_record(r) for r in raw['usgs']],60,100)
    principal={(p['ssn_record_id'],p['usgs_record_id']) for p in readj(MATCH/'graph_candidate_pairs.json')}
    allout=[];flat=[]
    for seconds in [10,30,60]:
        for km in [10,50,100]:
            ee=[e for e in broad if in_window(e,seconds,km)];pp=optimal_assignment(ee,seconds,km)
            old=next(v for v in expected if v['time_window_seconds']==seconds and v['distance_window_km']==km)
            assert len(pp)==old['graph_candidate_assignments'] and len(ee)==old['candidate_edges']
            writecsv(target/f'matching_{seconds}s_{km}km.csv',[dict(ssn_record_id=a,usgs_record_id=b) for a,b in sorted(pp)])
            both=sorted([(a,b) for a,b in pp if a in idx['ssn'] and b in idx['usgs']])
            a=np.array([idx['ssn'][x] for x,y in both],dtype=int);b=np.array([idx['usgs'][y] for x,y in both],dtype=int)
            la,lb=primary['ssn']['labels'][0],primary['usgs']['labels'][0]
            z=metric(la['roles'][a],lb['roles'][b],la['component_root_index'][a],lb['component_root_index'][b])
            out=dict(seconds=seconds,km=km,candidate_edges=len(ee),assigned_all=len(pp),assigned_both_above_cut=len(both),
                shared_both_with_principal=sum(p in principal for p in both),assignment_edge_jaccard_with_principal=len(pp&principal)/len(pp|principal),
                coverage_ssn=len(both)/len(idx['ssn']),coverage_usgs=len(both)/len(idx['usgs']),metrics=z)
            allout.append(out);flat.append({k:v for k,v in out.items() if k!='metrics'}|dict(agreement=z['agreement'],kappa=z['kappa'],ARI=z['partition']['ARI']))
    dump(target/'NINE_WINDOW_NN.json',allout);writecsv(target/'NINE_WINDOW_NN.csv',flat)

def retained_tables(target):
    metrics=readj(METHODS/'deterministic_study_v3/PAIRED_METRICS.json')
    annual=metrics['M4p5_native_author']['by_year']
    writecsv(target/'ANNUAL_RETAINED_V3.csv',[dict(year=y,n=z['n'],agreement=z['agreement'],kappa=z['kappa'],ARI=z['partition']['ARI'],matrix=json.dumps(z['matrix_first_rows_second_columns'])) for y,z in annual.items()])
    factorial=readj(METHODS/'deterministic_study_v3/MEASUREMENT_FACTORIAL.json')
    writecsv(target/'FACTORIAL_16_RETAINED_V3.csv',[dict(flags_time_location_magnitude=''.join(map(str,z['measurement_flags_time_location_magnitude'])),cut_source=z['cut_source'],fixed_cut=z['fixed_cut'],
        **{f'{p}_{k}':z[p][k] if k!='ARI' else z[p]['partition']['ARI'] for p in ['all','held_out_2021_2025'] for k in ['n','agreement','kappa','ARI']}) for z in factorial])
    dump(target/'RETAINED_TABLES_PROVENANCE.json',dict(annual_source_sha256=sha(METHODS/'deterministic_study_v3/PAIRED_METRICS.json'),factorial_source_sha256=sha(METHODS/'deterministic_study_v3/MEASUREMENT_FACTORIAL.json'),
        not_new_experiments=True,not_additive_causal_attribution=True,factorial=factorial,annual=annual))

def alaska(target):
    raw=[r for r in readcsv(PILOT/'inputs/alaska_usgs.csv') if Decimal(r['magnitude'])>=Decimal('4.5')]
    prepared=prepare_rows(raw);old=readj(DESIGN/'web_inputs/nn_parity/round_04/alaska_4_5_js.json')
    assert readj(DESIGN/'web_inputs/nn_parity/round_04/alaska_4_5_comparison.json')['status']=='PASS'
    payload=old['results'];assert prepared['ids']==payload['ids']
    family=next(f for f in payload['families'] if f['spec'].get('scientific'))
    assert family['spec']['training_end_exclusive']=='2023-01-01'
    nnrole=np.array([ROLE_CODE[r] for r in family['roles']]);nngroup=np.array(family['component'])
    days=prepared['utc_microseconds'].astype(float)/(86400*1e6)
    gk=gk_classify(days,prepared['lat_deg'],prepared['lon_deg'],prepared['m'])
    reference=gk_classify(days,prepared['lat_deg'],prepared['lon_deg'],prepared['m'],indexed=False)
    checks={k:bool(np.array_equal(gk[k],reference[k])) for k in ['group','native_flag','roles','root_indices']}
    assert all(checks.values()),checks
    gkrole=np.array([ROLE_CODE[str(r)] for r in gk['roles']])
    # GK zero groups are distinct singletons; never merge all ungrouped events.
    gkgroup=np.array([f'g{v}' if v else f's{i}' for i,v in enumerate(gk['group'])])
    _,gkgroup=np.unique(gkgroup,return_inverse=True)
    years=np.array([r['time_utc'][:4] for r in prepared['source_rows']])
    masks={'full_2020_2025':np.ones(len(years),dtype=bool),'development_2020_2022':years<'2023','evaluation_2023_2025':years>='2023'}
    masks.update({'year_'+y:years==y for y in sorted(set(years))})
    results={p:metric(nnrole[mask],gkrole[mask],nngroup[mask],gkgroup[mask]) for p,mask in masks.items()}
    np.savez_compressed(target/'ALASKA_NN_GK_M4_5_ARRAYS.npz',nn_role=nnrole,nn_component=nngroup,gk_role=gkrole,gk_component=gkgroup,**{f'gk_{k}':v for k,v in gk.items() if isinstance(v,np.ndarray)})
    writecsv(target/'ALASKA_NN_GK_M4_5.csv',[dict(record_id=rid,time_utc=prepared['source_rows'][i]['time_utc'],nn_role=LABELS[int(nnrole[i])],nn_component=int(nngroup[i]),gk_role=LABELS[int(gkrole[i])],gk_component=int(gkgroup[i])) for i,rid in enumerate(prepared['ids'])])
    dump(target/'ALASKA_TEMPORAL_METHOD_COMPARISON.json',dict(source='retained Alaska ComCat only',native_events=len(raw),NN_source_sha256=sha(DESIGN/'web_inputs/nn_parity/round_04/alaska_4_5_js.json'),family_spec=family['spec'],GK_indexed_exhaustive=checks,periods=results,
        interpretation='Conditional agreement of methods on one source; neither physical truth nor across-agency transfer validation.'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--cpu-approved',action='store_true');args=parser.parse_args()
    if not args.cpu_approved:raise PermissionError('Root CPU go-ahead required')
    verify_frozen();set_num_threads(1)
    target=HERE/'runs'/args.run_id
    if target.exists():raise FileExistsError('Never overwrite any completed or failed run')
    target.mkdir(parents=True)
    config=readj(HERE/'PROTOCOL.json')
    started=time.perf_counter()
    manifest=dict(schema='round2-catalog-run/1',started_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=sha(__file__),protocol_json_sha256=sha(HERE/'PROTOCOL.json'),protocol_md_sha256=sha(HERE/'PROTOCOL.md'),amendment_sha256={n:sha(HERE/n) for n in ['AMENDMENT_01.md','AMENDMENT_02.md']},inputs_manifest_sha256=sha(HERE/'INPUTS.json'),vendor_manifest_sha256=sha(HERE/'VENDOR.json'),python=sys.version,numpy=np.__version__,threads=1,cpu_approved_by_root=True)
    dump(target/'STARTED.json',manifest)
    try:
        raw={s:readcsv(PILOT/'inputs'/f'{s}.csv') for s in ['ssn','usgs']};pairs=readj(MATCH/'graph_candidate_pairs.json')
        cases=make_weights(target,raw,config)
        primary,idx,pp,si,ui,units,masks=pair_analysis(target,cases,raw,pairs,config)
        coverage_geography(target,raw,pairs,primary,idx);edge_controls(target,primary,idx,pp)
        matching(target,raw,primary,idx);retained_tables(target);alaska(target)
        verify_frozen()
        manifest.update(status='PASS',completed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,
            output_files=[dict(path=p.relative_to(target).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(target.rglob('*')) if p.is_file()],
            not_physical_truth=True,no_public_or_git_changes=True)
        dump(target/'MANIFEST.json',manifest)
        print(json.dumps(dict(status='PASS',directory=str(target),seconds=manifest['elapsed_seconds'],output_files=len(manifest['output_files']))),flush=True)
    except BaseException as e:
        dump(target/'FAILED.json',{**manifest,'status':'FAIL','exception_type':type(e).__name__,'error':str(e),'elapsed_seconds':time.perf_counter()-started})
        raise
if __name__=='__main__':main()
