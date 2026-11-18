# Control sintético anclado en descriptores de desarrollo, no ajusteETAS

16noviembre2026; autorizado como control adicional dentro del piloto. Este texto
se conserva antes de generar y evaluar. No es un protocolo público ni prospectivo
anterior al dictamen. No sobreescribir sintéticos anteriores ni elegir mejores casos.

Anclas separadasSSN/ComCatMéxico: registros originalesM>=4.5 de2016–2020.
Recalcular antes de generar: N, tasa=N/1827d, bMLE de magnitudes reportadas en bins
0.1conROUND_HALF_UP y corrección−.05, máximoMreportado, extensión de epicentros y
proyecciónWGS84AEQD centrada23.5N,102W. Guardar ANCHOR_PARAMETERS.json antes de
generar. No usar atributos2021–2025, etiquetas, acuerdo o verdad para ajustar nada.

Supuestos no ajustados: inmigrantes Poisson estacionario y espacioKDE de las
coordenadas de desarrollo, con núcleo gaussianoσ25km fijado. Ese ancho no es un
error de localización estimado. Evita convertir la reelección de un mismo punto
empírico en un átomo espacial. MarcasGR truncadas4.5..Mmaxdesarrollo con b_reportada;
productividadα=b/2; tiempoOmori c=.001d,θ=.2; desplazamiento de descendencia
gaussianoσ5km. Estos supuestos no estiman terremotos físicos ni escalamwcomún.

Ramificación ideal n=0,.3,.6,.8, con μ=(1−n)*tasa_totalobservada y constante de
productividad normalizada analíticamente paraGRtruncada. Así las cuatro versiones
comparten intensidadTOTALideal, no tasa de inmigrantes. La intensidad realizada
puede diferir por variabilidad y comienzo finito. Historia10años y evaluación5años,
con365.25d/año. Historia finita no demuestra estacionariedad; sin límites espaciales
o recortes ocultos. El horizonte temporal sícensura descendencia; se declara.

Semilla de entrenamiento independiente2026111600,n=.6porancla. Prueba: semillas
2026111601,2026111602,2026111603×2anclas×4n=24historias. PCG64 con namespace por
ancla,n,semilla yflujo. Sin resembrados ni descartar simulaciones adversas.
Guardas explícitas100generaciones/50000eventos: un aborto es resultado registrado,
no truncamiento silencioso.

DetecciónNN2013d1.6,w1; dos calibraciones predefinidas: (a)corte real de desarrollo
de la fuenteancla y(b)normalmixautoral ajustado sólo a la historia de la simulación
de entrenamiento independiente. Congelar ambos sin usar verdad ni prueba. Si
falla o no hay dosmodos, conservar fallo/diagnóstico, no fallback. TambiénGKfijo.

Medir por separado hijos/inmigrantes generados y familias/roles definidos por raíz
generadora+máximo retenido, como en SYNTHETIC_2013_PROTOCOL.md. PublicarTP/FP/FN/TN,
F1,FPR,marginales,ARIy líneas base triviales. Para n0, la verdad tiene todas las
familias de un evento; no asignarF1positivo cuando es indefinido. Tres semillas son
un barrido descriptivo, no CIpoblacional ni validación deMéxico. Mostrar ambos
cortes, todosn y todas las semillas; no escoger el que dé mejor resultado.
