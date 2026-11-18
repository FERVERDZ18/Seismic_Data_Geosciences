"""Explicit later CPU phase: three fresh small-core executions per comparator."""
import argparse,json,os,subprocess,sys,time,ctypes,traceback
from pathlib import Path
from common import BASE,ROOT,np,sha,write,load_dataset,now
from scipy.io import loadmat
METHODS=ROOT/'outputs/claude_response_2026-11-16/methods'
OCTAVE=ROOT/'outputs/claude_response_2026-11-16/runtime/octave-11.3.0-w64/mingw64/bin/octave-cli.exe'
def native_comparison(path,reference,kind):
    with np.load(path) as actual,np.load(reference) as ref:
        parent=actual['parent_index'];defined=(parent>=0)&(ref['parent_index']>=0)
        report=dict(parent_mismatches=int(np.count_nonzero(parent!=ref['parent_index'])),n=len(parent),both_defined=int(defined.sum()),
                    comparison_is_not_forced=True,source_contract=kind)
        for field in ['eta_native_seconds_metres','parent_distance_km']:
            a,b=actual[field],ref[field];finite=defined&np.isfinite(a)&np.isfinite(b)
            report[field]=dict(both_finite=int(finite.sum()),max_abs_difference=float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else None,
                               nonfinite_mask_equal=bool(np.array_equal(np.isfinite(a),np.isfinite(b))))
        if kind=='eqclustering':
            # Unit-adjust only in comparison; preserve all original comparator arrays.
            adjusted=actual['parent_dt_years_365p35']*365.35/365.25
            report['time_unit_comparison']=dict(original_days_per_year=365.35,target_days_per_year=365.25,
                max_abs_year_difference_after_unit_conversion=float(np.max(np.abs(adjusted[defined]-ref['parent_dt_years'][defined]))))
        return report
def process_memory(pid):
    class Info(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong),('peak',ctypes.c_size_t),('current',ctypes.c_size_t),('a',ctypes.c_size_t),('b',ctypes.c_size_t),('c',ctypes.c_size_t),('d',ctypes.c_size_t),('pagefile',ctypes.c_size_t),('peakpagefile',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);api=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p];api.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Info),ctypes.c_ulong]
    handle=kernel.OpenProcess(0x0400|0x0010,False,pid)
    if not handle:return None
    try:
        result=Info();result.cb=ctypes.sizeof(result)
        if not api.GetProcessMemoryInfo(handle,ctypes.byref(result),result.cb):return None
        return dict(peak_working_set_bytes=int(result.peak),working_set_bytes=int(result.current),peak_pagefile_bytes=int(result.peakpagefile))
    finally:kernel.CloseHandle(handle)
