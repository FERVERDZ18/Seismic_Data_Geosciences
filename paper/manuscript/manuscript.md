# A browser-based seismic data observatory for detecting and comparing earthquake sequences across North American catalogues

José Manuel Villa Vargas; Gabriel Hurtado Avilés¹*

¹ Escuela Superior de Cómputo (ESCOM), Instituto Politécnico Nacional, Mexico City, Mexico

*Corresponding author: Gabriel Hurtado Avilés. Email: ghurtadoa@ipn.mx.

ORCID: José Manuel Villa Vargas, https://orcid.org/0009-0009-2401-0661; Gabriel Hurtado Avilés, https://orcid.org/0009-0002-5686-1822.

## Abstract

Earthquake catalogues can assign different sequence roles to corresponding observations because measurements and surrounding records both change. We present a browser-based seismic data observatory with bounded magnitude-weighted spherical parent search and record-level explanations of disagreement. On 170~880 records, its one-thread KD search reproduces exhaustive outputs with a measured median speedup of 88.46×. A Mexican comparison preserves 170~880 SSN and 3945 ComCat records from 2016–2025. At M≥3.5, changing weight from 1 to 1.4 changes 55.45%/27.59% of defined SSN/ComCat parents. Above reported M 4.5, 889 candidate pairs cover 49.94%/70.78% of selected source records. Fixed-weight role agreement is 86.84% overall and 84.29% in temporal evaluation; representative-event Jaccard is only 41.30% overall. Source-specific apparent-b weights yield 37.17% temporal agreement, and a common higher weight yields 32.46%. At w=1, context restriction changes 59.07% of SSN versus 3.75% of ComCat parents over 2988 comparisons per source with parents defined in both contexts; a field factorial quantifies interacting responses. Shared-latent synthetic catalogues separate inclusion losses, role changes and ancestry recovery across 60 histories and 960 perturbation cells. Stable descriptions need not identify generated children accurately. A version-controlled southern extension tests boundary effects; Alaska supplies a single-source method comparison, while Canada remains descriptive. Native maps, timelines and inspection make these calculations explorable without replacing source records. Unknown SSN magnitude types, unadjudicated candidate identities and incompletely measured coverage constrain physical interpretation: operational families do not establish triggering or earthquake forecasts.

Keywords: earthquake sequences; catalogue comparison; nearest-neighbour search; browser computing; declustering; reproducibility

## 1. Introduction

Regional and global earthquake catalogues may describe a sequence differently: reported fields differ, and surrounding observations can change a fixed event's parent or family. Shared contributing solutions and incomplete provenance complicate apparent independence (Rösler et al., 2022). Agreement cannot supply physical truth.

Gardner and Knopoff (1974) use magnitude-dependent space–time windows. Nearest-neighbour methods combine time, distance and parent magnitude (Baiesi and Paczuski, 2004; Zaliapin and Ben-Zion, 2013), with distinct objectives for family identification and background recovery (Zaliapin and Ben-Zion, 2020). Network comparisons, proximity distributions and threshold selection are established (Varini et al., 2020; Hsu et al., 2024; Bountzis et al., 2026); visualization alone adds no identification principle.

We ask how to reproduce the weighted spherical parent search efficiently and quantify disagreements on fixed candidate keys when context, fields and calibration change separately. KD search accelerates earthquake early-warning databases (Yin et al., 2018), but ordinary spatial proximity does not minimize this asymmetric criterion. We bound it directly and expose families and witnesses in the browser. The geoscientific estimand is catalogue-dependent operational descriptions, rather than the general observation that errors affect clusters or the magnitude homogenization addressed by Sawires et al. (2019).

The observatory integrates observations, regional exploration and exports (Figure 1), extending client-side scientific computation (Galaz et al., 2022). Its earlier visualization prototype contains none of these experiments (Villa Vargas et al., 2026). Mexico supplies concurrent SSN–ComCat comparisons. Alaska compares methods within ComCat; the Canadian package remains descriptive because its retained period lacks a concurrent counterpart (Natural Resources Canada, n.d.).

<!-- figure: 1 -->

## 2. Methods

### 2.1. Observations, association and coverage

The original Mexican selection is UTC [2016-01-01,2026-01-01), latitude [14,33], longitude [−118,−86], reported M≥3.5: 170~880 SSN and 3945 ComCat records. The transboundary rectangle includes neighbouring countries and offshore observations. Alaska covers UTC [2020-01-01,2026-01-01), latitude [50,72], longitude [−170,−130], with 3630 ComCat records, excluding western Aleutians. Antimeridian fixtures are separate. Original fields remain unchanged; missing SSN identifiers receive deterministic local keys and missing magnitude types remain unknown. Source-copy grouping, agency association and sequence membership are distinct.

Candidate edges satisfy inclusive |Δt|≤30 s and distance≤50 km, with radius 6371.0088 km and 10^-9 km tolerance. Bipartite assignment maximizes cardinality, then minimizes the quantized sum |Δt|/30+distance/50, with stable ID ties. Magnitude does not determine identity. Nine windows combine 10/30/60 s with 10/50/100 km; GEM is a software comparator, not adjudicated truth (GEM Foundation, n.d.). Ten circular ComCat shifts of ±7/14/30/60/90 days are negative controls, not false-association-rate estimates.

