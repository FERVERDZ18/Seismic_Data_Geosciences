# Control del recorte sur: adquisición y cohortes separadas

17 noviembre 2026. Especificado antes de nuevas adquisiciones y análisis. Se
preservan todos los snapshots y resultados originales. El manifiesto SSN existente
declara coordenadas hasta10.271N y una captura nacional del6nov2026; esto demuestra
un paquete geográficamente más amplio que el piloto, no el conteo por periodo ni
una máscara de cobertura/completitud. Los conteos del tramo12≤lat<14 se inspeccionan
desde el mismo paquete, sin renovar SSN ni inventar valores ausentes.

## Adquisición primaria y control de versiones

Descargar sólo de USGS FDSN, GeoJSON de parámetros preferidos, sin contributor
ni catalog impuestos, eventtype=earthquake, Mreportada≥3.5, lat[12,33],
lon[−118,−86]. Dos peticiones:2016-01-01/2021-01-01 y2021-01-01/2026-01-01,
orderby=time-asc,limit20000. Los límites temporales del servicio son inclusivos;
filtrar localmente a cada intervalo cerrado-abierto para evitar duplicación.
Si un cuerpo llega al límite20000, marcar incompleto y no analizar: se requiere
enmienda de partición antes de continuar. No usar offsets sobre un catálogo vivo.

Conservar URL exacta, método, UTC de inicio/fin, status/cabeceras HTTP, bytes y
SHA256 de cada cuerpo, metadatos USGS y errores. Máximo tres intentos por petición,
con cuerpos/errores separados, sin sobrescribir. No afirmar captura atómica del
catálogo; dos respuestas observadas en un intervalo son una adquisición actual.
No inferir la hora de adquisición de `updated` de un evento.

La restricción14≤lat≤33 del MISMO cuerpo ampliado es el control actual de dominio
viejo. Así la comparación geográfica actual no mezcla dos consultas por separado.
Comparar esa restricción actual contra el viejo ComCat por ID original, con tabla
de IDs añadidos/ausentes/campos cambiados. Las ausencias pueden ser cambios de
selección/ID o revisión: no llamarlas terremotos borrados sin evidencia. Conservar
aliases `ids` del GeoJSON; un alias se informa separadamente de la igualdad de ID.
No anexar el tramo nuevo al snapshot viejo fingiendo una única fecha de captura.

## Cohortes y estimandos fijados

A: piloto original, SSN y ComCat lat[14,33],2016–25, cortes originales.
B: el mismo SSN14 y el ComCat actual restringido14, sin agregar tramo sur.
C: SSN existente y ComCat actual lat[12,33]. Se conservan etiquetas de adquisición
distintas por fuente y escenario. En cada uno, seleccionar≥4.5 con Decimal;
los pares se asignan sobre las observaciones≥3.5 mediante el contrato existente
30s/50km de máxima cardinalidad/mínimo coste. No cambiar ventana según acuerdo.

Primero publicar todos los conteos SSN por banda/corte/año; si no hay soporte SSN
al sur, reportarlo y no llamar al tramo una comparación válida. Observaciones de
ambas fuentes en la misma banda permiten una comparación descriptiva condicionada,
no garantizan detección común, identidades físicas ni completitud. No aplicar un
polígono terrestre como supuesto de cobertura; los eventos marinos se conservan.

NN: mismo kernel esférico v3,d1.6,w1,q.5, ajuste autoral sólo2016–20 y prueba
temporal2021–25. B reutiliza la clasificación SSN original; calcula ComCat actual14.
C recalcula padres de ambas fuentes y ajusta cada corte sólo en desarrollo12.
Conservar todos los arrays/cortes/fallos/modalidad/BIC. No sustituir un fallo.

Dos controles secundarios prefijados: ComCatB con corte ComCatA transportado;
ambas fuentesC con sus cortesB transportados, manteniendo sus padresC. Distinguir
padres/contexto de reajuste de frontera; no llamarlo separación causal física.
Reportar matrices, acuerdo/Jaccard por clase y ARI completo/test enB/C, cobertura y
estados de retención. Sobre la intersección de asignacionesB∩C por IDs oficiales,
mostrar cambios de padre/rol/componentes de cada fuente y acuerdo entre fuentes
con cortes recalibrados y transportados. No comparar porcentajes sobre denominadores
distintos sin mostrar esos denominadores.

Caso2017: ancla, reloj y radio150km se congelan desde el caso original. Contar
observaciones≥3.5/4.5 dentro de radio y días[−7,+30], dentro/fuera del viejo límite14;
exportar la lista y roles. Este control resuelve el recorte meridional de ESE
círculo si está contenido en el nuevo rectángulo, no prueba contexto global completo
de las familias NN. Reportar claramente borde nuevo12 y otros bordes persistentes.

## Ejecución y límites

No tocar sistema, manuscript.4, imágenesv0, contexto, Git o publicación. I/O y
código permitidos; ajuste/matching/cálculo de catálogo requieren turno CPU de root
después del benchmark. Fixtures pequeños verifican intervalos, selección, identidad
de snapshot y controles transportados antes de resultados. Salidas nuevas sin
sobrescritura, recibos de entradas/código/resultados y todos los negativos.

Fuentes primarias consultadas: [USGS FDSN API](https://earthquake.usgs.gov/fdsnws/event/1/)
(parámetros, extremos temporales inclusivos, máximo20000, filtros y preferencia de
origen/magnitud); [ComCat](https://earthquake.usgs.gov/data/comcat/) (catálogo de
parámetros/productos de redes contribuyentes). Estas páginas no certifican cobertura
completa de SSN o ComCat ni equivalencia de sus magnitudes.
