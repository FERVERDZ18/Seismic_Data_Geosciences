# A browser-based seismic data observatory for detecting and comparing earthquake sequences across North American catalogues

José Manuel Villa Vargas; Gabriel Hurtado Avilés¹*

¹ Escuela Superior de Cómputo (ESCOM), Instituto Politécnico Nacional, Mexico City, Mexico

*Corresponding author: Gabriel Hurtado Avilés. Email: ghurtadoa@ipn.mx.

ORCID: José Manuel Villa Vargas, https://orcid.org/0009-0009-2401-0661; Gabriel Hurtado Avilés, https://orcid.org/0009-0002-5686-1822.

## Abstract

When two earthquake catalogues report what appears to be the same event, a sequence algorithm can still choose different parents for it. We built a k-dimensional tree (KD-tree) search for magnitude-weighted parents and included it in a browser observatory. In a single-threaded native benchmark of 170~880 observations, the index returned the exhaustive results and reduced the median runtime from 524.04 s to 5.92 s. We used that search on two catalogues covering Mexico. At reported M≥3.5, increasing the magnitude weight from 1 to 1.4 changed 55% of defined parents in the Servicio Sismológico Nacional (SSN) catalogue and 28% in the U.S. Geological Survey Comprehensive Earthquake Catalog (ComCat). At reported M≥4.5, 772 of 889 candidate pairs had the same family role at weight 1, while the representative-event Jaccard index was 0.41. Weights estimated separately for each catalogue gave 37% agreement in temporal evaluation. Stable roles in simulations did not ensure recovery of the known families. Overlapping Mexican samples support agency comparisons. For Alaska we hold ComCat fixed and vary the method. Canada provides a descriptive inventory. The Mexican comparison rests on uncertain pair identities, incomplete magnitude-type metadata and unequal coverage.

Keywords: earthquake sequences; catalogue comparison; nearest-neighbour search; browser computing; declustering; reproducibility

## 1. Introduction

An earthquake can receive different roles when two agencies report different measurements. Even with those measurements fixed, changing the surrounding records can change its assigned parent. The agencies may also share solutions whose provenance is incomplete (Rösler et al., 2022). Agreement alone cannot establish triggering.

Gardner and Knopoff (1974) assign events using a time span and radius that depend on magnitude. Nearest-neighbour (NN) methods use lag, separation and the earlier event's magnitude (Baiesi and Paczuski, 2004; Zaliapin and Ben-Zion, 2013). Identifying families and recovering background seismicity use those links for distinct purposes (Zaliapin and Ben-Zion, 2020). Related studies compare declustered networks (Varini et al., 2020), examine proximity modes (Hsu et al., 2024) and automate NN declustering (Bountzis et al., 2026).

Yin et al. (2018) used a KD tree to speed early-warning queries. Our index bounds the parent score using lag, separation and magnitude. Exhaustive enumeration checks the minimiser. The lower magnitude cut tests whether parents change with weight and candidate pool. At the higher cut we measure how membership, substituted fields and thresholds change family roles. We keep agency magnitudes as reported (cf. Sawires et al., 2019).

Figure 1 shows how source data reach browser queries and exports, building on client-side computing (Galaz et al., 2022) and an earlier prototype (Villa Vargas et al., 2026). Mexico supplies concurrent SSN–ComCat samples. Alaska supports method comparisons within ComCat. The Canadian analysis is descriptive because the retained period lacks a concurrent counterpart (Natural Resources Canada, n.d.).

<!-- figure: 1 -->

## 2. Methods

### 2.1. Observations, association and coverage

Mexico's selection (UTC [2016-01-01,2026-01-01), latitude [14,33], longitude [−118,−86], reported M≥3.5) includes offshore and neighbouring areas, with 170~880 SSN and 3945 ComCat records. Alaska contributes 3630 ComCat records in UTC [2020-01-01,2026-01-01), latitude [50,72] and longitude [−170,−130]. This extent excludes the western Aleutians. We test the antimeridian separately. A missing SSN identifier receives a deterministic local key. The source fields, including missing magnitude types, carry through. Copy grouping, agency pairing and sequence membership are separate operations.

Candidate pairs require |Δt|≤30 s and separation≤50 km using radius 6371.0088 km and tolerance 10^-9 km. Among maximum-size one-to-one matchings, we minimize the quantized sum |Δt|/30+distance/50 and resolve ties by stable ID order. This leaves magnitude free for comparison. We test the 10/30/60 s by 10/50/100 km windows and compare with GEM software (GEM Foundation, n.d.). Ten circular ComCat shifts of ±7/14/30/60/90 days give negative controls. These tests give no adjudicated identities or false-association rate.

