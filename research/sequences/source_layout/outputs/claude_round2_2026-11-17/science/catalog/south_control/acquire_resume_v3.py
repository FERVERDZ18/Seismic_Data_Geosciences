"""Reuse unchanged HTTP200 bytes, then acquire the missing fixed interval."""
from pathlib import Path
import argparse,json,sys,time,urllib.request,urllib.error
sys.dont_write_bytecode=True
from prepare_and_acquire import HERE,sha,dump,stamp
def validate(data):
    x=json.loads(data);assert x['type']=='FeatureCollection' and isinstance(x['features'],list)
    ids=[f['id'] for f in x['features']];assert len(ids)==len(set(ids)) and len(ids)<20000
    if 'count' in x['metadata']:assert len(ids)==x['metadata']['count']
    return dict(features=len(ids),server_metadata=x['metadata'],count_field_present='count' in x['metadata'])
def seal():
    p=HERE/'SEAL_RESUME_V3.json'
    if p.exists():raise FileExistsError('Immutable seal')
    old=HERE/'acquisition/acquisition_02/2016_2021_attempt1.geojson';receipt=old.with_suffix('.receipt.json')
    dump(p,dict(sealed_utc=stamp(),script_sha256=sha(__file__),protocol_sha256=sha(HERE/'PROTOCOL.json'),amendments={n:sha(HERE/n) for n in ['AMENDMENT_DOWNLOAD_01.md','AMENDMENT_DOWNLOAD_02.md']},reused_body=dict(path=old.relative_to(HERE).as_posix(),sha256=sha(old),original_receipt_path=receipt.relative_to(HERE).as_posix(),original_receipt_sha256=sha(receipt)),scientific_analysis_performed=False))
    print(p.read_text())
def acquire(run_id):
    frozen=json.loads((HERE/'SEAL_RESUME_V3.json').read_text());assert frozen['script_sha256']==sha(__file__) and frozen['protocol_sha256']==sha(HERE/'PROTOCOL.json')
    for n,h in frozen['amendments'].items():assert sha(HERE/n)==h
    target=HERE/'acquisition'/run_id
    if target.exists():raise FileExistsError('Never overwrite evidence')
    target.mkdir(parents=True);responses=[]
    old=frozen['reused_body'];body=HERE/old['path'];oldreceipt=HERE/old['original_receipt_path']
    assert sha(body)==old['sha256'] and sha(oldreceipt)==old['original_receipt_sha256']
    original=json.loads(oldreceipt.read_text());data=body.read_bytes();newbody=target/'2016_2021_reused.geojson';newbody.write_bytes(data)
    r=dict(label='2016_2021',status='PASS',validation_kind='post-acquisition schema validation only; original receipt remains FAIL',new_network_request=False,original_receipt_status=original['status'],original_http_status=200,original_receipt=old,started_utc=original['started_utc'],completed_utc=original['completed_utc'],validated_utc=stamp(),url=original['url'],headers=original['headers'],body_file=newbody.name,body_sha256=sha(newbody),bytes=len(data),**validate(data))
    dump(target/'2016_2021_validation.receipt.json',r);responses.append(r)
    query=next(q for q in json.loads((HERE/'PROTOCOL.json').read_text())['queries'] if q['label']=='2021_2026')
    for attempt in range(1,4):
        prefix=f'2021_2026_attempt{attempt}';r=dict(label='2021_2026',method='GET',url=query['url'],started_utc=stamp(),new_network_request=True,attempt=attempt)
        try:
            request=urllib.request.Request(query['url'],headers={'User-Agent':'Seismic_Data_Geosciences academic reproducibility audit','Accept':'application/json'})
            with urllib.request.urlopen(request,timeout=45) as response:
                data=response.read();r.update(http_status=response.status,headers=dict(response.headers.items()),final_url=response.url)
            body=target/(prefix+'.geojson');body.write_bytes(data)
            r.update(status='PASS',body_file=body.name,body_sha256=sha(body),bytes=len(data),completed_utc=stamp(),**validate(data))
        except Exception as e:
            r.update(status='FAIL',error_type=type(e).__name__,error=str(e),completed_utc=stamp())
            if isinstance(e,urllib.error.HTTPError):
                body=target/(prefix+'.error');body.write_bytes(e.read());r.update(http_status=e.code,error_body_sha256=sha(body),headers=dict(e.headers.items()))
        dump(target/(prefix+'.receipt.json'),r);responses.append(r)
        if r['status']=='PASS':break
        if attempt<3:time.sleep(2)
    result=dict(status='PASS' if r['status']=='PASS' else 'FAIL',responses=responses,completed_utc=stamp(),protocol_sha256=sha(HERE/'PROTOCOL.json'),download_seal_sha256=sha(HERE/'SEAL_RESUME_V3.json'),no_atomic_snapshot_claim=True,no_catalogue_analysis_performed=True)
    dump(target/'MANIFEST.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='responses'}|dict(responses=[{k:r.get(k) for k in ['label','status','features','bytes','new_network_request']} for r in responses]),indent=2))
    if result['status']!='PASS':raise RuntimeError('Missing acquisition interval')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','acquire']);p.add_argument('--run-id',default='acquisition_03');a=p.parse_args();seal() if a.action=='seal' else acquire(a.run_id)
