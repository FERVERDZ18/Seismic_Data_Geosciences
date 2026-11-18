# Protocolo previo: coste equivalente y padres a escala del catálogo conservado

17 noviembre 2026. Estado inicial: **PREDEFINIDO, SIN RESULTADOS NUEVOS**.
Gabriel aprobó ampliar la validación. El coordinador debe incorporar este protocolo
a su protocolo maestro y conceder una ventana CPU exclusiva antes de medir.
No autoriza Git ni publicación de nuevos resultados. La autorización separada de
la revisión .4 no se transfiere a otra revisión científica.

## A. Preservación y pregunta

Conservar todos los resultados anteriores y todos los originales v0. Sólo escribir
en `outputs/claude_round2_2026-11-17/science/compute/`. El motor numérico reutilizado
es `outputs/claude_response_2026-11-16/index/spherical_weighted_v2.py` con el
exhaustivo optimizado `cached_balanced_exhaustive_v2.py`; ambos se usan sin editar.
Los scripts nuevos y sus hashes se sellarán antes de ejecutar; los imports/JIT no
se realizarán mientras otra lane mida CPU. No se instala software global.

Pregunta computacional: ¿cuál es el coste observado de búsqueda exhaustiva/KD/
octree con los mismos inputs, precisión, número de hilos y repeticiones?
Pregunta de uso científico a escala grande: ¿cómo cambian los padres mínimos y
sus proximidades de registros observados al variar peso/contexto? En M≥3.5 no se
asigna un corte EM ni roles de familia: la falta de bimodalidad no invalida la
búsqueda, pero impide interpretar su corte como separación de familias.

## B. Comparación nativa de coste

1. Input inmutable: `index/v2/benchmark_01/input_arrays.npz`, SHA256
   `759d39d59e8d882a8ae9d9a42b41c8711c8eb0c42bdf9bbd0e1ab0f5bad46a6a`,
   más su lista original de IDs. N=170880 SSN México2016–2025, Mreportada≥3.5.
2. Prefijos N={2000,5000,10000,20000,50000,100000,170880}, los mismos para los
   tres backends. Añadir los dos inputs científicos originales M≥4.5 (SSN1780 y
   ComCat1256) para no confundir el prefijo2000 de magnitudes menores con aquellas
   cohortes completas. Los inputs se verifican contra CSV/IDs originales.
3. d=1.6, w=1, q=.5, R=6367.3km; misma época2016 y aritmética temporal existente.
   Mismo guard de cuerda2e−7 y log1e−10, sin cambiar candidato/empates ni precisión.
4. **Un hilo** Numba/OMP/OpenBLAS/MKL en todos los backends. El índice sigue siendo
   serial. Tres procesos nuevos por input/backend. Cada proceso carga el input y
   calienta los tres backends con el mismo fixture64 antes de medir.
5. Orden balanceado predeterminado por repetición: ref/KD/octree;
   KD/octree/ref; octree/ref/KD. No otras tareas CPU intensivas propias simultáneas.
   Registrar máquina, runtime, librerías, variables de hilos, PID y tiempos UTC.
6. Tiempo principal: preparación geométrica+construcción+kernel+postproceso
   numérico. Registrar componentes y reloj exterior. Excluir carga/import/JIT y
   serialización; conservar sus tiempos aparte y no llamarlo latencia completa.
7. Conservar todos los tiempos; resumen mediana/min–max, cociente de medianas
   exhaustivo/índice. Tres réplicas no justifican intervalo de confianza de rendimiento.
   El benchmark antiguo de4hilos es histórico separado; no suple una nueva réplica.
8. Pico de working set, working set corriente y pico de pagefile antes del
   warm-up, antes y después de medir. Son métricas del proceso completo, incluidas
   bibliotecas/JIT; no memoria exclusiva del núcleo ni heap del navegador.
9. Igualdad exacta de todos los arrays de salida, con NaN en las mismas posiciones,
   contra el exhaustivo del mismo input. Fallos se conservan y bloquean la celda.
   No ocultar ausencia de ventaja en cohortes pequeñas ni favorecer una partición
   si sus rangos se solapan. Límite duro nativo1200s/celda; timeout se declara
   censurado y no se convierte en tiempo extrapolado ni speedup observado.

## C. Uso de escala grande sin familias EM

Inputs originales M≥3.5: SSN170880, ComCat3945 y2989 asignaciones candidatas
conservadas; no son identidades validadas. Orden UTCus/ID y campos originales.
Dos contextos: nativo completo y sólo los endpoints de esas2989asignaciones,
preservando exactamente los valores de cada fuente. Ningún ajuste EM/umbral/rol.

