"""Observed M3.5 parent sensitivity, never EM-family interpretation."""
import argparse,json,os,subprocess,sys,time,traceback
from pathlib import Path
from common import BASE,ROOT,np,now,sha,write,verify_seal,load_dataset,exact_outputs

WEIGHTS=[('w0p8',.8),('w0p9',.9),('w1p0',1.),('w1p1',1.1),('w1p2',1.2),('w1p3',1.3),('w1p4',1.4),
         ('w_b_usgs',1.0905428994843476),('w_b_ssn',1.3265675928192793)]
NODE=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/bin/node.exe')

def execute_native(out,dataset,label,w,backend,threads):
    cell=out/(dataset+'_'+label+'_'+backend)
    if cell.exists():
        rec=json.loads((cell/'receipt.json').read_bytes())
        if rec['status']!='PASS':raise RuntimeError('Preserve non-PASS cell, explicit amendment required: '+str(cell))
        return cell
    command=[sys.executable,'-X','utf8','-B',str(BASE/'native_worker.py'),'--cell',str(cell),'--dataset',dataset,
             '--backend',backend,'--threads',str(threads),'--kind','correctness','--w',repr(w)]
    env={**os.environ,'NUMBA_NUM_THREADS':str(threads),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    started=time.perf_counter()
    try:result=subprocess.run(command,cwd=BASE,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1200)
    except subprocess.TimeoutExpired as error:
        cell.mkdir(exist_ok=True);write(cell/'TIMEOUT.json',dict(status='CENSORED',limit_seconds=1200,at=now(),kind='correctness_not_benchmark'))
        (cell/'stdout_timeout.txt').write_bytes(error.stdout or b'');(cell/'stderr_timeout.txt').write_bytes(error.stderr or b'');raise
    (cell/'process_stdout.txt').write_bytes(result.stdout);(cell/'process_stderr.txt').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('Native correctness run failed: '+str(cell))
    rec=json.loads((cell/'receipt.json').read_bytes());rec['process_wall_seconds']=time.perf_counter()-started;write(cell/'receipt.json',rec)
    return cell

def node_parity(out,dataset,label,w,native_cell):
    source,context=dataset.split('_');folder=out/(dataset+'_'+label+'_node')
    if not folder.exists():
        command=[str(NODE),str(BASE/'node_parent_worker.cjs'),source,context,repr(w),str(folder)]
        result=subprocess.run(command,cwd=BASE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
        folder.mkdir(exist_ok=True);(folder/'stdout.txt').write_bytes(result.stdout);(folder/'stderr.txt').write_bytes(result.stderr)
        if result.returncode:raise RuntimeError('JS run failed: '+str(folder))
    rec=json.loads((folder/'receipt.json').read_bytes());_,ids,_=load_dataset(dataset)
    assert ids==json.loads((ROOT/rec['ids']['path']).read_bytes())
    with np.load(native_cell/'outputs.npz') as py:
        parent=np.fromfile(ROOT/rec['files']['parent']['path'],dtype='<i4')
        assert np.array_equal(parent,py['parent_index']),('Parent mismatch',dataset,label)
        with np.errstate(divide='ignore',invalid='ignore'):cut_score=np.log10(py['TN'])+np.log10(py['RN'])
        comparisons={}
        for field,expected in [('logEta',cut_score),('logProduct',py['eta_log10'])]:
            actual=np.fromfile(ROOT/rec['files'][field]['path'],dtype='<f8')
            assert np.array_equal(np.isnan(actual),np.isnan(expected))
            assert np.array_equal(np.isposinf(actual),np.isposinf(expected))
            assert np.array_equal(np.isneginf(actual),np.isneginf(expected))
            finite=np.isfinite(expected);delta=float(np.max(np.abs(actual[finite]-expected[finite]))) if finite.any() else 0.
            assert delta<=1e-10,('Unchanged score criterion failed',dataset,label,field,delta)
            comparisons[field]=dict(max_abs_difference=delta,criterion=1e-10,nonfinite_masks_equal=True)
    write(folder/'PARITY.json',dict(status='PASS',parents_exact=True,ids_exact=True,scores=comparisons,
          native_reference= native_cell.relative_to(ROOT).as_posix(),native_output_sha256=sha(native_cell/'outputs.npz'),
          scope='Declared finite observations and weights only; not universal IEEE guarantee'))
    return folder

def distribution(values):
    finite=values[np.isfinite(values)]
    return dict(n=int(len(values)),finite_n=int(len(finite)),nan=int(np.isnan(values).sum()),
                neginf=int(np.isneginf(values).sum()),posinf=int(np.isposinf(values).sum()),
                quantiles={str(q):float(np.quantile(finite,q)) for q in [.05,.5,.95]} if len(finite) else {})
def parent_comparison(a,b,indexes):
    left,right=a[indexes],b[indexes];defined=(left>=0)&(right>=0)
    # Indexes refer to the same original dataset. Context contrast uses IDs below.
    return dict(target_n=int(len(indexes)),both_defined=int(defined.sum()),first_undefined=int((left<0).sum()),
       second_undefined=int((right<0).sum()),changed_defined=int((left[defined]!=right[defined]).sum()),
       changed_fraction_defined=float(np.mean(left[defined]!=right[defined])) if defined.any() else None)

def summarize(out,cells):
    manifest=json.loads((BASE/'inputs/MANIFEST.json').read_bytes());pairs=json.loads((BASE/'inputs/candidate_pairs.json').read_bytes())
    data={};positions={};pair_parent={};prepared={}
    for dataset in ['ssn_native','usgs_native','ssn_common','usgs_common']:
        arrays,ids,spec=load_dataset(dataset);rows=json.loads((ROOT/spec['rows']['path']).read_bytes())
        prepared[dataset]=(arrays,ids,rows);positions[dataset]={v:i for i,v in enumerate(ids)}
        source=dataset.split('_')[0];pair_parent[source]={p[source+'_record_id']:i for i,p in enumerate(pairs)}
        for label,w in WEIGHTS:
            with np.load(Path(cells[dataset+'_'+label])/'outputs.npz') as z:data[dataset,label]={k:z[k].copy() for k in z.files}
    comparisons=[];cross=[];contexts=[]
    for dataset,(arrays,ids,rows) in prepared.items():
        source=dataset.split('_')[0];focal=np.array([positions[dataset][p[source+'_record_id']] for p in pairs],dtype=int)
        held=np.array([i for i,r in enumerate(rows) if r['time_utc']>='2021-01-01'],dtype=int)
        for label,w in WEIGHTS:
            current=data[dataset,label];base=data[dataset,'w1p0'];parent=current['parent_index'];defined=parent>=0
            for scope,indexes in [('all',np.arange(len(ids))),('evaluation_2021_2025',held),('candidate_endpoints',focal)]:
                valid=indexes[defined[indexes]]
                comparisons.append(dict(dataset=dataset,weight_label=label,w=w,scope=scope,
                    stability_vs_w1=parent_comparison(base['parent_index'],parent,indexes),
                    parent_dt_days=distribution(current['parent_dt_years'][indexes]*365.25),
                    parent_distance_km=distribution(current['parent_distance_km'][indexes]),
                    parent_reported_magnitude=distribution(arrays['m'][parent[valid]]),
                    log_proximity=distribution(current['eta_log10'][indexes])))
    for source in ['ssn','usgs']:
        na,ni,nr=prepared[source+'_native'];ca,ci,cr=prepared[source+'_common']
        targets=[p[source+'_record_id'] for p in pairs]
        for label,w in WEIGHTS:
            p_native=data[source+'_native',label]['parent_index'];p_common=data[source+'_common',label]['parent_index']
            for period in ['all','evaluation_2021_2025']:
                chosen=[rid for rid in targets if period=='all' or nr[positions[source+'_native'][rid]]['time_utc']>='2021-01-01']
                ids_native=[ni[p_native[positions[source+'_native'][rid]]] if p_native[positions[source+'_native'][rid]]>=0 else None for rid in chosen]
                ids_common=[ci[p_common[positions[source+'_common'][rid]]] if p_common[positions[source+'_common'][rid]]>=0 else None for rid in chosen]
                defined=[(a,b) for a,b in zip(ids_native,ids_common) if a is not None and b is not None]
                changed=sum(a!=b for a,b in defined)
                contexts.append(dict(source=source,weight_label=label,w=w,period=period,target_n=len(chosen),
                   both_defined=len(defined),native_undefined=ids_native.count(None),common_undefined=ids_common.count(None),
                   changed_parent=changed,changed_fraction_defined=changed/len(defined) if defined else None))
    configs=[(label,label,w,w,label) for label,w in WEIGHTS]+[('w_b_ssn','w_b_usgs',1.3265675928192793,1.0905428994843476,'source_specific_reported_b')]
    for context in ['native','common']:
        for sl,ul,sw,uw,label in configs:
            for period in ['all','evaluation_2021_2025']:
                stats=dict(target_n=0,both_candidate_parents=0,same_candidate_parent=0,ssn_unmatched_parent=0,usgs_unmatched_parent=0,ssn_no_parent=0,usgs_no_parent=0)
                for pair in pairs:
                    sn=positions['ssn_'+context][pair['ssn_record_id']];un=positions['usgs_'+context][pair['usgs_record_id']]
                    if period!='all' and prepared['ssn_'+context][2][sn]['time_utc']<'2021-01-01':continue
                    stats['target_n']+=1;parent_pairs=[]
                    for source,i,wl in [('ssn',sn,sl),('usgs',un,ul)]:
                        parent=int(data[source+'_'+context,wl]['parent_index'][i])
                        if parent<0:stats[source+'_no_parent']+=1;parent_pairs.append(None);continue
                        rid=prepared[source+'_'+context][1][parent];mapped=pair_parent[source].get(rid)
                        if mapped is None:stats[source+'_unmatched_parent']+=1
                        parent_pairs.append(mapped)
                    if all(x is not None for x in parent_pairs):
                        stats['both_candidate_parents']+=1
                        stats['same_candidate_parent']+=int(parent_pairs[0]==parent_pairs[1])
                n=stats['target_n'];c=stats['both_candidate_parents'];same=stats['same_candidate_parent']
                cross.append(dict(context=context,weight_configuration=label,ssn_w=sw,usgs_w=uw,period=period,**stats,
                     same_parent_fraction_all=same/n if n else None,same_parent_fraction_comparable=same/c if c else None,
                     comparable_fraction=c/n if n else None))
    write(out/'PARENT_SENSITIVITY_SUMMARY.json',dict(observations_changed=False,em_threshold_used=False,family_roles_used=False,
        interpretation='Observed nearest-parent/proximity sensitivity; candidate associations unreviewed, no triggering/completeness/physical-identity accuracy claim',
        weight_stability=comparisons,context_contrasts=contexts,cross_catalogue_candidate_parent_agreement=cross))

def main():
    p=argparse.ArgumentParser();p.add_argument('--cpu-exclusive-note',required=True);p.add_argument('--folder',default='large_parent_01')
    p.add_argument('--benchmark-folder',default='native_benchmark_01');p.add_argument('--resume',action='store_true');args=p.parse_args()
    verify_seal();out=(BASE/args.folder).resolve()
    if not out.is_relative_to(BASE):raise ValueError('Private folder only')
    if out.exists():
        if not args.resume:raise FileExistsError(out)
        manifest=json.loads((out/'MANIFEST.json').read_bytes());assert manifest['seal_sha256']==sha(BASE/'EXECUTION_SEAL.json')
    else:
        out.mkdir();manifest=dict(status='FROZEN',created_utc=now(),cpu_exclusive_note=args.cpu_exclusive_note,seal_sha256=sha(BASE/'EXECUTION_SEAL.json'),
           weights=WEIGHTS,em_threshold=False,physical_truth_validated=False,cells={})
    try:
        for dataset in ['ssn_native','usgs_native','ssn_common','usgs_common']:
            for label,w in WEIGHTS:
                verify_seal();key=dataset+'_'+label
                reuse=BASE/args.benchmark_folder/'ssn_native_170880_reference_0'
                if dataset=='ssn_native' and label=='w1p0' and reuse.exists():
                    expected,ids,_=load_dataset(dataset);bench=json.loads((reuse/'receipt.json').read_bytes())
                    assert bench['dataset']=='ssn_native' and bench['n']==len(ids) and bench['w']==1. and bench['status']=='PASS'
                    reference=reuse
                else:reference=execute_native(out,dataset,label,w,'reference',4)
                actual=execute_native(out,dataset,label,w,'kd',1)
                with np.load(reference/'outputs.npz') as ref,np.load(actual/'outputs.npz') as kd:parity=exact_outputs(ref,kd)
                write(actual/'FULL_REFERENCE_PARITY.json',dict(status='EXACT',reference=reference.relative_to(ROOT).as_posix(),fields=parity))
                node=node_parity(out,dataset,label,w,actual)
                manifest['cells'][key]=dict(native=str(actual),reference=str(reference),node=str(node),all_python_arrays_equal=True,node_parity='PASS')
                manifest.update(status='IN_PROGRESS',last_completed_utc=now());write(out/'MANIFEST.json',manifest)
                print(json.dumps(dict(dataset=dataset,w=w,status='FULL_REFERENCE_AND_NODE_PASS')),flush=True)
        summarize(out,{key:value['native'] for key,value in manifest['cells'].items()})
        manifest.update(status='PASS',completed_utc=now(),summary_sha256=sha(out/'PARENT_SENSITIVITY_SUMMARY.json'));write(out/'MANIFEST.json',manifest)
    except BaseException as error:
        manifest.update(status='INCOMPLETE_OR_FAILED',error=repr(error),traceback=traceback.format_exc(),last_utc=now());write(out/'MANIFEST.json',manifest);raise
if __name__=='__main__':main()