ComCat redistributes contributing solutions: event network, origin and magnitude sources remain separate; 28 origins/five magnitudes identify UNM, documented as Instituto de Geofísica, UNAM, with ECX contributions also present (U.S. Geological Survey, n.d.a, b, c). Natural Earth land polygons are geographic labels (Natural Earth, n.d.), not coverage measurements. Three southern-control cohorts separate original data at 14°N (A), updated ComCat at 14°N with unchanged SSN (B), and both sources extended to 12°N (C). SSN retains its 6 November 2026 snapshot; ComCat was acquired in two intervals on 17 November 2026, without assumed atomicity. Shared occupied cells at 0.5°/1°/2°, requiring at least one M≥3.5 observation from each source during 2016–2020, are frozen for evaluation. Projection retains C context; restriction recomputes within cells, transporting C cuts without refitting. This is observed support, not instrumental coverage or equal detection.

### 2.2. Magnitudes and temporal calibration

Reported M≥4.5 is principal; ≥4.4/4.1 are sensitivities, not certified completeness or common Mw. Decimal half-up 0.1 plotting bins follow native-value filtering. The half-bin Aki–Utsu estimator (Aki, 1965; Utsu, 1965) accompanies MAXC+0.2, cumulative goodness of fit and failed GFT95 tails (Wiemer and Wyss, 2000; Woessner and Wiemer, 2005). Decimal magnitude differences remain exact; SSN policy cannot impute missing types (Pérez-Campos, 2020).

Mexico develops on 2016–2020 and evaluates frozen parameters on 2021–2025; Alaska uses 2020–2022/2023–2025. These divisions follow an exploratory pilot; expanded protocols precede their new batches but follow review. Neither is blind prospective validation. Earlier observations remain eligible parents; retrospective representatives can depend on later component members.

### 2.3. Identification and numerical contracts

The principal Zaliapin–Ben-Zion (2013) method uses d=1.6, w=1, q=0.5. Weight 1 reproduces the reference convention, not a physical catalogue slope; customary apparent-b alternatives are tested (Zaliapin and Ben-Zion, 2020). Each target minimizes proximity over strictly earlier j:

<!-- equation: metric -->

Search uses elapsed seconds/metres; thresholds use years/kilometres. Radius 6367.3 km follows the author distribution. Python/JavaScript share epoch-year inputs derived from UTC microseconds relative to 2016-01-01 and 31~557~600 s/year, multiplied before subtraction. Sorting uses UTC/UTF-8 ID. Seventeen equal-time pairs are ineligible in SSN 170~880, leaving 14~599~901~743 earlier pairs; ties do not establish duplicates. The port clamps spherical cosine to [−1,1].

Threshold coordinates are {{math:rescaled-time}} and {{math:rescaled-distance}}. Two-normal EM fits development {{math:fit-log-product}}, starting means −6/−3, standard deviations 1 and tolerance 0.001. The source boundary intersects unweighted densities despite fitted weights. Failed fits, modes and BIC remain visible (Schwarz, 1978). Links satisfy {{math:cut-log-sum}}; fitting product-logs and cutting sums retain their floating distinction. Components are operational families, their largest reported M is representative with UTC/ID ties, and singletons isolated.

Evaluated distance 0 implies proximity 0 at positive lag: its −∞ log-score is excluded from EM but retained below every finite cut, with canonical parent ties. First records without parents remain separate. Numerical zero, coordinate coincidence, exact-copy rows and physical identity are audited separately.

The GPLv3 author distribution 636d07b identifies eq_cluster.m as 29 March 2021 (Zaliapin, n.d.); parent-search numerics run unchanged under Octave 11.3.0 with declared graphical adapters, not MATLAB. Eqclustering 393a02d (NVSeismoLab, n.d.) retains its 365.35-day convention and unclamped acos; only Python 2 syntax/NumPy aliases are adapted. External comparisons test parent selection, not equality of scores, EM cuts or roles.

GK radius is {{math:gk-radius}} km; following duration is {{math:gk-duration-low}} days below M 6.5, otherwise {{math:gk-duration-high}} days, with half that preceding interval. Descending M, UTC and ID govern allocation. Radius 6371.0088 km preserves the existing GK contract rather than silently replacing the NN reference constant. Indexed/exhaustive membership is tested with the same predicate.

### 2.4. Bounded spherical parent search

KD and midpoint-octree partitions index unit-sphere coordinates (Bentley, 1975; Virtanen et al., 2020). At {{math:target-time}}, strictly earlier parents are active. Each node stores its spatial box, latest active time U and maximum active magnitude H. For target-to-box distance ρ, {{math:earth-radius}} and {{math:lower-distance}}, every active j satisfies {{math:lag-bound}}, {{math:distance-bound}} and {{math:magnitude-bound}}, for d>0, w≥0. Their product bounds raw {{math:raw-metric-symbol}}:

<!-- equation: bound -->

U/H may describe different records; this weakens the bound without invalidating it. Static boxes can contain future locations, but U/H use eligible parents. Activation follows leaf-to-root paths; search visits the smaller-bound child first and prunes only strictly worse nodes. Candidate ties choose the smaller canonical index; empty nodes contain no candidate, and zero bounds cannot be pruned against zero incumbents. Depth is excluded.

Chord/log traversal guards 2×10^-7/10^-10 expand search without changing evaluated values. This real-arithmetic argument is not a universal IEEE/libm certificate. Finite observed inputs and coincident cross-leaf fixtures test selection/pruning. Exhaustive and indexed Python backends share the distance primitive; this is an independent traversal check, not an independent geometric oracle. JavaScript also shares canonical trigonometric preprocessing with consistency checks, so parity does not independently validate the complete latitude/longitude-to-geometry pipeline. KD storage is linear, activation O(Nh), worst-case search O(N²).