ComCat lists network, origin and magnitude sources separately. UNM (Instituto de Geofísica, UNAM) supplied 28 origins and five magnitudes in our selection. ECX appears among the contributors (U.S. Geological Survey, n.d.a, b, c). Natural Earth polygons tag onshore epicentres (Natural Earth, n.d.). Original-14 uses the original records down to 14°N. Updated-14 retains that extent with ComCat refreshed in two acquisitions on 17 November. Extended-12 includes both catalogues down to 12°N. All three use the 6 November 2026 SSN snapshot. Extended-12 masks of 0.5°, 1° and 2° mark cells with reported M≥3.5 events in both sources in 2016–2020. We score either original classifications or ones recomputed inside those cells at the same cutoffs. These masks describe reported occupancy.

### 2.2. Magnitudes and temporal calibration

The main cohort includes reported M≥4.5. We repeat the filter at 4.4 and 4.1. Plot bins use 0.1-unit half-up decimal rounding after filtering. We report the half-bin Aki–Utsu estimate (Aki, 1965; Utsu, 1965), maximum curvature plus 0.2 (MAXC+0.2) and cumulative goodness of fit (GFT), including failures to reach 95% (Wiemer and Wyss, 2000; Woessner and Wiemer, 2005). Distribution fits cannot show missed detections or establish a common scale. Pérez-Campos (2020) places SSN's Mw1 at 4.0 to 5.2 and W-phase moment magnitudes above 5.2 in 2020. Our cohort spans both ranges. We leave absent types unknown.

Mexico's 2021–2025 evaluation reuses parameters fitted in 2016–2020. Alaska's 2023–2025 evaluation reuses its 2020–2022 fit. Both retrospective splits followed the pilot. We specified the expanded analyses after review, before running their batches. Earlier parents remain eligible, and the retrospective representative can depend on later component members.

### 2.3. Identification and numerical contracts

For the reference comparison we set the distance exponent d=1.6, magnitude weight w=1 and coordinate split q=0.5 (Zaliapin and Ben-Zion, 2013). The usual magnitude weight is the Gutenberg–Richter b-value (Zaliapin and Ben-Zion, 2020), so we compare w=1 with alternatives fitted to reported magnitudes. For each target i, we select the strictly earlier j with the smallest proximity.

<!-- equation: metric -->

Search uses seconds and metres, cutoff coordinates years and kilometres. The radius is 6367.3 km, as in the author distribution. Python and JavaScript derive epoch years from UTC microseconds relative to 2016-01-01 using 31~557~600 s/year, then multiply before subtraction. UTC/UTF-8 ID determine order. In 170~880 SSN records, 17 equal-time pairs leave 14~599~901~743 eligible earlier pairs. Equal times alone cannot identify copies. The cosine enters acos after clamping to [−1,1].

The rescaled coordinates are {{math:rescaled-time}} and {{math:rescaled-distance}}. Expectation maximization (EM) fits two normals to development {{math:fit-log-product}} using initial means −6/−3, standard deviations of 1 and tolerance 0.001. The cutoff is where the two fitted densities agree at equal weights. We track modes, fit failures and Bayesian information criterion (BIC, Schwarz, 1978). A link survives when {{math:cut-log-sum}}. Using a sum of logs here preserves potential rounding differences from the fitted log of the product. Retained links give families with multiple members and isolated singletons. In a family, rank by greatest reported magnitude, then UTC and ID, to select its representative.

With positive lag, computed distance zero gives log proximity −∞. The link passes finite cuts, while the score stays outside the fit. The first record has no parent. We check computed zeros, coincident coordinates and source copies separately. Physical identity remains unadjudicated.

One reference runs eq_cluster.m (GPLv3, 636d07b, 29 March 2021) in Octave 11.3.0 with graphics adapters and the original numerical routine (Zaliapin, n.d.). We adapt only Python 2 syntax and NumPy aliases in Eqclustering 393a02d, keeping its 365.35-day convention and unclamped acos (NVSeismoLab, n.d.). Both tests compare parent identities.

Gardner–Knopoff (GK) uses a radius of {{math:gk-radius}} km and a forward window of {{math:gk-duration-low}} days below M 6.5 or {{math:gk-duration-high}} days otherwise, with half that span before the event. Allocation uses descending magnitude, UTC and ID. The indexed and exhaustive implementations share the membership rule and 6371.0088 km Earth radius.

### 2.4. Bounded spherical parent search

We partition unit-sphere coordinates with a KD tree or midpoint octree (Bentley, 1975; Virtanen et al., 2020). At {{math:target-time}}, only earlier observations are active. In addition to the spatial box, each node stores the latest active time U and highest active magnitude H. For distance ρ from the target to the box, {{math:earth-radius}} and {{math:lower-distance}}, each active j satisfies {{math:lag-bound}}, {{math:distance-bound}} and {{math:magnitude-bound}} when d>0 and w≥0. Multiplying these terms gives a lower bound on {{math:raw-metric-symbol}}.

<!-- equation: bound -->

