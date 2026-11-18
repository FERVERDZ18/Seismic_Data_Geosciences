"""Add initial-load observations before any browser execution; never run kernels."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def entry(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def main():
    prior = BASE / 'browser_harness'
    target = prior / 'v2'
    if target.exists() or (BASE / 'BROWSER_EXECUTION_SEAL_V2.json').exists():
        raise FileExistsError('Preserve all previous browser preparations')
    native = json.loads((BASE / 'native_benchmark_01/MANIFEST.json').read_bytes())
    stamp = datetime.now(timezone.utc).isoformat()
    amendment = BASE / 'AMENDMENT_BROWSER_LOAD_V2.md'
    if amendment.exists():
        raise FileExistsError(amendment)
    amendment.write_text(f'''# Enmienda previa al navegador: fases de carga inicial

Fecha UTC: {stamp}. Antes de toda apertura/ejecución del harness en navegador.
Se conocen {len(native['cells'])} celdas nativas completadas; estado nativo
{native['status']}. La solicitud del coordinador se recibió después de examinar
esos tiempos nativos y antes de observar resultados de navegador.

El protocolo D ya separaba carga inicial y cálculo del Worker. La versión1
excluía fetch/hash/decode/parse del reloj del núcleo, pero no guardaba sus costes
numéricos. Se conserva intacta con su sello. La versión2 añade observaciones de
performance.now para fetch hasta resolución, lectura de bytes, SHA256, UTF8
decode, JSON parse y comprobación de estructura/conteo. Guarda cada asset y
el total inicial; no convierte estas fases en paint o latencia de interfaz.

No cambian los24 ensayos, N={{2000,10000,50000,170880}}, tres réplicas, orden,
warm-up64, dos backends, límite120s, filas, kernel, tipos, outputs o criterios
de paridad. El Worker sólo cambia la ruta relativa del import al mismo JS
numérico. La entrada grande se lee de la copia V1 idéntica y sellada; no se
duplica ni se reescribe. No se ejecutó ningún cálculo del navegador.

La página debe permanecer visible durante el lote. Se registran observaciones
de visibilityState y sus cambios; no se mide ni garantiza ausencia de
suspensión del sistema operativo. No se mide paint, memoria pico del Worker
ni un tiempo puro de transferencia. El wall de celda y el tiempo del núcleo
siguen siendo observaciones separadas.

El validadorV2 únicamente apunta al manifiestoV2 y comprueba estos metadatos
adicionales; sus pruebas numéricas, tolerancias y tratamiento de censuras se
conservan idénticos. Los sellosV1 y sus archivos permanecen preservados.
''', encoding='utf-8')
    target.mkdir()
    html = (prior / 'index.html').read_text(encoding='utf-8')
    html = html.replace('Private nearest-parent browser benchmark', 'Private nearest-parent browser benchmark V2')
    html = html.replace('<p>Four sizes', '<p>Initial fetch/read/hash/decode/parse/validation observations are recorded separately. Keep this tab visible; paint and OS suspension are not measured.</p>\n<p>Four sizes')
    (target / 'index.html').write_text(html, encoding='utf-8')
    worker = (prior / 'worker.js').read_text(encoding='utf-8')
    assert worker.count("importScripts('nearest-parent.js');") == 1
    worker = worker.replace("importScripts('nearest-parent.js');", "importScripts('../nearest-parent.js');")
    (target / 'worker.js').write_text(worker, encoding='utf-8')
    harness = (prior / 'harness.js').read_text(encoding='utf-8')
    old_load = harness[harness.index('async function load(){'):harness.index('\nfunction oneCell(spec)')]
    new_load = '''let initialLoad;
const visibilityStarted=performance.now(),visibilityObservations=[{elapsed_ms:0,state:document.visibilityState}];
document.addEventListener('visibilitychange',()=>visibilityObservations.push({elapsed_ms:performance.now()-visibilityStarted,state:document.visibilityState}));
async function load(){
 const started=performance.now();
 initialLoad={started_utc:new Date().toISOString(),initial_visibility:document.visibilityState,assets:[],
   scope:'Initial byte fetch/read/SHA256/UTF8 decode/JSON parse/structure validation only; separate from Worker kernels, cell wall and paint',
   paint_measured:false,worker_peak_memory_measured:false,transfer_time_isolated:false,
   os_suspension:'Not measured or excluded; keep tab visible; user/OS processes uncontrolled'};
 let clock=performance.now();const manifestResponse=await fetch('BROWSER_MANIFEST.json');
 const manifestFetch=performance.now()-clock;if(!manifestResponse.ok)throw Error('HTTP '+manifestResponse.status+' manifest');
 clock=performance.now();const manifestBytes=await manifestResponse.arrayBuffer();const manifestRead=performance.now()-clock;
 clock=performance.now();const manifestText=new TextDecoder().decode(manifestBytes);const manifestDecode=performance.now()-clock;
 clock=performance.now();manifest=JSON.parse(manifestText);const manifestParse=performance.now()-clock;
 clock=performance.now();
 if(manifest.planned_cells!==24||manifest.wall_cap_seconds!==120||manifest.repetitions!==3||JSON.stringify(manifest.sizes)!==JSON.stringify(sizes))throw Error('Unexpected predefined plan');
 const manifestValidation=performance.now()-clock;
 initialLoad.manifest={bytes:manifestBytes.byteLength,fetch_resolution_ms:manifestFetch,body_read_ms:manifestRead,
   utf8_decode_ms:manifestDecode,json_parse_ms:manifestParse,validation_ms:manifestValidation};
 for(const item of manifest.assets){
   const observed={file:item.file,bytes:item.bytes};
   clock=performance.now();const response=await fetch(item.file);observed.fetch_resolution_ms=performance.now()-clock;
   if(!response.ok)throw Error('HTTP '+response.status+' '+item.file);
   clock=performance.now();const bytes=await response.arrayBuffer();observed.body_read_ms=performance.now()-clock;
   clock=performance.now();const actualHash=await digest(bytes);observed.sha256_ms=performance.now()-clock;
   clock=performance.now();if(actualHash!==item.sha256||bytes.byteLength!==item.bytes)throw Error('Asset mismatch '+item.file);
   observed.hash_and_size_validation_ms=performance.now()-clock;observed.sha256=actualHash;
   if(item.file==='../inputs_ssn_m35.json'){
     clock=performance.now();const text=new TextDecoder().decode(bytes);observed.utf8_decode_ms=performance.now()-clock;
     clock=performance.now();const parsed=JSON.parse(text);observed.json_parse_ms=performance.now()-clock;
     clock=performance.now();if(!Array.isArray(parsed.rows)||parsed.rows.length!==170880)throw Error('Unexpected cohort');
     rows=parsed.rows;observed.structure_and_count_validation_ms=performance.now()-clock;
   }
   initialLoad.assets.push(observed);
 }
 clock=performance.now();if(!rows||rows.length!==170880)throw Error('Missing cohort');
 initialLoad.final_validation_ms=performance.now()-clock;initialLoad.total_ms=performance.now()-started;
 initialLoad.completed_utc=new Date().toISOString();initialLoad.final_visibility=document.visibilityState;
 status.textContent='Verified170880 original observed rows. Ready for24 predefined cells; initial load observed separately; no results yet.';updateReady();
}'''
    harness = harness.replace(old_load, new_load)
    old_output = 'location:location.href,manifest,plan,cpu_note:'
    assert harness.count(old_output) == 1
    harness = harness.replace(old_output, 'location:location.href,manifest,plan,initial_load:initialLoad,visibility_observations:visibilityObservations,cpu_note:')
    (target / 'harness.js').write_text(harness, encoding='utf-8')
    assets = [('../inputs_ssn_m35.json', prior / 'inputs_ssn_m35.json'), ('../nearest-parent.js', prior / 'nearest-parent.js')]
    assets += [(p.name, p) for p in [target / 'worker.js', target / 'harness.js', target / 'index.html']]
    write(target / 'BROWSER_MANIFEST.json', dict(schema='private-browser-input-contract/2',
        assets=[dict(file=name, sha256=sha(path), bytes=path.stat().st_size) for name,path in assets],
        sizes=[2000,10000,50000,170880], repetitions=3, backends=['reference','kd'],wall_cap_seconds=120,planned_cells=24,
        initial_load_observations=True,paint_measured=False,os_suspension_measured=False))
    validator = (BASE / 'validate_browser_results.py').read_text(encoding='utf-8')
    assert validator.count("default='browser_result_01'") == 1
    validator = validator.replace("default='browser_result_01'", "default='browser_result_v2_01'")
    validator = validator.replace("BASE/'browser_harness/BROWSER_MANIFEST.json'", "BASE/'browser_harness/v2/BROWSER_MANIFEST.json'")
    marker = "    assert payload['plan']==expected\n"
    assert validator.count(marker) == 1
    validator = validator.replace(marker, marker + '''    load=payload['initial_load']
    assert load['paint_measured'] is False and load['worker_peak_memory_measured'] is False
    assert load['transfer_time_isolated'] is False and load['total_ms']>=0
    assert len(load['assets'])==5 and len(payload['visibility_observations'])>=1
    for asset in load['assets']:
        for key in ['fetch_resolution_ms','body_read_ms','sha256_ms','hash_and_size_validation_ms']:
            assert asset[key]>=0
    input_load=next(a for a in load['assets'] if a['file']=='../inputs_ssn_m35.json')
    for key in ['utf8_decode_ms','json_parse_ms','structure_and_count_validation_ms']:
        assert input_load[key]>=0
''')
    marker = "      user_agent=payload['user_agent'],observed_cells=len(results),"
    assert validator.count(marker) == 1
    validator = validator.replace(marker, "      initial_load=load,visibility_observations=payload['visibility_observations'],\n" + marker)
    ast.parse(validator)
    validator_path = BASE / 'validate_browser_results_v2.py'
    if validator_path.exists():
        raise FileExistsError(validator_path)
    validator_path.write_text(validator, encoding='utf-8')
    files = [amendment, Path(__file__).resolve(), validator_path, BASE/'PROTOCOL_COMPUTE.md',BASE/'common.py',
             BASE/'BROWSER_EXECUTION_SEAL.json',BASE/'BROWSER_ANALYSIS_SEAL.json',target/'BROWSER_MANIFEST.json']
    files += [path for _,path in assets]
    seal = dict(status='SEALED_BEFORE_ANY_BROWSER_EXECUTION_V2',created_utc=stamp,
        previous_seal=entry(BASE/'BROWSER_EXECUTION_SEAL.json'),numerical_kernel_changed=False,
        predefined_cells_changed=False,numerical_criteria_changed=False,
        chronology=dict(native_status=native['status'],native_cells_already_observed=len(native['cells']),browser_results_observed=0),
        entries=[entry(path) for path in sorted(set(files))],cpu_status='WAIT_ROOT_BROWSER_WINDOW')
    seal_path = BASE / 'BROWSER_EXECUTION_SEAL_V2.json'
    write(seal_path,seal)
    print(json.dumps(dict(path=seal_path.relative_to(ROOT).as_posix(),sha256=sha(seal_path),entries=len(seal['entries']),
                         native_cells_already_observed=len(native['cells']),browser_results_observed=0)))

if __name__=='__main__':
    main()