The native benchmark gives each backend one thread, three fresh processes, common 64-row warm-up, balanced order and seven chronological prefixes through 170~880, plus both complete principal cohorts. Geometry/construction/search/numeric postprocessing are timed; imports, JIT and serialization excluded. Peak process working set includes runtime/JIT. Timeouts are censored at 1200 s. Apps/OS, affinity and frequency are uncontrolled. Figure 2 retains the earlier four-thread protocol. Browser reference/KD Workers use N=2000/10000/50000/170880, three replicates and 120-s caps, separating transport/search without claiming reliable Worker peak memory. Browser host hardware is not independently verified, and cross-environment speed ratios are excluded. Current Node is 24.22.1; Node 22.12 results are historical.

The large M≥3.5 study varies nine fixed weights over native cohorts and endpoints of 2989 pairs, testing parent changes, comparability and lag/distance distributions against exhaustive/JavaScript results. The two retained apparent-b weights come from M≥4.5 development, not a fit to M≥3.5. Unimodal distributions prevent presenting these proximities as validated families.

### 2.5. Catalogue interventions and uncertainty

Principal comparisons retain candidates above the cut in both sources. Native classification uses all selected context; common-membership classification keeps candidate members with measurements/cuts fixed, while common-development refitting is separate. A factorial substitutes ComCat UTC/paired coordinates/M into common SSN fields on 889 keys, using each frozen cut. Original SSN membership/time define evaluation. Restriction preserves full-partition connections and does not recluster. GK additionally retains 0/25/50/75/100% unmatched SSN context with 20 seeds per intermediate fraction.

The grid fixes w=0.8–1.4 (step 0.1), both development b values, and δ=−0.5/0/+0.5; each weight refits development only. Metrics are confusion, agreement, kappa, ARI and class Jaccard (Cohen, 1960; Hubert and Arabie, 1985). Two thousand PCG64 resamples (seed 20261117) draw fixed units from the union of both baseline families and candidate links, separately for full/temporal evaluation. Percentiles measure conditional composition sensitivity, not nominal physical uncertainty; variant mergers across baseline units diagnose dependence not captured. Excluding the fixed 2017 family union projects labels while preserving context.

### 2.6. Shared-latent synthetic catalogues

Truth parents/roots are generated independently of NN/GK (Ogata, 1988, 1998): 600 immigrants/year, two Gaussian concentrations 80 km apart (σ=15 km), M 3.5–6.5, b=1, productivity exponent 0.5, Omori c=0.001 day and p=1.2 and offspring σ=5 km. A 365-day burn precedes 730 evaluation days. Thirty histories per branching regime 0/0.6 and three separate development histories fix a clean-A NN cut. Parameters are assumed, not Mexican maximum-likelihood estimates.

A/B share latent histories and fixed error ledgers. All 16 B combinations apply detection D (retention probability 0.65–0.95 increasing with M), magnitude M (+0.15 with Gaussian σ=0.15 and decimal rounding), position X ((+2,−2) km with Gaussian σ=5 km), and clock T (+2 s with Gaussian σ=2 s). Draws are reused. Evaluation separates missing/below-cut/retained observations on fixed clean-A keys. Root families and largest-retained representatives differ from generated-child truth, which persists when parents are hidden.

Family roles/ARI, child recovery and immigrant false positives are scored against constant, singleton and all-grouped baselines. Known latent identity is primary; actual candidate matching supplies secondary precision/recall. Clean-A development cut is primary; cell-specific development cuts test calibration. Histories, failures and interactions are retained; t intervals describe Monte Carlo variation between histories, not dependent factorial cells. Earlier ten-/24-history controls remain separate.

## 3. Results

### 3.1. Exact search and catalogue-scale sensitivity

All 81 native cells completed without failures or censoring, matching all ten numeric arrays against the exhaustive reference for each input. At 170~880 records, median exhaustive/KD/octree costs are 524.037/5.924/6.416 s: 88.46×/81.67× ratios of medians (Table 1). Principal SSN/ComCat exhaustive costs are only 56.6/28.3 ms, with KD 17.2/11.5 ms; the index is not necessary for interactive latency there. Three repetitions, chronological prefixes and uncontrolled OS activity do not establish an asymptotic law or cross-device performance. Full-input peak working-set ranges are 223.23–224.45/258.03–258.61/260.64–261.05 MiB; the first small-reference process reaches 221.40 MiB including cold compilation and is retained.

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

The historical full-input KD/octree traversals evaluate 6~396~697/5~190~090 pairs (0.0438%/0.0355%), but their four-thread reference in Figure 2 is separate from Table 1. All 36 weight/source/context cases match the complete exhaustive arrays. Four-thread verification is separate from Table 1 (native SSN w=1 reuses its identical one-thread reference); Node 24.22.1 matches IDs/parents and nonfinite masks, with maximum absolute log-score difference 7.38×10^-14 against the fixed 10^-10 criterion. No EM or family labels are fitted at M≥3.5.

Changing w from 1 to 1.4 alters 94~745/170~879 defined SSN parents (55.45%; temporal 45~817/80~195=57.13%) and 1088/3944 ComCat parents (27.59%; temporal 615/1842=33.39%). SSN median parent lag/distance changes from 0.320 day/14.947 km to 123.738 days/82.531 km; ComCat changes from 24.120 days/55.168 km to 109.131 days/99.994 km. Thus weight changes the times/distances selected by the same search, not merely its numerical score scale.

