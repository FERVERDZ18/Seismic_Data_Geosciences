"""Fixed development-only observed-support cells; no instrumental coverage claim."""
from collections import Counter
from decimal import Decimal,ROUND_FLOOR
import math
import run_catalog as cat
np=cat.np
def cell_key(row,resolution):
    step=Decimal(str(resolution));lon=Decimal(str(row['longitude']));lat=Decimal(str(row['latitude']))
    x=(lon+180)/step;y=(lat+90)/step
    ix=int(x.to_integral_value(rounding=ROUND_FLOOR));iy=int(y.to_integral_value(rounding=ROUND_FLOOR))
    if lon==Decimal('-86') and x==x.to_integral_value():ix-=1
    if lat==Decimal('33') and y==y.to_integral_value():iy-=1
    return ix,iy
def cell_feature(key,resolution,counts):
    ix,iy=key;west=max(-118,-180+ix*resolution);east=min(-86,-180+(ix+1)*resolution)
    south=max(12,-90+iy*resolution);north=min(33,-90+(iy+1)*resolution)
    assert west<east and south<north
    return dict(type='Feature',properties=dict(ix=ix,iy=iy,resolution_degrees=resolution,SSN_development_M3_5=counts['ssn'][key],ComCat_development_M3_5=counts['usgs'][key],meaning='observed support in both sources, not detection/completeness coverage'),geometry=dict(type='Polygon',coordinates=[[[west,south],[east,south],[east,north],[west,north],[west,south]]]))
def build_mask(raw,resolution):
    keys={s:{r['record_id']:cell_key(r,resolution) for r in rows} for s,rows in raw.items()}
    counts={s:Counter(keys[s][r['record_id']] for r in rows if r['time_utc']<'2021-01-01' and Decimal(r['magnitude'])>=Decimal('3.5')) for s,rows in raw.items()}
    common=set(counts['ssn'])&set(counts['usgs'])
    return keys,counts,common
