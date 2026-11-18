"""Tiny fixtures only; run after root's timing window to avoid import interference."""
from pathlib import Path
import run_south_control as s
import support_masks as support
def test_boundaries():
    row=dict(record_id='a',source='ssn',event_id='',time_utc='2016-01-01T00:00:00Z',latitude='13.9',longitude='-93',depth_km='10',magnitude='4.5',magnitude_type='')
    assert s.inside(row,12) and not s.inside(row,14)
    assert not s.inside({**row,'time_utc':'2026-01-01T00:00:00Z'},12)
    assert s.inside({**row,'latitude':'14'},14)
def test_time_and_snapshot_identity():
    assert s.iso_ms(1451606400123)=='2016-01-01T00:00:00.123Z'
    a=dict(record_id='same',source='ssn',event_id='',time_utc='2016-01-01T00:00:00Z',latitude='14',longitude='-93',depth_km='10',magnitude='4.5',magnitude_type='')
    b={**a,'time_utc':'2016-01-01T00:00:00.000Z','magnitude':'4.50'}
    assert s.signature(a)==s.signature(b)
    assert s.check_SSN([a],[b])['rows']==1
    try:s.check_SSN([a],[{**b,'magnitude':'4.6'}])
    except AssertionError:pass
    else:raise AssertionError('Changed source measure must fail identity check')
def test_transported_cut_keeps_parents():
    np=s.np;p=dict(m=np.array([6.,4.]),t_year=np.array([0.,1.]),ids=['a','b'])
    x=dict(parent_index=np.array([-1,0]),TN=np.array([np.nan,.01]),RN=np.array([np.nan,.001]))
    a=s.cat.classify_case(p,x,-5.5);b=s.cat.classify_case(p,x,-4.5)
    assert a['roles'].tolist()==[0,0] and b['roles'].tolist()==[1,2]
    assert x['parent_index'].tolist()==[-1,0]
def test_support_cell_boundaries_and_development_only():
    a=dict(record_id='a',longitude='-86',latitude='33',time_utc='2020-12-31T00:00:00Z',magnitude='3.5')
    assert support.cell_key(a,1)==(93,122)
    assert support.cell_key(a,.5)==(187,245)
    assert support.cell_key({**a,'longitude':'-118','latitude':'12'},2)==(31,51)
    b={**a,'record_id':'b','time_utc':'2021-01-01T00:00:00Z'}
    keys,counts,common=support.build_mask({'ssn':[a],'usgs':[b]},1)
    assert not common
    keys,counts,common=support.build_mask({'ssn':[a],'usgs':[{**b,'time_utc':'2020-01-01T00:00:00Z'}]},1)
    assert len(common)==1
    feature=support.cell_feature(next(iter(common)),1,counts)
    assert feature['geometry']['coordinates'][0]==[[-87,32],[-86,32],[-86,33],[-87,33],[-87,32]]
if __name__=='__main__':
    tests=[test_boundaries,test_time_and_snapshot_identity,test_transported_cut_keeps_parents,test_support_cell_boundaries_and_development_only]
    for t in tests:t()
    s.cat.dump(Path(__file__).parent/'TESTS.json',dict(status='PASS',tests=[t.__name__ for t in tests],runner_sha256=s.cat.sha(Path(s.__file__)),support_module_sha256=s.cat.sha(Path(support.__file__)),test_script_sha256=s.cat.sha(__file__),retained_catalogue_computation=False))
    print('PASS: four southern-control semantic fixtures; no catalogue computation')
