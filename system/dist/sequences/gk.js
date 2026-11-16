/* GK baseline for the private sequence pilot. No source records are removed.
 * Same windows, ordering, UTC and great-circle contract as gardner_knopoff.py.
 */
(function (root) {
  'use strict';
  const EARTH_KM = 6371.0088;
  const RAD = Math.PI / 180;
  const DISTANCE_EPSILON_KM = 1e-9;
  const wrap = x => ((x + 180) % 360 + 360) % 360 - 180;
  function distance(a, b) {
    const p1 = a.latitude * RAD, p2 = b.latitude * RAD;
    const dp = p2 - p1, dl = wrap(b.longitude - a.longitude) * RAD;
    const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
    return 2 * EARTH_KM * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
  }
  function cell(lat, lon) { return Math.floor(lat + 90) + ',' + Math.floor(wrap(lon) + 180); }
  function utcDays(value) {
    const match = /^(.*T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    if (!match) throw new Error('Canonical UTC Z with at most six fractional digits is required');
    const whole = Date.parse(match[1]+'Z')/1000;
    const fraction = Number((match[2] || '').padEnd(6,'0'))/1e6;
    if (!Number.isFinite(whole)) throw new Error('Invalid UTC instant');
    return (whole+fraction)/86400;
  }
  function normalize(rows) {
    return rows.map(r => ({...r, record_id: String(r.record_id),
      latitude: Number(r.latitude), longitude: Number(r.longitude), magnitude: Number(r.magnitude),
      days: utcDays(r.time_utc)
    })).sort((a,b) => a.days - b.days || (a.record_id < b.record_id ? -1 : a.record_id > b.record_id ? 1 : 0));
  }
  function classify(input, options = {}) {
    const rows = normalize(input), n = rows.length;
    const fraction = options.foreshockFraction === undefined ? .5 : options.foreshockFraction;
    const group = new Int32Array(n), flag = new Int8Array(n), buckets = new Map();
    rows.forEach((r,i) => { const k = cell(r.latitude, r.longitude); if (!buckets.has(k)) buckets.set(k, []); buckets.get(k).push(i); });
    const order = Array.from({length:n}, (_,i) => i).sort((i,j) => rows[j].magnitude - rows[i].magnitude || rows[i].days - rows[j].days || i-j);
    const roots = [];
    for (const i of order) {
      if (group[i]) continue;
      const r = rows[i], dr = 10 ** (.1238 * r.magnitude + .983);
      const dt = r.magnitude >= 6.5 ? 10 ** (.032 * r.magnitude + 2.7389) : 10 ** (.5409 * r.magnitude - .547);
      const rho = (dr + DISTANCE_EPSILON_KM + 1e-7) / EARTH_KM, latitudePad = rho / RAD;
      const lo = Math.max(-90, r.latitude - latitudePad), hi = Math.min(90, r.latitude + latitudePad);
      const reachesPole = lo <= -90 || hi >= 90;
      const longitudePad = reachesPole ? 180 : Math.asin(Math.min(1, Math.sin(rho) / Math.cos(r.latitude * RAD))) / RAD;
      const found = [];
      const checked = new Set();
      // Conservative spherical cap bounding box; exact distance decides membership.
      const firstLat = Math.max(0, Math.floor(lo + 90 - 1e-10));
      const lastLat = Math.min(180, Math.floor(hi + 90 + 1e-10));
      const firstLon = reachesPole ? 0 : Math.floor(r.longitude - longitudePad + 180 - 1e-10);
      const lastLon = reachesPole ? 359 : Math.floor(r.longitude + longitudePad + 180 + 1e-10);
      for (let y = firstLat; y <= lastLat; y++) for (let x = firstLon; x <= lastLon; x++) {
        const xx = ((x % 360) + 360) % 360, key = y + ',' + xx;
        if (checked.has(key)) continue; checked.add(key);
        for (const j of buckets.get(key) || []) {
          if (group[j]) continue;
          const delta = rows[j].days - r.days;
          if (delta >= -fraction * dt && delta <= dt && distance(r, rows[j]) <= dr + DISTANCE_EPSILON_KM) found.push(j);
        }
      }
      if (found.length > 1) {
        const id = roots.length + 1;
        for (const j of found) { group[j] = id; flag[j] = rows[j].days < r.days ? -1 : 1; }
        flag[i] = 0; roots.push(i);
      }
    }
    const roles = rows.map((r,i) => group[i] === 0 ? 'isolated' : flag[i] === 0 ? 'main' : 'associated');
    return {ids: rows.map(r=>r.record_id), rows, group, native_flag: flag, roles, roots,
      parameters: {earthKm: EARTH_KM, foreshockFraction: fraction, distanceEpsilonKm: DISTANCE_EPSILON_KM, time: 'native UTC continuous days', distance: 'epicentral great circle'}};
  }
  const api = {classify, distance, normalize, utcDays};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.SequencePilot = api;
})(typeof self !== 'undefined' ? self : globalThis);
