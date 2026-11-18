# Protocolo de validación del catálogo, segunda revisión

Fecha: 17 noviembre 2026. Análisis postrevisión autorizado por Gabriel; no es
prerregistro prospectivo, prueba ciega, validación física ni permiso de publicar.
Esta especificación se sella antes de nuevos resultados en esta lane. Se conservan
las entradas y resultados anteriores, el título y todas las imágenes de v0.

## Entradas y contrato numérico

Se usan exclusivamente snapshots locales ya conservados, con SHA256 en
`INPUTS.json`. México: SSN y ComCat 2016–2025, rectángulo lat[14,33],
lon[−118,−86], filtro decimal sobre magnitud reportada ≥4.5. No se certifica
completitud común ni se homogeneizan magnitudes. Los 2,989 enlaces son
asignaciones candidatas, sin adjudicación de identidad física. No hay descargas.

El cálculo NN reproduce v3: tiempo UTC en microsegundos y orden tiempo/ID UTF8,
esfera R=6367.3 km, d=1.6, q=.5, padre estrictamente anterior; inicialización y
frontera sin pesos de `author_normalmix_port.py` sin sustitución de fallos.
Ajustar con log10(TN*RN); cortar con log10(TN)+log10(RN)≤c. Conservar arrays
parentales y TN/RN, IDs y filas fuente para auditar la aritmética efectiva.
Copias versionadas de los kernels, clasificadores y licencias quedan en vendor/;
las únicas adaptaciones permitidas son localización de dependencias/cachés.

## S4: barrido completo y sensibilidad de frontera

Cada fuente se ejecuta con w∈{0.8,0.9,1,1.1,1.2,1.3,1.4,
1.0905428994843476,1.3265675928192793}. Los dos valores adicionales son b
aparentes de ComCat y SSN ya retenidos, no una calibración física común. No se
selecciona un peso ganador ni se elimina un resultado adverso. Los nueve valores
se aplican a ambas fuentes; además se presentan los cuatro cruces b×b y el
contraste b propio. El mismo w en ambas fuentes es un contraste distinto al de b
propio. Principal: w=1, sin cambiarlo según los resultados.

Para cada fuente/peso: ajustar únicamente eventos de desarrollo 2016–2020,
congelar c y evaluar 2021–2025. Reportar convergencia, corte, pesos/medias/sigmas,
BIC con 2/5 parámetros, número de modos y todos los fallos. BIC/modalidad son
diagnósticos de ajuste, no prueba de causalidad; no reemplazan el corte autoral.
Sensibilidad separada δ∈{−.5,0,+.5}: conservar padres y usar c(w)+δ. El contraste
principal se reproduce contra los arrays v3 conservados y sus IDs, padres y roles.

En cada caso: matrices 3×3, marginales, acuerdo, kappa, ARI de particiones,
Jaccard y F1 simétrico por clase; denominadores/roles nativos; número de familias,
tamaño/fracción máxima, duraciones y hueco temporal consecutivo máximo dentro
de cada componente no unitaria. Exportar todas las etiquetas y métricas, no sólo
agregados. Las clases son aislado, representante operativo y asociado, sin
interpretación causal de principal/réplica.

## S5: estimandos, cobertura y dependencia

El estimando principal es acuerdo de roles entre endpoints de candidatos donde
ambas magnitudes pasan4.5. Resultados completos2016–25 y temporales2021–25 se
separan; desarrollo2016–20 no es prueba externa. Se presentan todos los años.
La cobertura usa cada denominador nativo seleccionado. Distinguir ambos pasan,
sólo SSN pasa, sólo ComCat pasa, ninguno pasa y seleccionados sin asignación.
Los miembros bajo corte no reciben una clase ≥4.5. No inflar el acuerdo con los
pares excluidos/excluidos ni llamar a cobertura exactitud de matching.

Unidades dependientes, fijadas desde el principal w=1,δ=0: enlazar todos los
miembros de cada componente nativa SSN y ComCat; unir ambos endpoints de cada
candidato que pasa4.5 en ambas fuentes. Las componentes de esta unión definen
unidades compartidas simétricas. Cada unidad conserva todos sus pares. Estas
unidades permanecen fijas para comparar pesos y cortes; no se reconstruyen para
favorecer cada variante. Publicar IDs de unidad, tamaños, mayor fracción y número
efectivo1/Σp². Reportar también unidades restringidas a cada periodo.

