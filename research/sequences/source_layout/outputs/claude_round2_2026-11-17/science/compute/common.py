"""Private round2 glue; never edit the frozen numerical implementations."""
from pathlib import Path
import hashlib, json, os, sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
INDEX = ROOT/'outputs/claude_response_2026-11-16/index'
PILOT = ROOT/'outputs/sequence_pilot_2026-11-15'
sys.dont_write_bytecode = True
os.environ.setdefault('NUMBA_CACHE_DIR', str(BASE/'runtime/numba_cache'))
os.environ.setdefault('MPLCONFIGDIR', str(BASE/'runtime/matplotlib_cache'))
sys.path.insert(0, str(INDEX))
import spherical_weighted_v2 as engine
from cached_balanced_exhaustive_v2 import cached_balanced_exhaustive
from windows_memory import memory
engine.exhaustive = cached_balanced_exhaustive
np = engine.np

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
def write(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def verify_seal():
    seal=json.loads((BASE/'EXECUTION_SEAL.json').read_bytes())
    for item in seal['entries']:
        path=(ROOT/item['path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=item['sha256']:
            raise RuntimeError('Sealed input changed: '+str(path))
    return seal
def load_dataset(key, n=None):
    manifest=json.loads((BASE/'inputs/MANIFEST.json').read_bytes())
    spec=manifest['datasets'][key]
    with np.load(ROOT/spec['arrays']['path']) as source:
        data={k:source[k][:n].copy() if n is not None else source[k].copy()
              for k in ['t_year','lat_deg','lon_deg','m']}
    ids=json.loads((ROOT/spec['ids']['path']).read_bytes())
    return data, ids[:n] if n is not None else ids, spec
def warm():
    data=dict(t_year=np.arange(64,dtype=float)/365.25,lat_deg=np.linspace(10.,20.,64),
              lon_deg=np.linspace(-110.,-90.,64),m=np.full(64,4.))
    for backend in ['reference','kd','octree']: engine.run_arrays(**data,backend=backend)
def exact_outputs(reference, actual):
    if set(reference.files)!=set(actual.files): raise AssertionError('Output fields differ')
    details={}
    for key in reference.files:
        a,b=reference[key],actual[key]
        equal=a.dtype==b.dtype and a.shape==b.shape and np.array_equal(a,b,equal_nan=True)
        details[key]=dict(equal=bool(equal),dtype=str(a.dtype),shape=list(a.shape))
        if not equal: raise AssertionError('Exact output mismatch: '+key)
    return details