Rejilla por cada fuente y contexto:
`w={0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.0905428994843476,1.3265675928192793}`.
Los dos últimos son los b aparentes de desarrollo M4.5 ya conservados; aquí son
valores operativos de sensibilidad, no b calibrados para la cohorte M3.5.
d=1.6,q=.5; no seleccionar peso para maximizar concordancia. Referencia w=1.

Se guardan todos los padres/IDs/proximidades/dt/distancias y los inputs/hashes.
Resumen completo y temporal2021–2025, siempre con padres anteriores permitidos:

- cambio de padre frente a w=1 por fuente/contexto, en todas las filas y en los
  endpoints candidatos; denominadores/primer evento sin padre explícitos;
- cambio nativo→contexto común en los mismos endpoints, por peso, sin refitting;
- proporción de pares cuyos dos padres son endpoints emparejados y concordancia
  del índice de pareja de esos padres, tanto sobre todos los pares como condicionada
  a la comparabilidad. Padres no emparejados/no definidos permanecen separados;
- distribuciones descriptivas de tiempo/distancia/magnitud reportada del padre
  y score finito, con cuantiles y conteos no finitos. No son precisión causal,
  triggering, completitud ni equivalencia Mw. El cambio de score al variar w
  incluye por construcción su cambio de escala y no se interpreta solo como efecto.

Por cada peso/contexto, comparar KD con el exhaustivo completo. Para el control
de corrección se permiten4hilos, separado del benchmark1hilo y sin vender sus
tiempos como speedups. La salida nueva w=1 del benchmark puede reutilizarse sólo
si los arrays/IDs son exactamente los mismos. Ningún resultado4hilos antiguo
sustituye un control de nuevo peso. Comparar además con JS/Node bajo el criterio
ya existente de padres exactos y score absoluto≤1e−10; guardar discrepancias sin
aflojar el criterio. El alcance sigue siendo estos inputs finitos, no IEEE universal.

## D. Navegador real y comparadores existentes

Se preparará un harness privado para CUA, sin Playwright/CDP externo. Copia exacta
del JS actual y input canónico con sus hashes. Backends reference/KD reales, w=1,
fixture de warm-up idéntico y tres Workers/procesos lógicos nuevos por input.
N={2000,10000,50000,170880}; orden alternado por réplica. Límite120s/celda:
terminar Worker y registrar censura si excede; no extrapolar. Separar fetch/hash/
parse/transfer de preparación/construcción/search/export del Worker; no confundir
con latencia total o paint. Mostrar resultados/descarga reales y verificar sus
arrays frente a la referencia. No afirmar pico de memoria de Worker si no existe
medición fiable. Root controla el navegador y da la ventana CPU para esta fase.

Comparadores autoral2013/Octave y eqclustering0.1.0 se limitan a los dos inputs
principales M4.5: tres procesos nuevos por fuente/comparador, d1.6,w1,q.5,
hilos de librerías1. Registrar reloj de proceso y del núcleo separadamente.
El coste entre lenguajes no es una estimación aislada de ventaja algorítmica.

- Autoral: distribución GPL fijada636d07b, numéricos intactos, adaptadores gráficos
  existentes declarados, runtime Octave11.3.0; no afirmar ejecución MATLAB.
- Eqclustering: fuente Apache2 fijada393a02db, preservar NOTICE. Adaptación sólo
  de sintaxis Python2 y nombres constantes NumPy; guardar diff y hashes. No cambiar
  su365.35d, acos sin clamp, selección o regla de corte para forzar igualdad.
  Reportar padres/rawscore/distancia y discrepancias con el contrato actual;
  sólo comparar roles/cortes si sus definiciones/unidades se hacen explícitas.
  Si adaptación falla, conservar fallo y tratarlo como limitación de compatibilidad,
  no inventar un benchmark ni atribuirle tiempos de otra implementación.

## E. Congelación, ejecución y fallos

Antes de correr: sello de este protocolo, scripts nuevos, numéricos existentes,
inputs, IDs, runtime y aprobación CPU del coordinador. Carpetas por celda nuevas;
nunca sobrescribir resultados anteriores. Mantener stdout/stderr, receipts,
outputs y todos los timeouts/errores. Cambios posteriores se registran como
enmiendas fechadas con conocimiento de resultados explícito; no reetiquetar
los ensayos fallidos. La pregunta no está cerrada si sólo se escribe un texto.
Todo sigue local hasta nueva autorización específica de Git/publicación.
