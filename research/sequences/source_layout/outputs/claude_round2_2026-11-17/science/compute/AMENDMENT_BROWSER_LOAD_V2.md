# Enmienda previa al navegador: fases de carga inicial

Fecha UTC: 2026-11-17T17:25:45.390807+00:00. Antes de toda apertura/ejecución del harness en navegador.
Se conocen 77 celdas nativas completadas; estado nativo
IN_PROGRESS. La solicitud del coordinador se recibió después de examinar
esos tiempos nativos y antes de observar resultados de navegador.

El protocolo D ya separaba carga inicial y cálculo del Worker. La versión1
excluía fetch/hash/decode/parse del reloj del núcleo, pero no guardaba sus costes
numéricos. Se conserva intacta con su sello. La versión2 añade observaciones de
performance.now para fetch hasta resolución, lectura de bytes, SHA256, UTF8
decode, JSON parse y comprobación de estructura/conteo. Guarda cada asset y
el total inicial; no convierte estas fases en paint o latencia de interfaz.

No cambian los24 ensayos, N={2000,10000,50000,170880}, tres réplicas, orden,
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
