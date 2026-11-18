"""Read/copy canonical observations, no classification or timing experiment."""
import csv, json, shutil
from decimal import Decimal
from common import BASE, ROOT, INDEX, PILOT, engine, np, sha, write, now

def entry(path): return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
def main():
    target=BASE/'inputs'
    if target.exists(): raise FileExistsError('Preserve any prior preparation: '+str(target))
    target.mkdir(parents=True)
    originals={};datasets={};sources=[]
    pair_path=ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json'
    pairs=json.loads(pair_path.read_bytes()); assert len(pairs)==2989
    paired_ids={source:{p[source+'_record_id'] for p in pairs} for source in ['ssn','usgs']}
    original_bench=INDEX/'v2/benchmark_01/input_arrays.npz'
    assert sha(original_bench)=='759d39d59e8d882a8ae9d9a42b41c8711c8eb0c42bdf9bbd0e1ab0f5bad46a6a'
    for source in ['ssn','usgs']:
        path=PILOT/'inputs'/f'{source}.csv'
        with path.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
        assert all(Decimal(r['magnitude'])>=Decimal('3.5') for r in rows)
        assert len(rows)==(170880 if source=='ssn' else 3945)
        originals[source]=rows;sources.append(entry(path))
        for label,chosen in [('native',rows),('common',[r for r in rows if r['record_id'] in paired_ids[source]]),
                             ('principal45',[r for r in rows if Decimal(r['magnitude'])>=Decimal('4.5')])]:
            key=source+'_'+label; prep=engine.prepare_rows(chosen)
            if label=='common':assert len(chosen)==2989
            if label=='principal45':assert len(chosen)==(1780 if source=='ssn' else 1256)
            arrays=target/(key+'.npz');ids=target/(key+'_ids.json');observed=target/(key+'_rows.json')
            if key=='ssn_native':
                with np.load(original_bench) as previous:
                    for name in ['t_year','lat_deg','lon_deg','m']:
                        assert np.array_equal(previous[name],prep[name]),name
                assert prep['ids']==json.loads((INDEX/'v2/benchmark_01/ids.json').read_bytes())
                shutil.copyfile(original_bench,arrays)
            else:np.savez(arrays,**{name:prep[name] for name in ['t_year','lat_deg','lon_deg','m']})
            write(ids,prep['ids']);write(observed,prep['source_rows'])
            datasets[key]=dict(n=len(chosen),arrays=entry(arrays),ids=entry(ids),rows=entry(observed),
                               time_policy=prep['time_policy'],order_policy=prep['order_policy'])
    shutil.copyfile(pair_path,target/'candidate_pairs.json')
    source=ROOT/'system/dist/sequences/data/inputs_3_5.json'
    raw=json.loads(source.read_bytes()); browser_rows=raw['sources']['ssn']
    assert len(browser_rows)==170880
    prep=engine.prepare_rows(originals['ssn'])
    assert [r['record_id'] for r in browser_rows]==prep['ids']
    for key,column in [('t_year','t_year'),('latitude','lat_deg'),('longitude','lon_deg'),('magnitude','m')]:
        assert np.array_equal(np.array([r[key] for r in browser_rows]),prep[column]),key
    harness=BASE/'browser_harness';harness.mkdir(parents=True,exist_ok=True)
    browser_input=harness/'inputs_ssn_m35.json'
    browser_input.write_text(json.dumps({'schema':'private-browser-benchmark-input/1','rows':browser_rows},separators=(',',':'))+'\n',encoding='utf-8')
    shutil.copyfile(ROOT/'system/dist/sequences/nearest-parent.js',harness/'nearest-parent.js')
    write(target/'MANIFEST.json',dict(status='INPUTS_VERIFIED_NOT_CLASSIFIED',created_utc=now(),datasets=datasets,
          sources=sources,original_benchmark=entry(original_bench),pairs=entry(target/'candidate_pairs.json'),
          browser_source=entry(source),browser_input=entry(browser_input),
          browser_engine=entry(harness/'nearest-parent.js'),observations_changed=False))
    print(json.dumps({key:value['n'] for key,value in datasets.items()}))
if __name__=='__main__':main()

