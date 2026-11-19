# Seismic scientific reproduction package

**Audited scientific reproduction package for the article.** The six scientific stages were recalculated in a new isolated environment and copied workspace, with strict scientific comparisons. An additional1221 frozen synthetic-array/metric comparisons passed. Historical GEM evidence/counts and the ten shifts passed separately; persisted V3 arrays were revalidated with18 computed cells and6 preserved censures. Sixteen security/provenance fixtures passed. See [QA_SUMMARY.json](QA_SUMMARY.json) for the verified replay scope and platform.

The package supports the approved article title in `CITATION.cff`. José Manuel Villa Vargas remains first, without an institutional affiliation; Gabriel Hurtado Avilés is second and corresponding author. Current/v0 figure assets and private paper/Word/PDF sources are outside this numerical package. Existing sites and historical repositories are unaffected.

Browse [all readable scientific sources/configuration](SOURCE_INDEX.md), [component licenses](LICENSES_MAP.json), [table producers](TABLE_SOURCE_MAP.json) and [the comparison contract](EXPECTED_COMPARISON_CONTRACT.json). Numerical sources, small configurations, original licenses and documentation are plain files; data ZIPs are not needed to inspect code.

The [additional sequence analyses](r3/README.md) reproduce the article's weight and cutoff sensitivity, magnitude and distance strata, paired 2017 counts, empirical synthetic perturbations, chance-adjusted agreement and matched benchmark projection.

## Package contents

Readable selected scientific sources, original component licenses, frozen observations, protocols/seeds, shared latent truth/observation ledgers, expected scientific arrays/metrics/tables and a hash-checked logical-path-to-content map. Input/result blobs are deduplicated by SHA256 and stored in deterministic ZIP chunks. Every ZIP remains below95,000,000 bytes; a source file larger than a chunk is reconstructed from independently verified parts. Data archives are not executables.

`source_layout/` preserves the original relative project paths so import/routing dependencies remain inspectable. Its numerical sources are copied byte for byte. The consumer's `--workdir` must be a new independent folder outside any Git checkout and outside this package. The materializer never overwrites or deletes an existing folder, never extracts untrusted ZIP paths, and creates a small compatibility `AGENTS.md` sentinel only in that new workspace. No actual project instructions, private context, chats, reviewer reports, permissions or prompts are included.

`expected/` is materialized separately from executable output destinations. Expected results are never relabeled as a fresh calculation. Explicit older generated checkpoints remain identified as such; a separate legacy-v3 replay checks the supplied principal checkpoints. The current package does not claim to regenerate every historical exploratory output or every original figure.

## Environment and commands

First target: Windows x64, CPython3.12.14, and the exact dependency versions/hash lock supplied with the package. Create the environment locally, outside a source checkout. The corresponding clean-environment profiles and exact verification scope are recorded in `QA_SUMMARY.json`.

```powershell
python -m venv C:\seismic-replay-env
C:\seismic-replay-env\Scripts\python.exe -m pip install --require-hashes -r requirements-r2.lock
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --verify
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --replay-science --node node --workdir C:\seismic-independent-run
```