At w=1, restricting context to the 2989 candidate endpoints changes 1765/2988 defined SSN parents (59.07%) but 112/2988 ComCat parents (3.75%); temporal changes are 836/1277 (65.47%) and 49/1277 (3.84%). Across native catalogues, both parents are candidate endpoints for only 1199/2989 targets: 975 match, giving 32.62% over all targets versus 81.32% over comparable parents. Source-specific weights give 1816/2989=60.76%, or 1816/2204=82.40% conditional on comparability. Context/weight therefore alter both which parents are comparable and their agreement; neither denominator measures physical accuracy.

All weights and profiles remain available. At w=1, finite-score quantiles exclude 207 SSN/one ComCat −∞ score and one parentless NaN per native cohort; arrays retain them. These proximity sensitivities are not inferred family durations or triggering.

Twelve comparator runs preserve every parent for the two principal cohorts. Eqclustering kernel medians are 0.143/0.083 s and Octave 0.888/0.610 s (SSN/ComCat); language/runtime costs do not isolate algorithmic advantage. Scalar outputs differ: Eqclustering retains 365.35 days/year, and one colocated ComCat edge has zero distance in Eqclustering but approximately 0.095 m in the current primitive, with zero/nonzero scores respectively; first-record no-parent conventions also differ. These are parent-selection controls, not score or role oracles.

Historical Node 22.12 and Edge exports matched nine source/cut cases (200~982 row-case selections) and all 3036 principal records respectively, with tested score tolerance 10^-10. They are separate from the new large-input/browser run and do not independently validate geometric preprocessing.

In an actual IAB run (reported UA: Chrome 157 on Windows), 18 of 24 predefined cells completed; six exhaustive cells at N=50~000/170~880 reached the 120-s wall cap, with no failures. KD pipeline medians at N=2000/10~000/50~000/170~880 were 0.0324/0.2232/2.5510/12.8782 s; the largest-input range was 12.7537–18.0367 s. Completed parent IDs and nonfinite masks matched native exhaustive outputs; maximum absolute log-score difference was 3.38×10^-14 against the fixed 10^-10 criterion. Both browser backends had identical arrays at the two smaller sizes; larger sizes had completed KD repetitions only. Initial loopback loading/verification took 315.9 ms separately. No speedup is inferred from censored cells. Browser host hardware, production-network latency, paint and Worker peak memory were not established. The earlier V2 run completed but its export failed; its captured timings remain separately preserved without certified array parity.

### 3.2. Selection and native classification

The principal selection contains 1780 SSN, 1256 Mexico-window ComCat and 555 Alaska records. The Mexican association graph has 3007 edges, 17 ambiguous components and 2989 assignments. GEM also returns 2989, sharing 2984; agreement is not identity accuracy. Exact decimal comparison gives mean SSN−ComCat M=+0.13034 and 1112/2989 pairs with |ΔM|≥0.3. The mean depends on supplied ComCat type (+0.1422 mb; −0.0406 mww), while SSN types are unknown. Median distance/absolute lag are 14.29 km/1.15 s; the association window truncates their distributions.

Both endpoints pass 4.5 in 889 candidates; 661 pass only SSN, 138 only ComCat and 1301 neither. Among selected source records, 230 SSN and 229 ComCat have no assigned counterpart. Thus the agreement denominator covers 49.94%/70.78%, not all selected seismicity. Of the 229 unassigned ComCat records, 87 fall in Guatemala land polygons, 26 USA, three Honduras, two El Salvador, 19 Mexico and 92 outside those polygons. These are geographic labels, not measured network coverage. Across the nine windows, jointly eligible counts vary from 230 to 922 and NN agreement from 86.55% to 87.39%; shifted-time controls yield 2–31 assignments. Changing candidate selection can preserve aggregate agreement without proving the same event identities. Boundary controls are reported in Section 3.6.

Complete-interval apparent b/GFT at ≥4.5 are SSN 1.34/93.4%, Mexican ComCat 1.06/96.8% and Alaska 0.94/95.6% (Figure 3). SSN development has no accepted GFT95 tail. Short postevent ≥4.5 tails have fewer than 100 observations, so no local completeness estimate is asserted. At the main weight, development thresholds are −5.31563/−5.43694/−5.78909 for SSN/Mexican ComCat/Alaska, with two modes and lower two-normal BIC; these diagnostics do not certify physical families.

Native NN agreement is 772/889=86.84%, kappa 0.765 and ARI 0.926 (Table 2); temporal agreement is 322/382=84.29%, kappa 0.679 and ARI 0.791. Conditional resampling percentiles are [82.88,89.73]% and [79.59,88.68]%. Baseline units number 592/301, size-weighted effective numbers 32.01/181.05 and largest pair fractions 17.10%/2.88%; these diagnostics qualify the intervals. Class Jaccards are isolated 83.45%, representative 41.30% and associated 80.45% overall; temporal values are 83.63%, 40.00% and 64.84%. Their full-interval conditional percentile ranges are [79.08,87.34]%, [33.11,50.31]%, [61.87,88.32]% respectively. The representative mismatch is obscured by the overall agreement. Excluding the fixed 2017 family union (152 pairs) gives 85.48% overall and 84.80% temporally.

Table 2. Full-interval NN roles on the same 889 candidates. Rows are SSN and columns ComCat; each endpoint retains its native context. Temporal and class-specific matrices and all resampling replicates accompany the analysis.

