"""Schema-compatible acquisition only; no retained-catalogue analysis."""
from pathlib import Path
import argparse,json,sys,time,urllib.request,urllib.error
sys.dont_write_bytecode=True
from prepare_and_acquire import HERE,sha,dump,stamp
def seal_v2():
    p=HERE/'SEAL_DOWNLOAD_V2.json'
    if p.exists():raise FileExistsError('Do not reseal')
    dump(p,dict(sealed_utc=stamp(),script_sha256=sha(__file__),amendment_sha256=sha(HERE/'AMENDMENT_DOWNLOAD_01.md'),protocol_sha256=sha(HERE/'PROTOCOL.json'),scientific_analysis_performed=False))
    print(p.read_text())
def run(run_id):
    frozen=json.loads((HERE/'SEAL_DOWNLOAD_V2.json').read_text())
    assert frozen['script_sha256']==sha(__file__)
    assert frozen['amendment_sha256']==sha(HERE/'AMENDMENT_DOWNLOAD_01.md')
    assert frozen['protocol_sha256']==sha(HERE/'PROTOCOL.json')
    protocol=json.loads((HERE/'PROTOCOL.json').read_text());target=HERE/'acquisition'/run_id
    if target.exists():raise FileExistsError('Never overwrite evidence')
    target.mkdir(parents=True);records=[]
    dump(target/'STARTED.json',dict(started_utc=stamp(),download_seal_sha256=sha(HERE/'SEAL_DOWNLOAD_V2.json')))
    for query in protocol['queries']:
        success=False
        for attempt in range(1,4):
            prefix=f"{query['label']}_attempt{attempt}";receipt=dict(label=query['label'],url=query['url'],method='GET',started_utc=stamp(),attempt=attempt)
            try:
                request=urllib.request.Request(query['url'],headers={'User-Agent':'Seismic_Data_Geosciences academic reproducibility audit','Accept':'application/json'})
                with urllib.request.urlopen(request,timeout=45) as response:
                    data=response.read();receipt.update(http_status=response.status,headers=dict(response.headers.items()),final_url=response.url)
                body=target/(prefix+'.geojson');body.write_bytes(data);payload=json.loads(data)
                assert payload['type']=='FeatureCollection' and isinstance(payload['features'],list)
                ids=[f['id'] for f in payload['features']];assert len(ids)==len(set(ids))
                assert len(ids)<20000,'At cap; partition amendment required before analysis'
                if 'count' in payload['metadata']:assert len(ids)==payload['metadata']['count']
                receipt.update(status='PASS',bytes=len(data),body_file=body.name,body_sha256=sha(body),features=len(ids),count_field_present='count' in payload['metadata'],server_metadata=payload['metadata'],completed_utc=stamp());success=True
            except Exception as exc:
                receipt.update(status='FAIL',error_type=type(exc).__name__,error=str(exc),completed_utc=stamp())
                if isinstance(exc,urllib.error.HTTPError):
                    body=exc.read();(target/(prefix+'.error')).write_bytes(body);receipt.update(http_status=exc.code,headers=dict(exc.headers.items()),error_body_sha256=sha(target/(prefix+'.error')))
            dump(target/(prefix+'.receipt.json'),receipt);records.append(receipt)
            if success:break
            if attempt<3:time.sleep(2)
        if not success:
            dump(target/'FAILED.json',dict(status='FAIL',records=records));raise RuntimeError('Incomplete acquisition')
    dump(target/'MANIFEST.json',dict(status='PASS',completed_utc=stamp(),protocol_sha256=sha(HERE/'PROTOCOL.json'),download_seal_sha256=sha(HERE/'SEAL_DOWNLOAD_V2.json'),responses=records,no_atomic_snapshot_claim=True,no_catalogue_analysis_performed=True))
    print(json.dumps(dict(status='PASS',directory=str(target),responses=[dict(label=r['label'],features=r.get('features'),bytes=r.get('bytes'),status=r['status']) for r in records]),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','acquire']);p.add_argument('--run-id',default='acquisition_03');a=p.parse_args()
    seal_v2() if a.action=='seal' else run(a.run_id)
