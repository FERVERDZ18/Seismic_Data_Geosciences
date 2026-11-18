# Reproducir los métodosv3 sin conservar ruedas privadas

Este inventario reproduce el estudio numérico y los controlesv3. No reconstruye
por sí solo elmanuscrito, interfaz, correspondencias originales/GEM o dictámenes.
Se conserva la estructura relativa del repositorio bajo una raíz propia. No
requiereotros proyectos, servicios, Docker, credenciales o acceso a la PC original.

## Dependencias

`requirements-methods-v3.txt` registra versiones directas del entorno observado:
NumPy2.2.6,SciPy1.15.3,Numba0.63.1,llvmlite0.46.0,pyproj3.7.2.
El importadapter actual carga ademásbruces0.5.0,Matplotlib3.10.3 yutm0.8.1.
No significa que el estudioprincipal ejecute el adelgazamiento2020: el núcleo
actual es el vecino2013 con su primitive compartida y corte determinista.
Conservar las licencias de esos paquetes; las dependencias transitivas pueden
resolverse mediantepip. Esto es una lista de fuentes y versiones observadas, no
una afirmación de que ya se haya probado un segundo entorno limpio para estav3.

## Fuentes mínimas, conservando sus rutas

- `outputs/claude_response_2026-11-16/methods/`: los cinco driversv3, el ejecutor
  `run_full_v3_replay.py`, `deterministic_families.py`, `author_normalmix_port.py`,
  protocolos originales de las cuatrofases y `COSINE_V3_REPLAY_PROTOCOL.json`.
- `outputs/claude_response_2026-11-16/index/spherical_weighted_v2.py`.
- `outputs/sequence_pilot_2026-11-15/gardner_knopoff.py`.
- `outputs/sequence_pilot_2026-11-15/comparators/nearest_neighbor/bruces_reference.py`
  (adapter de importación actual). Si no existenlas carpetas `_deps`, utiliza las
  dependencias instaladas en el entorno activo; no es necesario copiar ruedas.

`author_normalmix_port.py` deriva del código autoralGPL3. Conservar su atribución,
elLICENSE y la distribución original fijada en `methods/authors_2013_exact/`, más
sus recibos de18blobs. No renombrar ese port como código original de los autores
actuales ni mezclar la licencia con la del núcleo independiente del índice.

## Entradas mínimas

1. `outputs/sequence_pilot_2026-11-15/inputs/ssn.csv`, `usgs.csv` y`alaska_usgs.csv`.
2. `outputs/ssn_usgs_pilot_2026-11-15/graph_candidate_pairs.json`.
3. `outputs/sequence_pilot_2026-11-15/synthetic/training/etas_20261000/events.csv`.
4. Para cada semilla20261120–20261129 ycadaescenarioetas/n0/n1:
   `outputs/sequence_pilot_2026-11-15/synthetic/test/{escenario}_{semilla}/events.csv`
   y`truth.csv`. Son61CSV delcontrol existente, no se necesitan susNPZprevios.

El estudioprincipal vuelve a producircalibration_v3; los nuevos controles anclados
se generan desde los datos de desarrollo y las semillas fijadas. Las licencias,
términos, atribuciones y procedencia de los catálogos siguen siendo necesarios.
Las entradas congeladas de pares no prueban identidad física ni reconstruyen su
proceso original de generación; ese proceso pertenece al paquete de asociación.

## Ejecución

Usar un entornoPython compatible con los paquetes fijados; instalar el archivo
requirements y ejecutar `methods/run_full_v3_replay.py` desde cualquier directorio
conservando la estructura de fuentes/entradas. No puede haber resultadosv3previos
en los destinos: los scripts se niegan a sobrescribir evidencia. Para un replay
independiente, usar una raíz nueva. No borrar salidas para hacer parecer nueva una
ejecución ya realizada.

Orden: estudioprincipal→120controlesoriginales→24anclados→resumen→cruce2×2.
Los cinco scripts se verifican contra el protocolo antes de correr. La primitive
numérica es una adaptación explícita para compartir el comportamiento del coseno
entrePython yJavaScript; no se atribuye al código autoral original.

Las salidas científicas comparables son arrays decodificados, IDs, máscaras,
particiones, roles, ajustes y métricas. Tiempos, rutas absolutas, hashes de fuente
cambiada y contenedoresNPZ pueden diferir. Ninguna coincidencia numérica convierte
las familias observadas en parentesco físico demostrado.

## Referencia autoral opcional, pero necesaria para repetir su verificación externa

Conservar los .m originales, sus18blobs/GPL y los tres shimsGUI más
`octave_wrappers/run_author2013.m` y`run_author2013_cases.py`. La ejecución anterior
se hizo realmente conGNUOctave11.3.0 portátil, no conMATLAB. El runtimeoficial puede
obtenerse aparte; no es necesario incluir≈1GBdebinarios en el archivo de fuentes.
Para comparar la versión adaptadav3 con el autor, declarar el cambio de primitive
y verificar padres/roles en los datos correspondientes, sin prometer igualdad
de bits de todas las funciones matemáticas entre runtimes.
