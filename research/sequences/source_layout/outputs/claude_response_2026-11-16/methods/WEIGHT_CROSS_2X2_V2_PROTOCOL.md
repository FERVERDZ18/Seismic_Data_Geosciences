# Enmienda diagnóstica: cruce2×2 del coeficiente de magnitud

16noviembre2026. Registrado antes de calcular las dos nuevas celdas. Es una
investigación postrevisión de la sensibilidad asimétrica ya observada; no un
prerregistro anterior a conocer los resultados ni una selección del mejor método.

Se mantiene principal d1.6,w1,Mreportada>=4.5. No cambiar título, imágenesv0,
observaciones, pares candidatos o conclusiones para favorecer un coeficiente.

Niveles numéricos fijos:

- Bajo:1.0905428994843476, b_reportadaComCat del desarrollo2016–2020.
- Alto:1.3265675928192793, b_reportadaSSN del mismo desarrollo.

Completar las dos combinaciones por fuente que faltan: SSN con coeficiente bajo
yComCat con coeficiente alto. Reutilizar explícitamente las dos ya conservadas
(SSNalto yComCatbajo) del estudiov2, sin sobrescribirlas. Elcoeficiente transportado
es una opción matemática; no convierteMSSNenMw ni estima una b física común.

Para cada nueva combinación fuente/coeficiente: calcular padres con el mismo
núcleo esférico d1.6 y ordenUTCmicrosegundos/ID; ajustar el normalmixautoral
únicamente en2016–2020 deESAfuente, inicialización original fija; congelar su c
para2021–2025. Ajuste enlog10(TN*RN); corte correcto log10(TN)+log10(RN)<=c.
Guardar padres, roles/componentes, corte, convergencia, pesos, dosmodos/BIC yfallos.
No sustituir un fallo o resultado adverso por otra inicialización, umbral o peso.

Construir los cuatro contrastes SSN/ComCat: bajo/bajo, bajo/alto, alto/bajo y
alto/alto. Reportar matrices,marginales,kappa,ARI y acuerdo sobre889pares completos
y382retenidos2021–2025. Conservar el contraste principalw1 por separado. Estos
son acuerdos entre clasificaciones condicionales, no exactitud o efecto físico.
La operación cambia elcoeficiente junto a su calibración prescrita por desarrollo.

Como diagnóstico de contexto adicional, calcular las dos nuevas combinaciones
sobre los889miembros comunes, conservando el corte de desarrollo nativo de su
fuente/coeficiente: no reajustarlo al reducir miembros. Reutilizar las dos celdas
comunesv2 existentes para completar otro2×2 y etiquetarlo aparte. No llamar
catálogo físico a esa intersección de miembros candidatos.

Todos los resultados van en weight_cross_2x2_v2/. Ningún cambio de sistema,
manuscrito, continuidad compartida, Git o publicación está autorizado por esto.
