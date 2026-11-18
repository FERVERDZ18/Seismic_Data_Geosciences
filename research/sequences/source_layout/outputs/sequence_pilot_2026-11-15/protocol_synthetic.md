# Especificación sintética subordinada al protocolo2 congelado

Este documento hace explícitas las ecuaciones y el formato del generador autorizado por `PROTOCOL_STAGE_2.md` (SHA256 **9be299b26162fafba6d62c58c6c93a87ae2f30b2d0ec372acdfee5f1b0a487b8**). No reemplaza ese protocolo ni ajusta parámetros a México. El generador es una implementación propia de un proceso de ramificación tipo ETAS, no una ejecución autoral de Ogata, Mathematica o bruces. Referencias conceptuales: ETAS/Hawkes marcado y Omori normalizado; como implementación pública de contraste, [bruces.modeling.etas](https://keurfonluu.github.io/bruces/api/modeling.html). La simplificación espacial gaussiana se declara expresamente.

## Tiempo, espacio y magnitudes

Unidad temporal: días de86400s; inicio−365, burn[-365,0), evaluación[0,365), H=365. UTC artificial de referencia: t=0 corresponde a2001-01-01T00:00:00Z; el burn empieza exactamente365d antes. No son terremotos históricos. Se conservan t_days y la representación UTC redondeada a microsegundos; no se añade jitter ni se reordena la verdad por el resultado de un detector.

Coordenadas verdaderas en kilómetros cartesianos de una AEQD WGS84 centrada en17°N,99°W. Se obtienen latitud/longitud por transformación inversa AEQD para los comparadores que las exigen; x/y originales permanecen disponibles para NND. Profundidad sintética fija10km, declarada como condición de control y no imputación de datos observados.

Inmigrantes: tasa μ=600/365d⁻¹ sobre todo el intervalo de730d. Espacio estacionario pero no uniforme:

```text
ρ0(x)=.5 φ2(x;(-40,0),15²I)+.5 φ2(x;(40,0),15²I),
φ2(x;a,σ²I)=exp(-||x-a||²/(2σ²))/(2πσ²).
```

Magnitudes independientes con Gutenberg–Richter truncada entre M0=3.5 y Mmax=6.5, b=1. Definir Δ=3 y β=b ln10:

```text
p(m)=β exp[-β(m−M0)]/(1−exp[-βΔ]),  M0≤m≤Mmax;
m=M0−ln[1−U(1−exp(-βΔ))]/β,  U~Uniform[0,1).
```

Es una escala sintética conocida; no se llama Mw ni se utiliza para completar el tipo SSN desconocido.

## ETAS: ramificación y censura del horizonte

Productividad k(m)=K10^[α(m−M0)], α=.5. La esperanza exacta bajo la GR truncada es

```text
E[10^(α(M−M0))] = b/(b−α) * (1−10^(-(b−α)Δ))/(1−10^(-bΔ)),
K = .6 / E[10^(α(M−M0))].
```

Así la razón de ramificación esperada en horizonte infinito es .6, sin forzar tamaños de familias o número total de eventos. Parámetros Omori: c=.001d, θ=.2 (p=1.2):

```text
g(s)=θ c^θ/(s+c)^(1+θ), s>0;
G(L)=1−(c/(c+L))^θ;
∫0∞g(s)ds=1.
```

Para un padre en t_i<H, L=H−t_i. Generar N_i~Poisson(k(m_i)G(L)); los retardos se distribuyen con densidad g/G(L) sobre(0,L), usando

```text
s=c[(1−U G(L))^(-1/θ)−1].
```

No mantener Poisson(k) y después renormalizar todos los hijos al horizonte: multiplicar por G(L) es necesario para conservar la ley censurada correcta. Los desplazamientos son N2(0,5²I)km respecto del padre, simplificación espacial fija del control. Cada hijo vuelve a ramificarse con los mismos parámetros y recibe una magnitud GR independiente.

El fondo inmigrante es estacionario; el proceso ramificado **arranca en−365 sin prehistoria**. Un año de burn no demuestra estacionariedad ETAS. Tampoco se afirma que haya exactamente1500 eventos en evaluación: esa cifra corresponde a la intensidad media ideal infinita600/(1−.6), no al tamaño del catálogo finito. Familias pueden cruzar el inicio o final de evaluación y se conserva esa información.

## Controles y semillas

Desarrollo independiente: ETAS con semilla20261000. Ajustar η0 mediante el procedimiento NN/FD/dos gaussianas de bruces, sin mirar padres/raíces. Congelar ese umbral antes de evaluar; si falla el ajuste se registra el fallo, sin buscar otra semilla.

Diez semillas de evaluación fijas:20261120..20261129. Cada una se utiliza en los tres escenarios:

- ETAS: proceso anterior.
- N0: mismos modelos de inmigración, espacio y magnitud, sin descendientes; cada evento es inmigrante y raíz propia.
- N1: sin descendientes; tasa temporal global .5μ en el primer semestre y1.5μ en el segundo de **cada** año de365d. Bloques[-365,-182.5),[-182.5,0),[0,182.5),[182.5,365). La tasa anual media sigue siendo μ. El espacio y las magnitudes no cambian.

PRNG NumPy PCG64 con SeedSequence([seed,block_code,stream_code]). Fondo compartido block100: stream1 conteo/tiempos,2 espacio,3 magnitudes; descendencia ETAS block200: stream1 conteos,2 retardos,3 magnitudes,4 desplazamientos. N0 conserva exactamente los mismos inmigrantes/posiciones/magnitudes de ETAS. N1 conserva esos inmigrantes y transforma monotonamente los tiempos dentro de cada año: para u uniforme en[0,1), fracción anual resultante2u si u<.25 y .5+(u−.25)/1.5 en otro caso. Esta transformación produce las tasas.5μ/1.5μ conservando el proceso Poisson y empareja el control con el mismo fondo. Se registran códigos y versiones. No se eligen semillas por concordancia. El control secundario observado es **el mismo catálogo reteniendo sólo M≥4.1**, con verdad intacta y sin recalibración elegida por resultados. No se añade otra función de detección distinta a la fijada por protocolo2.

N0/N1 conservan tasa inmigrante600/año, no la tasa total ideal ETAS1500/año; no atribuir diferencias de conteos brutos únicamente al agrupamiento. Informar denominadores y fracciones/F1 además de tamaños. La variación temporal N1 no es desencadenamiento físico.

## Identidades, formatos y evaluación

`events.csv` tiene el esquema básico de los inputs reales más x_km,y_km,t_days,is_eval. Contiene UIDs sintéticos opacos y tipo `synthetic_GR`; **no** padre, raíz o generación. El orden es UTC/UID estable. El NN recibe eventos de burn como contexto y sólo se puntúa is_eval; la observaciónM≥4.1 mantiene su propio contexto censurado.

`truth.csv` conserva por UID: direct_parent_id nullable, root_id, generation, immigrant flag, t_days, is_eval y flags de pertenencia al catálogo observadoM≥4.1. La verdad incluye TODO el burn; no renombrar un hijo como inmigrante porque su padre quede fuera del intervalo o bajo el corte observado. La condición hijo generado y el máximo de magnitud de familia son conceptos diferentes.

`catalogue.json` conserva parámetros, semillas/streams, contadores, hashes, límites y versión del generador. Entradas para cada caso completo y observado se distinguen; la tabla de verdad no se usa para ajustar η0 o escoger parámetros. NN: d1.5,w0,M100, alpha0=0 principal y1.5 sensibilidad; ninguna etiqueta de parentesco interviene en la calibración.

Puntuar agrupado/fondo frente a hijo/inmigrante generado y recuperación de familias sobre registros observados en evaluación. La recuperación de un padre directo sólo es observable cuando ese padre está disponible como entrada; no penalizar como fallo de enlace la ocultación del padre. No puntuar GK o multiplets como si prometieran recuperar padres directos. Toda conclusión es verdad del generador, no validación de identidades reales.

Guardas operativas: máximo20000 eventos por caso y100 generaciones; dispararlas produce fallo registrado, sin truncar silenciosamente ni volver a sortear. Presupuesto global del piloto:4GB/proceso y2h acumuladas de detectores/controles. El generador no produce pronósticos ni calibra peligro. No autoriza cambios Git, publicación o envío.
