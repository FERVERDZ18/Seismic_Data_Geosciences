# Diagnóstico prefijado de proximidades espaciales cero

17 noviembre 2026, antes de leer conteos de ceros. Es un diagnóstico postrevisión,
no verdad física ni modificación del algoritmo o del sistema. Los originales se
conservan. No se usará epsilon, piso espacial, padre alternativo ni reajuste de EM.

Entradas: los18casos México≥4.5 de catalog/runs/run_01: ambas fuentes y TODOS
los9pesos prefijados, δ0. Usar arrays/IDs/filas y cortes ya retenidos. Además,
auditar SIN clasificar familias los vectoresM3.5,w1 conservados de paridad round_04
para SSN y ComCat, ligados por ID a los CSV originales. No transferir roles de otro
corte ni inferir clases3.5 donde la mezcla no es estimable.

A. Separar ausencia de padre(p<0), RN=0 con padre válido, score−∞ con padre válido,
TN=0 y otros no finitos. El score de corte es log10(TN)+log10(RN), con los TN/RN
retenidos. Identificar por separado score de ajuste no finito durante2016–20:
el EM existente los excluye, mientras la clasificación puede conservar−∞≤c.
No confundir el primer registro sin padre con una arista espacial cero.

Para cada arista con padre válido y(RN=0 o score−∞), exportar IDs/UTC/coordenadas
padre-hijo, magnitudes, RN/TN/distancia guardada y score. Calcular lag desde los
UTC originales, evitando suponer unidades por el nombre de un campo heredado.
Distinguir coordenadas numéricamente idénticas de coordenadas distintas con
distancia computada0; no llamar a ambas «duplicados» ni terremotos idénticos.
Reportar lags mínimos/máximos, año del hijo, desarrollo/evaluación, fuente/peso,
corte4.5/3.5, y cualquier RN0 con distancia positiva como categoría excepcional.

B. Regla de ablación automática, aplicada a todos los casos4.5: si existen esas
aristas con padre válido, cambiar SÓLO su padre a−1 y conservar score/corte de ese
caso. Recalcular componentes y representante máximoM/UTC/ID con la función original.
No buscar otro padre, no rehacer índice, no reajustar frontera. Si no hay ceros,
producir el mismo contraste identidad, sin omitir ese caso. La operación se llama
«eliminación de aristas cero con padres/cortes congelados», nunca corrección de
exactitud, clasificación causal o nuevo método ya validado.

Reportar, antes/después: roles y particiones nativas completos/evaluación, los889
candidatos retenidos en ambas fuentes (y382 de2021–25), matriz/Jaccard/ARI/acuerdo
entre agencias para cada peso común; cambios de rol por fuente sobre mismos IDs.
Exportar arrays derivados y listas de aristas borradas. Las familias que contienen
las anclas fijas2017/2022 usan los IDs del caso existente y su contraparte candidata,
sin elegir una ancla nueva según la ablación. Reportar sus tamaños/UTC/duración y
el máximo span de cualquier componente no unitaria antes/después. Son componentes
operacionales, no secuencias físicas verificadas.

Código, protocolo y entradas se sellan con SHA antes de resultados; fixtures pequeños
se ejecutan únicamente tras el gate de CPU. Durante los81benchmarks sólo se escribe
código/texto. Sin cambios públicos, JS, manuscrito, contexto, Git o publicación.