Newly eligible records update U and H along the leaf-to-root path. Boxes may contain future epicentres. Maxima from different records loosen the bound. Search visits lower bounds first, prunes above the incumbent and scores active epicentres at leaves. Equal scores resolve by smaller canonical index.

Distinct epicentres in the cross-leaf fixture yield tied zero scores in floating point. Both trees agree with exhaustive search. To guard the real-arithmetic bound during pruning, subtract 2×10^-7 from the box chord (floor zero) and add 10^-10 to the incumbent log-score. Observed inputs also test traversal and parity. Python shares distance calculations and JavaScript checks shared canonical geometry. Full coordinate conversion lacks independent validation. KD storage is linear, activation O(Nh), worst-case search O(N²).

For each input we rotate backend order over three runs, launching a fresh one-thread process per backend. Each process warms up on 64 rows within its 1200-s wall limit. Inputs are seven chronological prefixes and both principal cohorts. We time geometry, construction, search and postprocessing, excluding imports, just-in-time (JIT) compilation and serialization. Peak working set includes runtime and JIT memory. Scheduling and CPU settings are uncontrolled. Browser Workers compare exhaustive and KD search at 2000, 10~000, 50~000 and 170~880 records, with three replicates and a 120-s cap. Loading is timed separately.

At M≥3.5 we rerun parent selection at nine weights in the two native catalogues and on the endpoints of the 2989 candidate pairs. We compare parent identities, lags and distances and check the outputs against exhaustive search and JavaScript. The two apparent-b weights are from the M≥4.5 development samples. The M≥3.5 proximity distributions are unimodal, so this comparison stops at parent selection.

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

Both indices reproduced all ten exhaustive arrays on every input, and all 81 native runs completed. For 170~880 SSN records, median runtime fell from 524.037 s to 5.924 s with the KD tree (88.46×) and 6.416 s with the octree (81.67×), with higher peak process memory (Table 1). On the M≥4.5 cohorts, exhaustive search took about 57 ms for SSN and 28 ms for ComCat. The indices primarily benefit full-input searches. The ratios compare medians from three replicates per backend and input on this machine. The inputs include chronological prefixes.

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

Browser speedup is measurable at 2000 and 10~000 records, where both searches finish. The six exhaustive cells at 50~000 and 170~880 reach the 120-s wall limit. In-app Chrome 157 (Windows) gives KD pipeline medians of 0.0324, 0.2232, 2.5510 and 12.8782 s, with 12.7537–18.0367 s at the largest size. All 18 outputs recover native parents and nonfinite masks. The maximum log-score difference is 3.38×10^-14. Loopback initialization and verification take a separate 315.9 ms. An earlier trial kept timings alone. Remote loading, paint and peak Worker memory remain unmeasured.

### 3.2. Selection and native classification

The principal cut retains 1780 SSN, 1256 Mexico-window ComCat and 555 Alaska records. The Mexican association graph has 3007 edges, 17 ambiguous components and 2989 assignments. GEM also returns 2989, sharing 2984. This measures agreement between implementations. Exact decimals give mean SSN−ComCat M=+0.13034, with |ΔM|≥0.3 in 1112/2989 pairs. The mean varies by supplied ComCat type (+0.1422 mb and −0.0406 mww). SSN magnitude types are unknown. Median separation and absolute lag are 14.29 km and 1.15 s in the distributions truncated by the association window.

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

Using each source's apparent b as its magnitude weight gives 51.52% overall role agreement and 37.17% in evaluation (Table 3). Using the larger b for both gives 47.36% and 32.46%. SSN fits have a single mode at the high-agreement w=1.2 setting and at exploratory magnitude cuts of 4.4 and 4.1.

As w rises from 1.2 to 1.3, temporal agreement falls from 86.13% to 34.03% with refitting. With the original w=1 cutoffs, agreement rises from 83.25% to 91.88% and the largest SSN family grows from 887 to 1193 events. Floor-centred cutoffs give 82.98% at both weights. Holding each refitted cutoff across weights confirms the interaction. The higher weight reduces agreement by 2.62 percentage points at the 1.2 cutoffs and by 28.01 at the 1.3 cutoffs.

Table 3. Prescribed native weight grid at δ=0 on the same 889/382 full/temporal candidates. Low/high are development slopes 1.090543/1.326568. Fit diagnostics are retained for every source; a finite EM cutoff alone does not imply supported mode separation.

<!-- table-widths: 1500, 1500, 1800, 1800, 2760 -->
| SSN w | ComCat w | All agreement | Temporal agreement | SSN modes / largest family |
| --- | --- | --- | --- | --- |
| 0.8 | 0.8 | 85.49% | 83.25% | 2 / 252 |
| 0.9 | 0.9 | 85.60% | 83.25% | 2 / 274 |
| 1 | 1 | 86.84% | 84.29% | 2 / 292 |
| 1.1 | 1.1 | 88.08% | 84.55% | 2 / 294 |
| 1.2 | 1.2 | 89.09% | 86.13% | 1 / 294 |
| 1.3 | 1.3 | 48.37% | 34.03% | 2 / 936 |
| 1.4 | 1.4 | 43.98% | 28.53% | 2 / 1065 |
| low | low | 88.41% | 85.08% | 2 / 294 |
| high | high | 47.36% | 32.46% | 2 / 955 |
| low | high | 86.39% | 82.46% | 2 / 294 |
| high | low | 51.52% | 37.17% | 2 / 955 |

