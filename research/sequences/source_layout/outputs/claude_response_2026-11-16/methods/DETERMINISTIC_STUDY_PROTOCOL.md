# Estudio determinista tras el dictamen, 16 noviembre2026

Especificado antes de los resultados de este nuevo estudio. No es prerregistro
prospectivo ni nueva autorización de publicación. Resultados previos se conservan.

El método principal es2013autoral d1.6,w1, selecciónMreportada>=4.5. Sensibilidades
M>=4.4/4.1, d1.5 y w=bMLE reportada por fuente sobre desarrollo. La selección4.5es
operativa; no certifica completitud, Mw común ni causalidad de las familias.

Cada entrada usaUTCmicrosegundos enteros menos2016-01-01, dividido por1e6 y31557600;
orden UTC,IDUTF8. El índice esférico nuevo se contrasta separadamente con código
autoral realGNUOctave y enumeración, no con el kernelAEQD anterior. Se conserva el
clamp de acos como adaptación numérica declarada; tiempo padre estricto y ceros
espaciales permitidos. Usar log10(TN*RN) al ajustar y log10(TN)+log10(RN) al cortar.
La convención autoral conserva igualdad con c. Índices/padres no son verdad física.

Ajustar normalmix_1D sólo en2016–2020 y congelar c para2021–2025. El portGPL se
contrasta conOctave, sin retocar la inicialización fija−6,−3/σ1,1 y la frontera sin
pesos que tiene el código autoral. Se reportan umbrales, convergencia y fallos; no
se usa una frontera alternativa cuando falla. Diagnosticar dos modos/BIC y reportar
si no apoyan la separación aunque el código original produzca una frontera.

Para cada corte, fuente y parametrización, ejecutar el catálogo original retenido
(native) y el mismo conjunto de pares candidatos retenidos en ambas fuentes
(common). No llamar a common un nuevo catálogo físico. En common evaluar por
separado el corte nativo congelado y el reajuste sólo sobre desarrollo común.

Se publican las comparaciones completas descriptivas y el subconjunto2021–2025:
matriz3×3, marginales, kappa, acuerdo de rol, ARI y precisión/recobrado de pares de
coagrupamiento. Las últimas métricas comparan particiones de catálogos, NO verdad
ni exactitud. Conservar todas las raíces de la partición original al restringir a
IDs comunes; no partir grupos que se conecten mediante registros de contexto.
Reportar denominadores por año y pérdidas de selección.

Factorial de mediciones sobre miembros comunesM4.5: ocho combinaciones de tiempo,
ubicación(lat+lon) yM reportada SSN/ComCat, sobre los mismos IDs canónicos. La
inclusión y el periodo de evaluación se fijan por los registrosSSN originales;
intervenir no vuelve a seleccionar los eventos. Aplicar por separado los dos
cortes nativos congeladosSSN/ComCat:16celdas. No reajustar al comparar esos factores.
Mismo d1.6,w1. Los híbridos son intervenciones computacionales etiquetadas, no
observaciones nuevas ni prueba de qué agencia tiene razón. El cambio de contexto
(native→common) se compara sin cambiar mediciones o corte.

No se calculan p de “mejor agencia” ni intervalos basados en supuesta independencia
de eventos o pares. Cinco años retenidos y un contraste regional limitan
generalización. Ambos resultados adversos y fallos permanecen visibles.

Extensión de calibración solicitada antes de ejecutar: exportar calibration.json
con los cortes4.5/4.4/4.1/3.5 paraSSN,ComCatMéxico yAlaskaComCat. El3.5sólo requiere
proximidades/ajuste de desarrollo, no factoriales adicionales. ParaAlaska el
desarrollo es2020–2022 y la evaluación2023–2025, con épocaUTC2016común. Es
transferencia entre métodos en una fuente, no segundo contraste entre agencias.
No inventar un corte si falla. El esquema conserva status, ajuste y diagnósticos.
