# Ejecución autoral y reparación R5/R10, 16 noviembre 2026

Este protocolo se fija antes de ejecutar los nuevos resultados observados. No es
prerregistro prospectivo: responde al dictamen recibido y no borra análisis previos.

Conservar el título aprobado, todos los originales v0 y el sistema. La ruta sigue
siendo detección/comparación de secuencias. El adelgazamiento 2020 w=0 queda como
análisis secundario de fondo, no resultado principal de familias ni innovación propia.

Fuentes autorales: dttrugman/Nearest_Neighbor_Cluster,
commit 636d07beb89bde7d7deb502db78beebb45528cca, GPL3. Los .m numéricos descargados
por archivo ZIP se conservan intactos. GNU Octave portátil oficial11.3.0 se ejecuta
sin instalación global y sin escribir otros proyectos. Los shims locales sólo
anulan waitbar, su set Name y su close. No se afirma ejecución en MATLAB.

Método principal: d=1.6, w=1, p=q=.5; el coeficiente de magnitud es operativo sobre
M reportada y no homogeneiza escalas. Entradas originales 2016–2025, M>=4.5.
Desarrollo 2016–2020; evaluación 2021–2025. Se entrega también el análisis completo
descriptivo separado. Ajustar el corte con normalmix_1D.m sólo al desarrollo y
congelarlo en la evaluación; no cambiarlo para mejorar concordancia o verdad.

El wrapper final utiliza UTC transcurrido desde2016-01-01T00:00:00Z/31557600 como años genéricos para ambos
kernels. Esto evita la conversión del cargador eq_cluster year+doy/365.25. bp.m
se ejecuta intacto: tiempo anterior estricto; R=6367.3km; coseno esférico sin clamp;
distancias coincidentes permitidas; n interno en segundos/metros y proximidad
para corte TN*RN en años/km. Las familias del script autoral conservan η=c;
el paper2013 describe η<c. Debe declarar esta convención de borde.

normalmix_1D.m ajusta pesos mediante EM pero calcula la intersección de normales
sin esos pesos; su inicialización es (-6,-3,1,1) y convergencia paramétrica .001.
No llamar equivalente al prototipo propio de posterior ponderado, multistart yBIC.
Reportar c, medias, desviaciones, pesos, distribución de proximidades y cualquier
resultado complejo, no finito, corte fuera de medias o ausencia de dos modos.
Un ajuste inválido se marca no estimable, sin corte de respaldo oculto. No ocultar
las etiquetas que produce el código original en tales casos, pero tampoco darles
validez estadística. Las proximidades/árboles sí pueden ser resultados computacionales.

Sensibilidades predefinidas: d=1.5; coeficiente w igual a bMLE reportada del
desarrollo por fuente; M>=4.1; umbral c±0.5unidadeslog10; intersección ponderada
del prototipo como variante separada. No usar sintéticos/evaluación para elegir.
No se infiere causalidad física ni identidad sísmica validada de un par candidato.

Antes de fijar la época común final, se ejecutaron dos casos de desarrollo con
época Unix. Se conservan sin sobrescribir y se etiquetan exploratorios; el protocolo
previo queda en AUTHOR_2013_PROTOCOL_unixepoch_exploratory.md. La época2016 se fijó
para una resta temporal estable común entre código autoral e índices. No se mezcla
un corte obtenido con una representación temporal con árboles de otra.