<!-- table-widths: 3360, 2000, 2000, 2000 -->
| SSN role | ComCat isolated | Representative | Associated |
| --- | --- | --- | --- |
| Isolated | 464 | 13 | 11 |
| Representative | 43 | 57 | 13 |
| Associated | 25 | 12 | 251 |

### 3.3. Weight, threshold and measurement effects

Weight sensitivity is substantial (Table 3). Source-specific apparent-b weights yield only 51.52% overall and 37.17% temporal agreement; using the larger weight in both gives 47.36%/32.46%. Both main crossed fits retain two-mode/BIC support. Equal weights 1.3 and 1.4 give 34.03% and 28.53% temporal agreement, while the largest SSN family contains 936/1065 records. Weight 1.2 gives higher agreement but its SSN fit is unimodal; it is not selected as a better scientific answer. Raising w favours high-magnitude parents, and refitted development boundaries also change: the sweep tests the combined weight/calibration convention. Baseline cut offsets −0.5/0/+0.5 yield 86.39/84.29/82.72% temporal agreement. Variant families can merge many baseline units, limiting uncertainty from fixed-unit resampling. Reported cuts 4.4/4.1 give native agreement 84.34%/78.61%; their SSN development distributions are unimodal, so their finite cutoffs remain exploratory.

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

Holding measurements and cuts fixed, common membership increases agreement to 830/889=93.36%; refitting gives 832/889=93.59%. The factorial shows all eight field patterns under each frozen cut (Table 4). UTC substitution alone changes no roles; magnitude and position have non-additive effects. Annual agreement ranges from 77.27% to 94.74% (Table 5), with fixed retrospective context. GK native/common agreement is 77.28%/84.36%; retaining 0/25/50/75/100% unmatched SSN context yields median agreement 81.33/80.20/79.30/78.12/77.28%. Higher agreement after thinning does not establish higher accuracy.

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

Cases are selected by maximum ComCat M in calendar 2017/2022, with earliest UTC/ID ties. Both source displays crop −7/+30 days and 150 km around that anchor without reclustering their full inputs. The Tehuantepec anchor is M 8.2, 8 September 2017: SSN/ComCat local counts are 3806/364 above 3.5 and 148/137 above 4.5. The Michoacán M 7.6 anchor, 19 September 2022, gives 1207/19 and 13/9; the SSN candidate reports 7.7. These differences are not detection probabilities.

The 2017 native SSN/ComCat anchor families grow from 292/204 at w=1 to 955/208 under source-specific apparent b, while local membership stays 148/136 (Figure 4). Paired-family Jaccard drops from 142/152=0.934 to 146/452=0.323; local overlap remains 85/86. In 2022, complete families change 21/10→84/10 with local membership 13/9 unchanged. The default 2017 SSN component spans 2631.62 days, with a 929.61-day consecutive gap. These are graph components, not continuously observed aftershock durations. The retained Figure 4 marks the original 14°N border. The 12°N control recovers the complete 150-km circle: its added strip contains four SSN M≥3.5 records but none≥4.5, and no ComCat records at either cut. This does not guarantee that all NN context lies within 12°N.

The first outside-window SSN role-change witness, M 7.1 on 19 September 2017, lies 627.695 km and 11.559 days from its M 8.2 candidate parent. Its score/cut changes from −5.22326>−5.31563 (isolated) to −7.90112≤−6.14514 (associated). The inspector (Figure 5) exposes IDs, source fields and both decisions; this reversal is not evidence of remote triggering.

Alaska compares methods within one retained ComCat source. Of 555 selected records, 313 inform development and 242 fall in 2023–2025. NN/GK agreement is 75.08%/70.25% in these periods, with ARI 0.579/0.643; complete-interval agreement is 72.97%, ARI 0.580. Temporal marginal counts isolated/representative/associated are NN 148/19/75 and GK 81/32/129. Indexed and exhaustive GK outputs match. This measures method dependence and implementation transfer, not cross-agency validation or all-Alaska seismicity.

### 3.5. Shared-latent validation

All 60 histories and 960 B cells completed without aborts or reseeding. A=B preserved roles, a software-consistency control. In the clustered regime, NN observed-root ARI declines from 0.637 [0.614,0.659] to 0.571 [0.541,0.601] under all operations; GK gives 0.009/0.007. NN child F1 is below the always-child baseline (clean 0.566 versus 0.710); GK also does not exceed it (0.706). In the null regime, clean immigrant false positives are 4.24%/96.95% for NN/GK, while the true singleton partition is recovered by the trivial singleton baseline. Cross-catalogue stability therefore cannot substitute for family or child accuracy.

Detection alone changes surviving roles on 2.25% of clean-A keys; magnitude and position change 16.65% and 10.05%; the clock operation changes none under the primary cut (Table 6). Combined disagreement is 30.55%, separating 11.86% inclusion loss and 18.69% retained-role changes; it is lower than the 41.15% sum of separate responses. Seven secondary development fits are unimodal and fail the diagnostic despite finite cutoffs; all results are retained. Matching precision/recall is 1 in the pure controls and approximately 0.999/1.000 under all operations in the clustered regime. These imposed errors test conditional computational responses, not real-agency error rates or additive physical causes.

Table 6. Complete twin factorial in the branching-0.6 regime: means across 30 independent histories, percent of fixed clean-A evaluation keys. D/M/X/T denote detection, magnitude, position and clock operations. Inclusion loss is shared by methods; retained-role changes and total disagreement are separate. Full Monte Carlo intervals, null-regime results, truth metrics and cell-specific-cut sensitivity accompany the analysis.

