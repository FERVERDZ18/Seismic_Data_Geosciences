"""Small Eqclustering core observation; no scientific run without coordinator."""
from pathlib import Path
import argparse,importlib.util,json,os,sys,time,hashlib,platform,traceback
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'outputs/sequence_pilot_2026-11-15/comparators/nearest_neighbor/_deps'))
sys.path.insert(0,str(ROOT/'outputs/claude_response_2026-11-16/index'))
import numpy as np
from windows_memory import memory
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--cell',required=True);p.add_argument('--rep',type=int,required=True);a=p.parse_args()
    cell=Path(a.cell).resolve()
    if not cell.is_relative_to(BASE) or cell.exists():raise ValueError('New private comparator cell required')
    seal=json.loads((BASE/'COMPARATOR_EXECUTION_SEAL.json').read_bytes())
    for item in seal['entries']:
        if sha(ROOT/item['path'])!=item['sha256']:raise RuntimeError('Comparator source changed')
    cell.mkdir(parents=True)
    manifest=json.loads((BASE/'inputs/MANIFEST.json').read_bytes());spec=manifest['datasets'][a.dataset]
    with np.load(ROOT/spec['arrays']['path']) as z:data={key:z[key].copy() for key in ['t_year','lat_deg','lon_deg','m']}
    adapter=BASE/'comparators/eqclustering_python3_constants.py'
    module=importlib.util.module_from_spec(s:=importlib.util.spec_from_file_location('round2_eqclustering',adapter));s.loader.exec_module(module)
    times=data['t_year']*31557600.;bp=module.BPFunction()
    rec=dict(status='RUNNING',dataset=a.dataset,n=len(times),rep=a.rep,numpy=np.__version__,python=sys.version,
       platform=platform.platform(),source_commit='393a02db91f278027cb9dbff7547199d1b667e69',adapter_sha256=sha(adapter),
       adaptation='Python2 date literal syntax and NumPy Inf/NaN constant spellings only; original365.35day normalization and unclamped acos preserved',
       algorithm='Original BPFunction core only; no prune/EM/family labels',before_warmup_memory=memory())
    write(cell/'receipt.json',rec)
    try:
        t=time.perf_counter();bp(times[:64],data['m'][:64],data['lon_deg'][:64],data['lat_deg'][:64],[],1.,1.6,None,False)
        rec['warmup_seconds']=time.perf_counter()-t;rec['before_measurement_memory']=memory()
        cpu=time.process_time();t=time.perf_counter()
        parent,eta,distance,years,parent_mag=bp(times,data['m'],data['lon_deg'],data['lat_deg'],[],1.,1.6,None,False)
        rec['kernel_seconds']=time.perf_counter()-t;rec['process_cpu_seconds']=time.process_time()-cpu;rec['after_measurement_memory']=memory()
        parent_index=np.full(len(times),-1,dtype=np.int64);valid=np.isfinite(parent);parent_index[valid]=parent[valid].astype(np.int64)
        np.savez_compressed(cell/'outputs.npz',parent_index=parent_index,eta_native_seconds_metres=eta,parent_distance_km=distance,
                            parent_dt_years_365p35=years,parent_reported_magnitude=parent_mag)
        rec.update(status='PASS',output_sha256=sha(cell/'outputs.npz'));write(cell/'receipt.json',rec)
        print(json.dumps(dict(dataset=a.dataset,rep=a.rep,n=len(times),seconds=rec['kernel_seconds'])),flush=True)
    except BaseException as e:
        rec.update(status='FAIL',error=repr(e),traceback=traceback.format_exc());write(cell/'receipt.json',rec);raise
if __name__=='__main__':main()

