"""Seal predefined phase1 sources/inputs before timing, using stdlib only."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,subprocess
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    target=BASE/'EXECUTION_SEAL.json'
    if target.exists():raise FileExistsError('Immutable seal already exists')
    sources=[BASE/name for name in ['PROTOCOL_COMPUTE.md','common.py','prepare_inputs.py','native_worker.py',
               'run_native_benchmark.py','run_large_parent_study.py','node_parent_worker.cjs','seal_execution.py']]
    old=ROOT/'outputs/claude_response_2026-11-16/index'
    sources += [old/name for name in ['spherical_weighted_v2.py','cached_balanced_exhaustive_v2.py','windows_memory.py']]
    sources += [ROOT/'system/dist/sequences/nearest-parent.js',ROOT/'system/dist/sequences/data/inputs_3_5.json']
    sources += list((BASE/'inputs').glob('*'))+[BASE/'browser_harness/inputs_ssn_m35.json',BASE/'browser_harness/nearest-parent.js']
    input_manifest=json.loads((BASE/'inputs/MANIFEST.json').read_bytes())
    for key in ['sources','original_benchmark','browser_source']:
        values=input_manifest[key];values=values if isinstance(values,list) else [values]
        sources += [ROOT/item['path'] for item in values]
    sources=sorted(set(p.resolve() for p in sources))
    for p in [BASE/name for name in ['common.py','prepare_inputs.py','native_worker.py','run_native_benchmark.py','run_large_parent_study.py','seal_execution.py']]:
        ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    node=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/bin/node.exe')
    subprocess.run([str(node),'--check',str(BASE/'node_parent_worker.cjs')],check=True,capture_output=True)
    entries=[]
    for path in sources:
        assert path.is_relative_to(ROOT) and path.is_file()
        entries.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
    value=dict(status='SEALED_BEFORE_ANY_NEW_MEASUREMENT',created_utc=datetime.now(timezone.utc).isoformat(),
       protocol_sha256=sha(BASE/'PROTOCOL_COMPUTE.md'),phase='1:matched native and large observed-parent study',entries=entries,
       benchmark_cells=81,benchmark_all_threads=1,benchmark_repetitions=3,
       runtime=dict(python_executable=__import__('sys').executable,node_executable=str(node)),
       cpu_status='WAIT_ROOT_EXCLUSIVE_GO',results_exist=False,
       later_phases='Browser and comparator definitions fixed in protocol; their adapter glue will have a separate pre-execution code seal and chronology statement. No choice based on performance outcomes is permitted.')
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),entries=len(entries),status=value['status'])))
if __name__=='__main__':main()
