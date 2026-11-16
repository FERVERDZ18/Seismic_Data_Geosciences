'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const D = require('../scripts/decimal_decisions.js');
let checks = 0;
function test(name, fn) { fn(); checks++; console.log('PASS ' + name); }

test('inclusive decimal boundary differs from the binary subtraction negative control', () => {
  assert.equal(D.differenceAtLeast('3.8', '3.5', '0.3'), true);
  assert.equal(Math.abs(3.8 - 3.5) >= 0.3, false);
  assert.equal(D.differenceAtLeast('3.7999999999999', '3.5', '0.3'), false);
  assert.equal(D.differenceAtLeast('3.8000000000001', '3.5', '0.3'), true);
});
test('decimal strings are conserved and exponent notation and negative zero are exact', () => {
  const parsed = D.parseDecimal('-0.00e+3');
  assert.equal(parsed.token, '-0.00e+3'); assert.equal(parsed.coefficient, 0n); assert.equal(parsed.exponent, 0n);
  assert.equal(D.compareDecimals('38e-1', '3.800'), 0);
  assert.equal(D.compareDecimals('-.3', '-0.3000000000001'), 1);
  assert.equal(D.differenceAtLeast('3.8e0', '+35e-1', '3e-1'), true);
});
test('missing values and already rounded numeric inputs are rejected', () => {
  for (const token of [null, undefined, '', ' ', ' 3.8', '3.8 ', 'NaN', 'Infinity', '3,8', true, 3.8, NaN, Infinity, 3n]) {
    assert.throws(() => D.parseDecimal(token), /string|decimal/i);
  }
  assert.throws(() => D.differenceAtLeast('3.8', null, '0.3'), /string/);
  assert.throws(() => D.differenceAtLeast('3.8', '3.5', '-0.3'), /nonnegative/);
  assert.throws(() => D.parseDecimal('1e10001'), /resource limit/);
});
test('difference decisions are symmetric and preserve values beyond binary precision', () => {
  for (const [a, b, delta] of [['3.8', '3.5', '0.3'], ['-1.3', '-1.0', '.3'], ['1e-13', '0', '.0000000000001'],
    ['9007199254740993', '9007199254740992', '1']]) assert.equal(D.differenceAtLeast(a, b, delta), D.differenceAtLeast(b, a, delta));
  assert.equal(D.differenceAtLeast('9007199254740993', '9007199254740992', '1'), true);
  assert.equal(D.differenceAtLeast('-0', '0', '0'), true);
});
test('inclusive selection preserves all four membership outcomes', () => {
  assert.equal(D.selectionThreshold('4.5', '4.50', '4.5'), 'both');
  assert.equal(D.selectionThreshold('4.5', '4.4999999999999', '4.5'), 'ssn_only');
  assert.equal(D.selectionThreshold('4.4999999999999', '4.5', '4.5'), 'usgs_only');
  assert.equal(D.selectionThreshold('4.49', '4.49', '4.5'), 'neither');
});
test('scale encoding never rounds and guards SQLite signed INTEGER and subtraction', () => {
  assert.equal(D.scaledInteger('4.4999999999999'), 44999999999999n);
  assert.equal(D.scaledInteger('3e-13'), 3n);
  assert.equal(D.scaledInteger('-0.0'), 0n);
  assert.throws(() => D.scaledInteger('1e-14'), /without rounding/);
  assert.equal(D.scaledInteger('922337.2036854775807'), 9223372036854775807n);
  assert.equal(D.scaledInteger('-922337.2036854775808'), -9223372036854775808n);
  assert.throws(() => D.scaledInteger('922337.2036854775808'), /INTEGER64/);
  assert.throws(() => D.auditRows([{ssn_mag:'922337.2036854775807', usgs_mag:'-1'}]), /INTEGER64/);
  assert.throws(() => D.auditRows([{ssn_mag:'-922337.2036854775808', usgs_mag:'0'}]), /INTEGER64/);
});
test('browser UMD and Node expose the same contract without mutation', () => {
  const context = {}; vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../scripts/decimal_decisions.js'), 'utf8'), context);
  assert.equal(context.DecimalDecisions.differenceAtLeast('3.8', '3.5', '0.3'), true);
  const rows = [{ssn_mag:'3.8', usgs_mag:'3.5'}], before = JSON.stringify(rows);
  assert.equal(D.auditRows(rows).absolute_delta['0.3'].count, 1); assert.equal(JSON.stringify(rows), before);
});
const artifactPath = path.join(__dirname, '../outputs/final_paper_2026-11-15/analysis/decimal_candidate_rows.json');
const referencePath = path.join(__dirname, '../outputs/final_paper_2026-11-15/analysis/DECIMAL_NATIVE_AUDIT.json');
if (fs.existsSync(artifactPath) && fs.existsSync(referencePath)) {
  test('all retained candidate rows match independent Decimal/Fraction/SQLite INTEGER decisions and index hashes', () => {
    const bytes = fs.readFileSync(artifactPath), artifact = JSON.parse(bytes), expected = JSON.parse(fs.readFileSync(referencePath, 'utf8'));
    assert.equal(artifact.schema, 'seismic-pair-decimal-audit/1');
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), expected.artifact_sha256);
    const actual = D.auditRows(artifact.rows, {scaleExponent:artifact.integer_scale_exponent});
    assert.equal(actual.row_count, expected.primary_pairs);
    for (const delta of D.DEFAULT_DELTAS) {
      const result = actual.absolute_delta[delta];
      const selectionHash = crypto.createHash('sha256').update(result.pair_indices.map(i => i + '\n').join(''), 'ascii').digest('hex');
      for (const implementation of ['python_decimal', 'python_fraction', 'sqlite_integer']) {
        assert.equal(result.count, expected.absolute_delta_decisions[delta][implementation].count);
        assert.equal(selectionHash, expected.absolute_delta_decisions[delta][implementation].selection_sha256);
      }
    }
    for (const threshold of D.DEFAULT_THRESHOLDS) for (const category of D.CATEGORIES)
      assert.equal(actual.magnitude_membership[threshold][category], expected.magnitude_membership[threshold][category]);
  });
} else console.log('SKIP full private artifact parity: retained artifact and independent audit are not both available');
console.log(JSON.stringify({passed:checks}));
