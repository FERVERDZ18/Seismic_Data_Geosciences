"""New magnitude-weighted spherical nearest-parent contract, isolated from legacy.

Algorithmic definitions follow bp.m/latlonkm.m (author distribution, 2013):
R=6367.3 km; linear dt[s]*r[m]**d*10**(-w*M). This is a clean Python
implementation, not a modified/copy of the author's GPL MATLAB source.
Version2 additionally shares the explicitly ordered small-angle cosine polynomial with JS.
The clamp, stable ordering and cosine primitive are documented numerical adaptations.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, os, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
LEGACY=ROOT/'outputs/sequence_pilot_2026-11-15/comparators/nearest_neighbor'
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'numba_gc_v2_cache'))
os.environ.setdefault('MPLCONFIGDIR',str(HERE/'matplotlib_cache'))
sys.dont_write_bytecode=True
sys.path.insert(0,str(LEGACY))
from bruces_reference import np, source_versions
from numba import njit,prange,set_num_threads,get_num_threads
from scipy.spatial import cKDTree
YEAR_SECONDS=31557600.0
RADIUS_KM=6367.3
EPOCH_UTC_US=1451606400000000  # 2016-01-01T00:00:00Z, common to every cohort
CHORD_GUARD=2e-7  # unit sphere, approx 1.27 m arc: conservative acos roundoff envelope
LOG_GUARD=1e-10  # traversal only, never alters candidate/parent comparisons


def utc_microseconds(value):
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Explicit UTC offset required')
    delta=dt.astimezone(timezone.utc)-datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1000000+delta.microseconds


def prepare_rows(rows):
    rows=sorted(rows,key=lambda r:(utc_microseconds(r['time_utc']),r['record_id'].encode('utf-8')))
    ids=[r['record_id'] for r in rows]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate record IDs; source namespace required')
    us=np.asarray([utc_microseconds(r['time_utc']) for r in rows],dtype=np.int64)
    # Feed bp the same epoch years, then reproduce its multiply-before-subtract.
    observed_seconds=(us-EPOCH_UTC_US).astype(np.float64)/1000000.0
    years=observed_seconds/YEAR_SECONDS
    lat=np.asarray([float(r['latitude']) for r in rows]);lon=np.asarray([float(r['longitude']) for r in rows])
    mag=np.asarray([float(r['magnitude']) for r in rows])
    return dict(ids=ids,source_rows=rows,utc_microseconds=us,t_seconds_observed=observed_seconds,t_year=years,
        lat_deg=lat,lon_deg=lon,m=mag,
        ids_sha256=hashlib.sha256(('\n'.join(ids)+'\n').encode('utf-8')).hexdigest(),
        time_policy='(UTCus-2016epoch)/1e6/31557600 years; bp multiply before subtraction',
        order_policy='Observed UTC integer microseconds, then original ID UTF-8 bytes')


def geometry(lat,lon):
    a=lat*np.pi/180.;b=lon*np.pi/180.
    sinlat=np.sin(a);coslat=np.cos(a)
    xyz=np.column_stack((coslat*np.cos(b),coslat*np.sin(b),sinlat))
    return sinlat,coslat,b,xyz


def build_tree(xyz,kind='kd',leafsize=16,max_depth=40):
    children=[];up=[];starts=[];stops=[];points=[];boxes=[];depths=[]
    point_leaf=np.empty(len(xyz),dtype=np.int64)
    def make(ids,parent,depth):
        k=len(children);children.append([-1]*8);up.append(parent);starts.append(-1);stops.append(-1)
        boxes.append(np.ravel(np.column_stack((xyz[ids].min(axis=0),xyz[ids].max(axis=0)))).tolist());depths.append(depth)
        return k
    def leaf(k,ids):
        starts[k]=len(points);points.extend(ids.tolist());stops[k]=len(points);point_leaf[ids]=k
    if kind=='kd':
        tree=cKDTree(xyz,leafsize=leafsize,balanced_tree=True,compact_nodes=True)
        def walk(node,parent,depth):
            ids=node.indices;k=make(ids,parent,depth)
            if node.split_dim<0:leaf(k,ids)
            else:children[k][0]=walk(node.lesser,k,depth+1);children[k][1]=walk(node.greater,k,depth+1)
            return k
        walk(tree.tree,-1,0)
    elif kind=='octree':
        def walk(ids,parent,depth,lo,hi):
            k=make(ids,parent,depth);mid=lo+(hi-lo)*.5
            spread=xyz[ids].max(axis=0)-xyz[ids].min(axis=0)
            if len(ids)<=leafsize or depth>=max_depth or not np.any(spread) or np.all((mid==lo)|(mid==hi)):
                leaf(k,ids);return k
            group=np.sum((xyz[ids]>=mid).astype(np.int8)*np.asarray([1,2,4],dtype=np.int8),axis=1)
            for q in range(8):
                chosen=ids[group==q]
                if not len(chosen):continue
                bits=np.asarray([bool(q&1),bool(q&2),bool(q&4)])
                children[k][q]=walk(chosen,k,depth+1,np.where(bits,mid,lo),np.where(bits,hi,mid))
            return k
        walk(np.arange(len(xyz),dtype=np.int64),-1,0,xyz.min(axis=0),xyz.max(axis=0))
    else:raise ValueError(kind)
    leafmask=np.asarray(starts)>=0;sizes=np.asarray(stops)-np.asarray(starts)
    arrays=tuple(np.asarray(a,dtype=np.int64) for a in (children,up,starts,stops,points,point_leaf))+(np.asarray(boxes),)
    return arrays,dict(kind=kind,nodes=len(children),leaves=int(leafmask.sum()),actual_max_depth=max(depths),
        actual_max_leaf_size=int(sizes[leafmask].max()),leafsize=leafsize,max_depth_limit=max_depth if kind=='octree' else None)


@njit(cache=True,fastmath=False)
def cosine_difference(x):
    if abs(x)<=0.02:
        y=x*x
        return 1.-y*(0.5-y*(1./24.-y*(1./720.-y*(1./40320.-y/3628800.))))
    return np.cos(x)


@njit(cache=True,fastmath=False)
def radius_km(si,ci,li,sj,cj,lj):
    dot=si*sj+ci*cj*cosine_difference(li-lj)
    # Stable real-valued adaptation; the untouched MATLAB reference has no clamp.
    dot=min(1.,max(-1.,dot))
    return RADIUS_KM*np.arccos(dot)


@njit(cache=True)
def one_candidate(t,s,c,l,m,i,j,d,w):
    dt=t[i]-t[j]
    if dt<=0:return np.inf,np.nan,np.nan
    r=radius_km(s[i],c[i],l[i],s[j],c[j],l[j])
    n=dt*(r*1000.)**d*10.**(-w*m[j])
    return n,dt/YEAR_SECONDS,r


@njit(cache=True,parallel=True)
def exhaustive(t,s,c,l,m,d,w):
    n=len(t);eta=np.full(n,np.inf);parent=np.full(n,-1,dtype=np.int64)
    dt=np.full(n,np.nan);radius=np.full(n,np.nan)
    for i in prange(n):
        best=np.inf;p=-1;bt=np.nan;br=np.nan
        for j in range(i):
            value,tv,rv=one_candidate(t,s,c,l,m,i,j,d,w)
            if value<best:best=value;p=j;bt=tv;br=rv
        eta[i]=best;parent[i]=p;dt[i]=bt;radius[i]=br
    return eta,parent,dt,radius


@njit(cache=True)
def bound(k,ti,xyz_i,latest,maximum,boxes,d,w):
    if not np.isfinite(latest[k]):return np.inf
    chord2=0.
    for ax in range(3):
        delta=max(boxes[k,2*ax]-xyz_i[ax],0.,xyz_i[ax]-boxes[k,2*ax+1])
        chord2+=delta*delta
    chord=max(0.,np.sqrt(chord2)-CHORD_GUARD)
    if chord==0:return -np.inf
    arc=2.*RADIUS_KM*1000.*np.arcsin(min(1.,chord*.5))
    return np.log10(ti-latest[k])+d*np.log10(arc)-w*maximum[k]


@njit(cache=True)
def indexed(t,s,c,l,m,xyz,d,w,children,up,starts,stops,points,pointleaf,boxes):
    n=len(t);nodes=len(up);latest=np.full(nodes,-np.inf);maximum=np.full(nodes,-np.inf)
    eta=np.full(n,np.inf);parent=np.full(n,-1,dtype=np.int64);dt=np.full(n,np.nan);radius=np.full(n,np.nan)
    # 0 evaluated pairs,1 visited nodes,2 bound tests,3 prune on pop,4 prune before push,5 leaf slots,6 activations
    counts=np.zeros(7,dtype=np.int64);stack=np.empty(nodes,dtype=np.int64);stackbound=np.empty(nodes)
    firstinactive=0
    for i in range(n):
        while firstinactive<n and t[firstinactive]<t[i]:
            j=firstinactive;k=pointleaf[j]
            while k>=0:
                latest[k]=max(latest[k],t[j]);maximum[k]=max(maximum[k],m[j]);k=up[k]
            firstinactive+=1;counts[6]+=1
        best=np.inf;p=-1;bt=np.nan;br=np.nan;sp=1;stack[0]=0
        stackbound[0]=bound(0,t[i],xyz[i],latest,maximum,boxes,d,w);counts[2]+=1
        while sp:
            sp-=1;k=stack[sp];lower=stackbound[sp];counts[1]+=1
            limit=np.log10(best) if best>0 else -np.inf
            if lower>limit+LOG_GUARD:counts[3]+=1;continue
            if starts[k]>=0:
                for off in range(starts[k],stops[k]):
                    j=points[off];counts[5]+=1
                    if t[j]>=t[i]:continue
                    counts[0]+=1;value,tv,rv=one_candidate(t,s,c,l,m,i,j,d,w)
                    if value<best or (value==best and (p<0 or j<p)):
                        best=value;p=j;bt=tv;br=rv
            else:
                chosen=np.empty(8,dtype=np.int64);lowerchosen=np.empty(8);nc=0
                for q in range(8):
                    child=children[k,q]
                    if child<0:continue
                    low=bound(child,t[i],xyz[i],latest,maximum,boxes,d,w);counts[2]+=1
                    if low>limit+LOG_GUARD:counts[4]+=1;continue
                    pos=nc
                    while pos>0 and low<lowerchosen[pos-1]:
                        chosen[pos]=chosen[pos-1];lowerchosen[pos]=lowerchosen[pos-1];pos-=1
                    chosen[pos]=child;lowerchosen[pos]=low;nc+=1
                for q in range(nc-1,-1,-1):
                    stack[sp]=chosen[q];stackbound[sp]=lowerchosen[q];sp+=1
        eta[i]=best;parent[i]=p;dt[i]=bt;radius[i]=br
    return eta,parent,dt,radius,counts


def run_arrays(t_year,lat_deg,lon_deg,m,d=1.6,w=1.,q=.5,backend='kd'):
    t_year=np.asarray(t_year,dtype=np.float64);lat=np.asarray(lat_deg,dtype=np.float64);lon=np.asarray(lon_deg,dtype=np.float64);m=np.asarray(m,dtype=np.float64)
    n=len(t_year)
    if n==0 or not all(len(a)==n for a in (lat,lon,m)):raise ValueError('Aligned nonempty inputs required')
    if not all(np.all(np.isfinite(a)) for a in (t_year,lat,lon,m)):raise ValueError('Finite inputs required')
    if d<=0 or w<0 or q<0 or q>1 or np.any(np.diff(t_year)<0) or np.any(abs(lat)>90) or np.any(abs(lon)>180):raise ValueError('Invalid domain')
    started=time.perf_counter();s,c,l,xyz=geometry(lat,lon);t=t_year*YEAR_SECONDS
    prepared_seconds=time.perf_counter()-started
    tree_seconds=0.;counters=None;tree_info=None
    if backend=='reference':
        started=time.perf_counter();eta,parent,dt,radius=exhaustive(t,s,c,l,m,float(d),float(w));core=time.perf_counter()-started
    else:
        started=time.perf_counter();arrays,tree_info=build_tree(xyz,kind=backend);tree_seconds=time.perf_counter()-started
        started=time.perf_counter();eta,parent,dt,radius,counters=indexed(t,s,c,l,m,xyz,float(d),float(w),*arrays);core=time.perf_counter()-started
    export_started=time.perf_counter()
    T=np.full(n,np.nan);R=np.full(n,np.nan);defined=parent>=0
    with np.errstate(divide='ignore',invalid='ignore'):
        T[defined]=np.log10(dt[defined])-q*w*m[parent[defined]]
        R[defined]=d*np.log10(radius[defined])-(1.-q)*w*m[parent[defined]]
        TN=np.full(n,np.nan);RN=np.full(n,np.nan)
        TN[defined]=dt[defined]*10.**(-q*w*m[parent[defined]])
        RN[defined]=radius[defined]**d*10.**(-(1.-q)*w*m[parent[defined]])
        logeta_sum=T+R
        logeta=np.log10(TN*RN)
    export_seconds=time.perf_counter()-export_started
    counter_names=('candidate_pairs','visited_nodes','bound_tests','pruned_on_pop','pruned_before_push','leaf_slots','activated_sources')
    return dict(parent_index=parent,eta_native_seconds_metres=eta,eta_log10=logeta,eta_log10_sum=logeta_sum,T_log10=T,R_log10=R,TN=TN,RN=RN,
        parent_dt_years=dt,parent_distance_km=radius,metadata=dict(n=n,d=d,w=w,q=q,radius_km=RADIUS_KM,
        backend=backend,threads=get_num_threads(),preparation_seconds=prepared_seconds,tree_seconds=tree_seconds,
        kernel_seconds=core,postprocess_seconds=export_seconds,total_seconds=prepared_seconds+tree_seconds+core+export_seconds,tree=tree_info,
        counters=dict(zip(counter_names,map(int,counters))) if counters is not None else None,
        zero_distance_retained=True,nonparent_logeta='NaN',distance='author acos with [-1,1] clamp and shared small-angle cosine v2',
        input_time='epoch years, author multiply before subtraction',chord_guard=CHORD_GUARD,log_prune_guard=LOG_GUARD))




