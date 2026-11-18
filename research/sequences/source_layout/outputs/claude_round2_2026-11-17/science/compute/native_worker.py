"""One fresh, sealed native measurement/control; caller must hold CPU window."""
import argparse, os, platform, time, traceback
from pathlib import Path
from common import BASE, ROOT, engine, np, memory, load_dataset, warm, now, sha, write, verify_seal

def main():
    p=argparse.ArgumentParser();p.add_argument('--cell',required=True);p.add_argument('--dataset',required=True)
    p.add_argument('--n',type=int);p.add_argument('--backend',choices=['reference','kd','octree'],required=True)
    p.add_argument('--threads',type=int,required=True);p.add_argument('--w',type=float,default=1.)
    p.add_argument('--kind',choices=['benchmark','correctness'],required=True);p.add_argument('--rep',type=int,default=0)
    args=p.parse_args();seal=verify_seal();cell=Path(args.cell).resolve()
    if not cell.is_relative_to(BASE) or cell.exists(): raise ValueError('New private cell required')
    cell.mkdir(parents=True);engine.set_num_threads(args.threads)
    started=time.perf_counter();data,ids,spec=load_dataset(args.dataset,args.n);load_seconds=time.perf_counter()-started
    rec=dict(status='RUNNING',started_utc=now(),dataset=args.dataset,n=len(ids),backend=args.backend,
       threads_requested=args.threads,threads_configured=engine.get_num_threads(),rep=args.rep,kind=args.kind,w=args.w,d=1.6,q=.5,
       pid=os.getpid(),platform=platform.platform(),cpu=platform.processor(),python_executable=os.sys.executable,
       versions=engine.source_versions(),seal_sha256=sha(BASE/'EXECUTION_SEAL.json'),input=spec,
       input_load_seconds=load_seconds,environment={k:os.environ.get(k) for k in ['NUMBA_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
       before_warmup_memory=memory(),memory_scope='Whole process high-water working set incl imports/JIT/warmup; not exclusive kernel memory')
    receipt=cell/'receipt.json';write(receipt,rec)
    try:
        t=time.perf_counter();warm();rec['warmup_seconds']=time.perf_counter()-t
        rec['before_measurement_memory']=memory();cpu=time.process_time();t=time.perf_counter()
        result=engine.run_arrays(**data,backend=args.backend,d=1.6,w=args.w,q=.5)
        rec['outer_measurement_seconds']=time.perf_counter()-t;rec['process_cpu_seconds']=time.process_time()-cpu
        rec['measurement']=result.pop('metadata');rec['after_measurement_memory']=memory()
        t=time.perf_counter();np.savez_compressed(cell/'outputs.npz',**result)
        rec['serialization_seconds_excluded']=time.perf_counter()-t
        rec.update(status='PASS',completed_utc=now(),output_sha256=sha(cell/'outputs.npz'))
        write(receipt,rec)
        print(os.linesep.join([str(cell),str(rec['measurement']['total_seconds'])]),flush=True)
    except BaseException as error:
        rec.update(status='FAIL',completed_utc=now(),error=repr(error),traceback=traceback.format_exc())
        write(receipt,rec);raise
if __name__=='__main__':main()

