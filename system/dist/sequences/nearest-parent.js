/* Independent JavaScript implementation of the published nearest-parent metric.
 * Scientific definitions: Zaliapin and Ben-Zion (2013), doi:10.1002/jgrb.50179.
 * Numeric contract and finite-input audit are documented with this release.
 * No source observation is removed or rewritten. Depth is not a metric input.
 */
(function (root) {
  'use strict';
  const YEAR = 31557600, R = 6367.3, RAD = Math.PI / 180;
  const CHORD_GUARD = 2e-7, LOG_GUARD = 1e-10;
  function cosineDifference(x) {
    // For |x|<=.02, the omitted x^12/12! term is below 8.6e-30.
    // Share one explicit expression across runtimes near coincident coordinates.
    // Decimal probes found a Windows-libm rounding difference; V8 was correct.
    // Rounded polynomial operations still require the declared finite-input audit.
    if(Math.abs(x)<=.02){const y=x*x;return 1-y*(.5-y*(1/24-y*(1/720-y*(1/40320-y/3628800))));}
    return Math.cos(x);
  }
  function prepare(rows) {
    const a = rows.map(r => ({...r, t: Number(r.t_year) * YEAR,
      latitude: Number(r.latitude), longitude: Number(r.longitude), magnitude: Number(r.magnitude)}));
    // Inputs are sealed in observed UTC microseconds / UTF-8 ID order.
    for (let i = 0; i < a.length; i++) {
      const r = a[i];
      if (![r.t, r.latitude, r.longitude, r.magnitude].every(Number.isFinite) ||
          Math.abs(r.latitude) > 90 || Math.abs(r.longitude) > 180 || (i && r.t < a[i-1].t)) {
        throw new Error('Finite, chronologically ordered spherical inputs required');
      }
      // Preserve the operation association of the reference geometry.
      const lat = r.latitude * Math.PI / 180, lon = r.longitude * Math.PI / 180;
      const supplied=['sin_lat','cos_lat','lon_rad','xyz'].filter(k=>r[k]!==undefined);
      if(supplied.length && supplied.length!==4)throw new Error('Incomplete canonical geometry');
      if(supplied.length){
        const values=[r.sin_lat,r.cos_lat,r.lon_rad,...(Array.isArray(r.xyz)?r.xyz:[])];
        if(values.length!==6||!values.every(Number.isFinite)||Math.abs(r.sin_lat-Math.sin(lat))>1e-14||Math.abs(r.cos_lat-Math.cos(lat))>1e-14||Math.abs(r.lon_rad-lon)>1e-14||Math.abs(Math.hypot(...r.xyz)-1)>1e-12)throw new Error('Canonical geometry disagrees with observed coordinates');
        const expected=[r.cos_lat*Math.cos(r.lon_rad),r.cos_lat*Math.sin(r.lon_rad),r.sin_lat];
        if(r.xyz.some((v,k)=>Math.abs(v-expected[k])>1e-14))throw new Error('Canonical spatial index disagrees with observed coordinates');
        r.s=r.sin_lat;r.c=r.cos_lat;r.l=r.lon_rad;r.xyz=r.xyz.slice();
      }else{
        r.s = Math.sin(lat); r.c = Math.cos(lat); r.l = lon;
        r.xyz = [r.c * Math.cos(lon), r.c * Math.sin(lon), r.s];
      }
    }
    return a;
  }
  function candidate(a, i, j, d, w) {
    const dt = a[i].t - a[j].t;
    if (dt <= 0) return null;
    const dot = a[i].s * a[j].s + a[i].c * a[j].c * cosineDifference(a[i].l - a[j].l);
    const r = R * Math.acos(Math.max(-1, Math.min(1, dot)));
    return [dt * (r * 1000) ** d * 10 ** (-w * a[j].magnitude), dt / YEAR, r];
  }
  function tree(a, leafSize = 16) {
    const nodes = [], leaf = new Int32Array(a.length);
    function build(ids, up) {
      const k = nodes.length, lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
      for (const i of ids) for (let q = 0; q < 3; q++) {lo[q] = Math.min(lo[q], a[i].xyz[q]); hi[q] = Math.max(hi[q], a[i].xyz[q]);}
      const n = {lo, hi, up, latest: -Infinity, maxM: -Infinity, children: null, ids: null}; nodes.push(n);
      const width = hi.map((v, q) => v - lo[q]), dim = width.indexOf(Math.max(...width));
      if (ids.length <= leafSize || !width[dim]) {n.ids = ids; for (const i of ids) leaf[i] = k;}
      else {
        ids.sort((i, j) => a[i].xyz[dim] - a[j].xyz[dim] || i - j);
        const mid = Math.floor(ids.length / 2);
        n.children = [build(ids.slice(0, mid), k), build(ids.slice(mid), k)];
      }
      return k;
    }
    if (a.length) build(a.map((_, i) => i), -1);
    return {nodes, leaf};
  }
  function lower(n, r, d, w) {
    if (!Number.isFinite(n.latest)) return Infinity;
    let c2 = 0;
    for (let q = 0; q < 3; q++) {const x = Math.max(n.lo[q] - r.xyz[q], 0, r.xyz[q] - n.hi[q]); c2 += x*x;}
    const chord = Math.max(0, Math.sqrt(c2) - CHORD_GUARD);
    if (!chord) return -Infinity;
    const radius = 2 * R * 1000 * Math.asin(Math.min(1, chord / 2));
    return Math.log10(r.t - n.latest) + d * Math.log10(radius) - w * n.maxM;
  }
  function search(input, options = {}) {
    const started = performance.now(), a = prepare(input), n = a.length;
    const d = options.d ?? 1.6, w = options.w ?? 1, q = options.q ?? .5;
    if (!(d > 0 && w >= 0 && q >= 0 && q <= 1)) throw new Error('Invalid metric parameters');
    const backend = options.backend || 'kd';
    if (!['kd', 'reference'].includes(backend)) throw new Error('Unknown backend');
    const parent = new Int32Array(n).fill(-1), eta = new Float64Array(n).fill(Infinity);
    const dt = new Float64Array(n).fill(NaN), distance = new Float64Array(n).fill(NaN);
    const builtAt = performance.now(), index = backend === 'kd' && n ? tree(a) : null, searchedAt = performance.now();
    let first = 0, pairs = 0, visited = 0, bounds = 0, pruned = 0;
    function compare(i, j) {
      const v = candidate(a, i, j, d, w); if (!v) return; pairs++;
      if (v[0] < eta[i] || (v[0] === eta[i] && (parent[i] < 0 || j < parent[i]))) {
        eta[i] = v[0]; parent[i] = j; dt[i] = v[1]; distance[i] = v[2];
      }
    }
    for (let i = 0; i < n; i++) {
      if (backend === 'reference') {for (let j = 0; j < i; j++) compare(i, j); continue;}
      while (first < n && a[first].t < a[i].t) {
        for (let k = index.leaf[first]; k >= 0; k = index.nodes[k].up) {
          const node = index.nodes[k]; node.latest = Math.max(node.latest, a[first].t); node.maxM = Math.max(node.maxM, a[first].magnitude);
        }
        first++;
      }
      const stack = [0];
      while (stack.length) {
        const node = index.nodes[stack.pop()]; visited++; bounds++;
        if (lower(node, a[i], d, w) > Math.log10(eta[i]) + LOG_GUARD) {pruned++; continue;}
        if (node.ids) {for (const j of node.ids) compare(i, j);}
        else {
          const [left, right] = node.children;
          const lb = lower(index.nodes[left], a[i], d, w), rb = lower(index.nodes[right], a[i], d, w); bounds += 2;
          if (lb <= rb) stack.push(right, left); else stack.push(left, right);
        }
      }
    }
    const finished = performance.now(), tn = new Float64Array(n).fill(NaN), rn = new Float64Array(n).fill(NaN);
    const logEta = new Float64Array(n).fill(NaN), logProduct = new Float64Array(n).fill(NaN);
    for (let i = 0; i < n; i++) if (parent[i] >= 0) {
      tn[i] = dt[i] * 10 ** (-q * w * a[parent[i]].magnitude);
      rn[i] = distance[i] ** d * 10 ** (-(1-q) * w * a[parent[i]].magnitude);
      // The author cluster-analysis script sums the logs of the rescaled arrays.
      logEta[i] = Math.log10(tn[i]) + Math.log10(rn[i]);
      logProduct[i] = Math.log10(tn[i] * rn[i]);
    }
    return {ids: a.map(r => r.record_id), parent, eta, dt, distance, tn, rn, logEta, logProduct,
      metadata: {backend, d, w, q, radius_km: R, zero_distance_retained: true,
        candidate_pairs: pairs, visited_nodes: visited, bound_tests: bounds, pruned_nodes: pruned,
        preparation_ms: builtAt-started, tree_ms: searchedAt-builtAt, kernel_ms: finished-searchedAt,
        postprocess_ms: performance.now()-finished, total_ms: performance.now()-started,
        geometry_input: input.every(r=>Array.isArray(r.xyz))?'canonical binary64 preprocessing':'JavaScript trigonometry',
        numerical_guard: 'Finite-input audited guard; no universal IEEE error certificate'}};
  }
  function families(result, rows, cut) {
    if (!Number.isFinite(cut)) throw new Error('An estimable frozen training threshold is required');
    const n = rows.length, component = new Int32Array(n), counts = new Map();
    // Every parent precedes its child, so chronological propagation finds components.
    for (let i = 0; i < n; i++) {
      const p = result.parent[i];
      component[i] = p >= 0 && result.logEta[i] <= cut ? component[p] : i;
      counts.set(component[i], (counts.get(component[i]) || 0) + 1);
    }
    const representatives = new Map();
    for (let i = 0; i < n; i++) {
      const c = component[i], j = representatives.get(c);
      if (j === undefined || Number(rows[i].magnitude) > Number(rows[j].magnitude)) representatives.set(c, i);
    }
    const roles = rows.map((_, i) => counts.get(component[i]) === 1 ? 'isolated' : representatives.get(component[i]) === i ? 'main' : 'associated');
    return {component, roles, representatives: [...representatives.values()].filter(i => counts.get(component[i]) > 1), threshold_log10: cut};
  }
  const api = {search, families, candidate, prepare, cosineDifference, YEAR, R};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SequenceNearestParent = api;
})(typeof self !== 'undefined' ? self : globalThis);
