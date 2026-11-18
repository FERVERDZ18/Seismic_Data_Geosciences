"""Independent stdlib arithmetic and receipt checks; no kernels or bootstrap runs."""
from pathlib import Path
from datetime import datetime
from collections import Counter
import csv,hashlib,json,math
HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/run_01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def check_matrix(z):
    matrix=z['matrix_first_rows_second_columns'];n=sum(map(sum,matrix));assert n==z['n']
    rows=list(map(sum,matrix));cols=[sum(matrix[i][j] for i in range(3)) for j in range(3)]
    assert rows==z['first_marginal'] and cols==z['second_marginal']
    if n:
        observed=sum(matrix[k][k] for k in range(3))/n;assert observed==z['agreement']
        expected=sum(a*b for a,b in zip(rows,cols))/n**2
        if expected<1:assert abs(z['kappa']-(observed-expected)/(1-expected))<1e-14
    else:assert z['agreement'] is None
    for k,(label,c) in enumerate(z.get('per_class',{}).items()):
        union=rows[k]+cols[k]-matrix[k][k];total=rows[k]+cols[k]
        assert c['union']==union and c['intersection']==matrix[k][k]
        assert c['jaccard']==(matrix[k][k]/union if union else None)
        assert c['symmetric_F1']==(2*matrix[k][k]/total if total else None)
def main():
    m=load(RUN/'MANIFEST.json');assert m['status']=='PASS'
    for r in m['output_files']:assert sha(RUN/r['path'])==r['sha256'],r['path']
    metrics=load(RUN/'WEIGHT_THRESHOLD_METRICS.json');count=0
    for c in metrics.values():
        if c['status']!='computed':continue
        for z in c['periods'].values():check_matrix(z);count+=1
    coverage=load(RUN/'COVERAGE.json');assert sum(coverage['candidate_cut_states'].values())==coverage['candidate_assignments']==2989
    for s,n in coverage['native_selected'].items():assert sum(coverage['selected_endpoint_state_counts'][s].values())==n
    retained=load(RUN/'RETAINED_TABLES_PROVENANCE.json');assert len(retained['factorial'])==16 and len(retained['annual'])==10
    assert sum(v['n'] for v in retained['annual'].values())==889
    for z in load(RUN/'NINE_WINDOW_NN.json'):check_matrix(z['metrics'])
    alaska=load(RUN/'ALASKA_TEMPORAL_METHOD_COMPARISON.json')
    assert all(alaska['GK_indexed_exhaustive'].values())
    for z in alaska['periods'].values():check_matrix(z)
    # The master and execution gate existed before the scientific batch.
    science=HERE.parent;gate=load(science/'CATALOG_GATE_01.json')
    assert gate['master_01_sha256']==sha(science/'MASTER_PROTOCOL_01.json')
    assert datetime.fromisoformat(gate['created_utc'])<datetime.fromisoformat(m['started_utc'])
    tests=load(HERE/'TESTS.json');assert tests['status']=='PASS' and tests['runner_sha256']==m['runner_sha256']
    result=dict(status='PASS',receipt_hash_checks=len(m['output_files']),independent_point_matrices=count,nine_window_matrices=9,
        original_candidate_states_and_endpoint_denominators=True,annual_10_and_factorial_16=True,alaska_indexed_exhaustive_and_temporal_matrices=True,
        master_precedes_execution=True,fixture_runner_matches_execution=True,manifest_sha256=sha(RUN/'MANIFEST.json'),
        master_sha256=sha(science/'MASTER_PROTOCOL_01.json'),gate_sha256=sha(science/'CATALOG_GATE_01.json'),verifier_sha256=sha(Path(__file__)))
    (HERE/'QC.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
