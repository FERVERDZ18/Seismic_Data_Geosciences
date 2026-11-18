# Validación nueva del detector2013 sobre sintéticos existentes

16noviembre2026; definido antes de evaluar. No sustituir ni alterar generador,
semillas, datos o resultados anteriores. No atribuir estas historias aMéxico.

Entrenamiento: únicamenteETAS20261000 ya conservado. Evaluación: diez semillas
20261120–20261129, cada una conETAS/N0/N1 conservados. Las tres versiones de una
semilla comparten inmigrantes, no son30observaciones independientes.

Principal: vecino2013esférico d1.6,w1, épocaUTC2016canónica, corte ajustado con
portautoralnormalmix sólo en entrenamiento y congelado en las historias de prueba.
Tres cortes de observación3.5/4.1/4.5. Sensibilidad dimensional predefinida d2 sólo
en4.5, porque la simulación tiene un campo bidimensional; no escoger segúnF1.
Si falla un ajuste se conserva el fallo y no se inventa un umbral. Guardar también
diagnósticoBIC/dosmodos, que no modifica silenciosamente el corte autoral.

Separar dos verdades:

1. Inmigrante vs hijo generado, conocido por el generador. ParaNN, la predicción
   binaria es enlace fuerte a un padre, no “no es el máximo de su familia”. ParaGK
   se reporta asociado respecto al máximo de su ventana; advertir diferencia de
   definición frente a un inmigrante generador. PublicarTP/FP/FN/TN,F1 yFPR.
2. Familias que comparten raíz generadora, restringidas a los eventos observados
   tras cada corte. Su máximo retenido más temprano es principal operativo,
   miembros restantes asociados y familias de un evento aislados. Comparar
   particiones porARI y pares de coagrupamiento; comparar tres roles/marginales.

Determinar la familia verdadera y su máximo sobre toda la historia observada
(incluida historia previa), antes de seleccionar el año evaluado. Los IDs de raíz
latente pueden corresponder a un evento bajo el corte, sin convertirlo en observado.
Los grupos conservan conexiones mediante eventos fuera del año evaluado. EnGK
los aislados tienen IDs distintos, no un grupo cero compartido.

Líneas base: siemprehijo, siempreinmigrante, todosenunafamilia y todosaislados.
F1sin positivos puede ser indefinido; no inventar un valor favorable. Conservar
resultados por caso/semilla, rangos y medias descriptivas; no CIpoblacional de30
experimentos independientes ni afirmación de superioridad general.

También conservar proporción en una familia, que incluye principal, frente a
proporción asociada. Guardar padres, máscaras, grupos, roles, verdad restringida,
denominadores y hashes. Esta evaluación responde aR9; no valida identidades
reales ni desencadenamiento físico en los catálogos observados.
