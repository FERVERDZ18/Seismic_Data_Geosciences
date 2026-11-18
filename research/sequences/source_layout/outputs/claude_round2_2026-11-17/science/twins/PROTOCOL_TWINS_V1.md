# Gemelos con historia latente compartida — protocolo v1

Fijado después del segundo dictamen y antes de este lote nuevo; **no es un prerregistro prospectivo**. La especificación ejecutable completa es `PROTOCOL_TWINS_V1.json`; `PROTOCOL_SHA256.json` sella ambos archivos antes de generar resultados. Este análisis es privado y no autoriza Git ni publicación.

Se generan 30 historias independientes sin descendencia y 30 con ramificación esperada 0.6. Cada historia conserva padres y raíces conocidos y produce dos observaciones A/B del mismo conjunto latente. Tres historias independientes adicionales de desarrollo fijan el umbral sin mirar la verdad de prueba. No se concatenan historias antes de buscar padres. El presupuesto acotado son 960 celdas B, con error Monte Carlo reportado a nivel de historia; no se detendrá el lote al obtener un resultado favorable.

A conserva los eventos y campos limpios, con magnitud reportada a una décima. B recorre el factorial completo detección, magnitud, posición y reloj (D/M/X/T). El ledger fija de antemano los errores individuales y los reutiliza entre celdas. La celda 0000 comprueba A=B; las cuatro perturbaciones puras y sus combinaciones evalúan cambios no triviales. Intensidades, semilla, fórmulas, límites, ventanas y calibraciones quedan en JSON. Son **supuestos sintéticos, no errores estimados de México ni un ajuste ETAS MLE**.

La identidad latente es la correspondencia principal. El asignador real se ejecuta aparte sin conocer esa identidad y se evalúa con precisión/exhaustividad. Ausencia, magnitud inferior al corte y retención se cuentan por separado, sobre claves de evaluación fijadas. Las familias verdaderas se definen por la raíz generadora observada en cada catálogo y su representante de mayor magnitud retenida. El objetivo hijo/inmigrante conserva el parentesco original, aunque el padre no se observe, y se puntúa aparte.

NN usa la aritmética canónica v3 del método de 2013 y un umbral de desarrollo limpio congelado como análisis principal; los umbrales por celda de desarrollo se reportan como sensibilidad secundaria. GK conserva sus ventanas y semántica explícitas. Se incluyen baselines triviales, métricas por clase, ARI y todos los fallos. Los diagnósticos de mezcla no ocultan resultados operativos estimables. Los resultados adversos anteriores siguen vigentes.

Las interacciones factoriales son contrastes condicionales entre operaciones conocidas. No se transformarán en porcentajes de causalidad física ni se presentará como aporte científico que restaurar exactamente un input produzca su mismo output. Se mostrarán también errores impuestos que no cambien etiquetas, fallos de detección, familias partidas y falsas asociaciones.

No se ejecuta el lote hasta recibir el gate del protocolo maestro y CPU. Las pruebas pequeñas anteriores a ese gate sólo verifican software y no son resultados científicos.
