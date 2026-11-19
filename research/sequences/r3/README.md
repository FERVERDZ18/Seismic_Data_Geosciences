# Additional sequence analyses

This package recomputes the fixed and refitted cutoff comparisons, the 2017 anchor-family comparison, the reported-magnitude split at M 5.2, and the d = 1.5 checks. The [weight design](WEIGHT_DESIGN.md) defines the intervention and the retained graph used to count bridges. [Role sensitivity](role_sensitivity.py) computes Cohen's kappa, adjusted Rand index and both native family sizes for each prescribed cell.

The [twin design](TWIN_DESIGN.md) specifies the common-member synthetic experiment. The replay reconstructs the original clean and Gaussian fields from the 60 sealed latent histories and observation ledgers. It resamples the observed joint vectors and checks the sampled indices and all 960 history cells. The latent catalogues are synthetic. The counterpart pairs describe retained observational data and may contain association error.

The [benchmark projection](benchmark_projection.py) rebuilds the [site's measurement asset](reference/performance-matched-data.json) from 81 one-thread receipts and checks 27 retained summaries. It does not measure new execution times. The underlying benchmark has its own `replay.py --bench-native` mode.

## Reproduce

From `research/sequences`, use the [pinned environment](../README.md#environment-and-commands) and a new location outside any Git checkout.

```powershell
C:\seismic-replay-env\Scripts\python.exe -I -B replay.py --materialize-only --workdir C:\seismic-r3-replay
C:\seismic-replay-env\Scripts\python.exe -I -B r3\reproduce.py --workspace C:\seismic-r3-replay
```

`r3-results` contains the fresh calculations and the replay receipt. The baseline materialization supplies the exact frozen M ≥ 4.5 arrays, paired endpoints, latent history records and benchmark receipts. The two d = 1.5 cases, the observed correspondence asset and the archived calibration are sealed in `inputs/`. All generated values are compared with `reference/`, including the observed 889-pair factorial and the 2017 counts. Integer counts, assignments and resampling indices must agree exactly. Derived floating-point fields use a combined absolute and relative tolerance of 10^-13. Replaying the package does not query the live catalogue services.

The [licence and provenance map](../LICENSES_MAP.json) covers the software, original sources and comparison data independently. Scientific output is separate from review notes and manuscript preparation files.
