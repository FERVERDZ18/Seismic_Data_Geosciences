"""Freeze post-review catalog protocol and copies, no scientific computation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
METHODS=ROOT/'outputs/claude_response_2026-11-16/methods'
INDEX=METHODS.parent/'index'
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
DESIGN=METHODS.parent/'catalog_design'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    if (HERE/'SEAL.json').exists(): raise FileExistsError('Protocol already sealed')
    vendor=HERE/'vendor';vendor.mkdir(exist_ok=False)
    source=[INDEX/'spherical_weighted_v2.py',METHODS/'author_normalmix_port.py',METHODS/'deterministic_families.py',PILOT/'gardner_knopoff.py',ROOT/'scripts/pilot_catalog_reconciliation.py',METHODS/'run_deterministic_study_v3.py',METHODS/'authors_2013_exact/LICENSE',METHODS/'authors_2013_exact/readme.txt']
    manifest=[]
    for p in source:
        dest=vendor/p.name;shutil.copyfile(p,dest)
        manifest.append(dict(source=p.relative_to(ROOT).as_posix(),copy=dest.relative_to(HERE).as_posix(),sha256=sha(p)))
    # Copy is exact. Runtime adds original dependency paths read-only and overrides
    # NUMBA_CACHE_DIR before imports; no source modification is needed.
    dump(HERE/'VENDOR.json',manifest)
    inputs=[PILOT/'inputs/ssn.csv',PILOT/'inputs/usgs.csv',PILOT/'inputs/alaska_usgs.csv',ROOT/'outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json',ROOT/'outputs/ssn_usgs_pilot_2026-11-15/pilot_results.json',DESIGN/'paired_diagnostics.csv',DESIGN/'scientific_diagnostics.compact.json',DESIGN/'CATALOG_DESIGN_AUDIT.json',ROOT/'system/dist/data/country-index.json',ROOT/'system/dist/data/events.json',ROOT/'system/dist/data/catalogs/ssn-mx/events.json',METHODS/'deterministic_study_v3/PAIRED_METRICS.json',METHODS/'deterministic_study_v3/MEASUREMENT_FACTORIAL.json',METHODS/'calibration_v3.json',DESIGN/'web_inputs/nn_parity/round_04/alaska_4_5_js.json',DESIGN/'web_inputs/nn_parity/round_04/alaska_4_5_comparison.json']
    for src in ['ssn','usgs']:
        inputs.extend(METHODS/'deterministic_study_v3/cases'/f'M4p5_{src}_native_author'/n for n in ['arrays.npz','ids.json','metadata.json','rows.json'])
    missing=[str(p) for p in inputs+source if not p.is_file()]
    if missing: raise FileNotFoundError(missing)
    dump(HERE/'INPUTS.json',[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in inputs])
    protocol=dict(schema='round2-catalog-protocol/1',scope='post-review conditional catalogue comparison; no physical truth',magnitude_cut='4.5',d=1.6,q=.5,weights=[.8,.9,1.,1.1,1.2,1.3,1.4,1.0905428994843476,1.3265675928192793],threshold_deltas=[-.5,0,.5],development_start_inclusive='2016-01-01',development_end_exclusive='2021-01-01',evaluation_end_exclusive='2026-01-01',bootstrap=dict(replications=2000,seed=20261117,generator='PCG64',units='fixed union of both native principal partitions and retained cross-source candidate edges',percentile_method='linear',warning_min_units=10,warning_max_pair_fraction=.5),matching_windows=dict(seconds=[10,30,60],km=[10,50,100]),edge_projection=dict(south_latitude_min=14.5,interior_lat=[14.5,32.5],interior_lon=[-117.5,-86.5]),alaska_development_end_exclusive='2023-01-01',md_sha256=sha(HERE/'PROTOCOL.md'),inputs_sha256=sha(HERE/'INPUTS.json'),vendor_sha256=sha(HERE/'VENDOR.json'),no_new_downloads=True,no_public_changes=True,no_git=True)
    dump(HERE/'PROTOCOL.json',protocol)
    dump(HERE/'SEAL.json',dict(sealed_utc=datetime.now(timezone.utc).isoformat(),files={n:sha(HERE/n) for n in ['PROTOCOL.md','PROTOCOL.json','INPUTS.json','VENDOR.json']},scientific_results_created=False))
    print(json.dumps(json.loads((HERE/'SEAL.json').read_text()),indent=2))
if __name__=='__main__': main()
