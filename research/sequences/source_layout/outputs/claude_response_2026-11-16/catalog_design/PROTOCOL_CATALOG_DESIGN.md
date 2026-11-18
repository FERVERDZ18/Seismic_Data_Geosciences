# Protocolo local de contraste R6–R8 y R11

Fijado el 16 de noviembre de 2026, antes de ejecutar los experimentos nuevos.
Este trabajo es una respuesta a crítica conocida; no es un registro prospectivo
del piloto original ni evidencia independiente de sus hipótesis.

## Alcance e invariantes

- Sólo entradas y resultados retenidos en el repositorio. Sin nueva cohorte ISC,
  sin catálogo externo adicional y sin calibración arbitraria a Mw.
- Las 2,989 asignaciones de la ventana principal son asociaciones candidatas;
  GEM no es una verdad de identidad y sus ocho ventanas secundarias canceladas
  no se presentarán como ejecutadas.
- Magnitud reportada >= 4.5 es el análisis principal nuevo; >= 4.1 es sensibilidad.
  Ninguno de esos cortes certifica completitud física ni iguala escalas de magnitud.
- No se cambian entradas, protocolos o recibos antiguos. Se enlazan sus hashes.
- Los intercambios y adelgazamientos son intervenciones computacionales, no
  observaciones sísmicas ni estimaciones causales de procesos tectónicos.
- No se seleccionan semillas, ventanas o casos por mejorar concordancia.

## Descriptores y controles ya existentes

Se extraen conteos por tipo de magnitud y agencia de origen ComCat; SSN mantiene
tipo ausente cuando no lo suministró la captura. La geografía usa el índice
terrestre Natural Earth existente y validado por hash + identidad de fila. Sus
etiquetas son diagnósticos de posición, **no** cobertura instrumental: mar afuera
no significa fuera de la cobertura SSN y no se descartan esos eventos.

Las diferencias de magnitud y sus cortes se calculan con Decimal sobre cadenas
de entrada. Los cuantiles descriptivos usan interpolación lineal; ninguna
fracción de pares se llama precisión, exhaustividad o validación de identidad.
Los b aparentes de las distribuciones retenidas usan Aki–Utsu para bins de 0.1
con corrección de media de bin; el ajuste acumulado GFT se muestra junto a b.
Se distingue ese cálculo de una pendiente deducida de dos conteos agregados.

## Factorial GK con conjunto común fijo

Para cada corte se retienen sólo pares que cumplen el corte en ambas fuentes.
No se reestima el matching. Hay tres factores binarios:

1. magnitud reportada del registro SSN o ComCat;
2. coordenadas epicentrales del registro SSN o ComCat;
3. tiempo UTC del registro SSN o ComCat.

Se ejecutan las ocho combinaciones completas usando el mismo GK continuo
existente (fracción precursora 0.5; radio terrestre 6371.0088 km; ventanas y
comparadores inclusivos originales). Cada combinación se repite con dos claves
de desempate: ID de procedencia SSN y ID de procedencia ComCat. La clave no
reescribe ningún ID observado: sólo fija el orden de entrada a magnitud/UTC
idénticos. Se añade una clave común de pareja como control. Se registra la tabla
completa de roles y los cambios de cada arista del cubo, no sólo el mejor cambio.
Las comparaciones de endpoints incluyen el mismo conjunto y no pueden atribuir
una diferencia de membresía a magnitud o ubicación.

Se comprueba que el endpoint SSN y ComCat con sus claves nativas reproduce los
roles C >=4.1 ya guardados. Con >=4.5, los resultados de los catálogos nativos
completos D45 se proyectan al mismo núcleo para distinguir su contexto de los
catálogos comunes rerun. Las interacciones son descriptivas y no se anuncian como
nueva técnica de atribución.

## Adelgazamiento controlado del contexto SSN

Para cada corte, se mantiene completo el núcleo común de pares evaluables. Se
retiran únicamente registros SSN fuera de ese núcleo. Se prueban fracciones de
retención de contexto 0, 0.25, 0.50, 0.75 y 1.00, 20 repeticiones predeterminadas
por fracción intermedia, con semillas 2026111600 a 2026111619. Selección uniforme
sin reemplazo, hash/semilla fijados; no se elige un resultado favorable.

La variable de respuesta es la distribución de cambios de rol sobre el núcleo
fijo, además de concordancia contra ComCat nativo y ComCat común. La condición
0 carece de variación aleatoria por construcción; no se interpreta como prueba
independiente. No se iguala una densidad regional de detección por reducir al azar
un catálogo, y el adelgazamiento no simula automáticamente fallos transitorios
postevento ni errores de magnitud/posición. Este experimento no modifica el
componente de evaluación ni sus parámetros.

## Sensibilidad de asociación y control temporal negativo

Se publican las nueve ventanas ya ejecutadas: tiempos 10,30,60 s y distancias
10,50,100 km. Para la ventana principal 30 s/50 km se ejecuta además el mismo
asignador uno-a-uno a máxima cardinalidad/coste mínimo, desplazando todos los
tiempos ComCat de modo circular dentro del intervalo [2016-01-01,2026-01-01), por
los diez desplazamientos predefinidos: -90,-60,-30,-14,-7,+7,+14,+30,+60,+90 días.
Se preservan epicentros y magnitudes. Se reporta el conteo completo de candidatos
y asignaciones de cada desplazamiento, con el coste temporal original; la
discontinuidad circular se documenta. Se añade sensibilidad de las asignaciones
originales en sus bordes (distancia y tiempo).

El desplazamiento es un **control negativo computacional**, no estimador de la
tasa de falsos emparejamientos reales: destruye relaciones de secuencia y puede
cambiar su densidad temporal local; sin identidades revisadas no hay precisión o
recall de identidad. No se excluyen pares del análisis por el resultado del nulo.

## Selección determinista de casos para nuevas figuras

Se proponen los máximos de magnitud reportada ComCat en los años 2017 y 2022,
dentro del rectángulo ya retenido, con desempate por UTC y luego ID. Son ejemplos
de secuencias ancladas, no una selección por concordancia. Ventana descriptiva
común: -7 a +30 días y 150 km alrededor del ancla ComCat; panel adicional de
sensibilidad 300 km si se ocultan sismos grandes relacionados regionalmente.
Ambos catálogos muestran sus coordenadas originales, magnitudes originales,
casos no emparejados, y vínculos candidatos sin convertirlos en identidades.

Se ilustrarán: (i) mapas de pares/no pares y roles discordantes, (ii) FMD y b/ajuste
por corte/tipo/origen y año, (iii) mapa + tiempo/magnitud de los dos casos. Todas
las imágenes v0 se conservan; estas figuras explican la nueva pregunta científica.

## Ejecución y límites

El protocolo se guarda con hash antes del lote. Cada comando se limita a menos
de 60 s o se fragmenta; se coordina CPU con el agente del benchmark de índices.
No se usan los tiempos de estos lotes compartidos como resultados de rendimiento.
Una respuesta metodológica correcta no garantiza aceptación editorial.
