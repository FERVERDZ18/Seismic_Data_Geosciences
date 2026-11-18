"""Explicit GK window baseline, continuous UTC, epicentral great-circle km.

Gardner & Knopoff (1974), window parameterization documented by HMTK/CORSSA.
Magnitude-priority allocation; foreshock fraction .5; deterministic ties.
This is our implementation, not an execution of the HMTK day-only routine.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.spatial import cKDTree

R = 6371.0088
DISTANCE_EPSILON_KM = 1e-9

def great_circle(lat1,lon1,lat2,lon2):
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp,dl=p2-p1,math.radians((lon2-lon1+180)%360-180)
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R*2*math.asin(math.sqrt(min(1.0,max(0.0,h))))

def windows(m):
    mag = np.asarray(m)
    distance = 10.0**(.1238*mag+.983)
    days = np.where(mag>=6.5,10.0**(.032*mag+2.7389),10.0**(.5409*mag-.547))
    return distance,days

def unit_vectors(lat,lon):
    p,l = np.deg2rad(lat),np.deg2rad(lon)
    return np.column_stack([np.cos(p)*np.cos(l),np.cos(p)*np.sin(l),np.sin(p)])

def classify(t_days,lat,lon,mag,foreshock_fraction=.5,indexed=True):
    t,lat,lon,mag = [np.asarray(v,dtype=float) for v in [t_days,lat,lon,mag]]
    n = len(t)
    if not all(len(v)==n for v in [lat,lon,mag]):
        raise ValueError('Unequal arrays')
    order = np.lexsort((np.arange(n),t,-mag))
    xyz = unit_vectors(lat,lon)
    tree = cKDTree(xyz) if indexed else None
    dr,dt = windows(mag)
    group = np.zeros(n,dtype=np.int64)
    flag = np.zeros(n,dtype=np.int64)
    roots = []
    for i in order:
        if group[i]:
            continue
        if indexed:
            radius = 2*np.sin(min(np.pi,(dr[i]+DISTANCE_EPSILON_KM+1e-7)/R)/2)
            # Conservative candidates only; the shared final predicate decides.
            candidates = np.asarray(tree.query_ball_point(xyz[i],np.nextafter(radius,np.inf)),dtype=np.int64)
        else:
            candidates = np.arange(n,dtype=np.int64)
        candidates = candidates[(group[candidates]==0)&(t[candidates]-t[i]>=-foreshock_fraction*dt[i])&(t[candidates]-t[i]<=dt[i])]
        keep=[]
        for j in candidates:
            if great_circle(lat[i],lon[i],lat[j],lon[j])<=dr[i]+DISTANCE_EPSILON_KM:
                keep.append(j)
        candidates=np.asarray(keep,dtype=np.int64)
        if len(candidates)>1:
            group[candidates]=len(roots)+1
            flag[candidates]=np.where(t[candidates]<t[i],-1,1)
            flag[i]=0
            roots.append(int(i))
    roles=np.full(n,'isolated',dtype='<U10')
    roles[group>0]='associated'
    roles[np.asarray(roots,dtype=np.int64)]='main'
    return {'group':group,'native_flag':flag,'roles':roles,'root_indices':np.asarray(roots,dtype=np.int64),
            'window_km':dr,'window_days':dt}

def verify():
    rng=np.random.default_rng(20261115)
    records=0
    for n in [2,30,250,1000]:
        t=np.sort(rng.uniform(0,365,n))
        lat=rng.uniform(14,33,n)
        lon=rng.uniform(-118,-86,n)
        mag=rng.uniform(3.5,7,n)
        a=classify(t,lat,lon,mag)
        b=classify(t,lat,lon,mag,indexed=False)
        for key in ['group','native_flag','roles','root_indices']:
            assert np.array_equal(a[key],b[key]),key
        records+=n
    # Foreshock, aftershock, equal magnitude, isolated event, same instant.
    a=classify([0,1,2,3,1000],[17]*5,[-99,-99,-99,-99,-90],[4,6,4,6,4])
    b=classify([0,1,2,3,1000],[17]*5,[-99,-99,-99,-99,-90],[4,6,4,6,4],indexed=False)
    assert np.array_equal(a['native_flag'],b['native_flag'])
    # Explicit distance/time boundaries, antimeridian, poles and equal instants.
    radius,days=windows(np.array([6.]))
    delta=radius[0]/R*180/math.pi
    controls=[]
    for extra,expected in [(-1e-6,True),(0,True),(5e-10,True),(2e-9,False)]:
        controls.append(([0,1],[0,0],[0,delta+extra/R*180/math.pi],[6,4],expected,'distance_'+str(extra)))
    for delta_t,expected in [(days[0],True),(days[0]+1e-8,False),(-.5*days[0],True),(-.5*days[0]-1e-8,False),(0,True)]:
        controls.append(([0,delta_t],[0,0],[0,.01],[6,4],expected,'time_'+str(delta_t)))
    controls.extend([([0,1],[0,0],[179.99,-179.99],[6,4],True,'antimeridian'),([0,1],[89.99,89.99],[0,179],[6,4],True,'north_pole'),([0,1],[-89.99,-89.99],[0,-179],[6,4],True,'south_pole')])
    for t,la,lo,m,expected,label in controls:
        for indexed in [False,True]:
            got=classify(t,la,lo,m,indexed=indexed)
            assert bool(got['group'][0])==expected,(label,indexed,got['group'])
    return {'indexed_vs_all_candidates_shared_haversine_predicate':True,'random_records':records,'edge_case_records':5,'boundary_controls':len(controls),
        'geometry':'great-circle epicentral, R=6371.0088km','foreshock_fraction':.5,
        'distance_epsilon_km':DISTANCE_EPSILON_KM,'prefilter_expansion_km':1e-7,
        'ties':'descending reported magnitude; ascending UTC; ascending input index (stable record ID at equal UTC)',
        'time':'native UTC continuous days; no truncation to calendar dates',
        'not_unmodified_HMTK_execution':True}

if __name__=='__main__':
    import json
    print(json.dumps(verify(),indent=2))