Refitting at w=1.3 puts 936 of 1780 SSN events in the largest family. Its 565 bridges join separate w=1.2 components. Of these, 525 keep the same candidate parent and now pass the cutoff. The M 8.2 event of September 2017 is the parent on 483 bridges, with median separation 155 km and lag 1011 days. Higher weights enlarge the attraction domains of large candidate parents (Zaliapin and Ben-Zion, 2020).

For the 2846 pairs at or below reported SSN M 5.2, median absolute magnitude difference is 0.2. For the 143 above, it is 0.1. At the principal cut, roles at w=1 agree in 649 of 746 and 123 of 143 pairs, respectively. With refitting from w=1.2 to 1.3, evaluation agreement falls from 278 to 101 of 323 pairs and from 51 to 29 of 59.

Refitting at d=1.5 and w=1 gives 786 of 889 agreements (88.41%), including 328 of 382 evaluation pairs. Applying the d=1.6 cutoffs gives 777 and 324 agreements. Table 3's low/low weight row also gives 88.41% overall, with 325 evaluation matches.

Restricting both inputs to common members while keeping their measurements and cutoffs fixed raises NN agreement from 772 to 830 of 889 pairs. Refitting raises the count to 832. GK agreement similarly rises from 77.28% to 84.36% under common membership. In the thinning experiments, median agreement falls as more unmatched SSN records are kept.

On common membership, UTC substitution changes no NN roles and the magnitude and position effects are non-additive (Table 4). Among annual comparisons, 2017 has the largest sample and highest agreement, with 180 of 190 pairs agreeing (Table 5). That year includes 122 agreements in 125 pairs within the fixed anchor-family union and 58 in 65 outside, keeping the retrospective classifications fixed.

Table 4. Complete observed-measurement factorial: eight UTC/location/magnitude substitution patterns and two frozen cutoffs (16 cells). Entries are role agreement against unchanged common-member SSN fields under the same indicated cutoff, not physical truth; 111 uses all matched ComCat fields. Each column retains the same 889 or 382 candidate keys.

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

Table 5. All annual native NN comparisons at reported M≥4.5 and w=1. Years 2016–2020 inform development and 2021–2025 form the temporal evaluation; none constitutes an independent catalogue validation.

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

Changing from w=1 to each source's apparent b grows the 2017 SSN/ComCat anchor families from 292/204 to 955/208. Local membership stays at 148/136 (Figure 4). Paired-family Jaccard falls from 142/152=0.934 to 146/452=0.323, with local overlap still 85/86. In 2022, full families grow from 21/10 to 84/10 and local membership stays at 13/9.

In the default 2017 SSN graph, consecutive members are up to 929.61 days apart over 2631.62 days. Graph membership leaves aftershock duration unresolved. In Figure 4 the 14°N boundary cuts the 150-km circle. Extending the query to 12°N completes the circle. Its added portion contains four SSN records at M≥3.5, none at M≥4.5 and no ComCat records at either cut. Candidate parents could lie south of 12°N.

The first outside-window SSN role change in the 2017 family union is the M 7.1 event of 19 September 2017, 627.695 km and 11.559 days from its M 8.2 candidate parent. Its score crosses the cutoff from isolated (−5.22326>−5.31563) to associated (−7.90112≤−6.14514). The inspector shows the IDs, source fields and both classifications (Figure 5). The change cannot establish remote triggering.

The 555 ComCat records in Alaska isolate method dependence within one catalogue. NN and GK agree on 235 of 313 development roles (75.08%) and 170 of 242 evaluation roles (70.25%). Partition ARIs are 0.579 and 0.643. In evaluation NN assigns 148 isolated, 19 representative and 75 associated roles. GK gives 81, 32 and 129. Its indexed and exhaustive outputs agree.

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

Figures 4 and 5 show the anchor families and their record-level differences.

<!-- figure: 4 -->

## 4. Integrated exploration

W1 is outside the local panel but remains accessible from Figure 5B. The two columns show one candidate and two scores. This comparison comes from the browser Worker, which reruns classification on hash-checked rows for each choice of weight or calculation membership. The display radius, dates and visible source can be changed independently of the Worker. The resulting view is available as a link, SVG or JSON.

<!-- figure: 5 -->

<!-- figure: 6 -->

Zooming into the southern band in Figure 6 changes the colours because a different set of epicentres now falls within each pixel neighbourhood. The query's rows still supply the download and the sql.js workspace (sql.js contributors, n.d.). The outlines come from Bird's PB2002 model (Bird, 2003).

