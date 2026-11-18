# Reanudación sin repetir cuerpos recibidos

17 noviembre2026, después de observar el esquema y antes de análisis científicos.
El adaptadorv2 se selló pero no se ejecutó. Root indicó reutilizar los cuerpos
HTTP200 íntegros en vez de repetir red por una suposición de metadata.count.

Se valida el primer cuerpo2016–2020 de acquisition_02 sobre sus mismos bytes.
Su recibo HTTP original permanece FAIL y no se reetiqueta. Un nuevo recibo sólo
valida esquema/IDs/límite, enlaza hashes del cuerpo y del recibo original e indica
que esa validación es posterior. Su hora de adquisición HTTP sigue siendo la
original. La respuesta2021–2025 nunca se solicitó: se adquiere ahora con los mismos
parámetros prefijados. El manifiesto combinado conserva ambos intervalos HTTP,
sin alegar atomicidad ni cambiar filtros/estimandos. No hay resultados NN/matching.
