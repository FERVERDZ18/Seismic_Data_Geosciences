"""Small semantic fixtures, no retained catalogue computation."""
from pathlib import Path
import json
import run_catalog as r
np=r.np

def test_metric():
    z=r.metric([0,0,1,2],[0,1,1,2])
    assert z['agreement']==.75
    assert z['per_class'][r.LABELS[0]]['jaccard']==.5
    assert z['per_class'][r.LABELS[1]]['symmetric_F1']==2/3
    assert r.metric([],[])['agreement'] is None
    assert r.metric([],[])['partition']['ARI'] is None

def test_units_context_bridge():
    # a0 and a2 share context a1; b0 and b1 are joined by their native group.
    ua=r.shared_units(np.array([0,0,0,3]),np.array([0,0,2]),np.array([0,2,3]),np.array([0,1,2]))
    assert ua.tolist()==[0,0,1]
    ub=r.shared_units(np.array([0,1]),np.array([0,0]),np.array([0,1]),np.array([0,1]))
    assert len(set(ub))==1

def test_bootstrap():
    a=np.array([0,0,1,2]);b=np.array([0,1,1,2]);u=np.array([0,0,1,2]);mask=np.ones(4,dtype=bool)
    plan=r.bootstrap_plan(u,mask,30,1234)
    assert plan['largest_pair_fraction']==.5 and plan['effective_units']==1/(.5**2+.25**2+.25**2)
    assert plan['fragile']
    x=r.bootstrap_values(a,b,u,mask,plan);same=r.intervals(x,x)
    assert same['intervals']['paired_agreement_difference_vs_w1_delta0']['percentile_2_5']==0
    assert same['intervals']['paired_agreement_difference_vs_w1_delta0']['percentile_97_5']==0
    restricted=r.bootstrap_plan(u,np.array([False,False,True,True]),30,1234)
    assert restricted['sizes'].tolist()==[1,1]
    assert r.bootstrap_plan(u,np.zeros(4,dtype=bool),10,1)['status']=='not_estimable'

def test_inclusive_canonical():
    p=dict(m=np.array([6.,4.,3.]),t_year=np.array([0.,1.,2.]),ids=['a','b','c'])
    result=dict(parent_index=np.array([-1,0,1]),TN=np.array([np.nan,.01,.1]),RN=np.array([np.nan,.001,.001]))
    z=r.classify_case(p,result,-5.)
    assert z['strong_link_mask'].tolist()==[False,True,False]
    assert z['roles'].tolist()==[1,2,0]
    assert z['component_size'].tolist()==[2,2,1]

def test_cross_baseline_unit_diagnostic():
    z=r.unit_spans(np.array([0,0,0,3]),np.array([0,0,1,2]))
    assert z['families_spanning_multiple_baseline_units']==1
    assert z['maximum_baseline_units_in_one_family']==2
    assert z['baseline_resampling_does_not_capture_new_cross_unit_dependence']

if __name__=='__main__':
    tests=[test_metric,test_units_context_bridge,test_bootstrap,test_inclusive_canonical,test_cross_baseline_unit_diagnostic]
    for test in tests:test()
    out=dict(status='PASS',semantic_tests=[t.__name__ for t in tests],retained_catalogue_computations=False,script_sha256=r.sha(__file__),runner_sha256=r.sha(Path(r.__file__)))
    r.dump(Path(__file__).parent/'TESTS.json',out)
    print(json.dumps(out,indent=2))
