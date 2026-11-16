'use strict';
importScripts('nearest-parent.js', 'gk.js');
self.onmessage = event => {
  const {request, rows, method, parameters, threshold} = event.data;
  try {
    const started = performance.now();
    let result;
    if (method === 'gk') {
      const g = self.SequencePilot.classify(rows);
      result = {ids: g.ids, native_group: Array.from(g.group), native_flag: Array.from(g.native_flag),
        component: Array.from(g.group, (v,i) => v === 0 ? -(i+1) : v), roles: g.roles,
        metadata: {...g.parameters, method: 'Gardner–Knopoff windows', total_ms: performance.now()-started}};
    } else {
      const p = self.SequenceNearestParent.search(rows, parameters);
      const c = self.SequenceNearestParent.families(p, rows, threshold);
      result = {ids: p.ids, parent: Array.from(p.parent), component: Array.from(c.component), roles: c.roles,
        log_eta: Array.from(p.logEta, x => Number.isFinite(x) ? x : x === -Infinity ? '-Infinity' : null),
        tn: Array.from(p.tn, x => Number.isFinite(x) ? x : null), rn: Array.from(p.rn, x => Number.isFinite(x) ? x : null),
        metadata: {...p.metadata, method: 'Deterministic nearest-neighbour families', threshold_log10: threshold}};
    }
    self.postMessage({request, result});
  } catch (error) { self.postMessage({request, error: String(error.message || error)}); }
};
