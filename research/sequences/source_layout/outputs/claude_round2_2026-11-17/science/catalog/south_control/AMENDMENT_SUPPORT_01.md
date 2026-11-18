# Soporte geográfico observado, condicionado al desarrollo

17 noviembre2026. Especificación posterior al estudio global y a la recepción de
los cuerpos HTTP, pero ANTES de inspeccionar los nuevos conteos por banda/celda o
calcular NN/matching sobre ellos. No se presenta como diseño prospectivo.

Para cada resolución fija0.5°,1°,2°, usar rejilla de origen(lon−180,lat−90).
Retener celdas con al menos una observación Mreportada≥3.5 de CADA fuente en
2016–2020 de cohorteC(lat12–33,lon−118–−86). Congelar esas celdas para evaluar
2021–2025. No elegir una resolución favorable ni usar evaluación para elegir celdas.
No renovar SSN ni usar observaciones imputadas. Reportar todas las celdas, sus
conteos de desarrollo por fuente, geometría y denominadores de evaluación.

Celdas semiabiertas hacia el extremo mayor. Un punto exactamente en el máximo
cerrado del dominio33N o−86E se asigna a la última celda interior. Exportar la
unión como capa GeoJSON de polígonos de celda sin solapamiento de área, recortados
al rectánguloC, con esa regla de pertenencia explícita; conservar también claves
enteras de rejilla y pertenencia por registro. Incluir tierra y mar sin filtro.

Dos contrastes separados por resolución:

1. Proyectar roles/particionesC completos en las asignacionesC donde AMBOS
   endpoints≥4.5 estén en la unión de celdas. Pueden ocupar celdas distintas.
   Se conservan contexto, parámetros y cortesC originales.
2. Restringir entradas NN de cada fuente a registros≥4.5 dentro de esas mismas
   celdas; recalcular padres con d1.6,w1,q.5 y transportar el corteC de ESA fuente,
   sin reajuste. Proyectar sobre exactamente los mismos pares del contraste1.
   Si una subcohorte es vacía, conservar arrays vacíos y not_estimable; no fallback.

Las asignaciones se mantienenC, calculadas a30s/50km sobre≥3.5 antes de máscara;
no se reasignan ni se optimiza el acuerdo. Reportar cobertura sobre todos los
seleccionados≥4.5 dentro de máscara y, separadamente, contraparte bajo corte,
contraparte fuera de máscara, ambos atributos conjuntos y sin asignaciónC.
Exportar matrices, Jaccard/F1 de clases y ARI completos y temporales; cambios de
padre/rol por fuente entre contextoC completo y restringido, con denominadores.

La capa describe soporte OBSERVADO de ambas fuentes durante desarrollo: NO es
máscara de cobertura instrumental, detección o completitud; una observación no
certifica esas propiedades. Tampoco adjudica identidad física de candidatos ni
independencia entre redes. Condiciona selección espacial después del estudio global
y puede truncar artificialmente el contexto NN; no llamar a la restricción una
mejora de exactitud, una validación causal o un catálogo regional completo.