Use a writable personal location instead of the illustrative `C:\` directories where necessary. No software is installed globally. Child processes disable user site packages and remove `PYTHONPATH`/`PYTHONHOME`. Dependency versions are inspected with `importlib.metadata` before numerical imports. The scientific run uses the supplied frozen data without contacting catalogue services. A later live query cannot reproduce the old snapshot.

`--replay-science` runs the fixed stages in `science_pipeline.json`: legacy-v3 verification, catalogue sensitivity, shared-truth twins, southern support controls, zero-distance diagnostics and36 indexed observed-parent/Node cases. It recomputes parents/roles/metrics from supplied frozen inputs and compares complete selected scientific arrays/tables. The indexed controller reuses unchanged numerical workers and summary code; it does not rerun the eight full170880-event exhaustive weight references. Complete original reference outputs and benchmark observations remain supplied as identified expected evidence. Benchmarks are not rerun by default. Timing values in fresh replay logs describe execution of the reproduction, not a repeated performance experiment; no identical duration/RSS/date is promised.

```powershell
# Optional modes, each in another new workdir:
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --materialize-only --workdir C:\seismic-data-check
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --bench-native --workdir C:\seismic-benchmark
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --browser-manual --workdir C:\seismic-browser
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --author-reference --octave octave-cli --workdir C:\seismic-author
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --verify-gem-history --workdir C:\seismic-gem-evidence
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --verify-browser-history --workdir C:\seismic-browser-evidence
```

`--browser-manual` starts the preserved V3 same-origin loopback server in the new workspace and prints its `/v3/` URL. Open it manually in the measured browser. The unchanged harness retains24 planned cells and120s Worker caps, serializes once, and POSTs to `/__results/browser-v3`. Exact Origin/Host and application/json are enforced with a256MiB request cap. Results are persisted outside the served root as `browser_consumer_v3_01/observed.json` and `receipt.json`; the first POST returns201, an identical-byte retry returns200 with the same receipt, and a different body is refused409. Ctrl+C closes the owned server after persistence. This mode neither automates a browser nor claims OS-wide exclusivity. A new consumer profile replaces private original CPU permission metadata. Numerical validation uses the preserved V3 validator against the supplied canonical reference arrays, separately from transport/schema verification.

V1 was prepared only. V2 had a real run whose export failed; its24 visible timings are retained, with18 computed and6 censored, no recovered arrays and no preserved user-agent/version. V3 is the separately labeled transport repeat, with24 persisted cells:18 computed and6 censored. Its canonical original POST was58,810,943 bytes, SHA256 `1a53ec72f288742da20ff5475a72f687d1729d02a8e93e9d99a389cffd330038`. Public copies explicitly remove private CPU notes and human filesystem paths; arrays/base64, per-field hashes, cells and measured observations remain intact. A derived receipt links the public bytes and retains the original received digest/length; it is never represented as a new POST. `--verify-browser-history` runs the preserved numerical validator without new browser timings. Node parity is a separate experiment.

`--bench-native` retains one thread, three new processes per backend/input and81 planned cells, with1200s per-worker caps. The upper sum of these caps is27h, not a predicted duration. Preserve errors/censures and record new hardware, wall times and working-set measurements; historical durations/RSS/dates are not expected to match.

The optional author/comparator profile uses separately obtained GNU Octave11.3.0, the unmodified author MATLAB-language sources and explicit GUI shims. It does not claim MATLAB execution. A consumer replay seal records the actual Octave binary/version and retains the historical seal separately. The source implementations and semantics remain unchanged; comparator differences are reported rather than forced to zero. Its two principal-M4.5 reference checkpoints and all twelve retained comparison results are supplied; that optional comparator experiment was not rerun during the clean core replay.

`--verify-gem-history` does not execute GEM again. It verifies the complete identified historical output evidence using the preserved standard-library verifier: exact original input CSVs, every merged membership, guest decision, exclusion and pair; original source pin/license/adapter/protocol; and the historical result manifest. It recomputes pair counts/intersection/symmetric differences and the ten fixed nonzero time shifts using the unchanged matcher functions. GEM's original d13e63 source is AGPL-3.0-only and its separate historical NumPy/engine environment is identified, not silently merged into the current pinned environment. The clean verification recovered2989 GEM and2989 graph assignments,2984 shared assignments and5+5 differing edges, and reproduced the ten-shift table. This is a verified historical-evidence profile, not a new49-minute GEM engine execution or performance claim.

## Verification and provenance

`package_io.py` verifies every logical file by size/SHA256, ZIP chunk bounds, portable relative paths and reviewed package helpers. Materialization rejects traversal, case-ambiguous paths, symlinks and existing workdirs. Numerical arrays are compared after decoding by exact field set/dtype/shape and equality with explicit NaN handling. JSON normalization removes only the declared runtime/container keys in `EXPECTED_COMPARISON_CONTRACT.json`; scientific lags, thresholds, denominators, fits and source hashes remain. CSV comparison covers every cell/order. A failure preserves the workdir, stdout/stderr and receipt.

`SOURCES_AND_RIGHTS.json` and `LICENSES_MAP.json` separate observed SSN/USGS inputs, synthetic assumptions, own software, the GPL EM port and original author distribution, Apache2 comparator/NOTICE, BSD3 bruces and recorded dependency licenses. Root MIT is not a license for every component or observation. Candidate associations are not adjudicated physical identities. Catalogue comparison is not earthquake prediction or damage estimation.

Private reviewer reports/prompts/contexts and the internal `CATALOG_DESIGN_AUDIT` aggregate are excluded. The old association report is replaced by an exact projection containing only its scientific sensitivity table. A declared adapter creates the compatibility filename and rebinds provenance-only input/checksum metadata in the newly materialized workspace, preserving original numerical source bytes and observed fields. `METADATA_TRANSFORMATIONS.json` and the local consumer receipt record original/public hashes and operations without exposing human paths. Hash aliases apply only to these declared provenance fields; they never relax array/cell comparisons or fitted values.

A runtime-created run-manifest hash is not blindly ignored. A specific alias is allowed only after each manifest validates its own complete inventory, every paired listed output passes strict scientific comparison, and all remaining non-runtime manifest fields agree. Tests reject a single changed scientific cell or parameter. The initial QA hash-only mismatch is retained in private replay history; a resume rechecks actual newly calculated outputs and does not copy expected outputs into their place.

The selected USGS58-CSV source can be restored separately from a fixed Git revision and exact hashes using the included restoration script and manifests; the scientific replay itself does not need a new network request. SSN and southern GeoJSON bodies must be supplied as the exact frozen bytes with their notices/provenance. The new southern capture stays separate from the earlier snapshot and preserves its original acquisition/validation failures.

The [versioned Zenodo deposit](https://doi.org/10.5281/zenodo.24361244) includes the additional analysis source, protocols and selected results. Its archive identifies the frozen baseline and each file in the full GitHub analysis by SHA-256. Reproduction with the complete package uses the commands above and in [r3/README.md](r3/README.md).
