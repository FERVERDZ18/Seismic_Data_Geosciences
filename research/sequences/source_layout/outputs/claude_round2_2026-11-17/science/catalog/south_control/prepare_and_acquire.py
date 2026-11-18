"""Seal a separate current ComCat acquisition; no clustering or matching here."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,time,urllib.request,urllib.error,urllib.parse
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def stamp():return datetime.now(timezone.utc).isoformat()
def seal():
    if (HERE/'SEAL.json').exists():raise FileExistsError('Do not reseal or overwrite a protocol')
    inputs=[ROOT/'system/dist/data/catalogs/ssn-mx/events.json',ROOT/'system/dist/data/catalogs/ssn-mx/manifest.json',ROOT/'research-data/catalogs/ssn-mx/ssn_19000101_20261106.csv',ROOT/'system/dist/data/events.json',ROOT/'system/dist/data/manifest.json',ROOT/'outputs/sequence_pilot_2026-11-15/inputs/ssn.csv',ROOT/'outputs/sequence_pilot_2026-11-15/inputs/usgs.csv',ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json',ROOT/'outputs/claude_response_2026-11-16/catalog_design/scientific_diagnostics.compact.json']
    dump(HERE/'INPUTS.json',[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in inputs])
    queries=[]
    for year,end in [(2016,2021),(2021,2026)]:
        params=dict(format='geojson',starttime=f'{year}-01-01T00:00:00Z',endtime=f'{end}-01-01T00:00:00Z',minlatitude=12,maxlatitude=33,minlongitude=-118,maxlongitude=-86,minmagnitude=3.5,eventtype='earthquake',orderby='time-asc',limit=20000)
        queries.append(dict(label=f'{year}_{end}',local_start_inclusive=f'{year}-01-01',local_end_exclusive=f'{end}-01-01',params=params,url='https://earthquake.usgs.gov/fdsnws/event/1/query?'+urllib.parse.urlencode(params)))
    dump(HERE/'PROTOCOL.json',dict(schema='round2-southern-context-control/1',queries=queries,md_sha256=sha(HERE/'PROTOCOL.md'),inputs_sha256=sha(HERE/'INPUTS.json'),download_script_sha256=sha(__file__),no_new_SSN_snapshot=True,no_mixing_old_and_new_ComCat=True,analysis_cpu_gate='WAIT root',old_latitude_min=14,new_latitude_min=12,magnitude_input_floor='3.5',magnitude_analysis_cut='4.5',development_end_exclusive='2021-01-01',w=1.,d=1.6,matching_seconds=30,matching_km=50))
    dump(HERE/'SEAL.json',dict(sealed_utc=stamp(),files={n:sha(HERE/n) for n in ['PROTOCOL.md','PROTOCOL.json','INPUTS.json']},scientific_results_created=False))
    print(json.dumps(json.loads((HERE/'SEAL.json').read_text()),indent=2))
def acquire(run_id):
    protocol=json.loads((HERE/'PROTOCOL.json').read_text());sealed=json.loads((HERE/'SEAL.json').read_text())
    for n,h in sealed['files'].items():assert sha(HERE/n)==h,n
    assert protocol['download_script_sha256']==sha(__file__)
    target=HERE/'acquisition'/run_id
    if target.exists():raise FileExistsError('Never overwrite response evidence')
    target.mkdir(parents=True);records=[]
    dump(target/'STARTED.json',dict(started_utc=stamp(),protocol_sha256=sha(HERE/'PROTOCOL.json'),script_sha256=sha(__file__)))
    for query in protocol['queries']:
        success=False
        for attempt in range(1,4):
            prefix=f"{query['label']}_attempt{attempt}";receipt=dict(label=query['label'],url=query['url'],method='GET',started_utc=stamp(),attempt=attempt)
            try:
                request=urllib.request.Request(query['url'],headers={'User-Agent':'Seismic_Data_Geosciences academic reproducibility audit','Accept':'application/json'})
                with urllib.request.urlopen(request,timeout=45) as response:
                    data=response.read();receipt.update(status=response.status,headers=dict(response.headers.items()),final_url=response.url)
                (target/(prefix+'.geojson')).write_bytes(data)
                payload=json.loads(data)
                assert payload['type']=='FeatureCollection'
                assert len(payload['features'])==payload['metadata']['count']
                assert len(payload['features'])<20000,'Response at cap; pre-analysis pagination amendment required'
                receipt.update(status='PASS',http_status=200,bytes=len(data),body_file=prefix+'.geojson',body_sha256=sha(target/(prefix+'.geojson')),features=len(payload['features']),server_metadata=payload['metadata'],completed_utc=stamp())
                success=True
            except Exception as exc:
                receipt.update(status='FAIL',error_type=type(exc).__name__,error=str(exc),completed_utc=stamp())
                if isinstance(exc,urllib.error.HTTPError):
                    body=exc.read();(target/(prefix+'.error')).write_bytes(body);receipt.update(http_status=exc.code,headers=dict(exc.headers.items()),error_body_sha256=sha(target/(prefix+'.error')))
            dump(target/(prefix+'.receipt.json'),receipt);records.append(receipt)
            if success:break
            if attempt<3:time.sleep(2)
        if not success:
            dump(target/'FAILED.json',dict(status='FAIL',records=records));raise RuntimeError('Acquisition incomplete; preserve failures')
    dump(target/'MANIFEST.json',dict(status='PASS',completed_utc=stamp(),protocol_sha256=sha(HERE/'PROTOCOL.json'),responses=records,no_atomic_snapshot_claim=True,no_catalogue_analysis_performed=True))
    print(json.dumps(dict(status='PASS',directory=str(target),responses=[dict(label=r['label'],features=r.get('features'),bytes=r.get('bytes'),status=r['status']) for r in records]),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','acquire']);p.add_argument('--run-id',default='acquisition_01');a=p.parse_args()
    seal() if a.action=='seal' else acquire(a.run_id)
