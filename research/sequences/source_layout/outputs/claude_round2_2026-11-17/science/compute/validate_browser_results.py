"""Verify an actual UI-downloaded result artifact, never invent browser runs."""
from pathlib import Path
import argparse,base64,hashlib,json
from common import BASE,ROOT,np,load_dataset,sha,write,now

def main():
    p=argparse.ArgumentParser();p.add_argument('--download',required=True);p.add_argument('--folder',default='browser_result_01')
    p.add_argument('--benchmark-folder',default='native_benchmark_01');args=p.parse_args()
    source=Path(args.download).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out=BASE/args.folder
    if out.exists():raise FileExistsError('Never overwrite observed browser evidence')
    out.mkdir();payload=json.loads(source.read_bytes())
    assert payload['schema']=='actual-browser-nearest-parent-cost/1'
    assert payload['manifest']==json.loads((BASE/'browser_harness/BROWSER_MANIFEST.json').read_bytes())
    expected=[dict(n=n,rep=r,backend=b) for n in [2000,10000,50000,170880] for r in range(3)
              for b in (['kd','reference'] if r%2 else ['reference','kd'])]
    assert payload['plan']==expected
    _,ids,_=load_dataset('ssn_native');results=[];javascript_outputs={}
    for index,cell in enumerate(payload['cells']):
        assert all(cell[key]==expected[index][key] for key in ['n','rep','backend'])
        if cell['status']=='CENSORED':
            assert cell['wall_limit_ms']==120000
            results.append(dict(n=cell['n'],rep=cell['rep'],backend=cell['backend'],status='CENSORED',wall_limit_ms=120000,
                                observed_cell_wall_ms=cell['cell_wall_ms']));continue
        if cell['status']!='COMPUTED':
            results.append(dict(n=cell['n'],rep=cell['rep'],backend=cell['backend'],status='FAIL',error=cell.get('error')));continue
        digest=hashlib.sha256(('\n'.join(ids[:cell['n']])+'\n').encode()).hexdigest()
        assert cell['id_count']==cell['n'] and cell['ids_sha256']==digest
        arrays={}
        for key,spec in cell['fields'].items():
            raw=base64.b64decode(spec['bytes'],validate=True);assert hashlib.sha256(raw).hexdigest()==cell['hashes'][key]
            dtype='<i4' if key=='parent' else '<f8';array=np.frombuffer(raw,dtype=dtype)
            assert len(array)==cell['n'];arrays[key]=array
        ref_path=BASE/args.benchmark_folder/f"ssn_native_{cell['n']}_reference_0/outputs.npz"
        with np.load(ref_path) as ref:
            assert np.array_equal(arrays['parent'],ref['parent_index'])
            with np.errstate(divide='ignore',invalid='ignore'):author_cut=np.log10(ref['TN'])+np.log10(ref['RN'])
            score_checks={}
            for key,expected_score in [('logEta',author_cut),('logProduct',ref['eta_log10'])]:
                actual=arrays[key]
                for fn in [np.isnan,np.isposinf,np.isneginf]:assert np.array_equal(fn(actual),fn(expected_score))
                finite=np.isfinite(expected_score);delta=float(np.max(np.abs(actual[finite]-expected_score[finite]))) if finite.any() else 0.
                assert delta<=1e-10,(cell['n'],cell['backend'],key,delta)
                score_checks[key]=dict(max_abs_delta=delta,criterion=1e-10,nonfinite_masks_equal=True)
        javascript_outputs.setdefault(cell['n'],[]).append((cell['backend'],cell['rep'],arrays))
        results.append(dict(n=cell['n'],rep=cell['rep'],backend=cell['backend'],status='PYTHON_REFERENCE_PASS',parents_exact=True,
             scores=score_checks,metadata=cell['metadata'],cell_wall_ms=cell['cell_wall_ms'],worker_wall_ms=cell['worker_wall_ms']))
    exact=[]
    for n,cells in javascript_outputs.items():
        first=cells[0][2]
        for backend,rep,arrays in cells:
            for key in first:assert np.array_equal(first[key],arrays[key],equal_nan=True),(n,backend,rep,key)
        exact.append(dict(n=n,observed_successful_cells=len(cells),all_js_arrays_exact=True,
                          both_backends_observed=len({item[0] for item in cells})==2))
    report=dict(status='OBSERVED_BROWSER_ARRAY_VERIFICATION_PASS' if not any(c['status']=='FAIL' for c in results) else 'OBSERVED_BROWSER_HAS_FAILURE',
      created_utc=now(),download=dict(path=str(source),sha256=sha(source),bytes=source.stat().st_size),
      user_agent=payload['user_agent'],observed_cells=len(results),predefined_cells=24,complete_plan=len(results)==24,
      results=results,within_js_parity=exact,censored=sum(c['status']=='CENSORED' for c in results),
      full_plan_pass_unconditionally_claimed=False,paint_or_worker_peak_memory_claimed=False,
      interpretation='Actual downloaded UI observations only; censored reference cells do not supply a measured speedup. Finite-input parity, not universal floating-point correctness.')
    write(out/'VERIFICATION.json',report)
    print(json.dumps({key:report[key] for key in ['status','observed_cells','predefined_cells','complete_plan','censored']}))
if __name__=='__main__':main()
