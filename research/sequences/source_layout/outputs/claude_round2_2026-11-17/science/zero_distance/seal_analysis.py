from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=HERE/'ANALYSIS_SEAL.json'
    if target.exists():raise FileExistsError('Do not reseal')
    tests=json.loads((HERE/'TESTS.json').read_text());assert tests['status']=='PASS' and tests['runner_sha256']==sha(HERE/'run_zero_distance.py')
    result=dict(sealed_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=sha(HERE/'run_zero_distance.py'),tests_sha256=sha(HERE/'TESTS.json'),protocol_sha256=sha(HERE/'PROTOCOL.json'),catalog_helper_sha256=sha(HERE.parent/'catalog/run_catalog.py'),scientific_zero_counts_not_read=True,cpu_gate='WAIT explicit root GO')
    target.write_text(json.dumps(result,indent=2)+'\n');print('ANALYSIS_SEAL.json SHA256:',sha(target));print('runner SHA256:',result['runner_sha256'])
if __name__=='__main__':main()
