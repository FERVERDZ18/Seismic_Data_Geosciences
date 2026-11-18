"""Deterministic family identification following Zaliapin & Ben-Zion (2013a).

This is a new, explicit implementation, NOT the authors' executable and NOT the
randomly sampled bruces Gaussian-mixture declustering mask. The caller supplies
the separately verified nearest-neighbour parent/eta arrays. No source is changed.

Primary method: doi:10.1002/jgrb.50179, sections 3.1--3.5. Development-only GMM
threshold estimation is an operational, reproducible implementation of its
mixture-separation proposal. Guards below are declared numerical safeguards, not
new geophysical constants. Failed fits return `not_estimable`, never a fallback.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def _log_normal(x, mean, variance):
    return -.5 * (np.log(2. * np.pi * variance) + (x - mean) ** 2 / variance)


def _em(x, initial_means, max_iter=1000, tolerance=1e-10):
    variance = float(np.var(x))
    variance_floor = max(1e-12, variance * 1e-8)
    means = np.asarray(initial_means, dtype=float)
    variances = np.full(2, variance)
    weights = np.full(2, .5)
    previous = -np.inf
    converged = False
    for iteration in range(max_iter):
        log_weighted = np.column_stack([
            np.log(weights[k]) + _log_normal(x, means[k], variances[k])
            for k in range(2)
        ])
        maxima = log_weighted.max(axis=1)
        log_denominator = maxima + np.log(np.exp(log_weighted - maxima[:, None]).sum(axis=1))
        likelihood = float(log_denominator.sum())
        responsibilities = np.exp(log_weighted - log_denominator[:, None])
        masses = responsibilities.sum(axis=0)
        if np.any(masses < 1e-8) or not math.isfinite(likelihood):
            return None
        means = (responsibilities * x[:, None]).sum(axis=0) / masses
        variances = np.maximum((responsibilities * (x[:, None] - means) ** 2).sum(axis=0) / masses,
                               variance_floor)
        weights = masses / len(x)
        if abs(likelihood - previous) <= tolerance * max(1., abs(previous)):
            # Never compare the first likelihood with -infinity.
            if math.isfinite(previous):
                converged = True
                break
        previous = likelihood
    order = np.argsort(means)
    return dict(means=means[order], variances=variances[order], weights=weights[order],
                log_likelihood=likelihood, converged=converged,
                iterations=iteration + 1, variance_floor=variance_floor)


def _intersection_between_means(means, variances, weights):
    # Equality of the two WEIGHTED Gaussian densities. Solve in scaled x for
    # numerical stability, retaining a single crossing between the fitted means.
    lo, hi = map(float, means)
    center, scale = (lo + hi) / 2., hi - lo
    if scale <= 0.:
        return None
    mu = (np.asarray(means) - center) / scale
    var = np.asarray(variances) / scale ** 2
    a = .5 * (1. / var[1] - 1. / var[0])
    b = mu[0] / var[0] - mu[1] / var[1]
    c = math.log(weights[0] / weights[1]) - .5 * math.log(var[0] / var[1]) \
        - .5 * mu[0] ** 2 / var[0] + .5 * mu[1] ** 2 / var[1]
    if abs(a) < 1e-12:
        candidates = [] if abs(b) < 1e-12 else [-c / b]
    else:
        discriminant = b * b - 4. * a * c
        candidates = [] if discriminant < 0. else [(-b - math.sqrt(discriminant)) / (2. * a),
                                                   (-b + math.sqrt(discriminant)) / (2. * a)]
    roots = [center + scale * z for z in candidates if -.5 < z < .5]
    return roots[0] if len(roots) == 1 else None


def fit_threshold_development(log_eta: Sequence[float], minimum_events=50):
    """Fit only prespecified development events; caller MUST enforce time split.

    Deterministic multi-start 2-component EM, compared with a single Gaussian by
    ordinary BIC. A two-component fit need not have two modes: a 4097-point grid
    over the data+six-sigma component range checks this separately. If bimodality
    or a boundary between the means is absent no automatic family cut is issued.
    All failed diagnostics are returned to be reported, never discarded.
    """
    supplied = np.asarray(log_eta, dtype=float)
    x = np.sort(supplied[np.isfinite(supplied)])
    result = dict(status='not_estimable', threshold_log10=None, input_events=len(supplied),
                  finite_events=len(x), nonfinite_events=int((~np.isfinite(supplied)).sum()),
                  algorithm='deterministic 1D two-Gaussian EM; weighted-density intersection',
                  initialization_quantiles=[[.1, .9], [.25, .75], [.4, .6]],
                  minimum_events=minimum_events, guard_details='BIC2 < BIC1; two mixture modes; unique crossing between means',
                  citations=['https://doi.org/10.1002/jgrb.50179'])
    if len(x) < minimum_events:
        return {**result, 'reason': 'insufficient_finite_development_events'}
    if np.ptp(x) < 1e-8:
        return {**result, 'reason': 'constant_or_nearly_constant_development_proximities'}
    mean, variance = float(np.mean(x)), float(np.var(x))
    likelihood1 = float(_log_normal(x, mean, variance).sum())
    fits = [_em(x, np.quantile(x, q)) for q in ([.1, .9], [.25, .75], [.4, .6])]
    valid = [f for f in fits if f is not None and f['converged']]
    if not valid:
        return {**result, 'reason': 'no_converged_EM_start'}
    fit = max(valid, key=lambda f: f['log_likelihood'])
    bic1 = 2 * math.log(len(x)) - 2 * likelihood1
    bic2 = 5 * math.log(len(x)) - 2 * fit['log_likelihood']
    means, variances, weights = fit['means'], fit['variances'], fit['weights']
    lower = min(float(x[0]), float(np.min(means - 6 * np.sqrt(variances))))
    upper = max(float(x[-1]), float(np.max(means + 6 * np.sqrt(variances))))
    grid = np.linspace(lower, upper, 4097)
    density = sum(weights[k] * np.exp(_log_normal(grid, means[k], variances[k])) for k in range(2))
    modes = np.flatnonzero((density[1:-1] > density[:-2]) & (density[1:-1] > density[2:])) + 1
    threshold = _intersection_between_means(means, variances, weights)
    result.update(means_log10=means.tolist(), variances=variances.tolist(), weights=weights.tolist(),
                  BIC_one=bic1, BIC_two=bic2, BIC_two_minus_one=bic2-bic1,
                  mixture_mode_count=len(modes), mixture_modes_log10=grid[modes].tolist(),
                  iterations=fit['iterations'], variance_floor=fit['variance_floor'],
                  converged_starts=len(valid), best_log_likelihood=fit['log_likelihood'],
                  candidate_threshold_log10=threshold)
    if bic2 >= bic1:
        return {**result, 'reason': 'single_Gaussian_BIC_preferred'}
    if len(modes) != 2:
        return {**result, 'reason': 'fitted_two_components_do_not_have_two_modes'}
    if threshold is None:
        return {**result, 'reason': 'no_unique_weighted_density_crossing_between_means'}
    return {**result, 'status': 'estimable', 'reason': None, 'threshold_log10': threshold}


def families_from_cut(parent_index, eta_log10, magnitudes, times, ids, threshold_log10, *, inclusive=False):
    """Return deterministic components and operational roles for a frozen cut.

    Input order must be chronological (time, source ID). Ties in maximum reported
    magnitude use earliest time then ID. `associated` is an operational membership,
    not a validated causal parent, aftershock, or duplicate-physical-event label.
    First/no-native-parent events can still be family roots; retain explicit flag.
    """
    parents = np.asarray(parent_index, dtype=np.int64)
    eta = np.asarray(eta_log10, dtype=float)
    mag = np.asarray(magnitudes, dtype=float)
    time = np.asarray(times, dtype=float)
    n = len(parents)
    if not math.isfinite(threshold_log10):
        raise ValueError('A finite, prespecified threshold is required')
    if not all(len(v) == n for v in (eta, mag, time, ids)):
        raise ValueError('Input arrays must have equal length')
    if np.any(np.diff(time) < 0):
        raise ValueError('Input events must be chronological')
    if np.any(parents >= np.arange(n)) or np.any(parents < -1):
        raise ValueError('Parents must be -1 or a strictly earlier index')
    keep = (parents >= 0) & ((eta <= threshold_log10) if inclusive else (eta < threshold_log10))
    effective = np.where(keep, parents, -1)
    root = np.empty(n, dtype=np.int64)
    for i, p in enumerate(effective):
        root[i] = i if p < 0 else root[p]
    counts = np.bincount(root, minlength=n)
    role = np.full(n, 2, dtype=np.int8)  # 0 isolated, 1 operational main, 2 associated
    chosen = {}
    for i, g in enumerate(root):
        key = (-float(mag[i]), float(time[i]), str(ids[i]))
        if g not in chosen or key < chosen[g][0]:
            chosen[g] = (key, i)
    for g, (_, i) in chosen.items():
        role[i] = 0 if counts[g] == 1 else 1
    return dict(component_root_index=root, component_size=counts[root], roles=role,
                retained_parent_index=effective, strong_link_mask=keep,
                parent_defined_mask=parents >= 0,
                role_definitions={'0': 'isolated', '1': 'operational maximum reported magnitude',
                                  '2': 'associated in deterministic nearest-neighbour family'})


if __name__ == '__main__':
    # Semantic checks, not a claim of empirical or geophysical validation.
    x = np.r_[np.linspace(-6.7, -5.3, 1000), np.linspace(-2.7, -1.3, 1000)]
    fit = fit_threshold_development(x)
    assert fit['status'] == 'estimable' and abs(fit['threshold_log10'] + 4.) < 1e-7
    assert fit == fit_threshold_development(x)
    assert fit_threshold_development([1.] * 100)['status'] == 'not_estimable'
    groups = families_from_cut([-1, 0, 1, 2], [np.inf, -5., -4., -7.],
                               [5., 6., 4., 4.], [0., 1., 2., 3.], ['a', 'b', 'c', 'd'], -4.)
    assert groups['component_root_index'].tolist() == [0, 0, 2, 2]
    assert groups['roles'].tolist() == [2, 1, 1, 2]
    assert groups['strong_link_mask'].tolist() == [False, True, False, True]
    print('PASS: deterministic mixture separation; failed fit explicit; strict cut; deterministic main selection')
