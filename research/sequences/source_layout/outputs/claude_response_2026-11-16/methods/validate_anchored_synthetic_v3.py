"""Additional simulated controls anchored only in observed training descriptors.

Not ETAS MLE, not observed earthquake families, not a model of physical Mexico.
All substantive parameters and test seeds are fixed in the accompanying protocol.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal,ROUND_HALF_UP
import csv
import json
import math
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
sys.path.insert(0,str(HERE))
from run_deterministic_study_v3 import np,calculate,make_labels,author_normalmix,mixture_diagnostics,comparison,partition_comparison,dump,sha,set_num_threads
from validate_synthetic_2013_v3 import child_scores,truth_arrays
sys.path.insert(0,str(PILOT))
from gardner_knopoff import classify
import pyproj

M0=4.5
YEAR=365.25
EPOCH=datetime(2021,1,1,tzinfo=timezone.utc)
START=-10*YEAR
STOP=5*YEAR
C=.001
THETA=.2
SPATIAL_BACKGROUND_SD=25.
SPATIAL_OFFSPRING_SD=5.
FORWARD=pyproj.Transformer.from_crs('EPSG:4326','+proj=aeqd +lat_0=23.5 +lon_0=-102 +datum=WGS84 +units=m +no_defs',always_xy=True)
INVERSE=pyproj.Transformer.from_crs('+proj=aeqd +lat_0=23.5 +lon_0=-102 +datum=WGS84 +units=m +no_defs','EPSG:4326',always_xy=True)


def anchor_parameters(source):
    p=PILOT/'inputs'/f'{source}.csv'
    with p.open(encoding='utf-8-sig',newline='') as f:
        rows=[r for r in csv.DictReader(f) if r['time_utc']<'2021-01-01' and Decimal(r['magnitude'])>=Decimal('4.5')]
    rounded=[float(Decimal(r['magnitude']).quantize(Decimal('.1'),rounding=ROUND_HALF_UP)) for r in rows]
    b=math.log10(math.e)/(float(np.mean(rounded))-(M0-.05))
    lats=np.array([float(r['latitude']) for r in rows]);lons=np.array([float(r['longitude']) for r in rows])
    x,y=FORWARD.transform(lons,lats)
    observed_days=(datetime(2021,1,1,tzinfo=timezone.utc)-datetime(2016,1,1,tzinfo=timezone.utc)).total_seconds()/86400.
    info=dict(source=source,input_sha256=sha(p),development='2016-2020',events=len(rows),
              duration_days=observed_days,total_rate_per_day=len(rows)/observed_days,
              total_rate_per_365p25_days=len(rows)/observed_days*YEAR,
              reported_b_bin0p1=b,reported_Mmax=max(float(r['magnitude']) for r in rows),
              magnitude_is_homogeneous_Mw=False,
              latitude_range=[float(lats.min()),float(lats.max())],longitude_range=[float(lons.min()),float(lons.max())],
              projected_x_range_km=[float(x.min()/1000.),float(x.max()/1000.)],
              projected_y_range_km=[float(y.min()/1000.),float(y.max()/1000.)],
              alpha_assumed=b/2,background_KDE_bandwidth_km_assumed=SPATIAL_BACKGROUND_SD,
              offspring_Gaussian_sd_km_assumed=SPATIAL_OFFSPRING_SD,c_days_assumed=C,theta_assumed=THETA,
              not_MLE_ETAS_fit=True)
    return info,np.column_stack((x/1000.,y/1000.))


def gr(generator,n,b,mmax):
    u=generator.random(n)
    return M0-np.log1p(-u*(1-10**(-b*(mmax-M0))))/(b*math.log(10.))


def simulate(info,points,seed,branching):
    source=info['source'];source_code=0 if source=='ssn' else 1
    def generator(stream):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed,source_code,int(branching*1000),840113,stream])))
    rt,rm,rs,rc,rd,ro=[generator(v) for v in range(6)]
    b,mmax,alpha=info['reported_b_bin0p1'],info['reported_Mmax'],info['alpha_assumed']
    span=mmax-M0
    expected=b/(b-alpha)*(1-10**(-(b-alpha)*span))/(1-10**(-b*span))
    productivity=branching/expected
    mu=info['total_rate_per_day']*(1-branching)
    n=int(rt.poisson(mu*(STOP-START)))
    t=np.sort(rt.uniform(START,STOP,n));magnitudes=gr(rm,n,b,mmax)
    xy=points[rs.integers(0,len(points),n)]+rs.normal(0,SPATIAL_BACKGROUND_SD,(n,2))
    events=[dict(t=float(ti),x=float(p[0]),y=float(p[1]),m=float(mi),parent=None,root=i,generation=0)
            for i,(ti,p,mi) in enumerate(zip(t,xy,magnitudes))]
    i=0
    while branching>0 and i<len(events):
        parent=events[i]
        if parent['generation']>=100:raise RuntimeError('Generation guard100; no truncation or reseeding')
        horizon=STOP-parent['t']
        cdf=-math.expm1(THETA*(math.log(C)-math.log(C+horizon)))
        count=int(rc.poisson(productivity*10**(alpha*(parent['m']-M0))*cdf))
        if len(events)+count>50000:raise RuntimeError('Event guard50000; no truncation or reseeding')
        delays=C*np.expm1(-np.log1p(-rd.random(count)*cdf)/THETA)
        child_mag=gr(rm,count,b,mmax);offsets=ro.normal(0,SPATIAL_OFFSPRING_SD,(count,2))
        for delay,magnitude,(dx,dy) in zip(delays,child_mag,offsets):
            events.append(dict(t=parent['t']+float(delay),x=parent['x']+float(dx),y=parent['y']+float(dy),
                               m=float(magnitude),parent=i,root=parent['root'],generation=parent['generation']+1))
        i+=1
    ids=[f'anchored-synthetic-{source}-{seed}-n{branching:.1f}-{i}' for i in range(len(events))]
    lon,lat=INVERSE.transform([e['x']*1000 for e in events],[e['y']*1000 for e in events])
    rows=[];truth={}
    for i,e in enumerate(events):
        stamp=(EPOCH+timedelta(days=e['t'])).isoformat(timespec='microseconds').replace('+00:00','Z')
        rows.append(dict(record_id=ids[i],source='synthetic_anchored_'+source,event_id=ids[i],time_utc=stamp,
                         latitude=str(float(lat[i])),longitude=str(float(lon[i])),magnitude=str(e['m']),magnitude_type='synthetic_GR'))
        truth[ids[i]]=dict(root_id=ids[e['root']],is_immigrant='1' if e['parent'] is None else '0',
                           is_eval='1' if e['t']>=0 else '0',generation=e['generation'],
                           direct_parent_id=None if e['parent'] is None else ids[e['parent']])
        if e['parent'] is not None:assert events[e['parent']]['t']<e['t']
    meta=dict(seed=seed,branching_ratio_ideal=branching,immigrant_rate_per_day=mu,productivity_K=productivity,
              expected_productivity_factor=expected,total_events=len(events),
              evaluated_events=sum(e['t']>=0 for e in events),
              evaluated_immigrants=sum(e['t']>=0 and e['parent'] is None for e in events),
              realized_evaluation_total_rate_per_365p25_days=sum(e['t']>=0 for e in events)/5.,
              maximum_generation=max(e['generation'] for e in events),
              finite_burn_not_stationarity_proof=True,spatial_cropping=False,simulation_parameters=info)
    return rows,truth,meta


def evaluate(prepared,result,truth,cut):
    group,role,child,mask=truth_arrays(prepared['source_rows'],truth)
    if cut is None:return None,None
    labels=make_labels(prepared,result,cut)
    item=dict(generated_child=child_scores(child[mask],labels['strong_link_mask'][mask]),
              roles_and_families=comparison(role[mask],labels['roles'][mask],group[mask],labels['component_root_index'][mask]),
              fraction_in_a_family=float(np.mean(labels['component_size'][mask]>1)),
              truth_immigrant_fraction=float(np.mean(~child[mask])),
              trivial_always_child=child_scores(child[mask],np.ones(int(mask.sum()),dtype=bool)),
              trivial_always_immigrant=child_scores(child[mask],np.zeros(int(mask.sum()),dtype=bool)),
              trivial_all_one_family=partition_comparison(group[mask],np.zeros(int(mask.sum()),dtype=int)),
              trivial_all_singletons=partition_comparison(group[mask],np.arange(int(mask.sum()))))
    return item,labels


def main():
    target=HERE/'anchored_synthetic_validation_v3'
    if target.exists():raise FileExistsError('Do not overwrite completed/failed synthetic evidence')
    target.mkdir();set_num_threads(1);started=time.perf_counter()
    params={s:anchor_parameters(s) for s in ['ssn','usgs']}
    # This descriptor receipt is written BEFORE any generation or evaluation.
    dump(target/'ANCHOR_PARAMETERS.json',dict(protocol_sha256=sha(HERE/'ANCHORED_SYNTHETIC_PROTOCOL.md'),
                                            anchors={s:v[0] for s,v in params.items()}))
    observed=json.loads((HERE/'calibration_v3.json').read_text(encoding='utf-8'))
    training=[];items=[];failures=[]
    for source,(info,points) in params.items():
        rows,truth,meta=simulate(info,points,2026111600,.6)
        prepared,result=calculate(rows,1.6,1.)
        trainmask=np.array([truth[rid]['is_eval']=='0' for rid in prepared['ids']])
        fitted=author_normalmix(result['eta_log10'][trainmask]);diag=mixture_diagnostics(fitted,result['eta_log10'][trainmask])
        training.append(dict(source=source,fit=fitted,diagnostics=diag,metadata=meta))
        trainpath=target/f'{source}_training';trainpath.mkdir()
        dump(trainpath/'rows.json',rows);dump(trainpath/'truth.json',truth);dump(trainpath/'metadata.json',training[-1])
        cuts={'observed_development':observed['cuts']['4.5'][source].get('threshold_log10'),
              'independent_synthetic_development':fitted.get('threshold_log10')}
        for seed in [2026111601,2026111602,2026111603]:
            for branching in [0.,.3,.6,.8]:
                name=f'{source}_seed{seed}_n{branching}'
                case=target/name;case.mkdir()
                try:rows,truth,meta=simulate(info,points,seed,branching)
                except RuntimeError as exc:
                    failure=dict(case=name,reason=str(exc),no_reseed=True);failures.append(failure);dump(case/'FAILURE.json',failure);continue
                prepared,result=calculate(rows,1.6,1.)
                group,role,child,evaluation=truth_arrays(prepared['source_rows'],truth)
                gk=classify(prepared['t_year']*365.25,prepared['lat_deg'],prepared['lon_deg'],prepared['m'])
                gk_role=np.array([{'isolated':0,'main':1,'associated':2}[str(v)] for v in gk['roles']],dtype=np.int8)
                gk_group=np.where(gk['group']>0,gk['group'],-np.arange(len(rows))-1)
                item=dict(case=name,source=source,seed=seed,branching=branching,metadata=meta,NN={},
                    GK=dict(generated_child=child_scores(child[evaluation],gk_role[evaluation]==2),
                            roles_and_families=comparison(role[evaluation],gk_role[evaluation],group[evaluation],gk_group[evaluation]),
                            fraction_in_a_family=float(np.mean(gk['group'][evaluation]>0))))
                arrays=dict(parent_index=result['parent_index'],eta_log10=result['eta_log10'],truth_group=group,truth_role=role,
                            true_generated_child=child,evaluated=evaluation,GK_group=gk_group,GK_role=gk_role)
                for cut_name,cut in cuts.items():
                    measures,labels=evaluate(prepared,result,truth,cut)
                    item['NN'][cut_name]=dict(threshold_log10=cut,metrics=measures)
                    if labels is not None:arrays[cut_name+'_group']=labels['component_root_index'];arrays[cut_name+'_role']=labels['roles']
                dump(case/'rows.json',prepared['source_rows']);dump(case/'truth.json',truth);dump(case/'ids.json',prepared['ids'])
                np.savez_compressed(case/'arrays.npz',**arrays)
                item.update(rows_sha256=sha(case/'rows.json'),truth_sha256=sha(case/'truth.json'),arrays_sha256=sha(case/'arrays.npz'))
                dump(case/'metrics.json',item);items.append(item)
        print(json.dumps(dict(source=source,training_fit_status=fitted['status'],completed=len([v for v in items if v['source']==source]))),flush=True)
    report=dict(schema='descriptor-anchored-synthetic-controls/1',synthetic=True,not_ETAS_MLE_fit=True,
                protocol_sha256=sha(HERE/'ANCHORED_SYNTHETIC_PROTOCOL.md'),parameters_sha256=sha(target/'ANCHOR_PARAMETERS.json'),
                script_sha256=sha(__file__),training=training,results=items,failures=failures,
                elapsed_seconds=time.perf_counter()-started,
                limits=['Only training rate, magnitude distribution and spatial footprint are observed anchors.',
                        'Productivity exponent, branching grid, kernels, KDE width and finite burn are assumed.',
                        'No fitted physical model or validation of Mexican earthquake parentage.',
                        'Three seeds per cell are a descriptive sensitivity grid, not independent population confidence.'])
    dump(target/'RESULTS.json',report)
    print(json.dumps(dict(completed=len(items),failures=len(failures),seconds=report['elapsed_seconds']),indent=2))


if __name__=='__main__':main()
