# Consultas en Álgebra Relacional y SQL — Proyecto Asignado (Sismos)

- **Entorno ejecutado:** SQLite-WASM (`sql.js`) integrado en *The Seismic Observatory* (`system/dist/` y GitHub Pages).
- **Tablas utilizadas:** `catalogs` (4 catálogos) y `records` (287,936 registros sísmicos enlazados por `catalogue_id`).

---

## Consulta 1 — Proyección (π)

- **Pregunta:** ¿Cuáles son el identificador, la etiqueta, el proveedor y la huella/corte (`snapshot`) de cada catálogo sísmico cargado en el observatorio?
- **Operador principal:** Proyección ($\pi$).
- **Expresión en Álgebra Relacional:**

$$\pi_{\text{catalogue\_id},\; \text{label},\; \text{provider},\; \text{snapshot}}(\text{catalogs})$$

- **Árbol de operadores:**
  ```text
  π (catalogue_id, label, provider, snapshot)
                      │
                  catalogs
  ```
- **SQL equivalente:**
  ```sql
  SELECT DISTINCT catalogue_id, label, provider, snapshot
  FROM catalogs;
  ```
- **Expresión en RelaX:**
  ```text
  pi catalogue_id, label, provider, snapshot (catalogs)
  ```
- **Correspondencia SQL ↔ Álgebra:** `FROM catalogs` representa la relación base (hoja del árbol) y `SELECT DISTINCT` ejecuta la proyección $\pi$, reteniendo únicamente las 4 columnas de interés y descartando campos adicionales como `source_hash` y `manifest_hash`.
- **Resultados obtenidos en SQLite-WASM (4 filas):**

| catalogue_id | label | provider | snapshot |
|---|---|---|---|
| `nrcan-ca-historical` | Canada and surroundings · 1985–2019 | `nrcan` | `sha256:f10b91ddbc683406e2f1a642aa8a15fba3d1b46eef3a775f2798cfdc75a31241` |
| `ssn-mx-historical` | Mexico · direct SSN · 1900–2026 | `ssn` | `sha256:0601c65544bc95ef865d3440e5e6d84249acdebd8edfb379669597096543f993` |
| `usgs-mx-historical` | Mexico region · paper snapshot | `usgs` | `8fe055ffe635875f7290906d45f70562a7896621` |
| `usgs-na-2020-2025` | North America · 2020–2025 | `usgs` | `8fe055ffe635875f7290906d45f70562a7896621` |

---

## Consulta 2 — Selección compuesta (σ)

- **Pregunta:** ¿Qué sismos del catálogo histórico del SSN (`ssn-mx-historical`) registrados a partir del año 2000 tuvieron una magnitud reportada mayor o igual a 7.5, mostrando su clave, fecha UTC, año y magnitud?
- **Operador principal:** Selección ($\sigma$) con predicado compuesto (`AND`).
- **Expresión en Álgebra Relacional:**

$$\pi_{\text{record\_key},\; \text{time},\; \text{year},\; \text{mag}}\Big(\sigma_{\text{catalogue\_id} = \text{'ssn-mx-historical'} \;\land\; \text{year} \ge 2000 \;\land\; \text{mag} \ge 7.5}(\text{records})\Big)$$

- **Árbol de operadores:**
  ```text
  π (record_key, time, year, mag)
                 │
  σ (catalogue_id = 'ssn-mx-historical' ∧ year >= 2000 ∧ mag >= 7.5)
                 │
              records
  ```
- **SQL equivalente:**
  ```sql
  SELECT record_key, time, year, mag
  FROM records
  WHERE catalogue_id = 'ssn-mx-historical'
    AND year >= 2000
    AND mag >= 7.5
  ORDER BY mag DESC, time ASC;
  ```
- **Expresión en RelaX:**
  ```text
  pi record_key, time, year, mag (
    sigma catalogue_id = 'ssn-mx-historical' and year >= 2000 and mag >= 7.5 (records)
  )
  ```
- **Correspondencia SQL ↔ Álgebra:** `FROM records` carga la relación base; `WHERE` aplica la selección $\sigma$ filtrando por agencia (`ssn-mx-historical`), periodo (`year >= 2000`) y umbral de magnitud (`mag >= 7.5`); `SELECT` ejecuta la proyección $\pi$ de las 4 columnas resultantes.
- **Resultados obtenidos en SQLite-WASM y en RelaX (4 filas exactas):**

| record_key | time | year | mag | Contexto en el manuscrito R3 |
|---|---|---|---|---|
| `ssn-mx-historical~ssn-local-3ec35ed592c96fcdf1d59319-1` | `2017-09-08T04:49:17Z` | 2017 | 8.2 | Evento ancla de Tehuantepec 2017 |
| `ssn-mx-historical~ssn-local-92077fb37af89cbe196caaed-1` | `2022-09-19T18:05:09Z` | 2022 | 7.7 | Evento ancla de Michoacán 2022 |
| `ssn-mx-historical~ssn-local-3c50f3a6ad66a0149a30c3a9-1` | `2003-01-22T02:06:34Z` | 2003 | 7.6 | Sismo de Tecomán, Colima 2003 |
| `ssn-mx-historical~ssn-local-0810ba4db13d973f71d10344-1` | `2012-03-20T18:02:48Z` | 2012 | 7.5 | Sismo de Ometepec, Guerrero 2012 |

