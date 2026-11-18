"""Execute the fixed v3 scientific replay in one process, no publication actions."""
from pathlib import Path
import hashlib
import importlib
import json
import os
import sys
import time

HERE=Path(__file__).resolve().parent
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'numba_cache_v3'))
os.environ.setdefault('MPLCONFIGDIR',str(HERE/'matplotlib_cache_v3'))
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))


def main():
    receipt=HERE/'V3_EXECUTION_RECEIPT.json'
    if receipt.exists():raise FileExistsError('Do not overwrite an execution receipt')
    protocol=json.loads((HERE/'COSINE_V3_REPLAY_PROTOCOL.json').read_text(encoding='utf-8'))
    for filename,entry in protocol['script_changes'].items():
        if hashlib.sha256((HERE/filename).read_bytes()).hexdigest()!=entry['new_script_sha256']:
            raise ValueError('Prepared scientific script changed: '+filename)
    phases=[]
    for filename in protocol['execution_order']:
        started=time.perf_counter()
        print('BEGIN_V3_PHASE '+filename,flush=True)
        importlib.import_module(Path(filename).stem).main()
        phases.append(dict(script=filename,elapsed_seconds=time.perf_counter()-started,status='completed'))
        print('END_V3_PHASE '+filename,flush=True)
    report=dict(status='completed',protocol_sha256=hashlib.sha256((HERE/'COSINE_V3_REPLAY_PROTOCOL.json').read_bytes()).hexdigest(),
                index_sha256=hashlib.sha256((HERE.parent/'index/spherical_weighted_v2.py').read_bytes()).hexdigest(),
                phases=phases,not_a_performance_benchmark=True,old_outputs_preserved=True)
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
