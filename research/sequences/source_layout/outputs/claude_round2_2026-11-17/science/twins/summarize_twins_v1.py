"""Read-only scientific result digest; no new histories, labels or calibration."""
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import run_twins_v1 as t

HERE = Path(__file__).resolve().parent


def get(value, path):
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def fmt(values, scale=1):
    values = [v*scale for v in values if v is not None]
    s = t.mc_summary(values)
    if not values:
        return 'NA (n=0)'
    ci = s['MC95_t']
    return f"{s['mean']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]; n={s['n_histories']}" if ci else f"{s['mean']:.3f}; n={s['n_histories']}"


def main():
    source = HERE/'run_v1/RESULTS.json'
    result = json.loads(source.read_text(encoding='utf-8'))
    assert result['completed_histories']==60 and not result['failures']
    records = []
    all_rows = []
    for history in result['results']:
        for cell, metrics in history['metrics'].items():
            for method in ('GK', 'NN_fixed_A_cut', 'NN_cell_development_cut'):
                recovery = metrics['B_recovery'][method]
                known = metrics['known_identity'][method]
                match = metrics['actual_matching']['evaluation_by_latent_A_time']
                row = dict(seed=history['seed'], branching=history['branching'], cell=cell, method=method,
                           A_keys=known['fixed_clean_A_evaluation_keys'], B_retained_evaluation=recovery.get('evaluated'),
                           missing=known['B_missing'], below_cut=known['B_below_cut'], retained_both=known['retained_both'], B_only_entrants=known['B_only_evaluation_entrants'],
                           inclusion_loss=known.get('inclusion_loss_fraction_fixed_A'), retained_role_change=known.get('retained_role_change_fraction_fixed_A'), total_disagreement=known.get('total_state_disagreement_fraction_fixed_A'),
                           cross_role_agreement=get(known, 'conditional_retained.agreement'), cross_ARI=get(known, 'conditional_retained.partition.ARI'),
                           true_role_agreement=get(recovery, 'observed_families_and_roles.agreement'), true_family_ARI=get(recovery, 'observed_families_and_roles.partition.ARI'),
                           child_F1=get(recovery, 'generated_child.F1'), immigrant_FPR=get(recovery, 'generated_child.true_immigrant_false_positive_fraction'),
                           always_child_F1=get(metrics, 'B_trivial_baselines.always_child.F1'),
                           all_singletons_ARI=get(metrics, 'B_trivial_baselines.all_singletons.partition.ARI'),
                           all_one_family_ARI=get(metrics, 'B_trivial_baselines.all_one_family.partition.ARI'),
                           matching_precision=match['precision'], matching_recall=match['recall'])
                for role in range(3):
                    for key in ('n', 'TP', 'FP', 'FN', 'TN', 'precision', 'recall', 'F1'):
                        row[f'role{role}_{key}'] = get(recovery, f'observed_families_and_roles.per_class.{role}.{key}')
                records.append(row)
                all_rows.append((history, metrics, method, row))
    csv_path = HERE/'ALL_HISTORY_CELL_METRICS.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    group = defaultdict(list)
    for row in records:
        group[row['branching'], row['cell'], row['method']].append(row)
    lines = ['# Gemelos: resultados del lote sellado', '',
             'Se completaron 60 historias de prueba independientes (30 por régimen), 960 celdas B y 3 historias separadas de desarrollo. Cero abortos; ningún resembrado. Las celdas de una misma historia son dependientes. Todas las cifras siguientes son medias por historia con intervalo Monte Carlo t del 95%; no son intervalos sobre México ni validación física.', '',
             f"Protocolo JSON SHA256 `{result['protocol_sha256']}`. Resultados SHA256 `{t.sha(source)}`. Tiempo del lote {result['elapsed_seconds']:.3f} s, sólo metadato de ejecución, no benchmark.", '',
             'D/M/X/T identifican detección/contexto, magnitud, posición y reloj. La tabla abrevia los controles puros y la combinación completa; el CSV y RESULTS.json conservan las 16 celdas y ambos umbrales NN.', '',
             '| Ramificación | Celda | Método | Pérdida de inclusión (%) | Cambio de rol entre retenidos / claves A (%) | Desacuerdo total / claves A (%) | ARI contra raíz verdadera | F1 hijo generado | F1 siempre hijo |',
             '|---|---|---|---|---|---|---|---|---|']
    for branch in (0., .6):
        for cell in ('0000', '1000', '0100', '0010', '0001', '1111'):
            for method in ('NN_fixed_A_cut', 'GK'):
                rows = group[branch, cell, method]
                fields = ['inclusion_loss', 'retained_role_change', 'total_disagreement', 'true_family_ARI', 'child_F1', 'always_child_F1']
                values = [fmt([r[f] for r in rows], 100 if i<3 else 1) for i, f in enumerate(fields)]
                lines.append('| '+ ' | '.join([str(branch), cell, method]+values)+' |')
    lines += ['', '## Calibración y control exacto', '']
    fits = json.loads((HERE/'run_v1/CALIBRATION.json').read_text(encoding='utf-8'))
    for cell, fit in fits.items():
        f, diag = fit['fit'], fit['diagnostics']
        lines.append(f"- {cell}: estado {f['status']}; corte {f.get('threshold_log10')}; modos {diag.get('mode_count')}; guard BIC/bimodal {diag.get('two_mode_BIC_guard_passed')}; {fit['finite_score_count']} scores finitos de desarrollo.")
    for method in ('GK', 'NN_fixed_A_cut', 'NN_cell_development_cut'):
        controls = [r for r in records if r['cell']=='0000' and r['method']==method]
        lines.append(f"- A=B {method}: {len(controls)} historias; máximo desacuerdo total {max(r['total_disagreement'] for r in controls):.16g}.")
    lines += ['', '## Emparejamiento secundario', '', '| Ramificación | Celda | Precisión | Exhaustividad |', '|---|---|---|---|']
    for branch in (0., .6):
        for cell in ('0000', '1000', '0100', '0010', '0001', '1111'):
            rows = group[branch, cell, 'GK']
            lines.append('| '+ ' | '.join([str(branch), cell, fmt([r['matching_precision'] for r in rows]), fmt([r['matching_recall'] for r in rows])])+' |')
    lines += ['', 'La precisión usa todas las asignaciones; la exhaustividad usa identidades latentes retenidas en ambas observaciones. Los registros sin contraparte por censura no se transforman en fallos de matching. Los roles por asignación real y por identidad conocida se conservan aparte.', '',
              '## Sensibilidad de calibración', '', '| Ramificación | Celda | Cambio emparejado de desacuerdo total: umbral por celda menos fijo A (puntos porcentuales) |', '|---|---|---|']
    for branch in (0., .6):
        for cell in t.CELLS:
            a = {r['seed']: r['total_disagreement'] for r in group[branch, cell, 'NN_fixed_A_cut']}
            b = {r['seed']: r['total_disagreement'] for r in group[branch, cell, 'NN_cell_development_cut']}
            lines.append('| '+ ' | '.join([str(branch), cell, fmt([(b[seed]-a[seed])*100 for seed in a if a[seed] is not None and b[seed] is not None])])+' |')
    lines += ['', '## Alcance e interpretación', '',
              'La verdad raíz/padre se generó sin NN/GK. Los roles verdaderos se definen sobre miembros retenidos de cada familia y su máximo reportado, mientras que hijo/inmigrante conserva parentesco aunque falte el padre. Por ello ARI, roles y F1 de hijos responden preguntas distintas. Las pérdidas de inclusión y los cambios de rol se dan con denominadores separados y fijos.', '',
              'Un ARI o una estabilidad altos no prueban declustering correcto. Deben leerse los falsos positivos del régimen sin descendencia, los baselines y las métricas por clase en el CSV. No se seleccionó un umbral por verdad de prueba ni se sustituyeron resultados adversos.', '',
              'Los contrastes de Mobius del factorial completo están en cada FACTORIAL_INTERACTIONS.json y en RESULTS.json; las combinaciones contienen interacciones y no representan porcentajes de causalidad física. Los errores son supuestos y el generador tiene núcleo espacial gaussiano y burn finito: no es una calibración ETAS MLE ni evidencia de representatividad de México.', '',
              'Se conservan los resultados previos: NN F1 de hijo 0.5542555 en el control anterior M4.5/d1.6; GK 0.684 frente al trivial 0.691 como medias descriptivas. El nuevo lote no borra esa evidencia ni convierte estabilidad entre catálogos en exactitud física.', '']
    target = HERE/'TWINS_RESULTS.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    t.dump(HERE/'POSTPROCESSING_RECEIPT.json', dict(created_utc=datetime.now(timezone.utc).isoformat(), generated_new_histories=False, recalibrated=False, recomputed_detectors=False, input_sha256=t.sha(source), postprocessor_sha256=t.sha(__file__), report_sha256=t.sha(target), csv_sha256=t.sha(csv_path), rows=len(records)))
    print(json.dumps(dict(report=str(target), csv_rows=len(records), results_sha256=t.sha(source))))


if __name__=='__main__':
    main()