<!-- table-widths: 1160, 1640, 1640, 1640, 1640, 1640 -->
| D/M/X/T | Inclusion loss | NN role change | NN total | GK role change | GK total |
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

The earlier ten-history M≥4.5 controls remain adverse evidence: NN family-role accuracy 0.802 and ARI 0.628 do not remove its child F1 0.554, below always-child 0.691; GK child F1 is 0.684. The separate 24 descriptor-anchored histories are conditional three-seed cell means, not Mexican accuracy estimates. Synthetic support is restricted by finite burn, Gaussian spatial kernels, assumed error intensities and the two new branching regimes.

### 3.6. Versioned boundary and colocation diagnostics

B retains the same 3945 ComCat IDs as A; 18 rows change selected measures (15 depth, two magnitude, one coordinate pair), without changing paired agreements. SSN 14°N reproduces its original cohort. A/B each retain 889/382 full/temporal pairs with 86.84%/84.29% agreement under native or transported cuts. Extending C to 12°N adds 101 SSN/637 ComCat records with reported M≥4.5: 959/416 pairs give 86.86%/85.10% under C development cuts, or 85.92%/83.65% under transported B cuts. These denominators differ. On 889 shared B∩C assignments, eight SSN/25 ComCat parents change to newly admitted observations; within-source role agreement is 99.33%/99.78% with transported cuts and 98.76%/98.43% after recalibration. All three observed-support resolutions are retained (Table 7).

Table 7. Frozen development support on C: cells observed by both sources at M≥3.5. Pair counts and agreements concern M≥4.5, full/temporal evaluation. Projection keeps complete C context; restriction recomputes within cells at transported C cuts. Occupancy does not measure equal detection or instrumental coverage.

<!-- table-widths: 1200, 1200, 2160, 2400, 2400 -->
| Degrees | Cells | Pairs all/test | Projected agreement all/test | Restricted agreement all/test |
| --- | --- | --- | --- | --- |
| 0.5 | 243 | 881/350 | 86.83%/84.86% | 86.61%/84.00% |
| 1 | 114 | 931/393 | 87.11%/85.50% | 87.11%/85.50% |
| 2 | 54 | 946/404 | 87.10%/85.64% | 87.10%/85.64% |

No valid parent edge has evaluated RN=0 at M≥4.5; the sole development nonfinite within each source/weight is the first, parentless record. However, a comparator-motivated post hoc audit finds one coincident-coordinate ComCat edge at every weight, evaluated at approximately 0.095 m (Texas). Deleting all coincident edges with other parents/cuts frozen changes one unpaired native ComCat role at eight weights, two at 1.4; all 889/382 paired statistics, fixed 2017/2022 anchor families and maximum spans remain unchanged. At M≥3.5, w=1, SSN has 247 coincident edges (207 RN=0/40 RN>0), ComCat two (one each); no distinct-coordinate numerical zero occurs. No family ablation is performed at 3.5. This graph-deletion diagnostic neither identifies duplicates nor corrects geometry or reranks alternative parents.

<!-- figure: 3 -->

<!-- figure: 4 -->

<!-- figure: 5 -->

## 4. Integrated exploration

<!-- figure: 6 -->

<!-- figure: 7 -->

Sequences share navigation, language and appearance with the observatory (Figure 5). Hash-verified observations enter a Worker that computes parents/scores/roles at frozen cuts, rather than loading Python labels. Changing weight/membership recalculates; display radius/days/sources crop presentation. SVG/JSON exports preserve records and view state. Image links address individual maps, timelines or source records; responsive layouts need not be pixel-identical.

The four-package view preserves provenance (Figure 6); heat is screen-space row concentration, with static PB2002 context (Bird, 2003). Browser SQL uses sql.js (sql.js contributors, n.d.); offline/JavaScript fixtures test specified common results.

Source profiles distinguish recorded/unavailable periods (Figure 7). Figures 8–10 retain source/land/magnitude selections with original coordinates, separate from pilot cohorts.

<!-- figure: 8 -->

<!-- figure: 9 -->

<!-- figure: 10 -->

Within-source comparison holds type/period/filters fixed (Figure 11). Top 10 preserves heterogeneous reported ranks and a continental locator (Figure 12); proximity gives direct spatial pairs (Figure 13). Together these interfaces connect source inspection with sequence analysis, without asserting homogeneous magnitudes, rates, recurrence or hazard.

<!-- figure: 11 -->

<!-- figure: 12 -->

<!-- figure: 13 -->

## 5. Discussion

Catalogue context changes fixed observations' parents/families without changing their measurements; field substitution changes classifications at fixed membership. The weight sweep shows why high aggregate agreement or stable local maps cannot establish parameter-independent descriptions. Representative Jaccard is much lower, and apparent-b weights produce large components with multiyear gaps, not continuously triggered aftershock durations.

Zaliapin and Ben-Zion (2015) relate parent–offspring statistics to location quality/transient incompleteness and distinguish aggregate stability from individual assignment. Here fixed candidate keys permit separate context, reported-field and calibration contrasts, exposing representative mismatch and locally stable membership despite unstable full components. The result is measured catalogue dependence accessible through bounded search, not the general discovery that errors affect clusters. It complements proximity/method comparisons (Hsu et al., 2024; Varini et al., 2020) and declustering/completeness/b sensitivity (Guastella et al., 2026). Without location truth or homogeneous magnitudes, these contrasts cannot identify physical error causes.