def restriction(target,source,rows,cut):
    prepared=cat.prepare_rows([r for r in rows if Decimal(r['magnitude'])>=Decimal('4.5')]);dest=target/source;dest.mkdir()
    cat.dump(dest/'ids.json',prepared['ids']);cat.dump(dest/'rows.json',prepared['source_rows'])
    if not prepared['ids']:
        np.savez_compressed(dest/'arrays.npz',parent_index=np.array([],dtype=int))
        meta=dict(status='not_estimable',reason='empty_mask_selected_cohort',events=0,transported_C_cut=cut)
        cat.dump(dest/'metadata.json',meta);return dict(prepared=prepared,result=None,labels=None,metadata=meta)
    result=cat.run_arrays(prepared['t_year'],prepared['lat_deg'],prepared['lon_deg'],prepared['m'],d=1.6,w=1.,q=.5,backend='kd')
    labels=cat.classify_case(prepared,result,cut) if cut is not None else None
    fields={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
    if labels is not None:fields.update({k:v for k,v in labels.items() if isinstance(v,np.ndarray)})
    np.savez_compressed(dest/'arrays.npz',**fields)
    meta=dict(status='computed' if labels is not None else 'not_estimable',events=len(prepared['ids']),transported_C_cut=cut,refit_performed=False,kernel_metadata=result['metadata'],arrays_sha256=cat.sha(dest/'arrays.npz'))
    cat.dump(dest/'metadata.json',meta);return dict(prepared=prepared,result=result,labels=labels,metadata=meta)
def paired_metrics(cases,pairs,restricted=False):
    labels={s:(c['labels'] if restricted else c['labels'].get('native')) for s,c in cases.items()}
    if any(z is None for z in labels.values()):return dict(status='not_estimable',reason='source_classification_not_estimable')
    idx={s:{rid:i for i,rid in enumerate(c['prepared']['ids'])} for s,c in cases.items()}
    pairs=[(a,b) for a,b in pairs if a in idx['ssn'] and b in idx['usgs']]
    si=np.array([idx['ssn'][a] for a,b in pairs],dtype=int);ui=np.array([idx['usgs'][b] for a,b in pairs],dtype=int)
    years=np.array([cases['ssn']['prepared']['source_rows'][i]['time_utc'][:4] for i in si]);a,b=labels['ssn'],labels['usgs']
    return dict(status='computed',period_rule='paired period by SSN observed UTC, as main analysis',periods={name:cat.metric(a['roles'][si[m]],b['roles'][ui[m]],a['component_root_index'][si[m]],b['component_root_index'][ui[m]]) for name,m in [('full',np.ones(len(si),dtype=bool)),('evaluation',years>='2021')]})
def source_changes(full,restricted):
    if restricted['labels'] is None or 'native' not in full['labels']:return dict(status='not_estimable')
    a,b=full['labels']['native'],restricted['labels'];fi={rid:i for i,rid in enumerate(full['prepared']['ids'])};ids=restricted['prepared']['ids']
    ii=np.array([fi[rid] for rid in ids],dtype=int);jj=np.arange(len(ids));years=np.array([r['time_utc'][:4] for r in restricted['prepared']['source_rows']])
    parent_full=full['result']['parent_index'];parent_new=restricted['result']['parent_index'];inside=set(ids)
    oldp=[None if parent_full[i]<0 else full['prepared']['ids'][int(parent_full[i])] for i in ii];newp=[None if parent_new[i]<0 else ids[int(parent_new[i])] for i in jj]
    return dict(status='computed',periods={name:dict(n=int(m.sum()),parent_changed=sum(oldp[i]!=newp[i] for i in np.flatnonzero(m)),full_context_parent_outside_mask=sum(oldp[i] is not None and oldp[i] not in inside for i in np.flatnonzero(m)),roles_and_partitions=cat.metric(a['roles'][ii[m]],b['roles'][jj[m]],a['component_root_index'][ii[m]],b['component_root_index'][jj[m]])) for name,m in [('full',np.ones(len(ids),dtype=bool)),('evaluation',years>='2021')]})
def run(target,raw,cases,pairs):
    folder=target/'observed_support';folder.mkdir();protocol=cat.readj(cat.Path(__file__).parent/'SUPPORT_PROTOCOL.json')
    pair_lookup={s:{p[pos]:p[1-pos] for p in pairs} for pos,s in enumerate(['ssn','usgs'])}
    lookup={s:{r['record_id']:r for r in rr} for s,rr in raw.items()}
    summaries=[]
    for resolution in protocol['resolutions_degrees']:
        dest=folder/f'grid_{str(resolution).replace(".","p")}';dest.mkdir()
        keys,counts,common=build_mask(raw,resolution)
        cat.dump(dest/'OBSERVED_SUPPORT.geojson',dict(type='FeatureCollection',name='Union of nonoverlapping cells with observed development support in both catalogues',properties=dict(resolution_degrees=resolution,development_period='2016-2020',magnitude_support_floor=3.5,not_network_or_completeness_coverage=True,query_clip_lon_lat=[[-118,12],[-86,33]],membership='half-open; query maximum coordinates assigned to final interior cell'),features=[cell_feature(k,resolution,counts) for k in sorted(common)]))
        membership={s:{rid for rid,key in kk.items() if key in common} for s,kk in keys.items()}
        maskrows={s:[r for r in rr if r['record_id'] in membership[s]] for s,rr in raw.items()}
        all_members=[];statecounts=Counter();profile=[]
        for s,rr in raw.items():
            other='usgs' if s=='ssn' else 'ssn'
            for r in rr:
                rid=r['record_id'];in_mask=rid in membership[s];ix,iy=keys[s][rid]
                all_members.append(dict(source=s,record_id=rid,time_utc=r['time_utc'],reported_magnitude=r['magnitude'],ix=ix,iy=iy,in_observed_support=in_mask))
                if not in_mask or Decimal(r['magnitude'])<Decimal('4.5'):continue
                counterpart=pair_lookup[s].get(rid)
                state='no_C_assignment' if counterpart is None else ('inside_' if counterpart in membership[other] else 'outside_')+('above_M4_5' if Decimal(lookup[other][counterpart]['magnitude'])>=Decimal('4.5') else 'below_M4_5')
                statecounts[s,'full',state]+=1
                if r['time_utc']>='2021-01-01':statecounts[s,'evaluation',state]+=1
            for period in ['full','evaluation']:
                selected=[r for r in maskrows[s] if Decimal(r['magnitude'])>=Decimal('4.5') and (period=='full' or r['time_utc']>='2021-01-01')]
                profile.append(dict(source=s,period=period,inside_selected_M4_5=len(selected),candidate_states={state:n for (src,p,state),n in statecounts.items() if src==s and p==period}))
        cat.writecsv(dest/'ROW_MEMBERSHIP.csv',all_members)
        retained=sorted((a,b) for a,b in pairs if a in membership['ssn'] and b in membership['usgs'] and Decimal(lookup['ssn'][a]['magnitude'])>=Decimal('4.5') and Decimal(lookup['usgs'][b]['magnitude'])>=Decimal('4.5'))
        cat.writecsv(dest/'FIXED_C_CANDIDATES_INSIDE_MASK.csv',[dict(ssn_record_id=a,usgs_record_id=b) for a,b in retained])
        projected=paired_metrics(cases,retained)
        restricted={s:restriction(dest,s,maskrows[s],cases[s]['fit'].get('threshold_log10')) for s in raw}
        comparison=paired_metrics(restricted,retained,restricted=True)
        summary=dict(resolution_degrees=resolution,development_supported_cells=len(common),source_development_observed_cells={s:len(c) for s,c in counts.items()},source_profile=profile,
            candidate_pairs_both_inside_above_cut=len(retained),project_full_C=projected,recalculate_only_supported_cells_transport_C_cut=comparison,
            same_source_context_changes={s:source_changes(cases[s],restricted[s]) for s in raw},
            limits='Observed development support only, not instrumental coverage/completeness or physical event identity. Fixed post-review spatial conditioning; restriction may truncate context; no favourable resolution selection.')
        cat.dump(dest/'RESULTS.json',summary);summaries.append(summary)
    cat.dump(folder/'RESULTS.json',summaries)
    return summaries
