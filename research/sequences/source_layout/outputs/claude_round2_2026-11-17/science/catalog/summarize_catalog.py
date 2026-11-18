"""Read completed evidence with stdlib only; no detector or new experiment."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json
HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/run_01'
def load(name):return json.loads((RUN/name).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(x):return 'NA' if x is None else f'{100*x:.2f}%'
def interval(z,key='agreement'):
    a=z['dependent_resampling']['intervals'][key]
    return f"[{pct(a['percentile_2_5'])}, {pct(a['percentile_97_5'])}]"
def main():
    manifest=load('MANIFEST.json');assert manifest['status']=='PASS'
    for row in manifest['output_files']:assert sha(RUN/row['path'])==row['sha256'],row['path']
    metrics=load('WEIGHT_THRESHOLD_METRICS.json');units=load('DEPENDENCE_UNITS.json')
    rows=[]
    for k,z in metrics.items():
        if z['status']=='computed' and z['delta']==0:
            full=z['periods']['full_2016_2025'];test=z['periods']['evaluation_2021_2025']
            rows.append((z['w_ssn'],z['w_usgs'],z['kind'],pct(full['agreement']),pct(test['agreement']),
                interval(full),interval(test),z['baseline_unit_fusion_diagnostics']))
    baseline=next(z for z in metrics.values() if z['status']=='computed' and z['w_ssn']==z['w_usgs']==1 and z['delta']==0)
    fit=[]
    for p in sorted((RUN/'cases').glob('*/metadata.json')):
        z=json.loads(p.read_text());fit.append(dict(source=z['source'],w=z['w'],fit=z['fit']['status'],c=z['fit'].get('threshold_log10'),mode_count=z['diagnostics'].get('mode_count'),guard_pass=z['diagnostics'].get('two_mode_BIC_guard_passed'),largest=z['classifications'].get('0',{}).get('largest_component'),fraction=z['classifications'].get('0',{}).get('largest_component_fraction')))
    with (RUN/'COMPONENTS.csv').open(encoding='utf-8',newline='') as f:components=list(csv.DictReader(f))
    longest=sorted(components,key=lambda z:float(z['duration_days']),reverse=True)[:5]
    alaska=load('ALASKA_TEMPORAL_METHOD_COMPARISON.json')
    summary=dict(status='PASS',all_output_hashes_verified=len(manifest['output_files']),run_manifest_sha256=sha(RUN/'MANIFEST.json'),
        baseline=baseline,dependence=units,weight_delta0_table=rows,fit_diagnostics=fit,longest_component_examples=longest,
        coverage=load('COVERAGE.json'),edge_controls=load('EXISTING_EDGE_CONTROLS.json'),nine_windows=load('NINE_WINDOW_NN.json'),alaska=alaska)
    (HERE/'RESULTS_SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    lines=['# Resultados privados de catálogo — segunda revisión','',
        f"Corrida `runs/run_01`, PASS. {len(manifest['output_files'])} hashes de salidas verificados; entradas y copias versionadas verificadas al principio/final. Tiempo del batch {manifest['elapsed_seconds']:.2f}s con un hilo; no es benchmark.",'',
        'El principal w=1 reproduce exactamente v3 por IDs, padres, TN/RN, roles y componentes. Todos los18 ajustes devolvieron un corte; los diagnósticos de modalidad/BIC se reportan por separado. No hubo descargas ni cambios públicos, del manuscrito, contexto o Git.','',
        '## Peso sin seleccionar un resultado favorable','',
        '| wSSN | wComCat | Contraste | Acuerdo2016–25 | Acuerdo2021–25 | Remuestreo completo | Remuestreo temporal |','|---:|---:|---|---:|---:|---|---|']
    for a,b,kind,full,test,ci1,ci2,_ in rows:lines.append(f'| {a:.12g} | {b:.12g} | {kind} | {full} | {test} | {ci1} | {ci2} |')
    lines+=['','Los intervalos son percentiles de sensibilidad de composición por unidades conjuntas fijas, no cobertura nominal demostrada ni incertidumbre de identidad física, completitud o ajuste. Si una familia variante fusiona unidades basales, esa dependencia nueva no está capturada; el JSON muestra todos esos diagnósticos.','',
        '## Umbral principal y clases','',
        '| δ | Acuerdo completo | Acuerdo temporal |','|---:|---:|---:|']
    for delta in [-.5,0,.5]:
        z=next(z for z in metrics.values() if z['w_ssn']==z['w_usgs']==1 and z['delta']==delta)
        lines.append(f"| {delta:+.1f} | {pct(z['periods']['full_2016_2025']['agreement'])} | {pct(z['periods']['evaluation_2021_2025']['agreement'])} |")
    for period in ['full_2016_2025','evaluation_2021_2025']:
        z=baseline['periods'][period];plan=units['plans'][period]
        lines+=['',f"{period}: n={z['n']}, acuerdo{pct(z['agreement'])}, ARI{z['partition']['ARI']:.4f}; unidades={len(plan['codes'])}, efectiva={plan['effective_units']:.2f}, máxima fracción{pct(plan['largest_pair_fraction'])}, frágil={plan['fragile']}.",
            f"Jaccard por clase aislado/representante/asociado: {', '.join(pct(c['jaccard']) for c in z['per_class'].values())}."]
    lines+=['',f"Exclusión fija de familias2017: {units['excluded_pairs']} de889pares. Es proyección sin esos pares, conservando todo el contexto y las etiquetas.",'',
        f"Acuerdo sin unión2017: completo{pct(baseline['periods']['full_without_fixed_2017_union']['agreement'])}, temporal{pct(baseline['periods']['evaluation_without_fixed_2017_union']['agreement'])}.",'',
        '## Cobertura, bordes, resultados retenidos y Alaska','',
        f"Cobertura ambos≥4.5: {json.dumps(summary['coverage']['coverage_both_over_selected'])}; estados{json.dumps(summary['coverage']['candidate_cut_states'])}. Contraparte bajo corte y sin asignación permanecen separados.",'',
        'Las nueve ventanas conservaron los conteos de asignación anteriores; tabla completa en `runs/run_01/NINE_WINDOW_NN.csv`. Geografía≥4.5 y estados por año están en `GEOGRAPHY_M4_5.csv` y `SELECTED_ENDPOINT_STRATA.csv`.',
        'Los controles de borde son sólo proyecciones con contexto completo: NO reparan el recorte ComCat al sur de14N ni certifican cobertura común. Esa extensión sigue necesitando nueva captura versionada y control de revisiones.',
        'Las16celdas factoriales y diez resultados anuales se extraen de v3 sin repetir experimentos; rutas `FACTORIAL_16_RETAINED_V3.csv` y `ANNUAL_RETAINED_V3.csv`. Sustituciones computacionales, no atribución causal aditiva.','',
        f"Alaska: {alaska['native_events']} registros≥4.5; GK indexado/exhaustivo idénticos en grupos, flags, roles y representantes. Sólo ComCat, comparación entre métodos y no entre agencias."]
    for p,z in alaska['periods'].items():
        if p.startswith('year_'):continue
        lines.append(f"- {p}: n={z['n']}, acuerdoNN/GK{pct(z['agreement'])}, ARI={z['partition']['ARI']:.4f}, marginalNN={z['first_marginal']}, marginalGK={z['second_marginal']}.")
    lines+=['','## Límites que permanecen','',
        'Las sensibilidades no validan identidades candidatas, familias causales, magnitudes homogéneas ni completitud. La dependencia del peso puede ser grande; se conserva el resultado adverso. El recorte sur no está solucionado sin datos nuevos. Este batch no cierra por sí mismo S3, S7, S1, S2 o la evaluación editorial.']
    (HERE/'RESULTS_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(hash_checks=len(manifest['output_files']),weight_delta0_table=rows,fit_diagnostics=fit,units={p:{k:v for k,v in z.items() if k not in ['codes','sizes']} for p,z in units['plans'].items()},alaska={p:dict(n=z['n'],agreement=z['agreement'],ARI=z['partition']['ARI']) for p,z in alaska['periods'].items() if not p.startswith('year_')}),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