<!-- figure: 7 -->

The time view behind Figure 7 explains why the two map selections in Figures 8B and 8C cannot be compared year by year. The USGS selection starts in 2020, the year after the Canadian selection ends. Counts refer to the source, dates and filters in each panel. Figures 8–10 show the stored epicentres, and the sequence pilot uses its own limits (Section 2).

<!-- figure: 8 -->

<!-- figure: 9 -->

<!-- figure: 10 -->

Each map poses a different query. Figure 11 compares two regions with the same USGS inputs and bins. Figure 12 retrieves the ten largest reported magnitudes. Figure 13 asks which of the large Guerrero events lie within 50 km of one another. The query links open the settings used for those figures.

<!-- figure: 11 -->

<!-- figure: 12 -->

<!-- figure: 13 -->

## 5. Discussion

The Tehuantepec circle covers a stable part of a component that grows from 292 to 955 in the full SSN view. Our w=1.2 and 1.3 experiment gives a way to trace such growth. For 525 of the 565 bridges the parent had already been selected. Those bridges enter the component through changes in scores and the fitted cutoff. A local count alone would miss their effect on the full graph.

Unequal coverage changes which records can be selected as parents. This adds to known effects of location error and short-term incompleteness (Zaliapin and Ben-Zion, 2015). A changed parent can move a point in Figure 3 into another part of the proximity distribution. Proximity modes inform cutoffs (Hsu et al., 2024), so catalogue selection matters when comparing declustering methods (Varini et al., 2020) and estimating completeness after classification (Guastella et al., 2026).

GK groups almost every immigrant in the simulations with branching set to zero. An always-child rule scores above both methods on child F1 in the clustered simulations. Agreement of roles by itself tells us little about recovery of the generating groups. On fixed members, substituting empirical differences alters more roles than the Gaussian case. Some of those differences may come from associations between different events.

Worst-case work is quadratic if the bound leaves most candidates to be scored. Both searches use the same geometry, so exact agreement can include the same rounding error. With identical coordinates, a cosine of 1−2⁻⁵³ returns about 0.0949 m. At M≥3.5 and w=1, 40 of 247 colocated SSN links have positive computed distances and 207 have zero. ComCat has one of each. At M≥4.5 an ablation drops the one ComCat colocated edge at each weight and keeps all other links and cutoffs. One unmatched role changes at eight weights and two at 1.4. The anchor families and paired results are unaffected.

The bootstrap reuses the Mexico candidate identities. A catalogue with adjudicated identities would be needed to estimate identity error. The unreported SSN magnitude types and uncertain completeness also limit the comparison. Later family members can change earlier role labels in this retrospective design. Alaska changes the algorithm within one source, and Canada's views show its available records. Our links describe the output of a grouping rule and cannot establish triggering, future earthquakes or damage.

## 6. Conclusions

On 170~880 inputs the median native search pipeline fell from nearly nine minutes to under six seconds, an 88.46-fold change with the same output arrays. Repeating it at M≥3.5 revealed changes in best parents before any cutoff. At M≥4.5, testing those cutoffs explained when a component grew without many new parents. In the browser the resulting view carries the selected source, settings and observed records with it.


## Code and data availability

