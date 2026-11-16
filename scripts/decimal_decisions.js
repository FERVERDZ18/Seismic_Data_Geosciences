/* Exact decisions over retained decimal strings. This is not magnitude homogenization. */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DecimalDecisions = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const MAX_POWER = 10000n;
  const SQLITE_MIN = -9223372036854775808n;
  const SQLITE_MAX = 9223372036854775807n;
  const DEFAULT_DELTAS = Object.freeze(['0.1', '0.2', '0.3', '0.5', '1']);
  const DEFAULT_THRESHOLDS = Object.freeze(['4.0', '4.5', '5.0', '5.5', '6.0', '6.5', '7.0']);
  const CATEGORIES = Object.freeze(['both', 'ssn_only', 'usgs_only', 'neither']);

  function power10(exponent) {
    if (exponent < 0n || exponent > MAX_POWER) throw new RangeError('Decimal exponent exceeds the exact-arithmetic resource limit');
    return 10n ** exponent;
  }

  function parseDecimal(token) {
    if (typeof token !== 'string') throw new TypeError('A retained decimal string is required; Number inputs are forbidden');
    if (token.length > 10000) throw new RangeError('Decimal token exceeds the resource limit');
    const match = /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(token);
    if (!match) throw new TypeError('Invalid retained decimal string');
    const fractional = match[3] === undefined ? (match[4] || '') : match[3];
    const integral = match[2] || '0';
    let coefficient = BigInt(integral + fractional) * (match[1] === '-' ? -1n : 1n);
    let exponent = BigInt(match[5] || '0') - BigInt(fractional.length);
    if (exponent < -MAX_POWER || exponent > MAX_POWER) throw new RangeError('Decimal exponent exceeds the exact-arithmetic resource limit');
    if (coefficient === 0n) exponent = 0n;
    else while (coefficient % 10n === 0n) { coefficient /= 10n; exponent += 1n; }
    return Object.freeze({token, coefficient, exponent});
  }

  function align(a, b) {
    const exponent = a.exponent < b.exponent ? a.exponent : b.exponent;
    return [a.coefficient * power10(a.exponent - exponent), b.coefficient * power10(b.exponent - exponent), exponent];
  }

  function compareParsed(a, b) {
    const values = align(a, b);
    return values[0] < values[1] ? -1 : values[0] > values[1] ? 1 : 0;
  }

  function compareDecimals(a, b) { return compareParsed(parseDecimal(a), parseDecimal(b)); }

  function differenceAtLeast(aToken, bToken, deltaToken) {
    const a = parseDecimal(aToken), b = parseDecimal(bToken), delta = parseDecimal(deltaToken);
    if (delta.coefficient < 0n) throw new RangeError('Absolute-difference delta must be nonnegative');
    const values = align(a, b);
    let coefficient = values[0] - values[1];
    if (coefficient < 0n) coefficient = -coefficient;
    return compareParsed({coefficient, exponent: values[2]}, delta) >= 0;
  }

  function selectionThreshold(ssnToken, usgsToken, thresholdToken) {
    const threshold = parseDecimal(thresholdToken);
    const ssn = compareParsed(parseDecimal(ssnToken), threshold) >= 0;
    const usgs = compareParsed(parseDecimal(usgsToken), threshold) >= 0;
    return ssn ? (usgs ? 'both' : 'ssn_only') : (usgs ? 'usgs_only' : 'neither');
  }

  function sqliteInteger64(value) {
    if (typeof value !== 'bigint') throw new TypeError('SQLite INTEGER guard requires BigInt');
    if (value < SQLITE_MIN || value > SQLITE_MAX) throw new RangeError('Value exceeds signed SQLite INTEGER64');
    return value;
  }

  function scaledInteger(token, scaleExponent = 13) {
    if (!Number.isSafeInteger(scaleExponent) || scaleExponent < 0 || scaleExponent > 10000) throw new RangeError('Scale exponent must be a nonnegative bounded integer');
    const decimal = parseDecimal(token), exponent = decimal.exponent + BigInt(scaleExponent);
    let value;
    if (exponent >= 0n) value = decimal.coefficient * power10(exponent);
    else {
      const divisor = power10(-exponent);
      if (decimal.coefficient % divisor !== 0n) throw new RangeError('Decimal cannot be encoded at this scale without rounding');
      value = decimal.coefficient / divisor;
    }
    return sqliteInteger64(value);
  }

  function auditRows(rows, options = {}) {
    if (!Array.isArray(rows)) throw new TypeError('Audit rows must be an array');
    const deltas = options.deltas || DEFAULT_DELTAS;
    const thresholds = options.thresholds || DEFAULT_THRESHOLDS;
    const scale = options.scaleExponent === undefined ? 13 : options.scaleExponent;
    if (!Array.isArray(deltas) || !Array.isArray(thresholds)) throw new TypeError('Deltas and thresholds must be string arrays');
    const absolute_delta = {}, magnitude_membership = {};
    for (const delta of deltas) {
      if (parseDecimal(delta).coefficient < 0n) throw new RangeError('Absolute-difference delta must be nonnegative');
      scaledInteger(delta, scale);
      absolute_delta[delta] = {count: 0, pair_indices: []};
    }
    for (const threshold of thresholds) {
      scaledInteger(threshold, scale);
      magnitude_membership[threshold] = {both: 0, ssn_only: 0, usgs_only: 0, neither: 0};
    }
    rows.forEach((row, index) => {
      if (!row || typeof row !== 'object') throw new TypeError('Each audit row must be an object');
      const ssn = scaledInteger(row.ssn_mag, scale), usgs = scaledInteger(row.usgs_mag, scale);
      sqliteInteger64(ssn - usgs);
      // SQLite abs(-2^63) overflows despite its argument being an INTEGER64.
      if (ssn - usgs === SQLITE_MIN) throw new RangeError('Absolute subtraction exceeds signed SQLite INTEGER64');
      for (const delta of deltas) if (differenceAtLeast(row.ssn_mag, row.usgs_mag, delta)) {
        absolute_delta[delta].count += 1;
        absolute_delta[delta].pair_indices.push(index + 1);
      }
      for (const threshold of thresholds) magnitude_membership[threshold][selectionThreshold(row.ssn_mag, row.usgs_mag, threshold)] += 1;
    });
    return {schema: 'seismic-pair-decimal-decisions/1', row_count: rows.length, integer_scale_exponent: scale, absolute_delta, magnitude_membership};
  }

  return Object.freeze({parseDecimal, compareDecimals, differenceAtLeast, selectionThreshold, scaledInteger, sqliteInteger64, auditRows,
    DEFAULT_DELTAS, DEFAULT_THRESHOLDS, CATEGORIES, SQLITE_MIN, SQLITE_MAX});
}));
