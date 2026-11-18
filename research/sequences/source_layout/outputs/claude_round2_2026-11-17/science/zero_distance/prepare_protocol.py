from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').exists())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'PROTOCOL.json'
    if out.exists():raise FileExistsError('Never reseal')
    base=HERE.parent/'catalog/runs/run_01';cases=[];inputs=[]
    manifest=json.loads((base/'MANIFEST.json').read_text());assert manifest['status']=='PASS'
    for d in sorted((base/'cases').iterdir()):
        meta=json.loads((d/'metadata.json').read_text());cases.append(dict(source=meta['source'],w=meta['w'],directory=d.relative_to(ROOT).as_posix()))
        inputs.extend(d/n for n in ['metadata.json','arrays.npz','ids.json','rows.json'])
    optional=[]
    for source in ['ssn','usgs']:
        p=ROOT/f'outputs/claude_response_2026-11-16/catalog_design/web_inputs/nn_parity/round_04/{source}_3_5_js.json'
        if p.exists():optional.append(dict(source=source,path=p.relative_to(ROOT).as_posix()));inputs.append(p)
        inputs.append(ROOT/f'outputs/sequence_pilot_2026-11-15/inputs/{source}.csv')
    inputs.extend([ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json',ROOT/'outputs/claude_response_2026-11-16/catalog_design/scientific_diagnostics.compact.json'])
    result=dict(schema='zero-distance-postreview-diagnostic/1',sealed_utc=datetime.now(timezone.utc).isoformat(),md_sha256=sha(HERE/'PROTOCOL.md'),cases=cases,optional_M3_5_w1=optional,inputs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in inputs],scientific_counts_not_read=True,cpu_gate='WAIT root',parent_edge_deletion_rule='parent>=0 and (RN==0 or log10(TN)+log10(RN)==-inf)',no_alternative_parent=True,no_refit=True,no_epsilon=True)
    out.write_text(json.dumps(result,indent=2)+'\n');print('PROTOCOL.json SHA256:',sha(out));print('PROTOCOL.md SHA256:',result['md_sha256'])
if __name__=='__main__':main()
