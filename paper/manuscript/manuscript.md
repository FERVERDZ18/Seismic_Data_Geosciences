# A browser-based seismic data observatory for detecting and comparing earthquake sequences across North American catalogues

José Manuel Villa Vargas; Gabriel Hurtado Avilés¹*

¹ Escuela Superior de Cómputo (ESCOM), Instituto Politécnico Nacional, Mexico City, Mexico

Email for José Manuel Villa Vargas: [villavjm@hotmail.com](mailto:villavjm@hotmail.com).

*Corresponding author: Gabriel Hurtado Avilés. Institutional email: [ghurtadoa@ipn.mx](mailto:ghurtadoa@ipn.mx). Personal email: [gabrielhuav@gmail.com](mailto:gabrielhuav@gmail.com).

ORCID: José Manuel Villa Vargas, [https://orcid.org/0009-0009-2401-0661](https://orcid.org/0009-0009-2401-0661); Gabriel Hurtado Avilés, [https://orcid.org/0009-0002-5686-1822](https://orcid.org/0009-0002-5686-1822).

## Abstract

When two earthquake catalogues report what appears to be the same event, a sequence algorithm can still choose different parents for it. We built a k-dimensional tree (KD-tree) search for magnitude-weighted parents and included it in a browser observatory. In a single-threaded native benchmark of 170~880 observations, the index returned the exhaustive results and reduced the median runtime from 524.04 s to 5.92 s. We used that search on two catalogues covering Mexico. At reported M≥3.5, increasing the magnitude weight from 1 to 1.4 changed 55% of defined parents in the Servicio Sismológico Nacional (SSN) catalogue and 28% in the U.S. Geological Survey Comprehensive Earthquake Catalog (ComCat). At reported M≥4.5, 772 of 889 candidate pairs had the same family role at weight 1, while the representative-event Jaccard index was 0.41. Using a separately fitted weight for each source lowered agreement to 37% on candidate pairs from 2021–2025. In Alaska we vary the method while holding ComCat fixed. The Canadian catalogue documents coverage. Simulated catalogues with known ancestry establish that stable roles can still miss known families.

Keywords: earthquake sequences; catalogue comparison; nearest-neighbour search; browser computing; declustering; reproducibility

## 1. Introduction

An earthquake can receive different roles when two agencies report different measurements. Even with those measurements fixed, changing the surrounding records can change its assigned parent. The agencies may also share solutions whose provenance is incomplete (Rösler et al., 2022). Agreement alone cannot establish triggering.

Gardner and Knopoff (1974) assign events using a time span and radius that depend on magnitude. Nearest-neighbour (NN) methods use lag, separation and the earlier event's magnitude (Baiesi and Paczuski, 2004; Zaliapin and Ben-Zion, 2013). Identifying families and recovering background seismicity use those links for distinct purposes (Zaliapin and Ben-Zion, 2020). Related studies compare declustered networks (Varini et al., 2020), examine proximity modes (Hsu et al., 2024) and automate NN declustering (Bountzis et al., 2026).

KD trees have served early-warning queries (Yin et al., 2018). We bound the lag–distance–magnitude score and verify the minimum by exhaustive enumeration. At M≥3.5 we test parent choice. At M≥4.5 we vary the inputs used to choose family roles, which affect aftershock counts and background estimates (Sawires et al., 2019).

Figure 1 traces the browser data flow (Galaz et al., 2022; Villa Vargas et al., 2026). Mexico provides contemporaneous samples, Alaska a single-source method check, and Canada a coverage inventory (Natural Resources Canada, n.d.).

## 2. Methods

### 2.1. Observations, association and coverage

Mexico's selection (UTC [2016-01-01,2026-01-01), latitude [14,33], longitude [−118,−86], reported M≥3.5) includes offshore and neighbouring areas, with 170~880 SSN and 3945 ComCat records. Alaska contributes 3630 ComCat records in UTC [2020-01-01,2026-01-01), latitude [50,72] and longitude [−170,−130]. This extent excludes the western Aleutians. We test the antimeridian separately. A missing SSN identifier receives a deterministic local key. Copy grouping, agency pairing and sequence membership are separate operations.

Candidate pairs require |Δt|≤30 s and separation≤50 km using radius 6371.0088 km and tolerance 10^-9 km. Among maximum-size one-to-one matchings, we minimize the quantized sum |Δt|/30+distance/50 and resolve ties by stable ID order. This leaves magnitude free for comparison. We test the 10/30/60 s by 10/50/100 km windows and compare with GEM software (GEM Foundation, n.d.). Ten circular ComCat shifts of ±7/14/30/60/90 days give negative controls. These tests give no adjudicated identities or false-association rate.

<!-- figure: 1 -->

ComCat lists network, origin and magnitude sources separately. UNM (Instituto de Geofísica, UNAM) supplied 28 origins and five magnitudes in our selection. ECX identifies Red Sísmica del Noroeste de México (RESNOM) at CICESE (U.S. Geological Survey, n.d.a, b, c). Natural Earth polygons tag onshore epicentres (Natural Earth, n.d.). Original-14 uses the original records down to 14°N. Updated-14 retains that extent with ComCat refreshed in two acquisitions on 17 November. Extended-12 includes both catalogues down to 12°N. All three use the 6 November 2026 SSN snapshot. Extended-12 masks of 0.5°, 1° and 2° mark cells with reported M≥3.5 events in both sources in 2016–2020. We score either original classifications or ones recomputed inside those cells at the same cutoffs. These masks describe reported occupancy.

### 2.2. Magnitudes and temporal calibration

Filter on reported magnitude first (M≥4.5, repeated at 4.4 and 4.1). Round to 0.1 by the half-up rule only for the plots. For each catalogue we report half-bin Aki–Utsu b (Aki, 1965; Utsu, 1965), MAXC+0.2 and cumulative goodness of fit (GFT). The cumulative fit diagnostic records failures to reach 95% (Wiemer and Wyss, 2000; Woessner and Wiemer, 2005). Pérez-Campos (2020) places SSN's Mw1 at 4.0 to 5.2 and W-phase moment magnitudes above 5.2 in 2020. We leave absent types unknown.

Mexico's 2021–2025 evaluation reuses parameters fitted in 2016–2020. Alaska's 2023–2025 evaluation reuses its 2020–2022 fit. Both retrospective splits followed the pilot. We specified the expanded analyses after review, before running their batches. Earlier parents remain eligible, and the retrospective representative can depend on later component members.

### 2.3. Identification and numerical contracts

For the reference comparison we set the distance exponent d=1.6, magnitude weight w=1 and coordinate split q=0.5 (Zaliapin and Ben-Zion, 2013). The usual magnitude weight is the Gutenberg–Richter b-value (Zaliapin and Ben-Zion, 2020), so we compare w=1 with alternatives fitted to reported magnitudes. For each target i, we select the strictly earlier j with the smallest proximity.

<!-- equation: metric -->

Search uses seconds and metres, cutoff coordinates years and kilometres. The radius is 6367.3 km, as in the author distribution. Python and JavaScript derive epoch years from UTC microseconds relative to 2016-01-01 using 31~557~600 s/year, then multiply before subtraction. UTC/UTF-8 ID determine order. In 170~880 SSN records, 17 equal-time pairs leave 14~599~901~743 eligible earlier pairs. Equal times alone cannot identify copies. The cosine enters acos after clamping to [−1,1].

The rescaled coordinates are {{math:rescaled-time}} and {{math:rescaled-distance}}. Expectation maximization (EM) fits two normals to development {{math:fit-log-product}} using initial means −6/−3, standard deviations of 1 and tolerance 0.001. The cutoff is the equal-weight intersection of the fitted densities. We track modes, fit failures and Bayesian information criterion (BIC, Schwarz, 1978). Keep links satisfying {{math:cut-log-sum}}, allowing the sum of logs to round differently from the fitted log-product. A singleton is isolated. In a larger component the event of highest reported magnitude represents the family, with earliest UTC then ID breaking ties. Other members are associated.

With positive lag, computed distance zero gives log proximity −∞. The link passes finite cuts, while the score stays outside the fit. The first record has no parent. We check computed zeros, coincident coordinates and source copies separately. Physical identity remains unadjudicated.

One reference runs eq_cluster.m (GPLv3, 636d07b, 29 March 2021) in Octave 11.3.0 with graphics adapters and the original numerical routine (Zaliapin, n.d.). We adapt only Python 2 syntax and NumPy aliases in Eqclustering 393a02d, keeping its 365.35-day convention and unclamped acos (NVSeismoLab, n.d.). Both tests compare parent identities.

Gardner–Knopoff (GK) uses a radius of {{math:gk-radius}} km and a forward window of {{math:gk-duration-low}} days below M 6.5 or {{math:gk-duration-high}} days otherwise, with half that span before the event. Allocation uses descending magnitude, UTC and ID. The indexed and exhaustive implementations share the membership rule and 6371.0088 km Earth radius.

### 2.4. Bounded spherical parent search

We partition unit-sphere coordinates with a KD tree or midpoint octree (Bentley, 1975; Virtanen et al., 2020). At {{math:target-time}}, only earlier observations are active. In addition to the spatial box, each node stores the latest active time U and highest active magnitude H. For distance ρ from the target to the box, {{math:earth-radius}} and {{math:lower-distance}}, each active j satisfies {{math:lag-bound}}, {{math:distance-bound}} and {{math:magnitude-bound}} when d>0 and w≥0. Multiplying these terms gives a lower bound on {{math:raw-metric-symbol}}.

<!-- equation: bound -->

Insert each eligible record by updating U and H from its leaf up to the root. A box can also cover future epicentres, and its U and H can come from separate records. Both cases reduce pruning. Search boxes in bound order and drop any box whose bound exceeds the best score. At leaves, score active records. Equal scores favour the smaller canonical index across the search.

Distinct epicentres in the cross-leaf fixture yield tied zero scores in floating point. Both trees agree with exhaustive search. To guard the real-arithmetic bound during pruning, subtract 2×10^-7 from the box chord (floor zero) and add 10^-10 to the incumbent log-score. Observed inputs also test traversal and parity. Python shares distance calculations and JavaScript checks shared canonical geometry. Full coordinate conversion lacks independent validation. KD storage is linear, activation O(Nh), worst-case search O(N²).

Native tests use seven chronological prefixes and both principal cohorts. Each backend runs three times in rotated order, in fresh one-thread processes, with a 64-row warm-up and 1200-s cap. Time covers geometry through postprocessing. Peak working set includes runtime and JIT, and CPU settings and scheduling are uncontrolled. Browser tests use 2000, 10~000, 50~000 and 170~880 records. Each method runs three times per size (120-s cap), with loading timed separately.

At M≥3.5 we rerun parent selection at nine weights in the two native catalogues and on the endpoints of the 2989 candidate pairs. We compare parent identities, lags and distances and check the outputs against exhaustive search and JavaScript. The two apparent-b weights are from the M≥4.5 development samples. The M≥3.5 distributions are unimodal. This comparison stops at candidate parents, before assigning families.

### 2.5. Catalogue interventions and uncertainty

The principal comparison scores jointly eligible pairs after classifying all selected records in each source. To test membership, we rerun on pair members at fixed measurements and cutoffs, then separately refit on common development records. For 889 SSN keys, the factorial substitutes combinations of UTC, coordinate pairs and magnitude from ComCat under each frozen cut. Original SSN membership and times define evaluation. Output subsets inherit full-family assignments. GK keeps eligible pair members and samples 0/25/50/75/100% of remaining eligible SSN rows, with 20 seeds per intermediate fraction.

At weights 0.8 to 1.4 in 0.1 steps and both development b estimates, we search for parents and fit the development cutoff. With parents fixed, apply −0.5/0/+0.5 offsets or carry over the w=1 cutoff, optionally subtracting 4.5(w−1) to offset the log-score shift at the magnitude floor. We compare partitions by adjusted Rand index (ARI) and roles by confusion counts, agreement, kappa and class Jaccard (Cohen, 1960; Hubert and Arabie, 1985). Joining baseline family members and candidate endpoints gives connected resampling units. We draw 2000 PCG64 resamples of those units (seed 20261117). Percentiles reflect sample composition. Alternative families can cross unit boundaries. We rescore pairs outside the fixed 2017 family union with original classifications.

### 2.6. Shared-latent synthetic catalogues

A simplified epidemic-type aftershock sequence (ETAS) generator supplies known parents and roots (Ogata, 1988, 1998). Its scenario parameters are 600 immigrants/year in two Gaussian concentrations 80 km apart (σ=15 km), M 3.5–6.5, b=1, productivity exponent 0.5, Omori c=0.001 day and p=1.2, and offspring displacement σ=5 km. A 365-day burn-in precedes 730 evaluation days. We generate 30 histories each at branching ratios 0 and 0.6. Three separate development histories set the reference NN cut.

We retain a clean copy of each history. The 16 factorial settings, including all factors off, reuse draws for detection D (retention 0.65–0.95, increasing with magnitude), magnitude M (+0.15, Gaussian σ=0.15 and decimal rounding), position X ((+2,−2) km, Gaussian σ=5 km), and clock C (+2 s, Gaussian σ=2 s). Latent keys track detection losses, below-cut observations and retained records. A missing parent leaves latent child status intact. The largest retained event of a root family may itself be a child.

We compare roles, partitions, child recovery and immigrant false positives against latent truth and constant, singleton and all-grouped baselines. Latent IDs define the main comparison, and candidate matching supplies a separate precision/recall check. Main runs use the clean development cutoff. Refitting by combination tests calibration. Monte Carlo t intervals use independent histories as units.

The post hoc comparison with observed substitutions fixes membership to keys retained in the clean catalogue and both perturbed scenarios. Burn-in events can supply parents. We run eight field combinations at the clean cutoff in each scenario. One uses prescribed Gaussian offsets. The other resamples joint signed ComCat-minus-SSN differences in magnitude, location and time from the 2989 observed candidate pairs, conditional on the pairing window.

## 3. Results

### 3.1. Exact search and catalogue-scale sensitivity

Both indices reproduced all ten exhaustive arrays on every input, and all 81 native runs completed. For 170~880 SSN records, median runtime fell from 524.037 s to 5.924 s with the KD tree (88.46×) and 6.416 s with the octree (81.67×), with higher peak process memory (Table 1 and Figure 2).

Table 1. Matched native costs on Ryzen 5 5600G/Windows: one thread and three fresh processes per input/backend. Seconds include numeric preparation, construction, search and postprocessing; imports/JIT/serialization are excluded. Peak process working set includes runtime/JIT and is not kernel-only memory. MiB=2^20 bytes. All 27 input/backend summaries and 81 runs, including omitted prefixes, are retained.

<!-- table-widths: 2100, 1400, 2460, 1300, 2100 -->
| Selection / N | Backend | Seconds median [range] | Reference/ backend | Peak process MiB range |
| --- | --- | --- | --- | --- |
| SSN M≥4.5 /1780 | Exhaustive | 0.056619 [0.056239–0.056891] | 1.00× | 180.81–221.40 |
| SSN M≥4.5 /1780 | KD | 0.017193 [0.016876–0.017307] | 3.29× | 180.16–180.94 |
| SSN M≥4.5 /1780 | Octree | 0.025707 [0.025156–0.027041] | 2.20× | 179.83–180.93 |
| ComCat M≥4.5 /1256 | Exhaustive | 0.028251 [0.028037–0.028416] | 1.00× | 180.19–181.09 |
| ComCat M≥4.5 /1256 | KD | 0.011477 [0.011288–0.012000] | 2.46× | 180.50–181.20 |
| ComCat M≥4.5 /1256 | Octree | 0.017427 [0.017232–0.018155] | 1.62× | 180.61–181.10 |
| SSN M≥3.5 /170~880 | Exhaustive | 524.037 [521.829–525.026] | 1.00× | 223.23–224.45 |
| SSN M≥3.5 /170~880 | KD | 5.924 [5.658–5.952] | 88.46× | 258.03–258.61 |
| SSN M≥3.5 /170~880 | Octree | 6.416 [6.354–6.439] | 81.67× | 260.64–261.05 |

<!-- figure: 2 -->

Under the earlier four-thread baseline protocol, KD and octree traversals evaluated about 0.044% and 0.036% of eligible full-input pairs. All 36 indexed M≥3.5 weight/context cases reproduced the exhaustive arrays. Node 24.22.1 reproduced IDs, parents and nonfinite masks, with a maximum absolute log-score difference of 7.38×10^-14 against the 10^-10 tolerance.

At M≥3.5, raising w from 1 to 1.4 favours larger candidate parents and changes 94~745 of 170~879 defined SSN parents and 1088 of 3944 ComCat parents. Median lag and separation increase from 0.32 to 124 days and 15 to 83 km in SSN, and from 24 to 109 days and 55 to 100 km in ComCat. These links change before thresholding them into families.

At w=1, limiting parent pools to the 2989 candidate endpoints changes 1765 of 2988 SSN parents and 112 of 2988 ComCat parents. This intervention removes about 98% of SSN and 24% of ComCat records. Such unequal reductions preclude a comparison of source sensitivity at matched retention. With full pools, 1199 paired targets have two parents that belong to candidate pairs. Of these, 975 select parents paired to each other (81.32% of comparable targets and 32.62% of all targets). Source-specific weights raise the comparable count to 2204, with agreement in 1816 (82.40% and 60.76%, respectively).

The w=1 arrays retain 207 SSN and one ComCat −∞ scores plus one parentless record per cohort. Finite-score quantiles omit those entries.

In twelve runs, the published comparators reproduced every parent in the two principal cohorts. Eqclustering's median kernel times are 0.143 s (SSN) and 0.083 s (ComCat). The author's Octave code takes 0.888 and 0.610 s, respectively. Both scan a catalogue-wide mask per target, admitting every earlier record. At 170~880 records this entails about 29.2 billion mask positions before distance calculations. The full-scale timings cover the shared native implementations.

Earlier parity checks covered 200~982 row-case selections in Node and 3036 principal records in Edge at a log-score tolerance of 10^-10.

The Chrome 157 Worker finished exhaustive search at 2000 and 10~000 records. All six runs with 50~000 or 170~880 records reached the 120-s limit. KD medians at these four sizes were 0.0324, 0.2232, 2.5510 and 12.8782 s on Windows. The full-catalogue runs took 12.7537–18.0367 s. All 18 completed runs matched native parent IDs and nonfinite masks, with finite log-scores within 3.38×10^-14. Local setup and verification took 315.9 ms separately. The earlier timing-only trial lacks output comparisons. These timings exclude remote transfer and map rendering. Peak Worker memory is unknown.

### 3.2. Selection and native classification

The principal cut retains 1780 SSN, 1256 Mexico-window ComCat and 555 Alaska records. The Mexican association graph has 3007 edges, 17 ambiguous components and 2989 assignments. GEM also returns 2989, sharing 2984. This measures agreement between implementations. Exact decimals give mean SSN−ComCat M=+0.13034, with |ΔM|≥0.3 in 1112/2989 pairs. The mean varies by supplied ComCat type (+0.1422 mb and −0.0406 mww). SSN magnitude types are unknown. Median separation and absolute lag are 14.29 km (spherical) and 1.15 s in the distributions truncated by the association window.

Of 2989 candidates, 889 clear M≥4.5 in both sources, 661 only in SSN, 138 only in ComCat and 1301 in neither. Among selected records, 230 SSN and 229 ComCat lack an assigned counterpart. Jointly eligible candidates cover 49.94% of selected SSN and 70.78% of selected ComCat records. Land polygons place the 229 unassigned ComCat records in Guatemala (87), the United States (26), Honduras (three), El Salvador (two), Mexico (19) or outside those polygons (92). Network coverage remains unmeasured. Across nine windows, jointly eligible counts range from 230 to 922 and NN agreement from 86.55% to 87.39%. Shifted-time controls yield 2–31 assignments. Stable aggregate agreement leaves individual matches unverified. Section 3.6 reports boundary controls.

Full-interval apparent b/GFT at M≥4.5 are 1.34/93.4% for SSN, 1.06/96.8% for Mexican ComCat and 0.94/95.6% for Alaska (Figure 3). SSN development yields no accepted GFT95 tail. Short postevent tails at this cut contain fewer than 100 observations, precluding a local completeness estimate here. Development thresholds at the main weight are −5.31563 (SSN), −5.43694 (Mexican ComCat) and −5.78909 (Alaska). All fits have two modes and lower BIC for the two-normal model. These diagnostics support an operational split. Physical family membership remains unverified.

Native NN roles agree in 772/889 pairs (86.84%, kappa 0.765, ARI 0.926, Table 2) and in 322/382 temporally (84.29%, kappa 0.679, ARI 0.791). Conditional resampling percentiles are [82.88,89.73]% and [79.59,88.68]%, respectively. Full and temporal comparisons have 592/301 resampling units, size-weighted effective counts of 32.01/181.05 and largest-unit shares of 17.10%/2.88%, qualifying the intervals. Jaccard scores show lower agreement for representatives. For isolated, representative and associated roles, scores are 83.45%, 41.30% and 80.45% overall and 83.63%, 40.00% and 64.84% temporally. Full-interval conditional percentile ranges are [79.08,87.34]%, [33.11,50.31]% and [61.87,88.32]% in that order. Excluding the fixed 2017 family union (152 pairs) gives 85.48% agreement overall and 84.80% temporally.

<!-- figure: 3 -->

Table 2. Full-interval NN roles on the same 889 candidates. Rows are SSN and columns ComCat; each endpoint retains its native context. Temporal and class-specific matrices and all resampling replicates accompany the analysis.

<!-- table-widths: 3360, 2000, 2000, 2000 -->
| SSN role | ComCat isolated | Representative | Associated |
| --- | --- | --- | --- |
| Isolated | 464 | 13 | 11 |
| Representative | 43 | 57 | 13 |
| Associated | 25 | 12 | 251 |

### 3.3. Weight, threshold and measurement effects

In Table 3, weighting each source by its apparent b yields 51.52% agreement overall and 37.17% in evaluation. Using the larger b for both lowers these to 47.36% and 32.46%. The SSN fits have one mode at the high-agreement w=1.2 setting and at exploratory cuts of M 4.4 and 4.1.

Raising w from 1.2 to 1.3 reduces temporal agreement from 86.13% to 34.03% with refitted cutoffs. With w=1 cutoffs, raw agreement rises from 83.25% to 91.88%, although κ falls from 0.663 to 0.580 and ARI from 0.852 to 0.787. At w=1.3, 329 of 351 agreements assign the associated role in both catalogues. The largest families grow from 887 to 1193 in SSN and 585 to 820 in ComCat. The prevalent role drives raw agreement up even as the partitions diverge. Floor-centred cutoffs give 82.98% at both weights. Swapping the refitted cutoffs between weights confirms their interaction.

Table 3. Native weight grid and cutoff sensitivity for 889 full-interval and 382 evaluation pairs. Agreement and κ compare roles. ARI compares partitions. Largest families count all 1780 SSN and 1256 ComCat records. Low/high denote weights 1.090543/1.326568. Grid rows refit at d=1.6 and offset zero. Fixed rows reuse source cutoffs. Centred rows adjust them at M 4.5. Rows at d=1.5 use w=1. SSN mode counts refer to grid fits.

<!-- table-widths: 1390, 1050, 1490, 1170, 1610, 1750, 900 -->
| SSN / ComCat w | All (%) | All κ / ARI | Temporal (%) | Temporal κ / ARI | Largest SSN / ComCat | SSN modes |
| --- | --- | --- | --- | --- | --- | --- |
| 0.8 / 0.8 | 85.49% | 0.746 / 0.872 | 83.25% | 0.672 / 0.705 | 252 / 186 | 2 |
| 0.9 / 0.9 | 85.60% | 0.746 / 0.917 | 83.25% | 0.665 / 0.772 | 274 / 200 | 2 |
| 1 / 1 | 86.84% | 0.765 / 0.926 | 84.29% | 0.679 / 0.791 | 292 / 204 | 2 |
| 1.1 / 1.1 | 88.08% | 0.779 / 0.933 | 84.55% | 0.659 / 0.683 | 294 / 208 | 2 |
| 1.2 / 1.2 | 89.09% | 0.792 / 0.928 | 86.13% | 0.669 / 0.716 | 294 / 207 | 1 |
| 1.3 / 1.3 | 48.37% | 0.234 / 0.148 | 34.03% | 0.128 / 0.012 | 936 / 203 | 2 |
| 1.4 / 1.4 | 43.98% | 0.187 / 0.109 | 28.53% | 0.090 / 0.008 | 1065 / 203 | 2 |
| low / low | 88.41% | 0.787 / 0.934 | 85.08% | 0.674 / 0.723 | 294 / 208 | 2 |
| high / high | 47.36% | 0.222 / 0.140 | 32.46% | 0.116 / 0.010 | 955 / 203 | 2 |
| low / high | 86.39% | 0.742 / 0.912 | 82.46% | 0.592 / 0.631 | 294 / 203 | 2 |
| high / low | 51.52% | 0.264 / 0.146 | 37.17% | 0.153 / 0.014 | 955 / 208 | 2 |
| 1.2, fixed w=1 | 87.85% | 0.738 / 0.849 | 83.25% | 0.663 / 0.852 | 887 / 585 | — |
| 1.2, centred | 87.18% | 0.780 / 0.834 | 82.98% | 0.687 / 0.671 | 472 / 286 | — |
| 1.2, w=1.3 cut | 62.43% | 0.372 / 0.207 | 62.04% | 0.299 / 0.083 | 559 / 150 | — |
| 1.3, fixed w=1 | 92.13% | 0.678 / 0.786 | 91.88% | 0.580 / 0.787 | 1193 / 820 | — |
| 1.3, centred | 88.41% | 0.798 / 0.898 | 82.98% | 0.709 / 0.676 | 619 / 373 | — |
| 1.3, w=1.2 cut | 87.74% | 0.788 / 0.860 | 83.51% | 0.696 / 0.647 | 518 / 315 | — |
| d=1.5, refit | 88.41% | 0.791 / 0.933 | 85.86% | 0.704 / 0.761 | 287 / 201 | — |
| d=1.5, fixed d=1.6 | 87.40% | 0.779 / 0.886 | 84.82% | 0.698 / 0.793 | 333 / 222 | — |

The SSN graph shows why the refitted cutoff matters. At w=1.3 the largest family contains 936 of 1780 events. It joins separate w=1.2 components via 565 bridges. Of these, 525 retain their candidate parent and now pass the cutoff. The September 2017 M 8.2 event parents 483 bridges, with median separation 155 km and lag 1011 days. Higher weights enlarge the attraction domains of large candidate parents (Zaliapin and Ben-Zion, 2020).

Median absolute magnitude differences are 0.2 for 2846 pairs at or below reported SSN M 5.2 and 0.1 for the 143 above it. At the principal cut and w=1, roles agree in 649 of 746 and 123 of 143 pairs, respectively. With refitting from w=1.2 to 1.3, evaluation agreements drop from 278 to 101 of 323 and from 51 to 29 of 59, respectively.

The spatial exponent has a smaller effect. With d=1.5 and w=1, refitting gives 786 of 889 agreements (88.41%), including 328 of 382 evaluation pairs. Reusing d=1.6 cutoffs gives 777 and 324. The low/low row in Table 3 also reaches 88.41% overall, with 325 evaluation agreements.

To isolate membership, we keep source measurements and cutoffs fixed. Using only common records raises NN agreement from 772 to 830 of 889 pairs, or 832 if the cutoffs are refitted. GK agreement rises from 77.28% to 84.36% on common members. During thinning, median agreement falls as more unmatched SSN records are retained.

For common members, substituting UTC leaves NN roles unchanged and the position and magnitude effects are non-additive (Table 4). In 2017, the largest annual sample, agreement peaks at 180 of 190 (Table 5). With retrospective classifications fixed, 122 of 125 pairs agree inside the fixed anchor-family union and 58 of 65 outside.

Table 4. Observed-measurement factorial, with eight UTC/location/magnitude substitution patterns and two frozen cutoffs. Entries compare roles with unchanged common-member SSN at each cutoff. Pattern 111 uses all matched ComCat fields. Each column retains 889 full-interval or 382 evaluation keys.

<!-- table-widths: 1600, 1940, 1940, 1940, 1940 -->
| UTC/X/M | SSN cut all | SSN cut temporal | ComCat cut all | ComCat cut temporal |
| --- | --- | --- | --- | --- |
| 000 | 100.00% | 100.00% | 100.00% | 100.00% |
| 001 | 97.30% | 96.34% | 97.19% | 96.86% |
| 010 | 95.05% | 94.76% | 95.95% | 95.55% |
| 011 | 93.70% | 92.67% | 94.15% | 92.93% |
| 100 | 100.00% | 100.00% | 100.00% | 100.00% |
| 101 | 97.30% | 96.34% | 97.19% | 96.86% |
| 110 | 95.05% | 94.76% | 95.95% | 95.55% |
| 111 | 93.70% | 92.67% | 94.15% | 92.93% |

Table 5. Annual native NN comparisons at reported M≥4.5 and w=1. Years 2016–2020 inform development and 2021–2025 form a retrospective temporal evaluation.

<!-- table-widths: 1800, 1500, 2260, 1900, 1900 -->
| UTC year | Candidate pairs | Agreement | Kappa | ARI |
| --- | --- | --- | --- | --- |
| 2016 | 77 | 89.61% | 0.772 | 0.928 |
| 2017 | 190 | 94.74% | 0.884 | 0.958 |
| 2018 | 83 | 89.16% | 0.803 | 0.933 |
| 2019 | 84 | 82.14% | 0.617 | 0.851 |
| 2020 | 73 | 79.45% | 0.638 | 0.935 |
| 2021 | 88 | 77.27% | 0.518 | 0.762 |
| 2022 | 77 | 84.42% | 0.620 | 0.788 |
| 2023 | 79 | 87.34% | 0.730 | 0.825 |
| 2024 | 69 | 85.51% | 0.757 | 0.960 |
| 2025 | 69 | 88.41% | 0.761 | 0.933 |

### 3.4. Named cases and transfer control

We choose the maximum reported ComCat magnitude in 2017 and 2022, breaking ties by earliest UTC and then ID. Both displays crop to 150 km and −7 to +30 days around the anchor after classifying full inputs. At M≥3.5 and M≥4.5, the SSN/ComCat counts are 3806/364 and 148/137 around the M 8.2 Tehuantepec anchor (8 September 2017), and 1207/19 and 13/9 around the M 7.6 Michoacán anchor (19 September 2022). Its SSN candidate reports M 7.7. These counts provide no detection probabilities.

Changing from w=1 to each source's apparent b grows the 2017 SSN/ComCat anchor families from 292/204 to 955/208. The local family remains at 148 SSN and 136 ComCat members, out of 148 and 137 eligible local records (Figure 4). Paired-family Jaccard falls from 142/152=0.934 to 146/452=0.323, with local overlap still 85/86. In 2022, full families grow from 21/10 to 84/10 and local membership stays at 13/9.

In the default 2017 SSN graph, consecutive members are up to 929.61 days apart over 2631.62 days. Graph membership leaves aftershock duration unresolved. In Figure 4 the 14°N boundary cuts the 150-km circle. Extending the query to 12°N completes the circle. Its added portion contains four SSN records at M≥3.5, none at M≥4.5 and no ComCat records at either cut. Candidate parents could lie south of 12°N.

The first outside-window SSN role change in the 2017 family union is the M 7.1 event of 19 September 2017, 627.695 km and 11.559 days from its M 8.2 candidate parent. Its score crosses the cutoff from isolated (−5.22326>−5.31563) to associated (−7.90112≤−6.14514). The inspector shows the IDs, source fields and both classifications (Figure 5). The change cannot establish remote triggering.

The 555 ComCat records in Alaska isolate method dependence within one catalogue. NN and GK agree on 235 of 313 development roles (75.08%) and 170 of 242 evaluation roles (70.25%). Partition ARIs are 0.579 and 0.643. In evaluation NN assigns 148 isolated, 19 representative and 75 associated roles. GK gives 81, 32 and 129. Its indexed and exhaustive outputs agree.

<!-- figure: 4 -->

### 3.5. Shared-latent validation

The 60 synthetic histories yield 960 factorial cells. Unperturbed catalogues reproduce clean roles. On clustered histories, NN root-partition ARI falls from 0.637 [0.614,0.659] to 0.571 [0.541,0.601] under all four operations. GK gives 0.009 and 0.007. On clean clustered histories, child F1 for NN (0.566) and GK (0.706) trails the always-child baseline (0.710). Without triggering, NN groups 4.24% of clean immigrants and GK groups 96.95%. Cross-catalogue agreement and recovery of known ancestry quantify different properties.

Of the fixed clean keys, 2.25% retain membership and change NN role under detection alone. The shares are 16.65% for magnitude and 10.05% for position. A clock perturbation alone changes no roles (Table 6). The combined 30.55% disagreement comprises 11.86 percentage points of inclusion loss and 18.69 of role changes. The isolated total responses sum to 41.15%. Seven secondary unimodal fits have finite cutoffs. Under all operations, clustered-history candidate matching has precision near 0.999 and recall near 1.000.

Table 6. Twin factorial in the branching-0.6 regime. Values are means across 30 histories, as percentages of fixed clean-catalogue evaluation keys. D, M, X and C denote detection, magnitude, position and clock. Inclusion losses are shared by both methods.

<!-- table-widths: 1160, 1640, 1640, 1640, 1640, 1640 -->
| D/M/X/C | Inclusion loss | NN role change | NN total | GK role change | GK total |
| --- | --- | --- | --- | --- | --- |
| 0000 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 0001 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 0010 | 0.00 | 10.05 | 10.05 | 1.23 | 1.23 |
| 0011 | 0.00 | 10.05 | 10.05 | 1.23 | 1.23 |
| 0100 | 2.23 | 16.65 | 18.88 | 1.46 | 3.69 |
| 0101 | 2.23 | 16.65 | 18.88 | 1.46 | 3.69 |
| 0110 | 2.23 | 20.80 | 23.03 | 1.93 | 4.16 |
| 0111 | 2.23 | 20.80 | 23.03 | 1.93 | 4.16 |
| 1000 | 9.98 | 2.25 | 12.23 | 0.46 | 10.44 |
| 1001 | 9.98 | 2.25 | 12.23 | 0.46 | 10.44 |
| 1010 | 9.98 | 10.43 | 20.41 | 1.17 | 11.15 |
| 1011 | 9.98 | 10.43 | 20.41 | 1.17 | 11.15 |
| 1100 | 11.86 | 15.22 | 27.08 | 1.54 | 13.40 |
| 1101 | 11.86 | 15.22 | 27.08 | 1.54 | 13.40 |
| 1110 | 11.86 | 18.69 | 30.55 | 1.81 | 13.67 |
| 1111 | 11.86 | 18.69 | 30.55 | 1.81 | 13.67 |

Earlier ten-history controls give child F1 of 0.554 for NN and 0.684 for GK, below the 0.691 baseline. The 24-history control reports conditional means across three seeds per cell.

Before synthetic detection and filtering, 25.67% of evaluation offsets have absolute magnitude difference ≥0.3, compared with 37.20% of observed candidate pairs. The respective WGS84 median separations are 6.37 and 14.25 km. Median absolute lags are 2.09 and 1.15 s. The candidate differences cannot isolate either catalogue's measurement error.

Across 5789 fixed evaluation keys in 30 clustered histories, changing only magnitude alters 7.92% of NN roles with Gaussian offsets and 8.22% using magnitudes from joint candidate draws. Replacing all three fields gives 12.94% (95% Monte Carlo interval 11.88–14.00%) and 16.28% (14.88–17.67%), respectively. Observed magnitude substitution also holds membership fixed (2.70%). For the 16.65% result, reapplying the magnitude cut can change the parent pool.

### 3.6. Versioned boundary and shared support

Updated-14 uses the same 3945 ComCat IDs as Original-14 and changes fifteen depths, two magnitudes and one coordinate pair. Against the unchanged SSN data, the refresh leaves agreement at 86.84% for 889 pairs and 84.29% for 382 evaluation pairs.

Extended-12 adds 101 SSN and 637 ComCat records at the principal cut. Its 959 overall and 416 evaluation pairs agree at 86.86% and 85.10% with new development cutoffs, or 85.92% and 83.65% with Updated-14 cutoffs. Among 889 shared pairs, eight SSN and 25 ComCat observations switch to newly admitted parents. Table 7 limits comparisons to grid cells where both sources reported events during development.

Table 7. Extended-12 grid cells occupied by both sources at M≥3.5 during development. Pair counts and agreement refer to the M≥4.5 selection. Projection filters the displayed pairs after classification. Restriction filters both input catalogues first and uses the Extended-12 cutoffs.

<!-- table-widths: 1200, 1200, 2160, 2400, 2400 -->
| Degrees | Cells | Pairs all/test | Projected agreement all/test | Restricted agreement all/test |
| --- | --- | --- | --- | --- |
| 0.5 | 243 | 881/350 | 86.83%/84.86% | 86.61%/84.00% |
| 1 | 114 | 931/393 | 87.11%/85.50% | 87.11%/85.50% |
| 2 | 54 | 946/404 | 87.10%/85.64% | 87.10%/85.64% |

## 4. Integrated exploration

Open W1 in the full map or from Figure 5B. The inspector shows why this record, which falls beyond the local circle, has one candidate parent and two scores. Display filters change the visible radius, dates or sources. Only a change in calculation membership or weight reruns classification on hash-checked rows. Links and SVG or JSON exports record the view.

<!-- figure: 5 -->

<!-- figure: 6 -->

Zooming into the southern band in Figure 6 changes the colours because a different set of epicentres now falls within each pixel neighbourhood. The query's rows still supply the download and the sql.js workspace (sql.js contributors, n.d.). The outlines come from Bird's PB2002 model (Bird, 2003).

<!-- figure: 7 -->

Figure 7 shows retained years. In Figures 8B and 8C the USGS selection begins in 2020 and the Canadian selection ends in 2019. The sequence pilot uses the limits in Section 2.

<!-- figure: 8 -->

Figure 9 uses the regional land filter. Figure 10 applies different magnitude cuts to the same Guerrero region and years.

<!-- figure: 9 -->

<!-- figure: 10 -->

Each map poses a different query. Figure 11 compares two regions with the same USGS inputs and bins. Figure 12 retrieves the ten largest reported magnitudes. Figure 13 asks which of the large Guerrero events lie within 50 km of one another. The query links open the settings used for those figures.

<!-- figure: 11 -->

<!-- figure: 12 -->

<!-- figure: 13 -->

## 5. Discussion

An event south of 14°N cannot become a parent in Original-14, even if its own event parameters are exact. Expanding the search changes the input to the proximity fit (Figure 3; Hsu et al., 2024). The downstream sample for declustering and completeness estimation can therefore depend on the boundary as well as on missing events or measurement error (Zaliapin and Ben-Zion, 2015; Varini et al., 2020; Guastella et al., 2026). The Tehuantepec maps illustrate why both ranges matter. The count inside the circle is 148 for SSN in both runs, while the complete family grows from 292 to 955.

On common members, replacing magnitude changes 7.92–8.22% of synthetic roles and 2.70% of observed roles at the SSN cutoff. Replacing all three fields changes 12.94–16.28% and 6.30%, respectively. Event density and spatial concentration may contribute. The design cannot isolate their contribution, and some observed offsets may come from mismatched earthquakes. The bootstrap conditions on the selected candidate pairs.

Bounds can leave quadratic work. Exact reproduction also preserves rounding: at coincident coordinates a cosine of 1−2⁻⁵³ gives about 0.0949 m. At M≥3.5 and w=1, 40 of 247 colocated SSN links have positive distances, as does one of two ComCat links. Dropping the colocated ComCat edge at M≥4.5 changes one unmatched role at eight weights and two at 1.4, without changing anchor families or paired results. Unknown magnitude types, detection gaps and retrospective roles further limit interpretation of physical triggering.

## 6. Conclusions

On 170~880 inputs the median native search pipeline fell from nearly nine minutes to under six seconds, an 88.46-fold change with the same output arrays. Repeating it at M≥3.5 revealed changes in best parents before any cutoff. At M≥4.5, testing those cutoffs explained when a component grew without many new parents. In the browser the resulting view carries the selected source, settings and observed records with it.

At w=1, the two Mexican catalogues assign the same role to 772 of 889 candidate pairs, but share only 41% of the union of representatives. Restricting the inputs to paired records while fixing the cutoffs yields 93.36% role agreement. Using fitted weights and the full native inputs yields 37.17% on 2021–2025 pairs. Those are separate comparisons. Among fixed members, substituting magnitude or position changes some roles, while the tested UTC substitutions leave them intact.

Known ancestry in the synthetic catalogues gives an additional test. Even without branching, GK groups most immigrants. On clustered samples with no perturbations, the always-child rule achieves a higher child F1 than either method. For observed data we recommend showing the representative overlap and full-family size alongside role agreement, and retaining the candidate pairs for inspection. Alaska tests dependence on the method within ComCat and Canada shows the retained years.

## Code and data availability

The [observatory](https://gabrielhuav.github.io/Seismic_Data_Geosciences/) runs from [commit 87dc5d3](https://github.com/gabrielhuav/Seismic_Data_Geosciences/tree/87dc5d3193cb4b5a229638e10ef5350d1dc8e411). The versioned Zenodo deposit [10.5281/zenodo.24361244](https://doi.org/10.5281/zenodo.24361244) archives the additional analysis code, protocols, aggregate tables and synthetic-history results. The original inputs and their licence notices are in the [frozen catalogue snapshot](https://github.com/gabrielhuav/Seismic_Data_Geosciences/tree/f5dae946eff95dd92510ce7607c57c989f92197a/research/sequences) (Servicio Sismológico Nacional, 2026). The [reproduction package](https://github.com/gabrielhuav/Seismic_Data_Geosciences/tree/main/research/sequences) includes the full analysis. Use `replay.py --replay-science` for the six baseline stages. To run the additional analyses, materialize the input files with `replay.py --materialize-only`, then use the same workspace with `r3/reproduce.py --workspace`.

## CRediT authorship contribution statement

José Manuel Villa Vargas: Conceptualization; Formal analysis; Supervision; Writing – original draft; Writing – review & editing.

Gabriel Hurtado Avilés: Data curation; Investigation; Methodology; Project administration; Resources; Software; Validation; Visualization.

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

## Declaration of competing interest

The authors declare no competing interests.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

OpenAI Codex assisted with literature searches, implementation, testing, numerical analysis, plotting code and manuscript revision. Anthropic Claude was used to review the manuscript and flag issues for correction. Retained data and reproducible scripts or the documented observatory views produced the figures. The authors reviewed and edited the content as needed and take full responsibility for the content of the published article.

## References

Aki, K., 1965. Maximum likelihood estimate of b in the formula log N = a − bM and its confidence limits. Bulletin of the Earthquake Research Institute, University of Tokyo 43(2), 237–239. [https://doi.org/10.15083/0000033631](https://doi.org/10.15083/0000033631).

Baiesi, M., Paczuski, M., 2004. Scale-free networks of earthquakes and aftershocks. Physical Review E 69, 066106. [https://doi.org/10.1103/PhysRevE.69.066106](https://doi.org/10.1103/PhysRevE.69.066106).

Bentley, J.L., 1975. Multidimensional binary search trees used for associative searching. Communications of the ACM 18, 509–517. [https://doi.org/10.1145/361002.361007](https://doi.org/10.1145/361002.361007).

Bird, P., 2003. An updated digital model of plate boundaries. Geochemistry, Geophysics, Geosystems 4, 1027. [https://doi.org/10.1029/2001GC000252](https://doi.org/10.1029/2001GC000252).

Bountzis, P., Lippiello, E., Baccari, S., Petrillo, G., 2026. Automatic earthquake declustering using the nearest-neighbor distance. Earth and Space Science 13, e2025EA004539. [https://doi.org/10.1029/2025EA004539](https://doi.org/10.1029/2025EA004539).

Cohen, J., 1960. A coefficient of agreement for nominal scales. Educational and Psychological Measurement 20, 37–46. [https://doi.org/10.1177/001316446002000104](https://doi.org/10.1177/001316446002000104).

Galaz, J., Cienfuegos, R., Echeverría, A., Pereira, S., Bertín, C., Prato, G., Karich, J.C., 2022. Integrating tsunami simulations in web applications using BROWNI, an open source client-side GPU-powered tsunami simulation library. Computers & Geosciences 159, 104976. [https://doi.org/10.1016/j.cageo.2021.104976](https://doi.org/10.1016/j.cageo.2021.104976).

Gardner, J.K., Knopoff, L., 1974. Is the sequence of earthquakes in Southern California, with aftershocks removed, Poissonian? Bulletin of the Seismological Society of America 64, 1363–1367. [https://doi.org/10.1785/BSSA0640051363](https://doi.org/10.1785/BSSA0640051363).

GEM Foundation, n.d. OpenQuake Model Building Toolkit, catalogue association implementation and documentation, source commit d13e63bebedcc6788e0ec88e8632957b749d3b60. [https://github.com/GEMScienceTools/oq-mbtk/tree/d13e63bebedcc6788e0ec88e8632957b749d3b60](https://github.com/GEMScienceTools/oq-mbtk/tree/d13e63bebedcc6788e0ec88e8632957b749d3b60) (accessed 15 November 2026).

Guastella, M., Figlioli, A., Martorana, R., D'Alessandro, A., 2026. Quantifying the impact of declustering techniques on completeness magnitude estimation. Bulletin of the Seismological Society of America 116, 946–962. [https://doi.org/10.1785/0120250144](https://doi.org/10.1785/0120250144).

Hsu, Y.-F., Zaliapin, I., Ben-Zion, Y., 2024. Informative modes of seismicity in nearest-neighbor earthquake proximities. Journal of Geophysical Research: Solid Earth 129, e2023JB027826. [https://doi.org/10.1029/2023JB027826](https://doi.org/10.1029/2023JB027826).

Hubert, L., Arabie, P., 1985. Comparing partitions. Journal of Classification 2, 193–218. [https://doi.org/10.1007/BF01908075](https://doi.org/10.1007/BF01908075).

Natural Earth, n.d. Admin 1–States, Provinces, 1:10 million, version 5.1.1. [https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/) (accessed 14 November 2026).

Natural Resources Canada, n.d. Earthquakes in Canada. Open Government Portal, record 4cedd37e-0023-41fe-8eff-bea45385e469. [https://open.canada.ca/data/en/dataset/4cedd37e-0023-41fe-8eff-bea45385e469](https://open.canada.ca/data/en/dataset/4cedd37e-0023-41fe-8eff-bea45385e469) (accessed 14 November 2026).

NVSeismoLab, n.d. eqclustering [software], source commit 393a02db91f278027cb9dbff7547199d1b667e69, Apache License 2.0. [https://github.com/NVSeismoLab/eqclustering/tree/393a02db91f278027cb9dbff7547199d1b667e69](https://github.com/NVSeismoLab/eqclustering/tree/393a02db91f278027cb9dbff7547199d1b667e69) (accessed 17 November 2026).

Ogata, Y., 1988. Statistical models for earthquake occurrences and residual analysis for point processes. Journal of the American Statistical Association 83, 9–27. [https://doi.org/10.1080/01621459.1988.10478560](https://doi.org/10.1080/01621459.1988.10478560).

Ogata, Y., 1998. Space-time point-process models for earthquake occurrences. Annals of the Institute of Statistical Mathematics 50, 379–402. [https://doi.org/10.1023/A:1003403601725](https://doi.org/10.1023/A:1003403601725).

Pérez-Campos, X., 2020. La magnitud de un sismo [in Spanish]. Geotecnia 256, 30–33. [https://www.smig.org.mx/archivos/revista-trimestral-smig/revista-geotecnia-smig-numero-256.pdf](https://www.smig.org.mx/archivos/revista-trimestral-smig/revista-geotecnia-smig-numero-256.pdf).

Rösler, B., Stein, S., Hough, S.E., 2022. On the documentation, independence, and stability of widely used seismological data products. Frontiers in Earth Science 10, 988098. [https://doi.org/10.3389/feart.2022.988098](https://doi.org/10.3389/feart.2022.988098).

Sawires, R., Santoyo, M.A., Peláez, J.A., Corona Fernández, R.D., 2019. An updated and unified earthquake catalog from 1787 to 2018 for seismic hazard assessment studies in Mexico. Scientific Data 6, 241. [https://doi.org/10.1038/s41597-019-0234-z](https://doi.org/10.1038/s41597-019-0234-z).

Schwarz, G., 1978. Estimating the dimension of a model. The Annals of Statistics 6(2), 461–464. [https://doi.org/10.1214/aos/1176344136](https://doi.org/10.1214/aos/1176344136).

Servicio Sismológico Nacional, 2026. Catálogo de sismos, México. Instituto de Geofísica, Universidad Nacional Autónoma de México. Downloaded 6 November 2026. [https://doi.org/10.21766/SSNMX/EC/MX](https://doi.org/10.21766/SSNMX/EC/MX).

sql.js contributors, n.d. sql.js, version 1.13.0: SQLite compiled to WebAssembly. [https://github.com/sql-js/sql.js/tree/v1.13.0](https://github.com/sql-js/sql.js/tree/v1.13.0) (accessed 14 November 2026).

U.S. Geological Survey, n.d.a. API documentation: earthquake catalog. [https://earthquake.usgs.gov/fdsnws/event/1/](https://earthquake.usgs.gov/fdsnws/event/1/) (accessed 14 November 2026).

U.S. Geological Survey, n.d.b. How products work in ComCat. [https://earthquake.usgs.gov/data/comcat/products.php](https://earthquake.usgs.gov/data/comcat/products.php) (accessed 14 November 2026).

U.S. Geological Survey, n.d.c. Contributing networks and catalogue sources. [https://earthquake.usgs.gov/data/catalog/contributors/](https://earthquake.usgs.gov/data/catalog/contributors/) (accessed 16 November 2026).

Utsu, T., 1965. A method for determining the value of b in a formula log n = a − bM showing the magnitude-frequency relation for earthquakes [in Japanese, English summary]. Geophysical Bulletin of the Hokkaido University 13, 99–103. [https://doi.org/10.14943/gbhu.13.99](https://doi.org/10.14943/gbhu.13.99).

Varini, E., Peresan, A., Zhuang, J., 2020. Topological comparison between the stochastic and the nearest-neighbor earthquake declustering methods through network analysis. Journal of Geophysical Research: Solid Earth 125, e2020JB019718. [https://doi.org/10.1029/2020JB019718](https://doi.org/10.1029/2020JB019718).

Villa Vargas, J.M., Hurtado Avilés, G., Climent Hernández, J.A., 2026. Cuando México tiembla: la historia contada por los datos [in Spanish]. AZCATL Revista de Divulgación en Ciencias, Ingeniería e Innovación 4 (6), 28–33. [https://doi.org/10.24275/AZC2026E1004](https://doi.org/10.24275/AZC2026E1004).

Virtanen, P., Gommers, R., Oliphant, T.E., Haberland, M., Reddy, T., Cournapeau, D., Burovski, E., Peterson, P., Weckesser, W., Bright, J., van der Walt, S.J., Brett, M., Wilson, J., Millman, K.J., Mayorov, N., Nelson, A.R.J., Jones, E., Kern, R., Larson, E., Carey, C.J., Polat, İ., Feng, Y., Moore, E.W., VanderPlas, J., Laxalde, D., Perktold, J., Cimrman, R., Henriksen, I., Quintero, E.A., Harris, C.R., Archibald, A.M., Ribeiro, A.H., Pedregosa, F., van Mulbregt, P., SciPy 1.0 Contributors, 2020. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nature Methods 17(3), 261–272. [https://doi.org/10.1038/s41592-019-0686-2](https://doi.org/10.1038/s41592-019-0686-2).

Wiemer, S., Wyss, M., 2000. Minimum magnitude of completeness in earthquake catalogs: examples from Alaska, the western United States, and Japan. Bulletin of the Seismological Society of America 90, 859–869. [https://doi.org/10.1785/0119990114](https://doi.org/10.1785/0119990114).

Woessner, J., Wiemer, S., 2005. Assessing the quality of earthquake catalogues: estimating the magnitude of completeness and its uncertainty. Bulletin of the Seismological Society of America 95, 684–698. [https://doi.org/10.1785/0120040007](https://doi.org/10.1785/0120040007).

Yin, L., Andrews, J., Heaton, T., 2018. Reducing process delays for real-time earthquake parameter estimation – An application of KD tree to large databases for Earthquake Early Warning. Computers & Geosciences 114, 22–29. [https://doi.org/10.1016/j.cageo.2018.01.001](https://doi.org/10.1016/j.cageo.2018.01.001).

Zaliapin, I., Ben-Zion, Y., 2013. Earthquake clusters in southern California I: identification and stability. Journal of Geophysical Research: Solid Earth 118, 2847–2864. [https://doi.org/10.1002/jgrb.50179](https://doi.org/10.1002/jgrb.50179).

Zaliapin, I., Ben-Zion, Y., 2015. Artefacts of earthquake location errors and short-term incompleteness on seismicity clusters in southern California. Geophysical Journal International 202, 1949–1968. [https://doi.org/10.1093/gji/ggv259](https://doi.org/10.1093/gji/ggv259).

Zaliapin, I., Ben-Zion, Y., 2020. Earthquake declustering using the nearest-neighbor approach in space-time-magnitude domain. Journal of Geophysical Research: Solid Earth 125, e2018JB017120. [https://doi.org/10.1029/2018JB017120](https://doi.org/10.1029/2018JB017120).

Zaliapin, I., n.d. Nearest_Neighbor_Cluster: earthquake cluster detection [software; eq_cluster.m version 29 March 2021]. GitHub distribution dttrugman/Nearest_Neighbor_Cluster, commit 636d07beb89bde7d7deb502db78beebb45528cca, GNU GPLv3. [https://github.com/dttrugman/Nearest_Neighbor_Cluster/tree/636d07beb89bde7d7deb502db78beebb45528cca](https://github.com/dttrugman/Nearest_Neighbor_Cluster/tree/636d07beb89bde7d7deb502db78beebb45528cca) (accessed 17 November 2026).

## Figure captions

Figure 1. Source records, browser processing and reusable exports. This interface selection includes 7107 of 287~936 rows across all catalogues for 2010–2025 at reported M≥4.5. A browser Worker runs SQL through sql.js (sql.js contributors, n.d.). Python/SQLite and JavaScript tests check results for stated inputs. This capture predates sequence views. PB2002 locates plate boundaries (Bird, 2003). Map boundaries need not depict accepted national boundaries. [Open implemented design](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=1&lang=en).

Figure 2. Native benchmark with one thread and three fresh processes per method and input. A shows elapsed times over seven chronological SSN M≥3.5 prefixes. B plots ratios of exhaustive to indexed medians. C shows peak working set across imports, runtime, compilation and warm-up. Bar endpoints in A and C show minima and maxima of three runs. D shows median times by phase for KD and octree at 170~880 records. Phase medians are computed separately. Linked results include nine inputs and 81 runs. [Explore matched benchmark](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=benchmark&benchmark_protocol=matched&lang=en).

Figure 3. Reported magnitude distributions for SSN Mexico (A), ComCat Mexico (B) and Alaska (E), with Aki–Utsu b and cumulative goodness of fit at cuts 4.1 and 4.5. Points in C and D show candidate parent edges at M≥4.5, d=1.6, w=1 and q=0.5. In C and D, events without an earlier record have no candidate edge. Each dot on or below the dashed cutoff fitted in 2016–2020 represents a retained edge. F groups reported differences for 2989 pairs by ComCat magnitude type. SSN types are unavailable. Boxes show medians and interquartile ranges, with whiskers at 1.5 times each range and points for outliers. Rare types are pooled. [Explore diagnostics](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=diagnostics&cut=4.5&pair_cut=3.5&lang=en).

Figure 4. Tehuantepec in 2017 (A–C) and Michoacán in 2022 (D–F), at reported M≥4.5 and d=1.6. At w=1 and apparent b, A and D show full families, B and E local maps, and C and F timelines. Blue marks SSN, orange ComCat and grey other records. Purple rings mark members added to the anchor family at w=b. Stars locate ComCat anchors. Dashed circles have 150 km radii, and dashed rectangles mark query bounds. Panel B shades territory south of 14°N. W1 and W2 identify record-level role changes. Grey lines in C and F join paired candidates. Links restore map settings. Sources are Natural Earth, SSN/UNAM and USGS ComCat.

Figure 5. Tehuantepec controls (A) and score comparison for W1 (B). Complete-family SSN counts grow from 292 to 955, with 148 family members inside a fixed circle. W1 keeps its candidate parent, and each log-score is compared with its corresponding cutoff. Links restore controls or W1.

Figure 6. Heat display for four source packages and 287~936 selected rows. Warmer colours indicate more epicentres per pixel neighbourhood, with equal weight per row. PB2002 marks plate boundaries. Map boundaries need not depict accepted national boundaries. [Open this view](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=2&lang=en).

Figure 7. SSN atlas with 242~288 selected rows. Package shape and hue stay fixed as magnitude shade changes. Time and coverage tools show retained years for four packages from three distributors. Map boundaries need not depict accepted national boundaries. [Atlas](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3&lang=en) and [Time and coverage](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3-time&lang=en).

Figure 8. Source-row selections. A is partial SSN 2026 at M≥4.5 with no land filter (204 records). B is USGS, 2020–2025, United States land, M≥3.5 (2335). C is NRCan, 1985–2019, Canada land, M≥3.5 (1492). D uses all packages, 2010–2025, M≥4.5 (7107). Exports include all selected rows. Sequence-pilot cohorts use separate bounds. Map boundaries need not depict accepted national boundaries. Panel links restore each view.

Figure 9. Land selections, 2000–2026, M≥3.5. A shows SSN Guerrero (19~963), B USGS California (551), C Canadian Yukon (225) and D Alaska (1112, including 739 USGS and 373 Canadian rows). Alaska packages cover different periods. Size and shade represent reported M. Guerrero's terrestrial maximum is 6.5. Three locality-labelled values of M 7.5, 7.2 and 7.1 fall outside Guerrero's land polygon. Map boundaries need not depict accepted national boundaries. Panel links restore each view.

Figure 10. SSN Guerrero land, 2000–2026 partial, M ≥4.5: 203 rows; Figure 9A differs only in threshold (M ≥3.5: 19~963), excluding 19~760. Earlier-interface capture and recomputed counts, without completeness inference. PB2002 neither reclassifies records nor supplies mechanisms. Map boundaries need not depict accepted national boundaries. [Open this zoomed map](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=6&lang=en).

Figure 11. USGS land queries return 15 records for Canada and 53 for Mexico at reported mww≥4.5 in 2020–2025. Both magnitude plots use 0.25-unit bins. Annual counts describe selected rows without completeness correction. [Open this comparison](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=7&lang=en).

Figure 12. Nine ranked epicentres appear inside a blue frame enlarged at left. A continental inset locates rank 4 in Alaska. Red dots denote epicentres, and leaders join offset badges to them. Ranking uses reported magnitudes on mixed scales. Each shared ComCat ID contributes one rank, retaining both sources. Map boundaries need not depict accepted national boundaries. [Top 10](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9a&lang=en).

Figure 13. SSN Guerrero land, 21~167 records since 1900 at M≥3.5 through partial 2026. Fourteen reach reported M≥7. Twelve of those events have a neighbour within 50 km, yielding ten distinct pairs. Dashed circles show search distance. SSN magnitude types are unknown. Other outlines show PB2002 plate boundaries. Map boundaries need not depict accepted national boundaries. [Proximity](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9b&lang=en).
