"""Verify actual V3 loopback POST bytes and numerical arrays; never run kernels."""
from pathlib import Path
import argparse,base64,hashlib,json
from common import BASE,ROOT,np,load_dataset,sha,write,now

def main():
    p=argparse.ArgumentParser();p.add_argument('--download','--observed',dest='download',required=True);p.add_argument('--folder',default='browser_result_v3_01')
    p.add_argument('--benchmark-folder',default='native_benchmark_01');args=p.parse_args()
    source=Path(args.download).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out=BASE/args.folder
    if out.exists():raise FileExistsError('Never overwrite observed browser evidence')
    out.mkdir();payload=json.loads(source.read_bytes())
    assert payload['schema']=='actual-browser-nearest-parent-cost/1'
    assert payload['manifest']==json.loads((BASE/'browser_harness/v3/BROWSER_MANIFEST.json').read_bytes())
    expected=[dict(n=n,rep=r,backend=b) for n in [2000,10000,50000,170880] for r in range(3)
              for b in (['kd','reference'] if r%2 else ['reference','kd'])]
    assert payload['plan']==expected
    assert len(payload['cells'])==24
    assert payload['transport']=='same-origin-loopback-post-v3'
    assert payload.get('fixture_only',False) is False
    receipt_path=source.with_name('receipt.json')
    receipt=json.loads(receipt_path.read_bytes())
    assert receipt['saved'] is True and receipt['fixture_only'] is False
    assert receipt['sha256']==sha(source) and receipt['bytes']==source.stat().st_size
    for asset in payload['manifest']['assets']:
        sealed_path=(BASE/'browser_harness/v3'/asset['file']).resolve()
        assert sha(sealed_path)==asset['sha256'] and sealed_path.stat().st_size==asset['bytes']
    inputs_manifest=json.loads((BASE/'inputs/MANIFEST.json').read_bytes())
    for key in ['arrays','ids','rows']:
        spec=inputs_manifest['datasets']['ssn_native'][key]
        pinned=ROOT/spec['path']
        assert sha(pinned)==spec['sha256'] and pinned.stat().st_size==spec['bytes']
    load=payload['initial_load']
    assert load['paint_measured'] is False and load['worker_peak_memory_measured'] is False
    assert load['transfer_time_isolated'] is False and load['total_ms']>=0
    assert len(load['assets'])==5 and len(payload['visibility_observations'])>=1
    for asset in load['assets']:
        for key in ['fetch_resolution_ms','body_read_ms','sha256_ms','hash_and_size_validation_ms']:
            assert asset[key]>=0
    input_load=next(a for a in load['assets'] if a['file']=='../inputs_ssn_m35.json')
    for key in ['utf8_decode_ms','json_parse_ms','structure_and_count_validation_ms']:
        assert input_load[key]>=0
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
        assert set(arrays)=={'parent','eta','dt','distance','tn','rn','logEta','logProduct'}
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
      initial_load=load,visibility_observations=payload['visibility_observations'],
      user_agent=payload['user_agent'],observed_cells=len(results),predefined_cells=24,complete_plan=len(results)==24,
      results=results,within_js_parity=exact,censored=sum(c['status']=='CENSORED' for c in results),
      full_plan_pass_unconditionally_claimed=False,paint_or_worker_peak_memory_claimed=False,
      interpretation='Actual persisted loopback POST observations only; censored reference cells do not supply a measured speedup. Finite-input parity, not universal floating-point correctness.')
    write(out/'VERIFICATION.json',report)
    print(json.dumps({key:report[key] for key in ['status','observed_cells','predefined_cells','complete_plan','censored']}))
if __name__=='__main__':main()