Bootstrap de unidades: B=2000, NumPy PCG64 semilla20261117, muestreo uniforme
con reemplazo de tantas unidades como unidades no vacías del estimando temporal.
Cada copia conserva sus pares; se calcula la razón de sumas, no la media de
acuerdos de unidades. Percentiles2.5/97.5 con interpolación lineal para acuerdo,
kappa y Jaccard/F1 por clase; diferencias pareadas de acuerdo frente al principal
con los mismos sorteos. ARI se reporta puntual. No bootstrap iid de pares.
Estos intervalos son sensibilidad de remuestreo condicionada a snapshot, matching,
pesos/ajustes y etiquetas; no tienen cobertura nominal demostrada ni cubren
identidad física, completitud o incertidumbre del ajuste. Señalar explícitamente
fragilidad si hay menos10unidades o la mayor supera50%; no ocultar el intervalo.

Exclusión2017 fija: ancla = mayor magnitud ComCat retenida en2017, empate por
UTC/ID. Tomar su candidata SSN, cuando exista. Congelar la unión de sus dos
familias nativas principales w1,δ0; excluir un par si cualquiera de sus endpoints
pertenece a esa unión. Conservar exactamente esa lista en todo el barrido.
Sólo proyectar clasificaciones completas: no eliminar contexto/reclasificar ni
llamar al resultado un catálogo sin2017. Reportar tamaño y cronología de la unión.

## S6: ventanas candidatas y borde geográfico

Recrear las nueve asignaciones ya definidas: Δt∈{10,30,60}s,
r∈{10,50,100}km, mismo matching óptimo y predicados/normalización de costes.
Comprobar conteos contra los recibos anteriores. Exportar cada lista de enlaces.
Proyectar únicamente roles/particiones NN nativos principales ya calculados, sin
reajustar NN al cambiar ventana. Reportar matriz, cobertura, acuerdo y solapamiento
de identidades candidatas; no elegir ventana según acuerdo. Si los enlaces viejos
no están serializados, regenerarlos es ejecución del contrato anterior, no nueva
búsqueda de ventana.

Geografía≥4.5: todas/ambos pasan/contraparte bajo corte/sin asignación por país
terrestre conservado, año y fuente. «Fuera de tierra» no significa fuera de red.
Sensibilidad de borde existente: proyectar pares cuyos DOS endpoints estén en el
rectángulo interior lat[14.5,32.5],lon[−117.5,−86.5], y por separado ambos en
lat≥14.5. Mantener contexto completo y cortes principales; no afirmar que estos
controles reparan contexto truncado ni describen cobertura instrumental.
Documentar explícitamente que el círculo150km de2017 cruza14N. Resolver ese
recorte mediante extensión ComCat requiere nueva cohorte/consulta y control de
revisiones contra el snapshot anterior; no se realiza ni se supone aquí.

## S8: resultados retenidos y transferencia monocatálogo

Extraer las16celdas factoriales v3 (ocho sustituciones UTC/epicentro/M×dos cortes)
y diez años desde los JSON conservados, con SHA. Expresar como sustituciones
computacionales bajo el mismo corte, no aportes causales aditivos ni observaciones
nuevas. Tabla anual principal con todos los denominadores y clases.

Alaska: Mreportada≥4.5, entrada2020–25 existente; desarrollo2020–22,
evaluación2023–25, umbral NN retenido y familias completas de paridad. Exportar
resultados temporales y por año desde esas etiquetas. Ejecutar GK≥4.5 sobre la
entrada seleccionada con implementación retenida y comprobar indexado/exhaustivo
sobre los555registros si son esos los IDs reales. Comparar NN/GK por matriz y
ARI, sin truth, sin segunda agencia ni validación causal. No filtrar etiquetas
GK3.5/4.1 para fingir GK4.5. Si faltan datos/IDs incompatibles, conservar el fallo.

## Ejecución, pruebas y recibos

No ejecutar cargas científicas hasta autorización de CPU de root. Las pruebas
pequeñas verifican inclusividad/frontera, denominadores, Jaccard, unidades
compartidas mediante contexto, bootstrap pareado y fallos vacíos. Los resultados
irán a un directorio de corrida nuevo; se prohíbe sobrescribir incluso fallos.
Guardar protocolo sellado y hash, manifiesto de entradas/código, entorno,
inicio/fin, todos los arrays y fallos, pruebas y recibo de salidas con SHA256.
Comprobar hashes de entradas al principio/final. Sin edición pública, manuscrito,
continuidad, Git, commit, push ni publicación por esta lane.
