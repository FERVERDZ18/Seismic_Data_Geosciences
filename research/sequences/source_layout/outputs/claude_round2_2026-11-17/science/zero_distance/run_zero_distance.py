"""Audit retained zero-distance edges and a frozen-parent edge-deletion diagnostic."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,json,sys,time
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists())
sys.dont_write_bytecode=True;sys.path.insert(0,str(HERE.parent/'catalog'))
import run_catalog as cat
np=cat.np
def score_and_zero(parent,TN,RN):
    with np.errstate(divide='ignore',invalid='ignore'):score=np.log10(TN)+np.log10(RN)
    return score,(parent>=0)&((RN==0)|np.isneginf(score))
def diagnostics(ids,rows,parent,TN,RN,distance,fit_score,source,w,cut):
    score,zero=score_and_zero(parent,TN,RN);dev=np.array([r['time_utc']<'2021-01-01' for r in rows]);defined=parent>=0
    edges=[]
    for i in np.flatnonzero(zero):
        j=int(parent[i]);a,b=rows[j],rows[i]
        lag=(cat.utc_nanoseconds(b['time_utc'])-cat.utc_nanoseconds(a['time_utc']))/1e9
        assert lag>0,('zero_edge_not_strict_UTC',ids[i],ids[j])
        identical=float(a['latitude'])==float(b['latitude']) and float(a['longitude'])==float(b['longitude'])
        edges.append(dict(source=source,w=w,magnitude_cut=cut,target_id=ids[i],parent_id=ids[j],target_UTC=b['time_utc'],parent_UTC=a['time_utc'],target_latitude=b['latitude'],target_longitude=b['longitude'],parent_latitude=a['latitude'],parent_longitude=a['longitude'],target_M=b['magnitude'],parent_M=a['magnitude'],lag_seconds=lag,lag_days=lag/86400,target_year=b['time_utc'][:4],period='development' if dev[i] else 'evaluation',identical_reported_coordinates=identical,computed_parent_distance_km=float(distance[i]),RN=float(RN[i]),TN=float(TN[i]),cut_score=str(score[i]),category='identical_coordinates' if identical else 'distinct_coordinates_computed_distance_zero' if distance[i]==0 else 'RN_or_score_zero_with_positive_distance'))
    counts=dict(source=source,w=w,magnitude_cut=cut,n=len(ids),
        without_native_parent=int((~defined).sum()),
        defined_parent_RN0=int(np.sum(defined&(RN==0))),
        defined_parent_TN0=int(np.sum(defined&(TN==0))),
        defined_parent_cut_score_neginf=int(np.sum(defined&np.isneginf(score))),
        defined_parent_cut_score_other_nonfinite=int(np.sum(defined&~np.isfinite(score)&~np.isneginf(score))),
        zero_edge_rule_count=int(zero.sum()),
        zero_by_target_year=dict(sorted(Counter(e['target_year'] for e in edges).items())),
        zero_by_period=dict(Counter(e['period'] for e in edges)),
        zero_coordinate_categories=dict(Counter(e['category'] for e in edges)),
        lag_seconds_min=min((e['lag_seconds'] for e in edges),default=None),
        lag_seconds_max=max((e['lag_seconds'] for e in edges),default=None),
        development_fit_score_nonfinite_all=int(np.sum(dev&~np.isfinite(fit_score))),
        development_fit_score_nonfinite_defined_parent=int(np.sum(dev&defined&~np.isfinite(fit_score))),
        development_fit_score_finite=int(np.sum(dev&np.isfinite(fit_score))))
    return counts,edges,score,zero
def family_summary(rows,ids,labels,anchor_ids):
    root=labels['component_root_index'];groups=[]
    for g in np.unique(root):
        ii=np.flatnonzero(root==g)
        if len(ii)<2:continue
        times=[cat.utc_nanoseconds(rows[i]['time_utc']) for i in ii]
        groups.append(dict(root_id=ids[int(g)],n=len(ii),start_UTC=rows[int(ii[0])]['time_utc'],end_UTC=rows[int(ii[-1])]['time_utc'],span_days=(times[-1]-times[0])/(86400*1e9),max_consecutive_gap_days=max((b-a for a,b in zip(times,times[1:])),default=0)/(86400*1e9)))
    idx={rid:i for i,rid in enumerate(ids)};anchors={}
    for year,rid in anchor_ids.items():
        if rid not in idx:anchors[year]=dict(status='anchor_not_selected',record_id=rid);continue
        g=int(root[idx[rid]]);members=np.flatnonzero(root==g)
        anchors[year]=dict(status='computed',anchor_id=rid,n=len(members),start_UTC=rows[int(members[0])]['time_utc'],end_UTC=rows[int(members[-1])]['time_utc'],span_days=(cat.utc_nanoseconds(rows[int(members[-1])]['time_utc'])-cat.utc_nanoseconds(rows[int(members[0])]['time_utc']))/(86400*1e9))
    return dict(nonunit_components=len(groups),maximum_span_component=max(groups,key=lambda r:(r['span_days'],r['root_id'])) if groups else None,largest_component=max(groups,key=lambda r:(r['n'],r['root_id'])) if groups else None,fixed_anchor_families=anchors)
def compare_sources(a,b,pairs):
    idxa={v:i for i,v in enumerate(a['ids'])};idxb={v:i for i,v in enumerate(b['ids'])}
    pairs=sorted([p for p in pairs if p['ssn_record_id'] in idxa and p['usgs_record_id'] in idxb],key=lambda p:(p['ssn_record_id'],p['usgs_record_id']))
    si=np.array([idxa[p['ssn_record_id']] for p in pairs]);ui=np.array([idxb[p['usgs_record_id']] for p in pairs]);year=np.array([a['rows'][i]['time_utc'][:4] for i in si])
    out={}
    for variant in ['before','deleted_zero_edges']:
        la,lb=a[variant],b[variant]
        out[variant]={name:cat.metric(la['roles'][si[m]],lb['roles'][ui[m]],la['component_root_index'][si[m]],lb['component_root_index'][ui[m]]) for name,m in [('full',np.ones(len(si),dtype=bool)),('evaluation',year>='2021')]}
    return out
def main(run_id,cpu_approved):
    if not cpu_approved:raise PermissionError('Root CPU go-ahead required')
    seal=cat.readj(HERE/'ANALYSIS_SEAL.json');assert cat.sha(__file__)==seal['runner_sha256']
    assert cat.sha(HERE/'PROTOCOL.json')==seal['protocol_sha256']
    assert cat.sha(Path(cat.__file__))==seal['catalog_helper_sha256']
    protocol=cat.readj(HERE/'PROTOCOL.json');assert cat.sha(HERE/'PROTOCOL.md')==protocol['md_sha256']
    for spec in protocol['inputs']:assert cat.sha(ROOT/spec['path'])==spec['sha256'],spec['path']
    target=HERE/'runs'/run_id
    if target.exists():raise FileExistsError('Never overwrite completed or failed evidence')
    target.mkdir(parents=True);started=time.perf_counter()
    receipt=dict(started_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=cat.sha(HERE/'PROTOCOL.json'),runner_sha256=cat.sha(__file__),analysis_seal_sha256=cat.sha(HERE/'ANALYSIS_SEAL.json'))
    cat.dump(target/'STARTED.json',receipt)
    try:
        pairs=cat.readj(cat.MATCH/'graph_candidate_pairs.json');oldcases=cat.readj(cat.DESIGN/'scientific_diagnostics.compact.json')['cases'];anchors={'ssn':{},'usgs':{}}
        for year in ['2017','2022']:
            uid=oldcases[year]['anchor']['record_id'];pair=next((p for p in pairs if p['usgs_record_id']==uid),None)
            anchors['usgs'][year]=uid;anchors['ssn'][year]=pair['ssn_record_id'] if pair else None
        cases={};counts=[];edgelist=[];source_metrics=[]
        for spec in protocol['cases']:
            d=ROOT/spec['directory'];ids=cat.readj(d/'ids.json');rows=cat.readj(d/'rows.json');meta=cat.readj(d/'metadata.json');a=np.load(d/'arrays.npz')
            assert ids==[r['record_id'] for r in rows]
            parent=a['parent_index'];TN=a['TN'];RN=a['RN'];source,w=spec['source'],spec['w']
            count,edges,score,zero=diagnostics(ids,rows,parent,TN,RN,a['parent_distance_km'],a['eta_log10'],source,w,'4.5')
            assert count['development_fit_score_finite']==meta['fit']['finite_events']
            before=cat.families_from_cut(parent,score,a['reported_magnitude'],a['t_year'],ids,meta['fit']['threshold_log10'],inclusive=True)
            assert np.array_equal(before['roles'],a['delta_0_roles']) and np.array_equal(before['component_root_index'],a['delta_0_component_root_index'])
            deleted=parent.copy();deleted[zero]=-1
            after=cat.families_from_cut(deleted,score,a['reported_magnitude'],a['t_year'],ids,meta['fit']['threshold_log10'],inclusive=True)
            count.update(zero_edges_accepted_before=int(np.sum(zero&before['strong_link_mask'])),accepted_neginf_edges_before=int(np.sum(np.isneginf(score)&before['strong_link_mask'])),roles_changed=int(np.sum(before['roles']!=after['roles'])),families_before=family_summary(rows,ids,before,anchors[source]),families_deleted_zero=family_summary(rows,ids,after,anchors[source]))
            counts.append(count);edgelist.extend(edges)
            dest=target/f'{source}_w{cat.wtag(w)}';dest.mkdir();cat.dump(dest/'ids.json',ids)
            np.savez_compressed(dest/'EDGE_DELETION_ARRAYS.npz',original_parent=parent,zero_edge_mask=zero,deleted_parent=deleted,original_score=score,**{f'before_{k}':v for k,v in before.items() if isinstance(v,np.ndarray)},**{f'deleted_{k}':v for k,v in after.items() if isinstance(v,np.ndarray)})
            dev=np.array([r['time_utc']<'2021-01-01' for r in rows])
            source_metrics.append(dict(source=source,w=w,periods={name:cat.metric(before['roles'][m],after['roles'][m],before['component_root_index'][m],after['component_root_index'][m]) for name,m in [('full',np.ones(len(ids),dtype=bool)),('evaluation',~dev)]}))
            cases[source,w]=dict(ids=ids,rows=rows,before=before,deleted_zero_edges=after)
        comparisons={str(w):compare_sources(cases['ssn',w],cases['usgs',w],pairs) for w in sorted({w for s,w in cases})}
        extra=[]
        for spec in protocol['optional_M3_5_w1']:
            source=spec['source'];raw=cat.readcsv(cat.PILOT/'inputs'/f'{source}.csv');lookup={r['record_id']:r for r in raw};x=cat.readj(ROOT/spec['path'])['results'];ids=x['ids'];rows=[lookup[rid] for rid in ids]
            parent=np.asarray(x['parent'],dtype=int);TN=np.asarray(x['tn'],dtype=float);RN=np.asarray(x['rn'],dtype=float)
            with np.errstate(divide='ignore',invalid='ignore'):fit_score=np.log10(TN*RN)
            count,edges,_,_=diagnostics(ids,rows,parent,TN,RN,np.asarray(x['distance'],dtype=float),fit_score,source,1.,'3.5')
            count['family_classification_performed']=False;extra.append(count);edgelist.extend(edges)
        cat.writecsv(target/'ZERO_EDGE_LIST.csv',edgelist)
        cat.dump(target/'RESULTS.json',dict(status='PASS',M4_5_cases=counts,M3_5_diagnostics_only=extra,same_source_edge_deletion_changes=source_metrics,cross_source_weight_comparisons=comparisons,fixed_anchors=anchors,not_physical_duplicate_identity=True,not_a_corrected_or_refitted_algorithm=True))
        for spec in protocol['inputs']:assert cat.sha(ROOT/spec['path'])==spec['sha256'],spec['path']
        receipt.update(status='PASS',completed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,output_files=[dict(path=p.relative_to(target).as_posix(),sha256=cat.sha(p),bytes=p.stat().st_size) for p in sorted(target.rglob('*')) if p.is_file()])
        cat.dump(target/'MANIFEST.json',receipt);print(json.dumps(dict(status='PASS',cases=len(counts),additional_M3_5=len(extra),seconds=receipt['elapsed_seconds']),indent=2))
    except BaseException as e:cat.dump(target/'FAILED.json',{**receipt,'status':'FAIL','error_type':type(e).__name__,'error':str(e)});raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='zero_run_01');p.add_argument('--cpu-approved',action='store_true');a=p.parse_args();main(a.run_id,a.cpu_approved)
