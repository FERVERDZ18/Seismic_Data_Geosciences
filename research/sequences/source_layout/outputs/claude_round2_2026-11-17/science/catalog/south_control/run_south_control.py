"""Version-separated, fixed-protocol southern context control. CPU-gated."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import argparse,hashlib,json,math,sys,time
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE.parent))
import run_catalog as cat
np=cat.np;ROOT=cat.ROOT
from pilot_catalog_reconciliation import epicentral_distance,EARTH_RADIUS_KM
def iso_ms(ms):return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(ms))).isoformat(timespec='milliseconds').replace('+00:00','Z')
def current_row(feature,body_name):
    p=feature['properties'];lon,lat,depth=feature['geometry']['coordinates']
    return dict(record_id='usgs-s6-current~'+feature['id'],source='usgs',event_id=feature['id'],time_utc=iso_ms(p['time']),latitude=str(lat),longitude=str(lon),depth_km='' if depth is None else str(depth),magnitude=str(p['mag']),magnitude_type=p.get('magType') or '',source_file=body_name,source_record='',package_row='')
def inside(r,lat_min):return '2016-01-01'<=r['time_utc']<'2026-01-01' and lat_min<=float(r['latitude'])<=33 and -118<=float(r['longitude'])<=-86 and Decimal(r['magnitude'])>=Decimal('3.5')
def source_rows():
    package=cat.readj(ROOT/'system/dist/data/catalogs/ssn-mx/events.json')
    fields=package['fields'];ssn=[]
    for i,vals in enumerate(package['rows'],1):
        x=dict(zip(fields,vals))
        if not ('2016-01-01'<=x['time']<'2026-01-01' and 12<=x['latitude']<=33 and -118<=x['longitude']<=-86):continue
        r=dict(record_id='ssn-mx-historical~'+x['id'],source='ssn',event_id='',time_utc=x['time'],latitude=str(x['latitude']),longitude=str(x['longitude']),depth_km='' if x['depth'] is None else str(x['depth']),magnitude=x['raw_magnitude'],magnitude_type='',source_file=x['file'],source_record=x['source_record'],package_row=i)
        if Decimal(r['magnitude'])>=Decimal('3.5'):ssn.append(r)
    acq=HERE/'acquisition/acquisition_03';manifest=cat.readj(acq/'MANIFEST.json');assert manifest['status']=='PASS'
    usgs=[];features={}
    protocol=cat.readj(HERE/'PROTOCOL.json')
    for response in manifest['responses']:
        assert response['status']=='PASS';p=acq/response['body_file'];assert cat.sha(p)==response['body_sha256']
        query=next(q for q in protocol['queries'] if q['label']==response['label'])
        for feature in cat.readj(p)['features']:
            row=current_row(feature,p.name)
            if query['local_start_inclusive']<=row['time_utc']<query['local_end_exclusive'] and inside(row,12):
                assert row['event_id'] not in features
                usgs.append(row);features[row['event_id']]=feature
    return ssn,usgs,features
def signature(r):
    return (cat.utc_nanoseconds(r['time_utc']),float(r['latitude']),float(r['longitude']),None if r['depth_km']=='' else Decimal(r['depth_km']),Decimal(r['magnitude']),r['magnitude_type'] or None)
def check_SSN(original,current):
    old={r['record_id']:r for r in original};new={r['record_id']:r for r in current if inside(r,14)}
    assert set(old)==set(new)
    assert all(signature(old[k])==signature(new[k]) for k in old)
    return dict(status='PASS',exact_ids_and_selected_measures=True,rows=len(old))
def revision_report(target,old,current,features):
    a={r['event_id']:r for r in old};b={r['event_id']:r for r in current if inside(r,14)}
    aliases={}
    for eid,f in features.items():
        for alias in (f['properties'].get('ids') or '').split(','):
            if alias:aliases.setdefault(alias,[]).append(eid)
    records=[];fields=['time_utc_instant','latitude','longitude','depth_km','magnitude','magnitude_type']
    for eid in sorted(set(a)|set(b)):
        if eid in a and eid in b:
            changes=[field for field,x,y in zip(fields,signature(a[eid]),signature(b[eid])) if x!=y]
            status='same_selected_measures' if not changes else 'changed_selected_measures'
        else:changes=[];status='old_only_in_fixed_domain' if eid in a else 'current_only_in_fixed_domain'
        records.append(dict(event_id=eid,status=status,changed_fields='|'.join(changes),old_magnitude=a[eid]['magnitude'] if eid in a else None,current_magnitude=b[eid]['magnitude'] if eid in b else None,
                            current_alias_preferred_ids='|'.join(aliases.get(eid,[])) if eid not in b else ''))
    cat.writecsv(target/'COMCAT_CURRENT_VS_ORIGINAL.csv',records)
    return dict(old_rows=len(a),current_rows=len(b),states=dict(Counter(r['status'] for r in records)),
        field_change_counts=dict(Counter(f for r in records for f in r['changed_fields'].split('|') if f)),
        old_only_with_current_alias=sum(r['status']=='old_only_in_fixed_domain' and bool(r['current_alias_preferred_ids']) for r in records),
        limits='Different query date/preferred snapshot and query-selection effects; not a retained public-history replay. Current restriction is from the exact same expanded HTTP bodies. Missing IDs are not labelled deleted earthquakes.')
def baseline_case(source,raw):
    p=cat.METHODS/'deterministic_study_v3/cases'/f'M4p5_{source}_native_author'
    prepared=cat.prepare_rows([r for r in raw if Decimal(r['magnitude'])>=Decimal('4.5')]);assert prepared['ids']==cat.readj(p/'ids.json')
    z=np.load(p/'arrays.npz');result={k:z[k] for k in ['parent_index','TN','RN','eta_log10','parent_dt_years','parent_distance_km']}
    metadata=cat.readj(p/'metadata.json');labels=cat.classify_case(prepared,result,metadata['fit']['threshold_log10'])
    assert np.array_equal(labels['roles'],z['roles']) and np.array_equal(labels['component_root_index'],z['component_root_index'])
    return dict(prepared=prepared,result=result,fit=metadata['fit'],labels={'native':labels,'transported':labels})
def calculate_case(target,scenario,source,raw,transport_cut):
    dest=target/'cases'/f'{scenario}_{source}';dest.mkdir(parents=True)
    prepared=cat.prepare_rows([r for r in raw if Decimal(r['magnitude'])>=Decimal('4.5')])
    result=cat.run_arrays(prepared['t_year'],prepared['lat_deg'],prepared['lon_deg'],prepared['m'],d=1.6,w=1.,q=.5,backend='kd')
    train=np.array([r['time_utc']<'2021-01-01' for r in prepared['source_rows']]);fit=cat.author_normalmix(result['eta_log10'][train]);diagnostics=cat.mixture_diagnostics(fit,result['eta_log10'][train])
    labels={}
    if fit['status']=='estimable':labels['native']=cat.classify_case(prepared,result,fit['threshold_log10'])
    if transport_cut is not None:labels['transported']=cat.classify_case(prepared,result,transport_cut)
    arrays={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
    arrays.update({f'{name}_{k}':v for name,x in labels.items() for k,v in x.items() if isinstance(v,np.ndarray)})
    np.savez_compressed(dest/'arrays.npz',**arrays);cat.dump(dest/'ids.json',prepared['ids']);cat.dump(dest/'rows.json',prepared['source_rows'])
    cat.dump(dest/'metadata.json',dict(scenario=scenario,source=source,fit=fit,diagnostics=diagnostics,transported_cut=transport_cut,development_events=int(train.sum()),events=len(prepared['ids']),kernel_metadata=result['metadata'],arrays_sha256=cat.sha(dest/'arrays.npz'),native_summary=cat.case_summary(prepared,labels['native']) if 'native' in labels else None))
    return dict(prepared=prepared,result=result,fit=fit,labels=labels)
def assign(rows):
    ee=cat.candidate_edges([cat.as_record(r) for r in rows['ssn']],[cat.as_record(r) for r in rows['usgs']],30,50)
    return sorted(cat.optimal_assignment(ee,30,50)),len(ee)
def compare(cases,pairs,variant='native'):
    idx={s:{rid:i for i,rid in enumerate(cases[s]['prepared']['ids'])} for s in cases}
    states=Counter('both' if a in idx['ssn'] and b in idx['usgs'] else 'ssn_only' if a in idx['ssn'] else 'usgs_only' if b in idx['usgs'] else 'neither' for a,b in pairs)
    retained=[(a,b) for a,b in pairs if a in idx['ssn'] and b in idx['usgs']]
    if any(variant not in c['labels'] for c in cases.values()):return dict(status='not_estimable',retention=dict(states)),retained
    si=np.array([idx['ssn'][a] for a,b in retained],dtype=int);ui=np.array([idx['usgs'][b] for a,b in retained],dtype=int)
    years=np.array([cases['ssn']['prepared']['source_rows'][i]['time_utc'][:4] for i in si]);a,b=cases['ssn']['labels'][variant],cases['usgs']['labels'][variant]
    masks={'full':np.ones(len(si),dtype=bool),'development':years<'2021','evaluation':years>='2021'}
    return dict(status='computed',native_selected={s:len(idx[s]) for s in idx},retention=dict(states),coverage={s:len(retained)/len(idx[s]) for s in idx},
        periods={p:cat.metric(a['roles'][si[m]],b['roles'][ui[m]],a['component_root_index'][si[m]],b['component_root_index'][ui[m]]) for p,m in masks.items()}),retained
def common_context_changes(B,C,common):
    out={}
    for s,pos in [('ssn',0),('usgs',1)]:
        ids=[p[pos] for p in common];ib={rid:i for i,rid in enumerate(B[s]['prepared']['ids'])};ic={rid:i for i,rid in enumerate(C[s]['prepared']['ids'])}
        bi=np.array([ib[rid] for rid in ids],dtype=int);ci=np.array([ic[rid] for rid in ids],dtype=int)
        years=np.array([B[s]['prepared']['source_rows'][i]['time_utc'][:4] for i in bi])
        bpar=B[s]['result']['parent_index'];cpar=C[s]['result']['parent_index']
        parentb=[None if bpar[i]<0 else B[s]['prepared']['ids'][int(bpar[i])] for i in bi];parentc=[None if cpar[i]<0 else C[s]['prepared']['ids'][int(cpar[i])] for i in ci]
        out[s]={}
        for period,m in [('full',np.ones(len(ids),dtype=bool)),('evaluation',years>='2021')]:
            selected=np.flatnonzero(m)
            entry=dict(n=int(m.sum()),changed_parent=sum(parentb[i]!=parentc[i] for i in selected),new_parent_outside_old_domain=sum(parentc[i] is not None and parentc[i] not in ib for i in selected))
            for v in ['native','transported']:
                if 'native' in B[s]['labels'] and v in C[s]['labels']:
                    a,b=B[s]['labels']['native'],C[s]['labels'][v]
                    entry['B_native_vs_C_'+v]=cat.metric(a['roles'][bi[m]],b['roles'][ci[m]],a['component_root_index'][bi[m]],b['component_root_index'][ci[m]])
            out[s][period]=entry
    return out
def case2017(target,expanded,cases):
    oldcase=cat.readj(cat.DESIGN/'scientific_diagnostics.compact.json')['cases']['2017'];anchor=oldcase['anchor'];a=cat.as_record(anchor)
    out=[];summary=[]
    for s,rows in expanded.items():
        idx={rid:i for i,rid in enumerate(cases[s]['prepared']['ids'])}
        for r in rows:
            days=(cat.utc_nanoseconds(r['time_utc'])-a.time_ns)/(86400*1e9)
            if -7<=days<=30 and epicentral_distance(a,cat.as_record(r))<=150+1e-9:
                role=None
                if r['record_id'] in idx and 'native' in cases[s]['labels']:role=cat.LABELS[int(cases[s]['labels']['native']['roles'][idx[r['record_id']]])]
                out.append(dict(source=s,**{k:r[k] for k in ['record_id','time_utc','latitude','longitude','magnitude']},south_of_old_14=float(r['latitude'])<14,native_NN_M4_5_role=role))
        for cut in [Decimal('3.5'),Decimal('4.5')]:
            rr=[r for r in out if r['source']==s and Decimal(r['magnitude'])>=cut]
            summary.append(dict(source=s,cut=str(cut),circle_and_clock_rows=len(rr),south_of_old_14=sum(r['south_of_old_14'] for r in rr)))
    radius=150/EARTH_RADIUS_KM;alat=math.radians(a.latitude)
    lon_delta=math.degrees(math.asin(math.sin(radius)/math.cos(alat)))
    bounds=dict(minlatitude=a.latitude-math.degrees(radius),maxlatitude=a.latitude+math.degrees(radius),minlongitude=a.longitude-lon_delta,maxlongitude=a.longitude+lon_delta)
    contained=bounds['minlatitude']>=12 and bounds['maxlatitude']<=33 and bounds['minlongitude']>=-118 and bounds['maxlongitude']<=-86
    cat.writecsv(target/'CASE_2017_CIRCLE_ROWS.csv',out)
    return dict(frozen_anchor=anchor,radius_km=150,relative_days_inclusive=[-7,30],circle_geodesic_bounds=bounds,new_rectangle_contains_full_circle=contained,counts=summary,
        limits='Retained observations, not complete physical sequence truth; controls southern clipping of the specified case circle, not all possible NN context outside the expanded rectangle.')
def main(run_id,cpu_approved):
    if not cpu_approved:raise PermissionError('Root CPU gate required')
    seal=cat.readj(HERE/'ANALYSIS_SEAL.json');assert cat.sha(__file__)==seal['runner_sha256']
    for name,h in seal['frozen_files'].items():assert cat.sha(HERE/name)==h,('analysis_code_or_protocol_changed',name)
    cat.verify_frozen()
    for n,h in cat.readj(HERE/'SEAL.json')['files'].items():assert cat.sha(HERE/n)==h
    for row in cat.readj(HERE/'INPUTS.json'):assert cat.sha(ROOT/row['path'])==row['sha256']
    assert cat.sha(HERE/'acquisition/acquisition_03/MANIFEST.json')==seal['acquisition_manifest_sha256']
    target=HERE/'runs'/run_id
    if target.exists():raise FileExistsError('Never overwrite a completed or failed run')
    target.mkdir(parents=True);started=time.perf_counter();cat.set_num_threads(1)
    receipt=dict(started_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=cat.sha(__file__),analysis_seal_sha256=cat.sha(HERE/'ANALYSIS_SEAL.json'),cpu_approved_by_root=True)
    cat.dump(target/'STARTED.json',receipt)
    try:
        ssn,usgs,features=source_rows();old={s:cat.readcsv(cat.PILOT/'inputs'/f'{s}.csv') for s in ['ssn','usgs']}
        ssncheck=check_SSN(old['ssn'],ssn);revision=revision_report(target,old['usgs'],usgs,features)
        B={s:[r for r in rows if inside(r,14)] for s,rows in [('ssn',ssn),('usgs',usgs)]};C=dict(ssn=ssn,usgs=usgs)
        profiles=[]
        for s,rows in C.items():
            for band in ['south_12_to_14','old_14_to_33','expanded_12_to_33']:
                rr=[r for r in rows if band=='expanded_12_to_33' or (float(r['latitude'])<14)==(band=='south_12_to_14')]
                for cut in [Decimal('3.5'),Decimal('4.5')]:
                    selected=[r for r in rr if Decimal(r['magnitude'])>=cut]
                    for year in ['all']+[str(y) for y in range(2016,2026)]:profiles.append(dict(source=s,band=band,cut=str(cut),year=year,n=sum(year=='all' or r['time_utc'].startswith(year) for r in selected)))
        cat.writecsv(target/'SOURCE_SUPPORT_BY_BAND.csv',profiles)
        support={s:next(z['n'] for z in profiles if z['source']==s and z['band']=='south_12_to_14' and z['cut']=='4.5' and z['year']=='all') for s in ['ssn','usgs']}
        A={s:baseline_case(s,old[s]) for s in ['ssn','usgs']}
        bc=dict(ssn=A['ssn'],usgs=calculate_case(target,'B_current_14','usgs',B['usgs'],A['usgs']['fit'].get('threshold_log10')))
        cc={s:calculate_case(target,'C_current_12',s,C[s],bc[s]['fit'].get('threshold_log10')) for s in ['ssn','usgs']}
        pairsB,edgesB=assign(B);pairsC,edgesC=assign(C)
        for name,rows,pairs in [('B',B,pairsB),('C',C,pairsC)]:
            for s,rr in rows.items():cat.writecsv(target/f'{name}_{s}_cohort.csv',rr)
            cat.writecsv(target/f'{name}_candidate_assignments.csv',[dict(ssn_record_id=a,usgs_record_id=b) for a,b in pairs])
        comparisons={};retained={}
        pairsA=sorted((p['ssn_record_id'],p['usgs_record_id']) for p in cat.readj(cat.MATCH/'graph_candidate_pairs.json'))
        for scenario,cases,pairs in [('A',A,pairsA),('B',bc,pairsB),('C',cc,pairsC)]:
            comparisons[scenario]={}
            for variant in ['native','transported']:comparisons[scenario][variant],retained[scenario]=compare(cases,pairs,variant)
        common=sorted(set(retained['B'])&set(retained['C']))
        context=common_context_changes(bc,cc,common)
        fixed={}
        for scenario,cases in [('B',bc),('C',cc)]:
            fixed[scenario]={v:compare(cases,common,v)[0] for v in ['native','transported']}
        case=case2017(target,C,cc)
        import support_masks
        support_results=support_masks.run(target,C,cc,pairsC)
        result=dict(status='PASS',SSN_original_restriction_check=ssncheck,source_support_south_M4_5=support,descriptive_cross_source_support_in_south=all(n>0 for n in support.values()),ComCat_revisions_and_selection=revision,
            source_snapshot_dates=dict(SSN='header2026-11-06; original bytes unchanged',ComCat='two original HTTP intervals in acquisition_03/MANIFEST.json; non-atomic current acquisition'),
            assignments=dict(B=dict(edges=edgesB,pairs=len(pairsB)),C=dict(edges=edgesC,pairs=len(pairsC)),common_both_above_M4_5=len(common)),
            comparisons=comparisons,fixed_common_assignment_comparisons=fixed,common_endpoint_context_changes=context,case2017=case,observed_development_support_controls=support_results,
            common_detection_coverage_certified=False,physical_pair_identity_validated=False,new_comcat_not_spliced_into_old_snapshot=True)
        cat.dump(target/'RESULTS.json',result);cat.writecsv(target/'COMMON_B_C_CANDIDATES.csv',[dict(ssn_record_id=a,usgs_record_id=b) for a,b in common])
        for row in cat.readj(HERE/'INPUTS.json'):assert cat.sha(ROOT/row['path'])==row['sha256']
        cat.verify_frozen()
        receipt.update(status='PASS',completed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started,output_files=[dict(path=p.relative_to(target).as_posix(),bytes=p.stat().st_size,sha256=cat.sha(p)) for p in sorted(target.rglob('*')) if p.is_file()])
        cat.dump(target/'MANIFEST.json',receipt);print(json.dumps(dict(status='PASS',seconds=receipt['elapsed_seconds'],support=support,assignments=result['assignments'],case2017_counts=case['counts']),indent=2))
    except BaseException as e:
        cat.dump(target/'FAILED.json',{**receipt,'status':'FAIL','error_type':type(e).__name__,'error':str(e)});raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='south_run_01');p.add_argument('--cpu-approved',action='store_true');a=p.parse_args();main(a.run_id,a.cpu_approved)
