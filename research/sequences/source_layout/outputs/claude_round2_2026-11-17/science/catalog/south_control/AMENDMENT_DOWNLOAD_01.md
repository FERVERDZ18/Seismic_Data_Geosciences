# Compatibilidad del recibo con USGS API2.8.4

17 noviembre2026, después de observar respuestas HTTP200 y antes de analizar
cualquier catálogo nuevo. El primer entorno no resolvió DNS; con el permiso de
red del entorno se recibieron tres cuerpos FeatureCollection, conservados en
acquisition_02 con recibos FAIL porque la validación suponía metadata.count.
La API2.8.4 observada no proporciona ese campo en estas consultas. No se ha
ejecutado matching, NN, ajuste ni seleccionado un resultado científico.

El adaptadorv2 conserva URLs, dos intervalos y todos los filtros del protocolo.
Valida FeatureCollection, features como lista, IDs únicos, len(features)<20000;
si existe metadata.count también exige igualdad. Conservar metadata.limit y
offset sin tratarlos como conteo total. Al llegar al límite no se analiza y se
requiere partición predefinida. Se realiza una adquisición nueva completa con
recibos propios; no se reescriben errores/cuerpos anteriores. El cambio es de
validación de esquema, sin cambio de datos solicitados ni del análisis acordado.