Twins supply truth for imposed operations and ancestry, showing interacting responses with inclusion losses kept separate. GK stability coexists with poor root recovery; NN's better root ARI coexists with weak child F1. Neither validates universal declustering superiority or an empirical error model. Restricting observed support or unmatched context changes the estimand; improved agreement is not an estimate of detection accuracy.

The bound preserves weighted spherical search with possible quadratic work. Native speedups are substantial at full scale, while small exhaustive cohorts already finish in milliseconds. Finite-input output parity tests pruning under a shared numerical geometry; canonical vectors and floating guards do not supply universal IEEE or independent end-to-end geometric certification.

Identities remain unadjudicated, SSN types missing, reported cuts uncertified, and retrospective labels use later component members. Conditional bootstrap percentiles do not remove these uncertainties. Alaska is single-source and Canada descriptive; cross-agency inference is Mexican. Results support reproducible operational descriptions and their sensitivity, without forecasting, damage estimates or demonstrated triggering.

## 6. Conclusions

The observatory combines bounded weighted parent search with source-level exploration. At 170~880 records, one-thread KD is 88.46× faster than exhaustive search with identical measured arrays. In Mexico, 86.84% fixed-weight role agreement coexists with 41.30% representative Jaccard and 37.17% temporal agreement under source-specific apparent b. Complete context/field contrasts, support controls and shared-latent twins quantify conditional responses while retaining inclusion losses and adverse recovery. Alaska adds method comparison; native maps/timelines connect computation to retained observatory functions. The contribution concerns operational sequence descriptions, with physical identity, homogeneous magnitude, completeness and triggering kept separate.


## Code and data availability

The repository https://github.com/gabrielhuav/Seismic_Data_Geosciences/tree/f5dae946eff95dd92510ce7607c57c989f92197a contains the deployed system revision and scientific reproduction package; the observatory is https://gabrielhuav.github.io/Seismic_Data_Geosciences/. The research/sequences directory supplies readable numerical sources, component licenses, frozen observations, protocols, versions, full tables and synthetic truth/error ledgers. Its six-stage offline replay recomputes the principal checkpoints, catalogue sensitivity, shared-truth twins, southern support controls, zero-distance diagnostics and indexed observed-parent cases. Larger exhaustive references remain identified expected evidence. Native benchmarks, browser runs and author-code comparisons have separate optional profiles; GEM verification checks retained historical evidence and recalculates agreement counts and time shifts without rerunning its engine. Windows x64 replay was audited in an isolated dependency-locked environment; timings and cross-platform behavior are not guaranteed identical. SSN terms, attribution and source hashes remain attached (Servicio Sismológico Nacional, 2026). Component licenses do not replace provider rights. No archival DOI or human scientific approval is implied by repository publication.

## CRediT authorship contribution statement

José Manuel Villa Vargas: Conceptualization; Formal analysis; Supervision; Writing – original draft; Writing – review & editing.

Gabriel Hurtado Avilés: Data curation; Investigation; Methodology; Project administration; Resources; Software; Validation; Visualization.

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

## Declaration of competing interest

The authors declare no competing interests.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

OpenAI Codex assisted literature discovery, software development, numerical analyses, testing, scientific figure scripts, manuscript drafting and document preparation. Claude assisted earlier literature screening, source checks and manuscript restructuring, and supplied an external automated critique. All tools were used as assistance to the named human authors; their outputs are not human authorship, journal peer review or evidence of author approval. Scientific plots are rendered from documented data and code; interface images are genuine browser captures or faithful compositions. No generative image synthesis or observational retouching is used. Detailed versions, dates, corrections and verification records accompany the reproduction material. Final scientific review and approval remain the responsibility of the human authors before submission.

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

Hunter, J.D., 2007. Matplotlib: A 2D graphics environment. Computing in Science & Engineering 9, 90–95. https://doi.org/10.1109/MCSE.2007.55.

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

Figure 1. Implemented delivery architecture. Embedded selection: 7107 of 287~936 source rows (2010–2025, reported M ≥4.5, all catalogues). SQL executes in a browser Worker through sql.js (sql.js contributors, n.d.); offline Python/SQLite audits and JavaScript parity fixtures check their declared inputs and result contracts. The retained interface capture precedes the sequence extension. PB2002 is cartographic context (Bird, 2003). Map boundaries need not depict accepted national boundaries. [Open implemented design](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=1&lang=en).

Figure 2. Historical exact-search measurements on the complete chronological SSN input (reported M≥3.5). This retained figure uses a single four-thread exhaustive reference and three one-thread KD/octree repetitions; the new matched one-thread experiment is reported separately in Table 1. (A) Scaling. (B) Evaluated fraction of strictly earlier candidate pairs. (C) Visited/pruned nodes. (D) Indexed full-input phase costs. Numeric preparation and construction are included; imports/JIT and disk serialization excluded. Ranges are observed, machine-specific values, not confidence intervals or evidence that one partition is generally superior. Worst-case quadratic work remains possible. Rendered from retained measurements with Matplotlib (Hunter, 2007). [Explore performance](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=benchmark&lang=en).