def main():
    p=argparse.ArgumentParser();p.add_argument('--cpu-exclusive-note',required=True);p.add_argument('--folder',default='comparators_01');p.add_argument('--benchmark-folder',default='native_benchmark_01');a=p.parse_args()
    seal=json.loads((BASE/'COMPARATOR_EXECUTION_SEAL.json').read_bytes())
    for item in seal['entries']:
        assert sha(ROOT/item['path'])==item['sha256']
    out=BASE/a.folder
    if out.exists():raise FileExistsError(out)
    out.mkdir();manifest=dict(status='FROZEN',started_utc=now(),cpu_note=a.cpu_exclusive_note,seal_sha256=sha(BASE/'COMPARATOR_EXECUTION_SEAL.json'),cells=[])
    env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1',
         'OCTAVE_HISTFILE':str(BASE/'runtime/octave_history_private')}
    try:
        for dataset in ['ssn_principal45','usgs_principal45']:
            arrays,ids,spec=load_dataset(dataset);reference=BASE/a.benchmark_folder/(dataset+'_reference_0')/'outputs.npz'
            input_csv=out/(dataset+'.csv');np.savetxt(input_csv,np.column_stack([arrays[k] for k in ['t_year','lat_deg','lon_deg','m']]),delimiter=',',fmt='%.17g')
            for rep in range(3):
                for kind in ['eqclustering','author_octave'] if rep%2==0 else ['author_octave','eqclustering']:
                    cell=out/(dataset+'_'+kind+'_'+str(rep));started=time.perf_counter()
                    if kind=='eqclustering':
                        command=[sys.executable,'-X','utf8','-B',str(BASE/'comparator_worker.py'),'--dataset',dataset,'--cell',str(cell),'--rep',str(rep)]
                        result=subprocess.run(command,env=env,cwd=BASE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
                        cell.mkdir(exist_ok=True);(cell/'stdout.txt').write_bytes(result.stdout);(cell/'stderr.txt').write_bytes(result.stderr)
                        if result.returncode:raise RuntimeError('Eqclustering compatibility/execution failure retained')
                        rec=json.loads((cell/'receipt.json').read_bytes())
                    else:
                        cell.mkdir();target=cell/'author_outputs.mat'
                        command=[str(OCTAVE),'--no-gui','--quiet','--no-init-file','--no-site-file','--no-history',str(BASE/'comparators/author_core.m'),
                                 str(input_csv),str(target),str(METHODS/'authors_2013_exact/eq_cluster'),str(METHODS/'octave_wrappers')]
                        observations=[]
                        with (cell/'stdout.txt').open('wb') as stdout,(cell/'stderr.txt').open('wb') as stderr:
                            process=subprocess.Popen(command,env=env,cwd=cell,stdout=stdout,stderr=stderr)
                            while process.poll() is None:
                                probe=process_memory(process.pid)
                                if probe:observations.append(probe)
                                if time.perf_counter()-started>120:process.terminate();raise TimeoutError('Author-core120s cap')
                                time.sleep(.05)
                            if process.returncode:raise RuntimeError('Author source failed')
                        values=loadmat(target,squeeze_me=True);parents=np.atleast_1d(values['P']).astype(np.int64)-1
                        np.savez_compressed(cell/'outputs.npz',parent_index=parents,eta_native_seconds_metres=np.atleast_1d(values['n']),
                            parent_distance_km=np.atleast_1d(values['D']),parent_dt_years=np.atleast_1d(values['T']))
                        rec=dict(status='PASS',dataset=dataset,n=len(ids),rep=rep,comparator=kind,kernel_seconds=float(values['kernel_seconds']),warmup_seconds=float(values['warmup_seconds']),
                            octave_version=str(values['octave_version']),source_commit=str(values['source_commit']),
                            observed_process_peak_working_set_bytes=max((v['peak_working_set_bytes'] for v in observations),default=None),
                            memory_scope='Sampled OS process high-water every50ms, includes startup/imports; only this spawned PID queried',
                            numerical_source_unmodified=True,shims='Existing waitbar/set/close adapters; GUI only',output_sha256=sha(cell/'outputs.npz'))
                    rec['process_wall_seconds']=time.perf_counter()-started;rec['comparison']=native_comparison(cell/'outputs.npz',reference,'eqclustering' if kind=='eqclustering' else 'author_octave')
                    write(cell/'receipt.json',rec);manifest['cells'].append(dict(dataset=dataset,rep=rep,comparator=kind,
                        kernel_seconds=rec['kernel_seconds'],process_wall_seconds=rec['process_wall_seconds'],receipt_sha256=sha(cell/'receipt.json'),path=cell.relative_to(ROOT).as_posix()))
                    manifest.update(status='IN_PROGRESS',last_utc=now());write(out/'MANIFEST.json',manifest);print(json.dumps(manifest['cells'][-1]),flush=True)
        manifest.update(status='PASS',completed_utc=now());write(out/'MANIFEST.json',manifest)
    except BaseException as e:
        manifest.update(status='INCOMPLETE_OR_FAILED',error=repr(e),traceback=traceback.format_exc(),at=now());write(out/'MANIFEST.json',manifest);raise
if __name__=='__main__':main()
