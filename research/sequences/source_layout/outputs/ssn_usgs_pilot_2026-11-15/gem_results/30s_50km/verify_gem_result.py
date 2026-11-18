"""Verify exported GEM associations against frozen CSVs and group memberships.

Standard-library audit, independent of the GEM implementation and its adapter.
This verifies evidence and numerical eligibility; it is not identity ground truth.
"""
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
PILOT = OUT.parent.parent
REPOSITORY = PILOT.parent.parent
COMMIT = 'd13e63bebedcc6788e0ec88e8632957b749d3b60'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    run = json.loads((OUT/'run.json').read_text(encoding='utf-8'))
    assert run['status'] == 'executed_official_GEM'
    assert run['gem_commit'] == COMMIT
    assert (run['host_source'], run['guest_source']) == ('SSN', 'USGS')
    assert (run['time_seconds'], run['distance_km']) == (30, 50)
    assert run['use_ids'] is False and run['use_kms'] is True
    assert run['excluded'] == 0
    for item in run['inputs']:
        assert digest(item['path']) == item['sha256']
    adapter = REPOSITORY/'scripts/pilot_gem_baseline.py'
    assert digest(adapter) == run['adapter_sha256']
    protocol = json.loads((PILOT/'protocol_freeze_receipt.json').read_text())
    assert digest(PILOT/'protocol_v1_frozen.md') == protocol['sha256']
    input_rows = [r for item in run['inputs'] for r in read_csv(item['path'])]
    records = {r['record_id']: r for r in input_rows}
    assert len(records) == len(input_rows) == run['host_input'] + run['guest_input']
    pairs = json.loads((OUT/'pairs.json').read_text())
    pairset = {(p['ssn_record_id'], p['usgs_record_id']) for p in pairs}
    assert len(pairset) == len(pairs) == run['associated_pairs']
    assert len({a for a, b in pairset}) == len(pairset)
    assert len({b for a, b in pairset}) == len(pairset)
    maximum_distance_difference = 0.0
    for pair in pairs:
        ssn, usgs = (records[pair[k]] for k in ('ssn_record_id', 'usgs_record_id'))
        assert (ssn['source'].upper(), usgs['source'].upper()) == ('SSN', 'USGS')
        times = [dt.datetime.fromisoformat(r['time_utc'].replace('Z', '+00:00'))
                 for r in (ssn, usgs)]
        delta = abs((times[0] - times[1]).total_seconds())
        assert delta == pair['time_delta_seconds'] and delta < 30
        lat1, lat2 = (math.radians(float(r['latitude'])) for r in (ssn, usgs))
        lon1, lon2 = (math.radians(float(r['longitude'])) for r in (ssn, usgs))
        h = math.sin((lat1-lat2)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon1-lon2)/2)**2
        distance = 2*6371.0*math.asin(math.sqrt(h))
        difference = abs(distance - pair['gem_distance_km'])
        maximum_distance_difference = max(maximum_distance_difference, difference)
        # Numerical agreement check only, not an association tolerance.
        assert difference < 1e-8 and pair['gem_distance_km'] < 50
    memberships = read_csv(OUT/'memberships.csv')
    assert len(memberships) == len(records)
    assert collections.Counter(r['record_id'] for r in memberships) == collections.Counter(records.keys())
    groups = collections.defaultdict(list)
    for row in memberships:
        assert row['source'] == records[row['record_id']]['source'].upper()
        groups[row['gem_event_id']].append(row)
    assert len(groups) == run['retained_groups']
    member_pairs = set()
    for group in groups.values():
        assert 1 <= len(group) <= 2
        if len(group) == 2:
            by_source = {r['source']: r['record_id'] for r in group}
            assert set(by_source) == {'SSN', 'USGS'}
            member_pairs.add((by_source['SSN'], by_source['USGS']))
    assert member_pairs == pairset
    decisions = read_csv(OUT/'guest_decisions.csv')
    assert len(decisions) == run['guest_input']
    assert {r['record_id'] for r in decisions if r['decision'] == 'associated_by_GEM'} == {b for a, b in pairset}
    warning_ids = sorted(set(re.findall(r'Trying to add evID (\S+)',
                                        (OUT/'gem_stdout_stderr.log').read_text())))
    decisions_by_id = {r['record_id']: r['decision'] for r in decisions}
    files = [dict(path=p.name, bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'GEM_RESULT_MANIFEST.json']
    receipt = dict(status='PASS', utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   gem_commit=COMMIT, protocol_sha256=protocol['sha256'],
                   associations=len(pairset), preserved_source_rows=len(memberships),
                   internal_groups=len(groups), excluded=run['excluded'],
                   maximum_independent_distance_difference_km=maximum_distance_difference,
                   checks=['parameters_and_source_order', 'input_and_adapter_hashes',
                           'frozen_protocol_hash', 'unique_pair_keys_and_one_to_one_constraint',
                           'UTC_differences_and_strict_time_window', 'independent_haversine_R6371',
                           'every_input_row_preserved_once', 'pairs_equal_actual_exported_group_memberships',
                           'guest_decisions_agree_with_pairs'],
                   same_agency_attempt_warnings=[dict(record_id=r, final_decision=decisions_by_id[r]) for r in warning_ids],
                   timing_context='Single operational run; secondary pilot runs shared hardware until 19:31UTC and were cancelled. Not a controlled performance benchmark.',
                   limits='Evidence/eligibility audit only; no independently established physical-event identities or accuracy metrics.',
                   files=files)
    (OUT/'GEM_RESULT_MANIFEST.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status', 'associations', 'preserved_source_rows', 'internal_groups', 'maximum_independent_distance_difference_km')}, indent=2))


if __name__ == '__main__':
    main()
