from pathlib import Path
import run_zero_distance as z
np=z.np
def test_first_is_not_zero_edge():
    score,mask=z.score_and_zero(np.array([-1,0,1]),np.array([np.nan,1.,1.]),np.array([np.nan,0.,.1]))
    assert mask.tolist()==[False,True,False] and np.isnan(score[0]) and np.isneginf(score[1])
def test_frozen_edge_deletion_no_alternative():
    p=np.array([-1,0,1]);TN=np.array([np.nan,1.,.1]);RN=np.array([np.nan,0.,.001]);m=np.array([6.,4.,3.]);t=np.array([0.,1.,2.]);ids=['a','b','c']
    score,zero=z.score_and_zero(p,TN,RN);a=z.cat.families_from_cut(p,score,m,t,ids,-3.,inclusive=True)
    deleted=p.copy();deleted[zero]=-1;b=z.cat.families_from_cut(deleted,score,m,t,ids,-3.,inclusive=True)
    assert deleted.tolist()==[-1,-1,1] and p.tolist()==[-1,0,1]
    assert a['roles'].tolist()==[1,2,2] and b['roles'].tolist()==[0,1,2]
    assert b['component_root_index'].tolist()==[0,1,1]
def test_no_zero_is_identity():
    p=np.array([-1,0]);TN=np.array([np.nan,1.]);RN=np.array([np.nan,.001]);score,zero=z.score_and_zero(p,TN,RN)
    assert not zero.any()
    a=z.cat.families_from_cut(p,score,[6.,4.],[0.,1.],['a','b'],-3.,inclusive=True)
    b=z.cat.families_from_cut(np.where(zero,-1,p),score,[6.,4.],[0.,1.],['a','b'],-3.,inclusive=True)
    assert np.array_equal(a['roles'],b['roles'])
if __name__=='__main__':
    tests=[test_first_is_not_zero_edge,test_frozen_edge_deletion_no_alternative,test_no_zero_is_identity]
    for t in tests:t()
    z.cat.dump(Path(__file__).parent/'TESTS.json',dict(status='PASS',tests=[t.__name__ for t in tests],runner_sha256=z.cat.sha(Path(z.__file__)),test_sha256=z.cat.sha(Path(__file__)),retained_catalogue_computation=False))
    print('PASS: three zero-edge semantic fixtures; no retained-data computation')
