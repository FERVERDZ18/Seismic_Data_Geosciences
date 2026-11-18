"""Protocol2 branching-process controls with explicit latent parentage; no detectors."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parent
PILOT = BASE.parent
sys.path[0:0] = [str(PILOT / 'comparators/nearest_neighbor/_deps'), str(PILOT / 'comparators/carluccio/_deps')]
import numpy as np
import pyproj

PROTOCOL_SHA = '9be299b26162fafba6d62c58c6c93a87ae2f30b2d0ec372acdfee5f1b0a487b8'
M0, MMAX, B, ALPHA, NU, C, THETA = 3.5, 6.5, 1., .5, .6, .001, .2
EXPECTED_PRODUCTIVITY_FACTOR = B/(B-ALPHA)*(1-10**(-(B-ALPHA)*(MMAX-M0)))/(1-10**(-B*(MMAX-M0)))
K = NU/EXPECTED_PRODUCTIVITY_FACTOR
ANCHOR = datetime(2001, 1, 1, tzinfo=timezone.utc)
TRANSFORMER = pyproj.Transformer.from_crs('+proj=aeqd +lat_0=17 +lon_0=-99 +datum=WGS84 +units=m +no_defs', 'EPSG:4326', always_xy=True)
EVENT_FIELDS = ['record_id','source','event_id','time_utc','latitude','longitude','depth_km','magnitude','magnitude_type','source_file','source_record','package_row','x_km','y_km','t_days','is_eval']
TRUTH_FIELDS = ['record_id','direct_parent_id','root_id','generation','is_immigrant','t_days','is_eval','retained_m4p1','latent_creation_index']


def rng(seed, block, stream):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, block, stream])))


def gr(generator, count):
    u = generator.random(count)
    return M0-np.log1p(-u*(-math.expm1(-B*math.log(10)*(MMAX-M0))))/(B*math.log(10))


def background(seed):
    rt, rs, rm = rng(seed,100,1), rng(seed,100,2), rng(seed,100,3)
    n = int(rt.poisson(1200))
    times = np.sort(rt.uniform(-365,365,n))
    xy = rs.normal(0,15,(n,2))
    xy[:,0] += np.where(rs.random(n)<.5,-40.,40.)
    return [{'t':float(t), 'x':float(x), 'y':float(y), 'm':float(m), 'parent':None, 'root':i, 'generation':0}
            for i,(t,(x,y),m) in enumerate(zip(times,xy,gr(rm,n)))]


def generate(seed, scenario):
    events = background(seed)
    if scenario == 'n1':
        for event in events:
            year_start = -365. if event['t']<0 else 0.
            u = (event['t']-year_start)/365
            warped = 2*u if u<.25 else .5+(u-.25)/1.5
            event['t'] = year_start + 365*warped
    elif scenario == 'etas':
        rc, rt, rm, rs = (rng(seed,200,index) for index in range(1,5))
        i = 0
        while i<len(events):
            parent = events[i]
            if parent['generation']>=100:
                raise RuntimeError('Generation guard100 reached; no silent truncation or re-seeding')
            limit = 365-parent['t']
            cdf = -math.expm1(THETA*(math.log(C)-math.log(C+limit)))
            n = int(rc.poisson(K*10**(ALPHA*(parent['m']-M0))*cdf))
            if len(events)+n>20000:
                raise RuntimeError('Count guard20000 reached; no silent truncation or re-seeding')
            delays = C*np.expm1(-np.log1p(-rt.random(n)*cdf)/THETA)
            marks, offsets = gr(rm,n), rs.normal(0,5,(n,2))
            for delay, magnitude, (dx,dy) in zip(delays,marks,offsets):
                events.append({'t':parent['t']+float(delay), 'x':parent['x']+float(dx), 'y':parent['y']+float(dy),
                    'm':float(magnitude), 'parent':i, 'root':parent['root'], 'generation':parent['generation']+1})
            i += 1
    elif scenario != 'n0':
        raise ValueError('Unknown predeclared scenario')
    for i,event in enumerate(events):
        assert -365<=event['t']<365 and M0<=event['m']<=MMAX
        if event['parent'] is not None:
            parent = events[event['parent']]
            assert parent['t']<event['t'] and event['generation']==parent['generation']+1
            assert event['root']==parent['root'] and events[event['root']]['parent'] is None
        else:
            assert event['root']==i and event['generation']==0
    return events


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_case(seed, scenario, split):
    target = BASE/split/f'{scenario}_{seed}'
    if (target/'catalogue.json').exists():
        raise ValueError('Do not overwrite existing synthetic evidence: '+str(target))
    target.mkdir(parents=True,exist_ok=True)
    events = generate(seed,scenario)
    uids = ['syn-'+hashlib.sha256(f'{scenario}:{seed}:{i}'.encode()).hexdigest()[:24] for i in range(len(events))]
    lons,lats = TRANSFORMER.transform([event['x']*1000 for event in events],[event['y']*1000 for event in events])
    order = sorted(range(len(events)),key=lambda i:(events[i]['t'],uids[i]))
    event_rows, truth_rows = [], []
    for row_index,i in enumerate(order):
        event=events[i]
        stamp=(ANCHOR+timedelta(days=event['t'])).isoformat(timespec='microseconds').replace('+00:00','Z')
        event_rows.append(dict(zip(EVENT_FIELDS,[uids[i],f'synthetic_{scenario}',uids[i],stamp,float(lats[i]),float(lons[i]),10.,event['m'],'synthetic_GR',f'{scenario}_{seed}',row_index,row_index,event['x'],event['y'],event['t'],int(event['t']>=0)])))
        truth_rows.append(dict(zip(TRUTH_FIELDS,[uids[i],'' if event['parent'] is None else uids[event['parent']],uids[event['root']],event['generation'],int(event['parent'] is None),event['t'],int(event['t']>=0),int(event['m']>=4.1),i])))
    for name,fields,rows in [('events.csv',EVENT_FIELDS,event_rows),('events_m4p1.csv',EVENT_FIELDS,[row for row in event_rows if row['magnitude']>=4.1]),('truth.csv',TRUTH_FIELDS,truth_rows)]:
        with (target/name).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    assert len(set(uids))==len(events)
    assert not ({'direct_parent_id','root_id','generation','latent_creation_index'}&set(EVENT_FIELDS))
    counts={'total':len(events),'burn':sum(event['t']<0 for event in events),'evaluation':sum(event['t']>=0 for event in events),
        'immigrants':sum(event['parent'] is None for event in events),'evaluation_children':sum(event['t']>=0 and event['parent'] is not None for event in events),
        'observed_m4p1_total':sum(event['m']>=4.1 for event in events),'observed_m4p1_evaluation':sum(event['t']>=0 and event['m']>=4.1 for event in events),
        'maximum_generation':max(event['generation'] for event in events),
        'evaluation_child_with_parent_before_evaluation':sum(event['t']>=0 and event['parent'] is not None and events[event['parent']]['t']<0 for event in events)}
    metadata={'schema':'seismic-synthetic-parentage-control/1','synthetic':True,'scenario':scenario,'seed':seed,'split':split,
        'protocol_stage2_sha256':PROTOCOL_SHA,'generator_sha256':hash_file(Path(__file__)),
        'parameters':{'mu_per_year':600,'days_per_year':365,'start':-365,'evaluation_start':0,'end_exclusive':365,'M0':M0,'Mmax':MMAX,'b':B,'alpha':ALPHA,'branching_ratio_infinite':NU,'K':K,'productivity_expectation':EXPECTED_PRODUCTIVITY_FACTOR,'c_days':C,'theta':THETA,'background_centers_km':[[-40,0],[40,0]],'background_sd_km':15,'offspring_sd_km':5,'synthetic_depth_km':10},
        'random_streams':{'engine':'PCG64','seed_sequence':'[seed,block,stream]','background_block':100,'background_streams':{'times':1,'space':2,'magnitudes':3},'offspring_block':200,'offspring_streams':{'counts':1,'delays':2,'magnitudes':3,'offsets':4},'paired_background_across_scenarios':True},
        'versions':{'numpy':np.__version__,'pyproj':pyproj.__version__,'python':sys.version},'counts':counts,
        'files':{name:{'sha256':hash_file(target/name),'bytes':(target/name).stat().st_size} for name in ('events.csv','events_m4p1.csv','truth.csv')},
        'limits':['Own branching generator, not native bruces ETAS or fitted empirical seismicity.','Finite burn is not proof of Hawkes stationarity.','Truth kept separate from detector inputs.','N0/N1 share immigrant rate600/year, not ideal ETAS total rate1500/year.','Observation stress is fixed M>=4.1, not a fitted detection model.']}
    (target/'catalogue.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return {'case_id':f'{scenario}_{seed}','path':target.relative_to(PILOT).as_posix(),'metadata_sha256':hash_file(target/'catalogue.json'),**counts}


def main():
    assert hash_file(PILOT/'PROTOCOL_STAGE_2.md')==PROTOCOL_SHA
    # An independent numerical quadrature verifies the analytic truncated-GR normalization.
    grid=np.linspace(M0,MMAX,100001)
    density=B*math.log(10)*np.exp(-B*math.log(10)*(grid-M0))/(1-10**(-B*(MMAX-M0)))
    assert abs(float(np.trapezoid(density,grid))-1)<1e-8
    assert abs(float(np.trapezoid(density*K*10**(ALPHA*(grid-M0)),grid))-NU)<1e-8
    started=time.perf_counter()
    cases=[write_case(20261000,'etas','training')]
    for seed in range(20261120,20261130):
        for scenario in ('etas','n0','n1'):
            cases.append(write_case(seed,scenario,'test'))
    manifest={'schema':'seismic-synthetic-control-manifest/1','status':'PASS','synthetic':True,'protocol_stage2_sha256':PROTOCOL_SHA,
        'protocol_synthetic_sha256':hash_file(PILOT/'protocol_synthetic.md'),'generator_sha256':hash_file(Path(__file__)),
        'training_seed':20261000,'test_seeds':list(range(20261120,20261130)),'K':K,'analytic_branching_ratio':NU,
        'normalization_quadrature_passed':True,'parent_root_horizon_checks_passed':True,'detectors_executed_by_generator':False,
        'elapsed_seconds':time.perf_counter()-started,'cases':cases}
    (BASE/'SYNTHETIC_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','cases':len(cases),'K':K,'seconds':manifest['elapsed_seconds'],'total_rows':sum(case['total'] for case in cases),'training':cases[0],'manifest':str(BASE/'SYNTHETIC_MANIFEST.json')},indent=2))


if __name__=='__main__':
    main()