---

## Consulta 3 — Reunión (⋈)

- **Pregunta:** ¿A qué catálogo y agencia proveedora pertenece cada sismo con magnitud reportada mayor o igual a 7.5, mostrando su clave, fecha UTC, año, magnitud, tipo de magnitud, etiqueta del catálogo y proveedor?
- **Operador principal:** Reunión ($\bowtie$) entre `records` y `catalogs` mediante `catalogue_id`.
- **Expresión en Álgebra Relacional:**

$$\pi_{r.\text{record\_key},\; r.\text{time},\; r.\text{year},\; r.\text{mag},\; r.\text{mag\_type},\; c.\text{label},\; c.\text{provider}}\Big(\sigma_{\text{mag} \ge 7.5}(\rho_r(\text{records})) \bowtie_{r.\text{catalogue\_id} = c.\text{catalogue\_id}} \rho_c(\text{catalogs})\Big)$$

- **Árbol de operadores:**
  ```text
  π (r.record_key, r.time, r.year, r.mag, r.mag_type, c.label, c.provider)
                                     │
                   ⋈ (r.catalogue_id = c.catalogue_id)
                        ╱                       ╲
             σ (mag >= 7.5)                 ρ_c (catalogs)
                   │
             ρ_r (records)
  ```
- **SQL equivalente:**
  ```sql
  SELECT r.record_key, r.time, r.year, r.mag, r.mag_type, c.label, c.provider
  FROM records r
  JOIN catalogs c ON r.catalogue_id = c.catalogue_id
  WHERE r.mag >= 7.5
  ORDER BY r.mag DESC, r.time ASC;
  ```
- **Expresión en RelaX:**
  ```text
  pi r.record_key, r.time, r.year, r.mag, r.mag_type, c.label, c.provider (
    (sigma mag >= 7.5 (rho r (records)))
    join r.catalogue_id = c.catalogue_id
    rho c (catalogs)
  )
  ```
- **Correspondencia SQL ↔ Álgebra:** `records r` y `catalogs c` corresponden al renombramiento ($\rho$); `JOIN ... ON r.catalogue_id = c.catalogue_id` realiza la reunión ($\bowtie$); `WHERE r.mag >= 7.5` aplica la selección ($\sigma$) empujada hacia la hoja de `records` en el árbol para reducir tuplas antes de cruzar; `SELECT` ejecuta la proyección final ($\pi$).
- **Resultados obtenidos en SQLite-WASM (61 filas totales: 26 SSN, 26 USGS-MX, 6 USGS-NA, 3 NRCan; se muestran las 10 de mayor magnitud):**

| record_key | time | year | mag | mag_type | label | provider |
|---|---|---|---|---|---|---|
| `ssn-mx-historical~ssn-local-21e02f842b5c108f04633023-1` | `1932-06-03T10:36:52Z` | 1932 | 8.20 | `NULL` | Mexico · direct SSN · 1900–2026 | `ssn` |
| `ssn-mx-historical~ssn-local-3ec35ed592c96fcdf1d59319-1` | `2017-09-08T04:49:17Z` | 2017 | 8.20 | `NULL` | Mexico · direct SSN · 1900–2026 | `ssn` |
| `usgs-mx-historical~us2000ahv0` | `2017-09-08T04:49:19.180Z` | 2017 | 8.20 | `mww` | Mexico region · paper snapshot | `usgs` |
| `usgs-na-2020-2025~ak0219neiszm` | `2021-07-29T06:15:49.188Z` | 2021 | 8.20 | `mww` | North America · 2020–2025 | `usgs` |
| `usgs-mx-historical~iscgem906183` | `1932-06-03T10:36:58.080Z` | 1932 | 8.10 | `mw` | Mexico region · paper snapshot | `usgs` |
| `ssn-mx-historical~ssn-local-1df5c2fe2815950a5391ae33-1` | `1985-09-19T13:17:49Z` | 1985 | 8.10 | `NULL` | Mexico · direct SSN · 1900–2026 | `ssn` |
| `usgs-mx-historical~usp0002jwe` | `1985-09-19T13:17:47.350Z` | 1985 | 8.00 | `mw` | Mexico region · paper snapshot | `usgs` |
| `usgs-mx-historical~usp00074vc` | `1995-10-09T15:35:53.910Z` | 1995 | 8.00 | `mw` | Mexico region · paper snapshot | `usgs` |
| `ssn-mx-historical~ssn-local-08e872b32e8352d85578f58e-1` | `1995-10-09T15:35:54Z` | 1995 | 8.00 | `NULL` | Mexico · direct SSN · 1900–2026 | `ssn` |
| `usgs-mx-historical~iscgem908744` | `1928-06-17T03:19:32.370Z` | 1928 | 7.99 | `mw` | Mexico region · paper snapshot | `usgs` |

> **Observación analítica vinculada al artículo R3:** En los resultados reales se aprecian eventos duplicados entre agencias con diferencias de magnitud y metadatos: por ejemplo, Tehuantepec 2017 aparece en SSN como `8.2` con `mag_type = NULL` y en USGS-MX como `8.2` (`mww`); Michoacán 2022 aparece en SSN como `7.7` (`NULL`) y en USGS-MX/USGS-NA como `7.6` (`mww`); y México 1985 como `8.1` (`NULL`) en SSN frente a `8.0` (`mw`) en USGS-MX.
