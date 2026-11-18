"""Execute unmodified author .m code in portable GNU Octave; local outputs only."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import csv
import hashlib
import json
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PILOT=ROOT/'outputs/sequence_pilot_2026-11-15'
sys.path[:0]=[str(PILOT/'comparators/nearest_neighbor/_deps'),str(PILOT/'comparators/carluccio/_deps')]
import numpy as np
from scipy.io import loadmat

OCTAVE=HERE.parent/'runtime/octave-11.3.0-w64/mingw64/bin/octave-cli.exe'
WRAPPER=HERE/'octave_wrappers/run_author2013.m'
EPOCH=datetime(2016,1,1,tzinfo=timezone.utc).timestamp()


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(source,split,cutoff=None,b=1.,d=1.6):
    label=f'{source}_M45_{split}_b{b:.12g}_d{d:.12g}_epoch2016'
    destination=HERE/'author2013_results'/label
    if destination.exists():raise FileExistsError('Never overwrite scientific evidence: '+label)
    destination.mkdir(parents=True)
    original=PILOT/'inputs'/f'{source}.csv'
    rows=[]
    with original.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            if Decimal(row['magnitude'])<Decimal('4.5'):continue
            if split=='development' and row['time_utc']>='2021-01-01':continue
            rows.append(row)
    rows.sort(key=lambda r:(r['time_utc'],r['record_id']))
    ids=[r['record_id'] for r in rows]
    matrix=np.array([[(datetime.fromisoformat(r['time_utc'].replace('Z','+00:00')).timestamp()-EPOCH)/31557600.,
                      float(r['latitude']),float(r['longitude']),float(r['magnitude'])] for r in rows])
    input_csv=destination/'input_numeric.csv';np.savetxt(input_csv,matrix,delimiter=',',fmt='%.17g')
    (destination/'ids.json').write_text(json.dumps(ids,indent=2)+'\n',encoding='utf-8')
    (destination/'rows.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    out=destination/'author_outputs.mat'
    command=[str(OCTAVE),'--no-gui','--quiet','--no-init-file','--no-site-file',str(WRAPPER),
             str(input_csv),str(out),str(b),str(d)]
    if cutoff is not None:command.append(format(cutoff,'.17g'))
    started=time.perf_counter()
    completed=subprocess.run(command,cwd=destination,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=120)
    seconds=time.perf_counter()-started
    (destination/'stdout.txt').write_text(completed.stdout,encoding='utf-8')
    (destination/'stderr.txt').write_text(completed.stderr,encoding='utf-8')
    metadata=dict(schema='authors-2013-GNU-Octave-execution/1',case=label,
        protocol_sha256=sha(HERE/'AUTHOR_2013_PROTOCOL.md'),input_original=str(original),input_original_sha256=sha(original),
        input_numeric_sha256=sha(input_csv),source_commit='636d07beb89bde7d7deb502db78beebb45528cca',
        executable=str(OCTAVE),wrapper_sha256=sha(WRAPPER),command=command,returncode=completed.returncode,
        elapsed_seconds=seconds,events=len(rows),split=split,b=b,d=d,reported_magnitude_not_Mw_homogenized=True,
        status='execution_failed',cutoff_frozen_from_development=cutoff,
        time_origin_utc='2016-01-01T00:00:00Z',time_unit='31557600 UTC elapsed seconds')
    if completed.returncode==0 and out.is_file():
        values=loadmat(out,squeeze_me=True)
        c=values['c'].item() if isinstance(values['c'],np.ndarray) else values['c']
        eta=np.atleast_1d(values['eta_log10'])
        role=np.atleast_1d(values['role'])
        parents=np.atleast_1d(values['P']).astype(np.int64)-1
        pmain=np.atleast_1d(values['Pfin']).astype(np.int64)-1
        np.savez_compressed(destination/'arrays.npz',parent_index=parents,main_index=pmain,eta_log10=eta,
            cut_eta_log10=values['cut_eta_log10'],
            T_log10=np.log10(values['TN']),R_log10=np.log10(values['RN']),roles=role,
            native_distance_km=values['D'],native_time_years=values['T'])
        valid=bool(np.isreal(c) and np.isfinite(c))
        metadata.update(status='executed',c_log10=float(np.real(c)) if valid else str(c),
            native_cut_is_finite_real=valid,complex_eta_count=int(np.count_nonzero(np.imag(eta))),
            finite_eta_count=int(np.count_nonzero(np.isfinite(eta))),
            no_earlier_parent_count=int(np.count_nonzero(parents<0)),
            coincident_parent_count=int(np.count_nonzero((np.atleast_1d(values['D'])==0)&(parents>=0))),
            role_counts={str(int(v)):int(np.count_nonzero(role==v)) for v in [0,1,2]},
            mu1=str(values['mu1']),mu2=str(values['mu2']),sigma1=str(values['sigma1']),sigma2=str(values['sigma2']),
            weight_A=str(values['A']),weight_A2=str(values['A2']),mat_sha256=sha(out),
            runtime='GNU Octave 11.3.0; not MATLAB',numerical_upstream_unmodified=True)
    (destination/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:metadata.get(k) for k in ['case','status','events','c_log10','complex_eta_count','role_counts','elapsed_seconds']}),flush=True)
    return metadata


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='development_only':
        for source in ['ssn','usgs']:run(source,'development')
    else:
        raise SystemExit('Explicit development_only required; full/frozen cases are orchestrated separately.')