Run `replay.py --replay-science` from research/sequences in the [pinned repository](https://github.com/gabrielhuav/Seismic_Data_Geosciences/tree/f5dae946eff95dd92510ce7607c57c989f92197a), using the environment in its README. The six stages use frozen tables and were checked against packaged results in clean Windows x64. The README also lists the timing, browser, reference-code and GEM checks. The new cutoff and resampling runs reuse that input with local scripts. The [observatory](https://gabrielhuav.github.io/Seismic_Data_Geosciences/) records provider attribution and terms (Servicio Sismológico Nacional, 2026).

## CRediT authorship contribution statement

José Manuel Villa Vargas: Conceptualization; Formal analysis; Supervision; Writing – original draft; Writing – review & editing.

Gabriel Hurtado Avilés: Data curation; Investigation; Methodology; Project administration; Resources; Software; Validation; Visualization.

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

## Declaration of competing interest

The authors declare no competing interests.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

OpenAI Codex assisted with literature searches, software and testing, numerical analysis, plotting code, drafting and revision. Anthropic Claude assisted with source checks, manuscript restructuring and automated critique. The figures were produced from documented data or from the working observatory. The named authors are responsible for verifying the analysis and manuscript before editorial submission.

## References

Aki, K., 1965. Maximum likelihood estimate of b in the formula log N = a − bM and its confidence limits. Bulletin of the Earthquake Research Institute, University of Tokyo 43(2), 237–239. https://repository.dl.itc.u-tokyo.ac.jp/records/33631.

Baiesi, M., Paczuski, M., 2004. Scale-free networks of earthquakes and aftershocks. Physical Review E 69, 066106. https://doi.org/10.1103/PhysRevE.69.066106.

Bentley, J.L., 1975. Multidimensional binary search trees used for associative searching. Communications of the ACM 18, 509–517. https://doi.org/10.1145/361002.361007.

Bird, P., 2003. An updated digital model of plate boundaries. Geochemistry, Geophysics, Geosystems 4, 1027. https://doi.org/10.1029/2001GC000252.

Bountzis, P., Lippiello, E., Baccari, S., Petrillo, G., 2026. Automatic earthquake declustering using the nearest-neighbor distance. Earth and Space Science 13, e2025EA004539. https://doi.org/10.1029/2025EA004539.

Cohen, J., 1960. A coefficient of agreement for nominal scales. Educational and Psychological Measurement 20, 37–46. https://doi.org/10.1177/001316446002000104.

Galaz, J., Cienfuegos, R., Echeverría, A., Pereira, S., Bertín, C., Prato, G., Karich, J.C., 2022. Integrating tsunami simulations in web applications using BROWNI, an open source client-side GPU-powered tsunami simulation library. Computers & Geosciences 159, 104976. https://doi.org/10.1016/j.cageo.2021.104976.

Gardner, J.K., Knopoff, L., 1974. Is the sequence of earthquakes in Southern California, with aftershocks removed, Poissonian? Bulletin of the Seismological Society of America 64, 1363–1367. https://doi.org/10.1785/BSSA0640051363.

GEM Foundation, n.d. OpenQuake Model Building Toolkit, catalogue association implementation and documentation, source commit d13e63bebedcc6788e0ec88e8632957b749d3b60. https://github.com/GEMScienceTools/oq-mbtk/tree/d13e63bebedcc6788e0ec88e8632957b749d3b60 (accessed 15 November 2026).

Guastella, M., Figlioli, A., Martorana, R., D'Alessandro, A., 2026. Quantifying the impact of declustering techniques on completeness magnitude estimation. Bulletin of the Seismological Society of America 116, 946–962. https://doi.org/10.1785/0120250144.

Hsu, Y.-F., Zaliapin, I., Ben-Zion, Y., 2024. Informative modes of seismicity in nearest-neighbor earthquake proximities. Journal of Geophysical Research: Solid Earth 129, e2023JB027826. https://doi.org/10.1029/2023JB027826.

Hubert, L., Arabie, P., 1985. Comparing partitions. Journal of Classification 2, 193–218. https://doi.org/10.1007/BF01908075.

Natural Earth, n.d. Admin 1–States, Provinces, 1:10 million, version 5.1.1. https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/ (accessed 14 November 2026).

Natural Resources Canada, n.d. Earthquakes in Canada. Open Government Portal, record 4cedd37e-0023-41fe-8eff-bea45385e469. https://open.canada.ca/data/en/dataset/4cedd37e-0023-41fe-8eff-bea45385e469 (accessed 14 November 2026).

NVSeismoLab, n.d. eqclustering [software], source commit 393a02db91f278027cb9dbff7547199d1b667e69, Apache License 2.0. https://github.com/NVSeismoLab/eqclustering/tree/393a02db91f278027cb9dbff7547199d1b667e69 (accessed 17 November 2026).

Ogata, Y., 1988. Statistical models for earthquake occurrences and residual analysis for point processes. Journal of the American Statistical Association 83, 9–27. https://doi.org/10.1080/01621459.1988.10478560.

Ogata, Y., 1998. Space-time point-process models for earthquake occurrences. Annals of the Institute of Statistical Mathematics 50, 379–402. https://doi.org/10.1023/A:1003403601725.

Pérez-Campos, X., 2020. La magnitud de un sismo [in Spanish]. Geotecnia 256, 31–34. https://www.smig.org.mx/archivos/revista-trimestral-smig/revista-geotecnia-smig-numero-256.pdf.

Rösler, B., Stein, S., Hough, S.E., 2022. On the documentation, independence, and stability of widely used seismological data products. Frontiers in Earth Science 10, 988098. https://doi.org/10.3389/feart.2022.988098.

Sawires, R., Santoyo, M.A., Peláez, J.A., Corona Fernández, R.D., 2019. An updated and unified earthquake catalog from 1787 to 2018 for seismic hazard assessment studies in Mexico. Scientific Data 6, 241. https://doi.org/10.1038/s41597-019-0234-z.

Schwarz, G., 1978. Estimating the dimension of a model. The Annals of Statistics 6(2), 461–464. https://doi.org/10.1214/aos/1176344136.

Servicio Sismológico Nacional, 2026. Catálogo de sismos, México. Instituto de Geofísica, Universidad Nacional Autónoma de México. Downloaded 6 November 2026. https://doi.org/10.21766/SSNMX/EC/MX.

sql.js contributors, n.d. sql.js, version 1.13.0: SQLite compiled to WebAssembly. https://github.com/sql-js/sql.js/tree/v1.13.0 (accessed 14 November 2026).

U.S. Geological Survey, n.d.a. API documentation: earthquake catalog. https://earthquake.usgs.gov/fdsnws/event/1/ (accessed 14 November 2026).

U.S. Geological Survey, n.d.b. How products work in ComCat. https://earthquake.usgs.gov/data/comcat/products.php (accessed 14 November 2026).

U.S. Geological Survey, n.d.c. Contributing networks and catalogue sources. https://earthquake.usgs.gov/data/catalog/contributors/ (accessed 16 November 2026).

Utsu, T., 1965. A method for determining the value of b in a formula log n = a − bM showing the magnitude-frequency relation for earthquakes [in Japanese, English summary]. Geophysical Bulletin of the Hokkaido University 13, 99–103. https://doi.org/10.14943/gbhu.13.99.

Varini, E., Peresan, A., Zhuang, J., 2020. Topological comparison between the stochastic and the nearest-neighbor earthquake declustering methods through network analysis. Journal of Geophysical Research: Solid Earth 125, e2020JB019718. https://doi.org/10.1029/2020JB019718.

Villa Vargas, J.M., Hurtado Avilés, G., Climent Hernández, J.A., 2026. Cuando México tiembla: la historia contada por los datos [in Spanish]. AZCATL Revista de Divulgación en Ciencias, Ingeniería e Innovación 4 (6), 28–33. https://doi.org/10.24275/AZC2026E1004.

Virtanen, P., Gommers, R., Oliphant, T.E., et al., 2020. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nature Methods 17, 261–272. https://doi.org/10.1038/s41592-019-0686-2.

Wiemer, S., Wyss, M., 2000. Minimum magnitude of completeness in earthquake catalogs: examples from Alaska, the western United States, and Japan. Bulletin of the Seismological Society of America 90, 859–869. https://doi.org/10.1785/0119990114.

Woessner, J., Wiemer, S., 2005. Assessing the quality of earthquake catalogues: estimating the magnitude of completeness and its uncertainty. Bulletin of the Seismological Society of America 95, 684–698. https://doi.org/10.1785/0120040007.

Yin, L., Andrews, J., Heaton, T., 2018. Reducing process delays for real-time earthquake parameter estimation – An application of KD tree to large databases for Earthquake Early Warning. Computers & Geosciences 114, 22–29. https://doi.org/10.1016/j.cageo.2018.01.001.

Zaliapin, I., Ben-Zion, Y., 2013. Earthquake clusters in southern California I: identification and stability. Journal of Geophysical Research: Solid Earth 118, 2847–2864. https://doi.org/10.1002/jgrb.50179.

Zaliapin, I., Ben-Zion, Y., 2015. Artefacts of earthquake location errors and short-term incompleteness on seismicity clusters in southern California. Geophysical Journal International 202, 1949–1968. https://doi.org/10.1093/gji/ggv259.

Zaliapin, I., Ben-Zion, Y., 2020. Earthquake declustering using the nearest-neighbor approach in space-time-magnitude domain. Journal of Geophysical Research: Solid Earth 125, e2018JB017120. https://doi.org/10.1029/2018JB017120.

Zaliapin, I., n.d. Nearest_Neighbor_Cluster: earthquake cluster detection [software; eq_cluster.m version 29 March 2021]. GitHub distribution dttrugman/Nearest_Neighbor_Cluster, commit 636d07beb89bde7d7deb502db78beebb45528cca, GNU GPLv3. https://github.com/dttrugman/Nearest_Neighbor_Cluster/tree/636d07beb89bde7d7deb502db78beebb45528cca (accessed 17 November 2026).

## Figure captions

Figure 1. How source records move through the observatory. The selection shown from the original interface is 7107 of 287~936 rows, across all catalogues for 2010–2025 at reported M ≥4.5. A browser Worker runs SQL through sql.js (sql.js contributors, n.d.). The Python/SQLite audit and JavaScript parity fixtures test the results for the stated inputs. The image precedes the sequence workspace. PB2002 locates plate boundaries for context (Bird, 2003). Map boundaries need not depict accepted national boundaries. [Open implemented design](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=1&lang=en).

Figure 2. Native benchmark with one thread and three fresh processes per method and input. A follows elapsed time over seven prefixes of the chronological SSN M≥3.5 cohort. B divides the median exhaustive time by the median indexed time. C shows peak working set across imports, runtime, compilation and warm-up. Endpoints of the bars in A and C give the minimum and maximum of three runs. D separates the median phase times for KD and octree at 170~880 records. Each median is computed for its phase separately. The observatory view contains all nine inputs and 81 runs. [Explore the matched benchmark](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=benchmark&benchmark_protocol=matched&lang=en) (available after the observatory update).

Figure 3. A and B show the reported magnitude distributions in SSN and ComCat Mexico, and E shows Alaska. We fit Aki–Utsu b and show cumulative goodness of fit at reported cuts of 4.1 and 4.5. The fits describe the retained magnitudes. In C and D, each point is a candidate parent edge from the native M≥4.5 cohort at d=1.6, w=1 and q=0.5. The first record has no point because it has no earlier parent. A point on or below its dashed 2016–2020 cutoff retains the edge. F groups the reported differences of all 2,989 pairs by ComCat magnitude type, since SSN did not supply types. The boxes show the median and interquartile range, the whiskers extend to 1.5 times that range and the points plot all outliers. Rare types are pooled in this display. [Explore diagnostics](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=diagnostics&cut=4.5&pair_cut=3.5&lang=en).

Figure 4. Tehuantepec in 2017 (A–C) and Michoacán in 2022 (D–F), with reported M≥4.5 and d=1.6. Compare w=1 with the apparent b of each source. Blue marks SSN, orange ComCat and grey other retained records. Purple rings show records added to the family at w=b. The star locates the ComCat anchor. The dashed circle has a 150 km radius, and the dashed rectangle marks the retained query bounds. Panel B shades the area beyond the original query south of 14°N. W1 and W2 are examples of records to inspect for a role change. Grey lines in C and F join candidate pairs. The linked Leaflet panels open at the positions used for the SVG exports. Word stores each SVG with a 300 ppi PNG fallback. Map sources are Natural Earth, SSN/UNAM and USGS ComCat.

Figure 5. Tehuantepec controls (A) and the two scores for W1 (B). In A, compare the complete-family count (292→955) with the 148 SSN family members still inside the circle. In B, read across the parent row first, then compare each log-score with its own cutoff. The links return to the controls or to W1 at the saved settings.

Figure 6. Four source packages, 287~936 selected rows. The coastal band appears warm because many selected rows fall in the same pixel neighbourhoods. Every row has unit weight. The capture predates the current grouping and sequence controls. PB2002 marks the plates for context. Map boundaries need not depict accepted national boundaries. [Open this view](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=2&lang=en).

Figure 7. With the SSN package selected, the atlas shows 242~288 rows. Package shape and hue stay fixed as magnitude shade changes. The time and coverage view traces the retained years for the four packages supplied by three distributors. Map boundaries need not depict accepted national boundaries. [Atlas](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3&lang=en) and [Time and coverage](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3-time&lang=en).

Figure 8. Source-row selections: (A) SSN, 2026 partial, M ≥4.5, no land filter: 204; (B) USGS North American windows, 2020–2025, M ≥3.5, United States land: 2335; (C) Canadian source, 1985–2019, M ≥3.5, Canada land: 1492; (D) all packages, 2010–2025, M ≥4.5: 7107. Extent does not restrict exports. These are preserved interface selections, not the sequence-pilot cohorts. Map boundaries need not depict accepted national boundaries. Links immediately below panels restore their views.

Figure 9. Land selections, 2000–2026, M ≥3.5: (A) SSN Guerrero, 19~963; (B) USGS California, 551; (C) Canadian Yukon, 225; (D) Alaska, 1112 (739 USGS; 373 Canadian). Counts follow each package's coverage; the Alaska sources are not contemporaneous. Size/shade encode reported M without conversion. Guerrero's terrestrial maximum is 6.5; three locality-labelled M 7.5/7.2/7.1 records lie outside the land polygon, not evidence of absent regional earthquakes. Map boundaries need not depict accepted national boundaries. Links immediately below panels restore their views.

Figure 10. SSN Guerrero land, 2000–2026 partial, M ≥4.5: 203 rows; Figure 9A differs only in threshold (M ≥3.5: 19~963), excluding 19~760. Earlier-interface capture and recomputed counts, without completeness inference. PB2002 neither reclassifies records nor supplies mechanisms. Map boundaries need not depict accepted national boundaries. [Open this zoomed map](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=6&lang=en).

Figure 11. The USGS queries for land in Canada and Mexico return 15 and 53 records, respectively, at reported mww ≥4.5 in 2020–2025. Both magnitude plots use the same 0.25-unit bins. Annual counts describe the selected rows without a completeness correction. [Open this comparison](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=7&lang=en).

Figure 12. Nine of the ten ranks lie in the blue frame, enlarged at left. The continental inset locates rank 4 in Alaska. Red dots mark epicentres and leaders run from offset badges to their locations. The ranking uses reported magnitudes on mixed scales. Rows with a common ComCat ID contribute one rank while retaining both sources. Map boundaries need not depict accepted national boundaries. [Top 10](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9a&lang=en).

Figure 13. Of 21~167 SSN land records in Guerrero since 1900 (M ≥3.5, partial 2026), fourteen reach reported M ≥7. Among those, twelve have at least one neighbour within 50 km, yielding ten distinct pairs. Dashed circles mark the search distance. SSN magnitude types are unknown. The other outlines show PB2002 plate boundaries. Map boundaries need not depict accepted national boundaries. [Proximity](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9b&lang=en).