Figure 3. Reported magnitudes and nearest-neighbour diagnostics. Cumulative retained
magnitude distributions for (A) SSN, (B) ComCat Mexico and (E) the Alaska cohort
include Aki–Utsu b fits and cumulative goodness-of-fit scores above native cuts
4.1/4.5; neither certifies physical completeness or magnitude-scale equivalence.
(C–D) Weighted nearest-neighbour T–R coordinates for native M≥4.5 cohorts use
d=1.6, w=1 and q=0.5. Dashed lines show source-specific thresholds frozen from
2016–2020 development data; points below or on the line retain their candidate
parent link. Each T–R panel omits its first record, which has no earlier parent. Links
define operational families, not physical triggering. (F) All 2,989 candidate
pairs retain their exact reported magnitude differences, grouped by supplied
ComCat type; SSN types are unavailable. Boxes show median/IQR, whiskers 1.5IQR,
and points all outliers; small types are pooled for display only. [Explore diagnostics](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?workspace=sequences&view=diagnostics&cut=4.5&pair_cut=3.5&lang=en).

Figure 4. Native system exports for the preselected 2017 (A–C) and 2022 (D–F) cases, using native reported M≥4.5 cohorts, d=1.6 and w=1 versus source-specific apparent b. The maps retain the live Leaflet projection, viewport and drawing order; the six native SVG exports are embedded with 300 ppi PNG compatibility fallbacks. Blue denotes SSN, orange ComCat, purple rings additions under b and grey other retained records. Stars mark the ComCat anchors; dashed circles delimit 150 km and dashed rectangles the retained query. The shaded strip in B was not queried south of 14°N. W1/W2 labels identify role-change witnesses where present without relocating records. Timeline grey lines connect candidate observations, not adjudicated identities. Each image links to its native view and saved map position. Map credit: Natural Earth; SSN/UNAM; USGS ComCat. These operational families do not establish physical triggering or aftershock duration.

Figure 5. Retained observatory controls and inspection: (A) the 2017 case settings, family summaries and legend; (B) the W1 source identity and weight-comparison table. The full inspector exposes original fields, parent navigation and both decisions. Each image opens its case or validated W1 selection. Native view links preserve analytical settings, map positions and the selected source record; display-window changes do not recluster.

Figure 6. Earlier source-row capture: four packages, 287~936 selected source rows; later opt-in copy grouping and the sequence prototype are absent. Point/heat views share selection and exports. Heat encodes unweighted on-screen row concentration, neither physical density nor hazard; PB2002 is contextual. Map boundaries need not depict accepted national boundaries. [Open this view](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=2&lang=en).

Figure 7. SSN source profile: 242~288 rows. Hue/shape identify source; shade indicates reported magnitude within a hue. Four packages from three distributors are not independent agencies. The time/coverage view separates recorded intervals from unavailable years. Map boundaries need not depict accepted national boundaries. [Atlas](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3&lang=en) and [Time and coverage](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=3-time&lang=en).

Figure 8. Source-row selections: (A) SSN, 2026 partial, M ≥4.5, no land filter: 204; (B) USGS North American windows, 2020–2025, M ≥3.5, United States land: 2335; (C) Canadian source, 1985–2019, M ≥3.5, Canada land: 1492; (D) all packages, 2010–2025, M ≥4.5: 7107. Extent does not restrict exports. These are preserved interface selections, not the sequence-pilot cohorts. Map boundaries need not depict accepted national boundaries. Links immediately below panels restore their views.

Figure 9. Land selections, 2000–2026, M ≥3.5: (A) SSN Guerrero, 19~963; (B) USGS California, 551; (C) Canadian Yukon, 225; (D) Alaska, 1112 (739 USGS; 373 Canadian). Counts follow each package's coverage; the Alaska sources are not contemporaneous. Size/shade encode reported M without conversion. Guerrero's terrestrial maximum is 6.5; three locality-labelled M 7.5/7.2/7.1 records lie outside the land polygon, not evidence of absent regional earthquakes. Map boundaries need not depict accepted national boundaries. Links immediately below panels restore their views.

Figure 10. SSN Guerrero land, 2000–2026 partial, M ≥4.5: 203 rows; Figure 9A differs only in threshold (M ≥3.5: 19~963), excluding 19~760. Earlier-interface capture and recomputed counts, without completeness inference. PB2002 neither reclassifies records nor supplies mechanisms. Map boundaries need not depict accepted national boundaries. [Open this zoomed map](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=6&lang=en).

Figure 11. USGS North American windows, 2020–2025, mww, M ≥4.5: Canada/Mexico land selections contain 15/53 rows. Shared 0.25-unit magnitude bins and annual counts describe selected records, not completeness-adjusted rates or relative hazard. This within-source regional comparison differs from the new paired SSN–ComCat sequence comparison. [Open this comparison](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=7&lang=en).

Figure 12. Earlier heterogeneous Top 10, grouping identical ComCat identifiers and retaining both provenances; separate from exact-copy selection and SSN–USGS candidate identity. Mexico detail shows nine ranks; the continental locator labels rank 4 in Alaska, with a blue detail-extent frame. Red dots are epicentres; offset badges use leaders. This is not a homogeneous Mw ranking or a sequence classification. Map boundaries need not depict accepted national boundaries. [Top 10](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9a&lang=en).

Figure 13. SSN Guerrero land, 1900–2026 partial: 21~167 M ≥3.5 rows; fourteen M ≥7 records yield ten direct pairs within 50 km involving twelve records. Magnitude type is unreported. Links/circles show geometry, not recurrence, independence or risk. Sequence methods additionally use time and catalogue context. PB2002 is context. Map boundaries need not depict accepted national boundaries. [Proximity](https://gabrielhuav.github.io/Seismic_Data_Geosciences/?figure=9b&lang=en).
