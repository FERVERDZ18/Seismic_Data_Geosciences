"""Balanced matched-thread benchmarks; no measurements before explicit CPU note."""
import argparse, json, os, statistics, subprocess, sys, time
from common import BASE, ROOT, np, now, sha, write, verify_seal, exact_outputs

SIZES=[2000,5000,10000,20000,50000,100000,170880]
ORDERS=[['reference','kd','octree'],['kd','octree','reference'],['octree','reference','kd']]
def main():
    p=argparse.ArgumentParser();p.add_argument('--cpu-exclusive-note',required=True)
    p.add_argument('--folder',default='native_benchmark_01');p.add_argument('--resume',action='store_true');args=p.parse_args()
    seal=verify_seal();out=(BASE/args.folder).resolve()
    if not out.is_relative_to(BASE):raise ValueError('Private destination only')
    inputs=[('ssn_principal45',None),('usgs_principal45',None)]+[('ssn_native',n) for n in SIZES]
    manifest_path=out/'MANIFEST.json'
    if out.exists():
        if not args.resume:raise FileExistsError('Preserve existing run')
        manifest=json.loads(manifest_path.read_bytes())
        assert manifest['seal_sha256']==sha(BASE/'EXECUTION_SEAL.json')
    else:
        out.mkdir();manifest=dict(status='FROZEN',created_utc=now(),cpu_exclusive_note=args.cpu_exclusive_note,
          seal_sha256=sha(BASE/'EXECUTION_SEAL.json'),threads_all=1,repetitions=3,inputs=inputs,order=ORDERS,
          timeout_seconds_per_cell=1200,cells=[],timing_scope='geometry+build+kernel+numerical export; no import/JIT/load/serialization')
        write(manifest_path,manifest)
    environment={**os.environ,'NUMBA_NUM_THREADS':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    try:
        for dataset,n in inputs:
            label=dataset+('_'+str(n) if n else '')
            for rep,order in enumerate(ORDERS):
                for backend in order:
                    verify_seal();cell=out/(label+'_'+backend+'_'+str(rep))
                    if cell.exists():
                        old=json.loads((cell/'receipt.json').read_bytes())
                        if old['status']!='PASS':raise RuntimeError('Existing non-PASS cell needs explicit amendment/new folder: '+str(cell))
                        continue
                    command=[sys.executable,'-X','utf8','-B',str(BASE/'native_worker.py'),'--cell',str(cell),'--dataset',dataset,
                             '--backend',backend,'--threads','1','--kind','benchmark','--rep',str(rep)]
                    if n:command+=['--n',str(n)]
                    started=time.perf_counter()
                    try:run=subprocess.run(command,cwd=BASE,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1200)
                    except subprocess.TimeoutExpired as error:
                        cell.mkdir(exist_ok=True);write(cell/'TIMEOUT.json',dict(status='CENSORED',wall_limit_seconds=1200,observed_utc=now(),command=command))
                        (cell/'stdout_timeout.txt').write_bytes(error.stdout or b'');(cell/'stderr_timeout.txt').write_bytes(error.stderr or b'');raise
                    (cell/'process_stdout.txt').write_bytes(run.stdout);(cell/'process_stderr.txt').write_bytes(run.stderr)
                    rec=json.loads((cell/'receipt.json').read_bytes());rec['process_wall_seconds']=time.perf_counter()-started;write(cell/'receipt.json',rec)
                    if run.returncode or rec['status']!='PASS':raise RuntimeError('Worker failed: '+str(cell))
                    reference=out/(label+'_reference_0')/'outputs.npz'
                    with np.load(reference) as ref,np.load(cell/'outputs.npz') as actual:parity=exact_outputs(ref,actual)
                    write(cell/'PARITY.json',dict(status='EXACT',reference=str(reference.relative_to(ROOT)),fields=parity))
                    manifest['cells'].append(dict(dataset=dataset,n=rec['n'],backend=backend,rep=rep,total_seconds=rec['measurement']['total_seconds'],
                       process_wall_seconds=rec['process_wall_seconds'],peak_working_set_bytes=rec['after_measurement_memory']['peak_working_set_bytes'],
                       path=cell.relative_to(ROOT).as_posix(),receipt_sha256=sha(cell/'receipt.json'),all_arrays_equal=True))
                    manifest.update(status='IN_PROGRESS',last_completed_utc=now());write(manifest_path,manifest)
                    print(json.dumps(manifest['cells'][-1]),flush=True)
        summaries=[]
        for dataset,n in inputs:
            rows=[r for r in manifest['cells'] if r['dataset']==dataset and (r['n']==n if n else True)]
            # Principal datasets are distinct; no hidden choice of repetition.
            ref=statistics.median(r['total_seconds'] for r in rows if r['backend']=='reference')
            for backend in ['reference','kd','octree']:
                values=[r['total_seconds'] for r in rows if r['backend']==backend]
                peaks=[r['peak_working_set_bytes'] for r in rows if r['backend']==backend]
                assert len(values)==3
                summaries.append(dict(dataset=dataset,n=rows[0]['n'],backend=backend,repetitions=3,threads=1,
                   median_seconds=statistics.median(values),min_seconds=min(values),max_seconds=max(values),
                   median_speedup_vs_reference=ref/statistics.median(values),peak_working_set_bytes=peaks,
                   memory_scope='Whole process including imports/JIT/warmup'))
        write(out/'SUMMARY.json',summaries);manifest.update(status='PASS',completed_utc=now(),summary_sha256=sha(out/'SUMMARY.json'));write(manifest_path,manifest)
    except BaseException as error:
        manifest.update(status='INCOMPLETE_OR_FAILED',error=repr(error),last_utc=now());write(manifest_path,manifest);raise
if __name__=='__main__':main()
