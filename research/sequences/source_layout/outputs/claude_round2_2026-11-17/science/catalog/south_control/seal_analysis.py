"""Bind tested private code and fixed acquired bytes, before scientific execution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=HERE/'ANALYSIS_SEAL.json'
    if target.exists():raise FileExistsError('Never reseal a completed scientific protocol')
    tests=json.loads((HERE/'TESTS.json').read_text());assert tests['status']=='PASS'
    assert tests['runner_sha256']==sha(HERE/'run_south_control.py')
    assert tests['support_module_sha256']==sha(HERE/'support_masks.py')
    names=['PROTOCOL.md','PROTOCOL.json','INPUTS.json','SEAL.json','AMENDMENT_DOWNLOAD_01.md','AMENDMENT_DOWNLOAD_02.md','AMENDMENT_SUPPORT_01.md','SUPPORT_PROTOCOL.json','SEAL_RESUME_V3.json','TESTS.json','run_south_control.py','support_masks.py','../run_catalog.py','../VENDOR.json','../INPUTS.json','../PROTOCOL.json','../PROTOCOL.md','../AMENDMENT_01.md','../AMENDMENT_02.md']
    result=dict(schema='round2-south-control-tested-analysis-seal/1',sealed_utc=datetime.now(timezone.utc).isoformat(),runner_sha256=sha(HERE/'run_south_control.py'),frozen_files={n:sha(HERE/n) for n in names},acquisition_manifest_sha256=sha(HERE/'acquisition/acquisition_03/MANIFEST.json'),analysis_results_created=False,cpu_gate='WAIT root explicit go-ahead')
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('ANALYSIS_SEAL.json SHA256:',sha(target));print('Runner SHA256:',result['runner_sha256'])
if __name__=='__main__':main()
