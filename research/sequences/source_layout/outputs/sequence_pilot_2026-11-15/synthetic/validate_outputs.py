"""Independent standard-library checks of written controls and parentage tables."""
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
import math
from pathlib import Path

BASE=Path(__file__).resolve().parent
PILOT=BASE.parent
ANCHOR=datetime(2001,1,1,tzinfo=timezone.utc)


def read(path):
    with path.open(encoding='utf-8',newline='') as stream:return list(csv.DictReader(stream))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=json.loads((BASE/'SYNTHETIC_MANIFEST.json').read_text(encoding='utf-8'))
    assert len(manifest['cases'])==31
    assert sha(PILOT/'PROTOCOL_STAGE_2.md')==manifest['protocol_stage2_sha256']
    checks=[];immigrants={}
    for case in manifest['cases']:
        folder=PILOT/case['path'];metadata=json.loads((folder/'catalogue.json').read_text(encoding='utf-8'))
        assert sha(folder/'catalogue.json')==case['metadata_sha256']
        for name,record in metadata['files'].items():
            assert sha(folder/name)==record['sha256'] and (folder/name).stat().st_size==record['bytes']
        events=read(folder/'events.csv');observed=read(folder/'events_m4p1.csv');truth=read(folder/'truth.csv')
        assert len(events)==len(truth)==case['total']
        assert not({'direct_parent_id','root_id','generation','latent_creation_index'}&events[0].keys())
        by_id={row['record_id']:row for row in truth};assert len(by_id)==len(truth)
        event_by_id={row['record_id']:row for row in events};assert event_by_id.keys()==by_id.keys()
        assert [row['record_id'] for row in observed]==[row['record_id'] for row in events if float(row['magnitude'])>=4.1]
        previous=None;roots={}
        for event in events:
            value=float(event['t_days']);stamp=datetime.fromisoformat(event['time_utc'].replace('Z','+00:00'))
            assert -365<=value<365 and 3.5<=float(event['magnitude'])<=6.5
            assert abs((stamp-(ANCHOR+timedelta(days=value))).total_seconds())<=1e-6
            assert event['is_eval']==str(int(value>=0))
            ordering=(stamp,event['record_id']);assert previous is None or ordering>=previous;previous=ordering
        for row in sorted(truth,key=lambda x:float(x['t_days'])):
            uid=row['record_id'];parent=row['direct_parent_id'];generation=int(row['generation'])
            if parent:
                assert parent in by_id and float(by_id[parent]['t_days'])<float(row['t_days'])
                assert generation==int(by_id[parent]['generation'])+1 and row['root_id']==roots[parent]
                roots[uid]=roots[parent];assert row['is_immigrant']=='0'
            else:
                roots[uid]=uid;assert row['root_id']==uid and generation==0 and row['is_immigrant']=='1'
            assert row['retained_m4p1']==str(int(float(event_by_id[uid]['magnitude'])>=4.1))
        background=[]
        for row in sorted(truth,key=lambda x:int(x['latent_creation_index'])):
            if row['is_immigrant']=='1':
                event=event_by_id[row['record_id']]
                background.append(tuple(float(event[key]) for key in ('t_days','x_km','y_km','magnitude')))
        immigrants[(metadata['seed'],metadata['scenario'])]=background
        checks.append({'case_id':case['case_id'],'status':'PASS','rows':len(events),'observed_rows':len(observed),'parent_root_graph_checked':True})
    for seed in range(20261120,20261130):
        assert immigrants[(seed,'etas')]==immigrants[(seed,'n0')]
        before=immigrants[(seed,'n0')];after=immigrants[(seed,'n1')];assert len(before)==len(after)
        for a,b in zip(before,after):
            assert a[1:]==b[1:]
            start=-365. if a[0]<0 else 0.;u=(a[0]-start)/365
            expected=start+365*(2*u if u<.25 else .5+(u-.25)/1.5)
            assert b[0]==expected and (a[0]>=0)==(b[0]>=0)
    result={'schema':'seismic-synthetic-written-output-validation/1','status':'PASS','cases':checks,
        'manifest_sha256':sha(BASE/'SYNTHETIC_MANIFEST.json'),'paired_immigrants_exact':True,'n1_time_warp_exact':True,
        'observed_membership_exact':True,'detector_input_contains_parentage':False,'detectors_executed':False}
    (BASE/'VALIDATION_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','cases':len(checks),'rows':sum(row['rows'] for row in checks),'parents_roots_utc_observation_pairing_verified':True}))


if __name__=='__main__':main()
