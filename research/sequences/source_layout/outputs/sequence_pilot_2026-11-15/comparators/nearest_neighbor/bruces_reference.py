"""Transparent adapter to executable bruces0.5.0 NND2020 random thinning.

Not the authors' MATLAB execution. No real-data work occurs on import or --toy.
Caller must freeze the scientific protocol before calling this on real cohorts.
Upstream source remains unchanged; random nulls and numerical sentinels are native.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'numba_cache'))
os.environ.setdefault('MPLCONFIGDIR',str(HERE/'matplotlib_cache'))
for dependency in [HERE.parent/'carluccio/_deps',HERE/'_deps']:
    if dependency.is_dir():sys.path.insert(0,str(dependency))

import numpy as np
import bruces
from bruces._helpers import set_seed
from pyproj import CRS,Transformer

NN=importlib.import_module('bruces.decluster.nearest_neighbor._nearest_neighbor')


@dataclass
class Prepared:
    catalog:object
    ids:list[str]
    source_rows:list[dict]
    geometry:dict


def _get(row,*names):
    for name in names:
        if name in row and row[name] not in ('',None):return row[name]
    raise ValueError('Missing field: '+repr(names))


def _utc(value):
    stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if stamp.tzinfo is None:raise ValueError('Explicit UTC offset required')
    return stamp.astimezone(timezone.utc).replace(tzinfo=None)


def prepare_rows(rows,center=(23.5,-102.0)):
    """Project unchanged lon/lat to fixed-center WGS84AEQD km, use public Catalog.

    Rows accept id/record_id/event_id, time_utc/time/origin_time, lat/latitude,
    lon/longitude, magnitude/mag. Raw IDs/types remain in source_rows.
    Public Catalog's native NumPy sorting is reproduced in the ID index map.
    """
    rows=list(rows)
    normalized=[(_utc(_get(r,'time_utc','time','origin_time')),
                 str(_get(r,'record_id','event_id','id')),r) for r in rows]
    normalized.sort(key=lambda r:(r[0],r[1]))
    times=np.asarray([r[0] for r in normalized],dtype=object)
    lat=np.asarray([float(_get(r[2],'latitude','lat')) for r in normalized])
    lon=np.asarray([float(_get(r[2],'longitude','lon')) for r in normalized])
    magnitudes=np.asarray([float(_get(r[2],'magnitude','mag')) for r in normalized])
    if not np.isfinite(lat).all() or not np.isfinite(lon).all() or not np.isfinite(magnitudes).all():raise ValueError('Nonfinite observed value')
    if not ((abs(lat)<=90).all() and (abs(lon)<=180).all()):raise ValueError('Coordinate outside domain')
    if len({r[1] for r in normalized})!=len(normalized):raise ValueError('Repeated row identifier')
    lat0,lon0=map(float,center)
    crs=CRS.from_proj4(f'+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs')
    transform=Transformer.from_crs('EPSG:4326',crs,always_xy=True)
    east,north=transform.transform(lon,lat)
    east=np.asarray(east)*.001;north=np.asarray(north)*.001
    if not np.isfinite(east).all() or not np.isfinite(north).all():raise ValueError('Projection failure')
    # use_depth=False means the zeros are a computational coordinate placeholder,
    # not an imputed observed depth; source depths remain untouched in source_rows.
    catalog=bruces.Catalog(times,eastings=east,northings=north,depths=np.zeros(len(times)),magnitudes=magnitudes)
    order=np.argsort(times) # same sorting call as unmodified Catalog.__init__
    assert np.array_equal(catalog.eastings,east[order]) and np.array_equal(catalog.northings,north[order])
    ids=[normalized[i][1] for i in order]
    metadata={'kind':'WGS84 azimuthal equidistant followed by native planar Euclidean km distances',
      'center_latitude':lat0,'center_longitude':lon0,'crs_wkt':crs.to_wkt(),
      'order':'Input normalized UTC+ID; native public Catalog NumPy sorting retained; exact output ID map stored.',
      'depth_used':False,'depth_zero_placeholder_is_observed':False,
      'geodesic_pairwise_distances_claimed':False}
    return Prepared(catalog,ids,[normalized[i][2] for i in order],metadata)


def fit_eta0(prepared,development_end_utc='2021-01-01T00:00:00Z',d=1.5):
    """Native deterministic FD histogram/two-Gaussian curve_fit, development only.

    Returned threshold is LOG10 eta0, not linear eta0. None is recorded failure;
    no silent fallback to the public decluster API's all-background skip path.
    """
    cutoff=_utc(development_end_utc)
    mask=np.asarray([t<cutoff for t in prepared.catalog.origin_times])
    subset=prepared.catalog[mask]
    if len(subset)<10:return {'status':'not_estimable','development_events':len(subset),'log10_eta0':None,'reason':'fewer_than10_events'}
    started=time.perf_counter()
    try:
        threshold=subset.fit_cutoff_threshold(d=d,w=0.0,use_depth=False)
        if threshold is not None and not np.isfinite(threshold):threshold=None
        status='estimated' if threshold is not None else 'not_estimable'
        reason=None if threshold is not None else 'native_unimodality_or_fit_failure'
    except (RuntimeError,ValueError,OverflowError,ZeroDivisionError) as error:
        threshold=None;status='not_estimable';reason=type(error).__name__+': '+str(error)
    return {'status':status,'log10_eta0':float(threshold) if threshold is not None else None,
      'development_events':len(subset),'development_end_exclusive_utc':development_end_utc,
      'd':d,'w':0.0,'use_depth':False,'seconds':time.perf_counter()-started,
      'fit':'Unmodified bruces.Catalog.fit_cutoff_threshold; Freedman-Diaconis histogram; deterministic two-Gaussian scipy.curve_fit; high-mean mode mu-2sigma.',
      'random_seed_required_for_fit':False,'reason':reason}


def _arrays(catalog):
    return (catalog.years,catalog.eastings,catalog.northings,catalog.depths,catalog.magnitudes)


def run_reference(prepared,log10_eta0,M=100,alpha0=0.0,seed=1729,draw_seeds=range(1730,1750),d=1.5):
    """Return native eta/kappa/logalpha, probabilities, and reused-normalization draws.

    This is the unmodified published Python implementation, with an adapter that
    exposes its intermediate arrays. Public API parity is checked separately on
    synthetic input. Real execution requires an agreed frozen caller protocol.
    """
    if log10_eta0 is None or not np.isfinite(log10_eta0):raise ValueError('A frozen estimable log10_eta0 is required')
    if M<1:raise ValueError('M must be positive')
    catalog=prepared.catalog;t,x,y,z,m=_arrays(catalog)
    set_seed(seed)
    eta=np.empty(len(t),dtype=np.float64)
    started=time.perf_counter()
    NN.proximity_catalog(t,x,y,z,m,t,x,y,z,d,0.0,False,eta)
    eta_seconds=time.perf_counter()-started
    background_pool_count=int(np.sum(eta>log10_eta0))
    if not background_pool_count:raise ValueError('Native background calibration pool is empty')
    started=time.perf_counter()
    kappa=NN.proximity_vector(t,x,y,z,m,eta,d,0.0,float(log10_eta0),int(M),False)
    logalpha=NN.normalize_proximity(eta,kappa)
    normalization_seconds=time.perf_counter()-started
    # Exact native public API decision expression and RNG stream after the100
    # normalizations. Additional draws reuse the SAME kappa/logalpha arrays.
    native_mask=logalpha+alpha0>np.log10(np.random.rand(len(t)))
    with np.errstate(under='ignore',over='ignore'):
        p=np.minimum(10.0**(logalpha+alpha0),1.0)
        sensitivity_p=np.minimum(10.0**(logalpha+1.5),1.0)
    masks={str(seed):native_mask}
    for draw_seed in draw_seeds:
        rng=np.random.RandomState(int(draw_seed))
        masks[str(draw_seed)]=logalpha+alpha0>np.log10(rng.rand(len(t)))
    from native_parent_kernel import parent_kernel
    parent_eta,parents,skipped_zero=parent_kernel(t,x,y,m,d)
    if not np.array_equal(parent_eta,eta):
        raise ValueError('Instrumented parent companion differs from native proximity values')
    undefined=parents<0
    return {'eta_log10':eta,'kappa_log10':kappa,'normalized_log10_alpha':logalpha,
      'background_probability':p,'background_probability_alpha1_5':sensitivity_p,'background_draw_masks':masks,
      'parents':parents,'skipped_zero_distance_parent_pairs':skipped_zero,'parent_undefined_mask':undefined,
      'metadata':{'implementation':'bruces0.5.0 random thinning, not author MATLAB execution',
        'd':d,'w':0.0,'use_depth':False,'M':M,'alpha0':alpha0,'alpha0_sensitivity':1.5,'seed':seed,
        'additional_draw_seeds':list(map(int,draw_seeds)),'background_pool_count':background_pool_count,
        'native_undefined_parent_count':int(undefined.sum()),'native_eta_sentinel':20.0,
        'parent_companion_native_proximity_bit_parity':True,'skipped_zero_distance_parent_pair_count':int(skipped_zero.sum()),
        'native_no_valid_kappa_normalized_logalpha':-20.0,
        'undefined_parent_has_no_physical_role_label':True,
        'time_model':'native bruces decimal calendar years; strict earlier parents; exact0spatial distance excluded',
        'geometry':prepared.geometry,'eta_seconds':eta_seconds,'normalization_seconds':normalization_seconds}}


def source_versions():
    packages=['bruces','numpy','scipy','numba','llvmlite','utm','pyproj','matplotlib']
    return {name:importlib.metadata.version(name) for name in packages}


def run_toy():
    """Operability and API parity only; no earthquake catalogue is loaded."""
    rng=np.random.RandomState(4201)
    rows=[]
    for i in range(128):
        seconds=int(i*7300+rng.uniform(0,6000))
        stamp=datetime.fromtimestamp(1577836800+seconds,tz=timezone.utc).isoformat().replace('+00:00','Z')
        rows.append({'id':f'synthetic-{i:04d}','time_utc':stamp,'latitude':23.5+rng.normal(0,.15),
          'longitude':-102+rng.normal(0,.15),'magnitude':3.5+rng.uniform(0,2),'magnitude_type':None})
    rows[15]['latitude']=rows[14]['latitude'];rows[15]['longitude']=rows[14]['longitude']
    rows[28]['time_utc']=rows[27]['time_utc']
    prepared=prepare_rows(rows)
    result=run_reference(prepared,-1.0,M=4,draw_seeds=[1730,1731])
    expected=bruces.decluster.nearest_neighbor(prepared.catalog,return_indices=True,method='thinning',
      d=1.5,w=0.0,eta_0=-1.0,alpha_0=0.0,use_depth=False,M=4,seed=1729)
    actual=np.flatnonzero(result['background_draw_masks']['1729'])
    assert np.array_equal(actual,expected),'Adapter does not reproduce public API draw'
    assert not np.isnan(result['background_probability']).any()
    changed=[dict(r,magnitude=100-r['magnitude']) for r in rows]
    other=run_reference(prepare_rows(changed),-1.0,M=4,draw_seeds=[1730,1731])
    assert np.array_equal(result['eta_log10'],other['eta_log10'])
    assert np.array_equal(result['normalized_log10_alpha'],other['normalized_log10_alpha'])
    receipt={'status':'PASS','scope':'Synthetic operability and public API exact mask parity only; no real catalogue run.',
      'events':len(rows),'M':4,'source_versions':source_versions(),'public_api_mask_parity':True,
      'w0_magnitude_invariance':True,'same_coordinates_and_times_not_jittered':True,
      'undefined_parent_count':result['metadata']['native_undefined_parent_count'],
      'module_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/'TOY_API_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    if sys.argv[1:]!=['--toy']:raise SystemExit('Only --toy is enabled. Real runs require the frozen root protocol caller.')
    print(json.dumps(run_toy(),indent=2))
