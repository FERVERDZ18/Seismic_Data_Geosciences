"""Seal later-stage glue before its execution; prior native chronology explicit."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,hashlib,json,subprocess,shutil
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def entry(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def main():
    browser=BASE/'browser_harness';comparators=BASE/'comparators'
    if (BASE/'BROWSER_EXECUTION_SEAL.json').exists() or (BASE/'COMPARATOR_EXECUTION_SEAL.json').exists():raise FileExistsError('Later seals immutable')
    raw=ROOT/'outputs/claude_round2_2026-11-17/audit/primary_sources/eqclustering_393a02db.py'
    assert sha(raw)=='ad65da59bcf65ecdae300adacc4dff8a1e5537252c33e6ddacc1338de2f2db0b'
    original=raw.read_text(encoding='utf-8')
    changes=[('datetime.datetime(1970, 01, 01, 00, 00, 00)','datetime.datetime(1970, 1, 1, 0, 0, 0)'),('np.Inf','np.inf'),('np.NaN','np.nan')]
    adapted=original
    counts={}
    for old,new in changes:
        counts[old]=adapted.count(old);assert counts[old]>0
        adapted=adapted.replace(old,new)
    ast.parse(adapted)
    target=comparators/'eqclustering_python3_constants.py'
    if target.exists():raise FileExistsError(target)
    target.write_text(adapted,encoding='utf-8')
    patch=comparators/'PYTHON3_CONSTANT_COMPATIBILITY.diff'
    patch.write_text(''.join(difflib.unified_diff(original.splitlines(True),adapted.splitlines(True),fromfile='eqclustering393a02db-original',tofile='python3-syntax-constants-only')),encoding='utf-8')
    notice=ROOT/'outputs/claude_round2_2026-11-17/audit/primary_sources/eqclustering_NOTICE.txt'
    shutil.copyfile(notice,comparators/'NOTICE_eqclustering.txt')
    write(comparators/'ADAPTATION.json',dict(raw=entry(raw),adapted=entry(target),diff=entry(patch),replacements=counts,
      numerical_algorithm_changed=False,year365p35_preserved=True,acos_without_clamp_preserved=True,algorithm_executed=False))
    native=BASE/'native_benchmark_01/MANIFEST.json'
    known=json.loads(native.read_bytes()) if native.exists() else {'cells':[],'status':'NOT_STARTED'}
    chronology=dict(native_status_at_glue_seal=known['status'],native_cells_already_observed=len(known['cells']),
       statement='Later browser/comparator glue completed after these native observations. All N/repetition/cap/comparator/semantic choices were fixed in PROTOCOL_COMPUTE before the first native result; no choice changed from those outcomes.')
    node=Path('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/bin/node.exe')
    for path in [browser/'worker.js',browser/'harness.js']:
        subprocess.run([str(node),'--check',str(path)],check=True,capture_output=True)
    assets=[browser/name for name in ['inputs_ssn_m35.json','nearest-parent.js','worker.js','harness.js','index.html']]
    write(browser/'BROWSER_MANIFEST.json',dict(schema='private-browser-input-contract/1',assets=[dict(file=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in assets],
       sizes=[2000,10000,50000,170880],repetitions=3,backends=['reference','kd'],wall_cap_seconds=120,planned_cells=24))
    for kind,files in [('BROWSER',assets+[browser/'BROWSER_MANIFEST.json']),('COMPARATOR',[BASE/'comparator_worker.py',BASE/'run_comparators.py',*comparators.glob('*')])]:
        files += [BASE/'PROTOCOL_COMPUTE.md',BASE/'inputs/MANIFEST.json',BASE/'common.py']
        if kind=='COMPARATOR':
            methods=ROOT/'outputs/claude_response_2026-11-16/methods'
            files += list((methods/'authors_2013_exact/eq_cluster').glob('*.m'))
            files += [methods/'octave_wrappers'/name for name in ['waitbar.m','set.m','close.m']]
            files += [ROOT/'outputs/claude_response_2026-11-16/runtime/octave-11.3.0-w64/mingw64/bin/octave-cli.exe']
            for path in [BASE/'comparator_worker.py',BASE/'run_comparators.py']:ast.parse(path.read_text(encoding='utf-8'))
        files=sorted(set(p.resolve() for p in files if p.is_file()))
        value=dict(status='SEALED_BEFORE_THIS_PHASE_EXECUTION',created_utc=datetime.now(timezone.utc).isoformat(),phase=kind,
            protocol_sha256=sha(BASE/'PROTOCOL_COMPUTE.md'),entries=[entry(p) for p in files],chronology=chronology,
            cpu_status='WAIT_SEPARATE_ROOT_GO',results_of_this_phase_exist=False)
        seal=BASE/(kind+'_EXECUTION_SEAL.json');write(seal,value)
        print(json.dumps(dict(phase=kind,path=seal.relative_to(ROOT).as_posix(),sha256=sha(seal),entries=len(files))))
if __name__=='__main__':main()
