"""Offline, provenance-preserving SSN--USGS candidate-association pilot.

Run only with the frozen protocol in docs/pilot_ssn_usgs_protocol.md. No row is
deleted or merged. Assignments are candidate associations, never reference labels.
Python standard library only; outputs are private by default.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
import calendar
from collections import Counter, defaultdict, deque
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'outputs/ssn_usgs_pilot_2026-11-15'
EARTH_RADIUS_KM = 6371.0088
DISTANCE_TOLERANCE_KM = 1e-9
NANOSECOND = 1_000_000_000
COST_SCALE = 1_000_000_000
SEED = 'ssn-usgs-pilot-v1'
GEM_COMMIT = 'd13e63bebedcc6788e0ec88e8632957b749d3b60'
SOURCE_IDS = {'ssn': 'ssn-mx-historical', 'usgs': 'usgs-mx-historical'}
PINNED_PACKAGES = {
    'ssn-mx-historical': '0ec2dfd575d67bdf0a5009938cccbf03548207c6d47e95f7038b08398712c7e2',
    'usgs-mx-historical': '7acac40dae8b60cd35443de3458f92bb8980f6f4923e4bd1b268ada87dc3aefe',
    'usgs-na-2020-2025': '2d250a645b279c459b850e2d97b4a376d0f68478a86a4c1ec5396735070c7303',
}
PINNED_MANIFESTS = {
    'ssn-mx-historical': '7f563caed9069f07fec86c271d627b6fa48455ce7cb542065388428024af4b0b',
    'usgs-mx-historical': '7ab89ec5726c8febeb002f717431b427975372ef4c99191b3d6716337d20c63b',
}
UTC_PATTERN = re.compile(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(?:Z|\+00:00)$')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_nanoseconds(value: str) -> int:
    """Require explicit UTC; preserve up to nanosecond fractions exactly."""
    match = UTC_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f'Unsupported explicit UTC timestamp: {value!r}')
    whole = datetime(*(int(x) for x in match.groups()[:6]), tzinfo=timezone.utc)
    seconds = calendar.timegm(whole.utctimetuple())
    fraction = int((match[7] or '').ljust(9, '0'))
    return seconds * NANOSECOND + fraction


@dataclass(frozen=True)
class Record:
    record_id: str
    source: str
    event_id: str | None
    time_utc: str
    time_ns: int
    latitude: float
    longitude: float
    depth_km: float | None
    magnitude: float
    magnitude_type: str | None
    source_file: str = ''
    source_record: int | None = None
    package_row: int = 0


@dataclass(frozen=True)
class Edge:
    ssn: str
    usgs: str
    delta_ns: int  # SSN minus USGS
    distance_km: float

    @property
    def pair(self):
        return self.ssn, self.usgs


def epicentral_distance(a: Record, b: Record) -> float:
    p, q = math.radians(a.latitude), math.radians(b.latitude)
    dl = math.radians((b.longitude - a.longitude + 180) % 360 - 180)
    h = math.sin((q-p)/2)**2 + math.cos(p)*math.cos(q)*math.sin(dl/2)**2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(max(0, min(1, h))), math.sqrt(max(0, 1-h)))


def candidate_edges(ssn: list[Record], usgs: list[Record], seconds: int, km: float) -> list[Edge]:
    if seconds <= 0 or km <= 0:
        raise ValueError('Candidate windows must be positive')
    for rows in (ssn, usgs):
        if len({r.record_id for r in rows}) != len(rows):
            raise ValueError('Duplicate source-row key')
    if any(r.source != 'ssn' for r in ssn) or any(r.source != 'usgs' for r in usgs):
        raise ValueError('Bipartite inputs must have distinct declared sources')
    ordered = sorted(ssn, key=lambda r: (r.time_ns, r.record_id))
    times = [r.time_ns for r in ordered]
    bound = seconds * NANOSECOND
    result = []
    for b in usgs:
        for a in ordered[bisect_left(times, b.time_ns-bound):bisect_right(times, b.time_ns+bound)]:
            distance = epicentral_distance(a, b)
            if distance <= km + DISTANCE_TOLERANCE_KM:
                result.append(Edge(a.record_id, b.record_id, a.time_ns-b.time_ns, distance))
    return sorted(result, key=lambda e: e.pair)


def in_window(edge: Edge, seconds: int, km: float) -> bool:
    return abs(edge.delta_ns) <= seconds*NANOSECOND and edge.distance_km <= km+DISTANCE_TOLERANCE_KM


def cost_units(edge: Edge, seconds: int, km: float) -> int:
    return round((abs(edge.delta_ns)/(seconds*NANOSECOND) + edge.distance_km/km) * COST_SCALE)


def components(edges: list[Edge]) -> list[list[Edge]]:
    by_node = defaultdict(list)
    for i, edge in enumerate(edges):
        by_node[('ssn', edge.ssn)].append(i)
        by_node[('usgs', edge.usgs)].append(i)
    seen = set()
    groups = []
    for start in sorted(by_node):
        if start in seen:
            continue
        pending = [start]
        indexes = set()
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            for i in by_node[node]:
                indexes.add(i)
                edge = edges[i]
                for other in [('ssn', edge.ssn), ('usgs', edge.usgs)]:
                    if other not in seen:
                        pending.append(other)
        groups.append(sorted((edges[i] for i in indexes), key=lambda e: e.pair))
    return groups


def _optimal_component(edges: list[Edge], seconds: int, km: float) -> set[tuple[str, str]]:
    """Successive shortest augmenting paths, including reverse assignment arcs."""
    if len(edges) == 1:
        return {edges[0].pair}
    left = sorted({e.ssn for e in edges})
    right = sorted({e.usgs for e in edges})
    nodes = [('source', '')] + [('ssn', x) for x in left] + [('usgs', x) for x in right] + [('sink', '')]
    index = {key: i for i, key in enumerate(nodes)}
    source, sink = 0, len(nodes)-1
    graph = [[] for _ in nodes]

    def arc(a, b, cost):
        forward = [b, len(graph[b]), 1, cost]
        reverse = [a, len(graph[a]), 0, -cost]
        graph[a].append(forward)
        graph[b].append(reverse)
        return forward

    for key in left:
        arc(source, index[('ssn', key)], 0)
    assignments = {}
    for edge in sorted(edges, key=lambda e: e.pair):
        assignments[edge.pair] = arc(index[('ssn', edge.ssn)], index[('usgs', edge.usgs)], cost_units(edge, seconds, km))
    for key in right:
        arc(index[('usgs', key)], sink, 0)
    while True:
        distances = [math.inf] * len(nodes)
        distances[source] = 0
        previous = [None] * len(nodes)
        pending = deque([source])
        queued = {source}
        while pending:
            a = pending.popleft()
            queued.remove(a)
            for ai, edge in enumerate(graph[a]):
                b, _, capacity, cost = edge
                if capacity and distances[a] + cost < distances[b]:
                    distances[b] = distances[a] + cost
                    previous[b] = (a, ai)
                    if b not in queued:
                        pending.append(b)
                        queued.add(b)
        if previous[sink] is None:
            break
        b = sink
        while b != source:
            a, ai = previous[b]
            edge = graph[a][ai]
            edge[2] -= 1
            graph[b][edge[1]][2] += 1
            b = a
    return {pair for pair, edge in assignments.items() if edge[2] == 0}


def optimal_assignment(edges: list[Edge], seconds: int, km: float) -> set[tuple[str, str]]:
    if len({e.pair for e in edges}) != len(edges):
        raise ValueError('Duplicate candidate edge')
    result = set()
    for group in components(edges):
        result.update(_optimal_component(group, seconds, km))
    return result


def greedy_assignment(edges: list[Edge], seconds: int, km: float) -> set[tuple[str, str]]:
    used_left, used_right, pairs = set(), set(), set()
    for edge in sorted(edges, key=lambda e: (cost_units(e, seconds, km), abs(e.delta_ns), e.distance_km, e.pair)):
        if edge.ssn not in used_left and edge.usgs not in used_right:
            pairs.add(edge.pair)
            used_left.add(edge.ssn)
            used_right.add(edge.usgs)
    return pairs


def concordance(a: set, b: set) -> dict:
    return {'intersection': len(a & b), 'only_first': len(a-b), 'only_second': len(b-a),
            'union': len(a | b), 'jaccard': len(a & b)/len(a | b) if a | b else None,
            'interpretation': 'Edge-set concordance, not physical-event accuracy.'}


def summarize(edges: list[Edge], ssn_count: int, usgs_count: int, seconds: int, km: float) -> tuple[dict, set, set]:
    start = time.perf_counter()
    groups = components(edges)
    assigned = optimal_assignment(edges, seconds, km)
    greedy = greedy_assignment(edges, seconds, km)
    degrees_left, degrees_right = Counter(e.ssn for e in edges), Counter(e.usgs for e in edges)
    costs = {e.pair: cost_units(e, seconds, km) for e in edges}
    return {'time_window_seconds': seconds, 'distance_window_km': km, 'candidate_edges': len(edges),
            'ssn_rows': ssn_count, 'usgs_rows': usgs_count,
            'ssn_with_candidates': len(degrees_left), 'usgs_with_candidates': len(degrees_right),
            'ssn_without_candidates': ssn_count-len(degrees_left), 'usgs_without_candidates': usgs_count-len(degrees_right),
            'ssn_with_multiple_candidates': sum(n > 1 for n in degrees_left.values()),
            'usgs_with_multiple_candidates': sum(n > 1 for n in degrees_right.values()),
            'connected_components': len(groups), 'isolated_one_edge_components': sum(len(g) == 1 for g in groups),
            'ambiguous_components': sum(len(g) > 1 for g in groups),
            'maximum_component_edges': max(map(len, groups), default=0),
            'graph_candidate_assignments': len(assigned), 'greedy_candidate_assignments': len(greedy),
            'graph_normalized_cost': sum(costs[p] for p in assigned)/COST_SCALE,
            'greedy_normalized_cost': sum(costs[p] for p in greedy)/COST_SCALE,
            'graph_greedy_concordance': concordance(assigned, greedy),
            'assignment_elapsed_seconds': time.perf_counter()-start}, assigned, greedy


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def verified_read(path: Path, expected: str, inputs: list, root: Path, expected_bytes=None) -> bytes:
    data = path.read_bytes()
    if sha256(data) != expected or (expected_bytes is not None and len(data) != expected_bytes):
        raise ValueError(f'Input checksum/size mismatch: {path}')
    inputs.append({'path': path.relative_to(root).as_posix(), 'sha256': expected, 'bytes': len(data)})
    return data


def load_cohorts(root: Path) -> tuple[dict[str, list[Record]], list, dict]:
    dist = root / 'system/dist'
    registry_raw = (dist/'data/catalogs.json').read_bytes()
    registry = json.loads(registry_raw)
    inputs = [{'path': 'system/dist/data/catalogs.json', 'sha256': sha256(registry_raw), 'bytes': len(registry_raw)}]
    cohorts = {}
    profile = {}
    start, stop = utc_nanoseconds('2016-01-01T00:00:00Z'), utc_nanoseconds('2026-01-01T00:00:00Z')
    for source, cid in SOURCE_IDS.items():
        cat = next(c for c in registry['catalogs'] if c['id'] == cid)
        if cat['sha256'] != PINNED_PACKAGES[cid] or cat['manifest_sha256'] != PINNED_MANIFESTS[cid]:
            raise ValueError(f'Frozen source package or manifest changed: {cid}')
        package = json.loads(verified_read(dist/cat['events_url'], cat['sha256'], inputs, root, cat.get('events_bytes')))
        manifest = json.loads(verified_read(dist/cat['manifest_url'], cat['manifest_sha256'], inputs, root))
        for spec in manifest['files']:
            path = root / (spec['public_copy_path'] if source == 'ssn' else 'data/raw/usgs/'+spec['path'])
            verified_read(path, spec['sha256'], inputs, root, spec['bytes'])
        rows = []
        seen = set()
        for ordinal, values in enumerate(package['rows'], start=1):
            row = dict(zip(package['fields'], values))
            if len(values) != len(package['fields']) or row['id'] in seen:
                raise ValueError('Invalid package width or duplicate key')
            seen.add(row['id'])
            instant = utc_nanoseconds(row['time'])
            lat, lon, mag = row['latitude'], row['longitude'], row['mag']
            if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in [lat, lon, mag]):
                raise ValueError('Non-finite coordinates or magnitude')
            if start <= instant < stop and 14 <= lat <= 33 and -118 <= lon <= -86 and mag >= 3.5:
                rows.append(Record(cid+'~'+row['id'], source, row['id'] if source == 'usgs' else None,
                                   row['time'], instant, lat, lon, row['depth'], mag, row.get('magType') or None,
                                   row.get('file', ''), row.get('source_record'), ordinal))
        cohorts[source] = rows
        profile[source] = {'source_catalogue': cid, 'package_rows': len(package['rows']), 'cohort_rows': len(rows),
                           'by_year': dict(sorted(Counter(r.time_utc[:4] for r in rows).items())),
                           'magnitude_types': dict(Counter(r.magnitude_type or '<not supplied>' for r in rows)),
                           'official_event_ids': sum(r.event_id is not None for r in rows)}
    return cohorts, inputs, profile


COHORT_COLUMNS = ['record_id', 'source', 'event_id', 'time_utc', 'latitude', 'longitude', 'depth_km',
                  'magnitude', 'magnitude_type', 'source_file', 'source_record', 'package_row']


def export_cohorts(cohorts: dict, output: Path):
    for source, rows in cohorts.items():
        with (output/(source+'_cohort.csv')).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COHORT_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({name: getattr(row, name) for name in COHORT_COLUMNS})


def exact_copy_control(root: Path, inputs: list) -> dict:
    dist = root/'system/dist'
    registry = json.loads((dist/'data/catalogs.json').read_bytes())
    by_id = {}
    for cid in ['usgs-mx-historical', 'usgs-na-2020-2025']:
        cat = next(c for c in registry['catalogs'] if c['id'] == cid)
        if cat['sha256'] != PINNED_PACKAGES[cid]:
            raise ValueError('Frozen exact-copy control changed')
        p = json.loads(verified_read(dist/cat['events_url'], cat['sha256'], inputs, root))
        by_id[cid] = {row[0]: dict(zip(p['fields'], row)) for row in p['rows']}
    mx, na = by_id.values()
    shared = mx.keys() & na.keys()
    common = set(next(iter(mx.values()))) & set(next(iter(na.values()))) - {'file'}
    return {'shared_original_usgs_ids': len(shared),
            'same_common_source_values': sum(all(mx[k][f] == na[k][f] for f in common) for k in shared),
            'compared_fields': sorted(common),
            'interpretation': 'Exact-copy integrity control only; not a reference for cross-agency physical identity.'}


def read_gem_pairs(path: Path, records: dict) -> set:
    if path.suffix.lower() == '.json':
        values = json.loads(path.read_text(encoding='utf-8-sig'))
    else:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            values = list(csv.DictReader(stream))
    result = set()
    for value in values:
        pair = value['ssn_record_id'], value['usgs_record_id']
        if pair[0] not in records or pair[1] not in records or records[pair[0]].source != 'ssn' or records[pair[1]].source != 'usgs':
            raise ValueError('GEM pair does not refer to these frozen cohort rows')
        result.add(pair)
    return result


def validate_gem_run(pair_path: Path, cohorts: dict, output: Path) -> dict:
    """Bind a real baseline to its declared method and our exact exported CSVs."""
    run_path = pair_path.with_name('run.json')
    raw = run_path.read_bytes()
    metadata = json.loads(raw)
    expected = {'status': 'executed_official_GEM', 'time_seconds': 30, 'distance_km': 50,
                'host_source': 'SSN', 'guest_source': 'USGS', 'gem_commit': GEM_COMMIT,
                'host_input': len(cohorts['ssn']), 'guest_input': len(cohorts['usgs'])}
    if any(metadata.get(key) != value for key, value in expected.items()) or metadata.get('use_kms') is not True or metadata.get('use_ids') is not False:
        raise ValueError('GEM baseline metadata differs from the frozen primary comparator')
    entries = {Path(item['path'].replace('\\', '/')).name: item['sha256'] for item in metadata.get('inputs', [])}
    for source in ['ssn', 'usgs']:
        name = source+'_cohort.csv'
        if entries.get(name) != sha256((output/name).read_bytes()):
            raise ValueError('GEM baseline CSV hashes differ from this frozen cohort export')
    manifest_path = pair_path.with_name('GEM_RESULT_MANIFEST.json')
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest.get('status') != 'PASS' or manifest.get('gem_commit') != GEM_COMMIT
            or manifest.get('protocol_sha256') != sha256((output/'protocol_v1_frozen.md').read_bytes())):
        raise ValueError('GEM artifact manifest does not match the frozen protocol')
    files = manifest.get('files', [])
    if not {pair_path.name, run_path.name}.issubset({f['path'] for f in files}):
        raise ValueError('GEM artifact manifest omits its pairs or run metadata')
    for entry in files:
        name = entry['path']
        if Path(name).name != name:
            raise ValueError('GEM artifact names must be local filenames')
        content = (pair_path.parent/name).read_bytes()
        if sha256(content) != entry['sha256'] or len(content) != entry['bytes']:
            raise ValueError('GEM artifact hash or byte size mismatch')
    return {'path': str(run_path), 'sha256': sha256(raw), 'verified_primary_settings': expected,
            'artifact_manifest_sha256': sha256(manifest_raw), 'verified_artifact_files': len(files),
            'use_kms': True, 'use_ids': False, 'inputs': metadata['inputs'],
            'adapter_sha256': metadata.get('adapter_sha256'), 'engine_version': metadata.get('engine_version')}


def gem_diagnostics(gem_path: Path, records: dict, broad: list[Edge], primary: list[Edge], graph_pairs: set, gem_pairs: set) -> dict:
    """Post-discovery harmonization; never replaces the prespecified primary run."""
    if gem_path.suffix.lower() == '.json':
        reported = json.loads(gem_path.read_text(encoding='utf-8-sig'))
    else:
        with gem_path.open(encoding='utf-8-sig', newline='') as stream:
            reported = list(csv.DictReader(stream))
    scale = 6371.0/EARTH_RADIUS_KM
    strict = {}
    for edge in broad:
        a, b = records[edge.ssn], records[edge.usgs]
        # Match Python datetime's truncation of submicrosecond source fractions.
        micro_delta_ns = ((a.time_ns//1000)-(b.time_ns//1000))*1000
        gem_distance = edge.distance_km*scale
        if abs(micro_delta_ns) < 30*NANOSECOND and gem_distance < 50:
            strict[edge.pair] = Edge(edge.ssn, edge.usgs, micro_delta_ns, gem_distance)
    own = {e.pair for e in primary}
    common = own & strict.keys()
    clock_errors, distance_errors, unexpected = [], [], set()
    for row in reported:
        pair = row['ssn_record_id'], row['usgs_record_id']
        a, b = records[pair[0]], records[pair[1]]
        if row.get('time_delta_seconds') not in (None, ''):
            error = abs(abs(float(row['time_delta_seconds']))-abs(a.time_ns-b.time_ns)/NANOSECOND)
            clock_errors.append(error)
            if error > 1e-6:
                unexpected.add(pair)
        if row.get('gem_distance_km') not in (None, ''):
            error = abs(float(row['gem_distance_km'])-epicentral_distance(a, b)*scale)
            distance_errors.append(error)
            if error > 1e-6:
                unexpected.add(pair)
    eligible_common = common-unexpected
    strict_graph = optimal_assignment(list(strict.values()), 30, 50)
    return {'status': 'Post-discovery diagnostic requested after primary graph results; primary thresholds/results unchanged.',
            'gem_sphere_radius_km': 6371.0, 'gem_time_threshold': 'strict < 30 seconds after Python datetime microsecond truncation',
            'gem_distance_threshold': 'strict < 50 km',
            'source_rows_with_nonzero_submicroseconds': sum(r.time_ns % 1000 != 0 for r in records.values()),
            'primary_only_eligible_pairs': len(own-strict.keys()), 'gem_model_only_eligible_pairs': len(strict.keys()-own),
            'reported_time_error_max_seconds': max(clock_errors, default=None),
            'reported_distance_error_max_km_after_radius_normalization': max(distance_errors, default=None),
            'reported_clock_or_distance_disagreements_over_1e_6': len(unexpected),
            'graph_gem_concordance_after_common_eligibility': concordance(graph_pairs & eligible_common, gem_pairs & eligible_common),
            'gem_strict_model_graph_assignments': len(strict_graph),
            'gem_strict_model_graph_vs_gem': concordance(strict_graph, gem_pairs),
            'interpretation': 'Numerical/representation harmonization and method concordance only; no identity labels or accuracy.'}


def blind_cases(strata: dict[str, set], limit=25) -> tuple[list, dict]:
    chosen, used, counts = [], set(), {}
    for name, pairs in strata.items():
        available = pairs-used
        order = sorted(available, key=lambda p: (sha256((SEED+'\0'+p[0]+'\0'+p[1]).encode()), p))
        selected = order[:limit]
        counts[name] = {'available_after_prior_strata': len(available), 'selected': len(selected), 'shortfall': limit-len(selected)}
        for pair in selected:
            case_id = 'case-'+sha256((SEED+'\0'+pair[0]+'\0'+pair[1]).encode())[:20]
            chosen.append({'case_id': case_id, 'ssn_record_id': pair[0], 'usgs_record_id': pair[1], 'stratum': name})
            used.add(pair)
    return sorted(chosen, key=lambda x: x['case_id']), counts


def export_blind_cases(cases: list, records: dict, output: Path):
    target = output/'adjudication_blinded.csv'
    if target.exists():
        with target.open(encoding='utf-8', newline='') as stream:
            if any(any(row.get(field, '').strip() for field in ['human_judgement', 'independent_evidence', 'reviewer'])
                   for row in csv.DictReader(stream)):
                raise ValueError('Refusing to overwrite a blinded table containing human work')
    columns = ['case_id']
    measurements = ['time_utc', 'latitude', 'longitude', 'depth_km', 'magnitude', 'magnitude_type']
    columns += [side+'_'+field for side in ['a', 'b'] for field in measurements]
    columns += ['human_judgement', 'independent_evidence', 'reviewer']
    discovery_cases = []
    source_lookup = []
    with target.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            # Stable A/B masking avoids placing every SSN row in the same column.
            pair = (records[case['ssn_record_id']], records[case['usgs_record_id']])
            if int(case['case_id'][-1], 16) % 2:
                pair = pair[::-1]
            discovery_cases.append({**case, 'record_a_id': pair[0].record_id, 'record_b_id': pair[1].record_id})
            source_lookup.append({'case_id': case['case_id'], **{side: {
                'record_id': record.record_id, 'source': record.source, 'official_event_id': record.event_id,
                'source_file': record.source_file, 'source_record': record.source_record, 'package_row': record.package_row}
                for side, record in zip(['a', 'b'], pair)}})
            row = {'case_id': case['case_id'], 'human_judgement': '', 'independent_evidence': '', 'reviewer': ''}
            for side, record in zip(['a', 'b'], pair):
                row.update({side+'_'+field: getattr(record, field) for field in measurements})
            writer.writerow(row)
    write_json(output/'adjudication_discovery_key.json', {'status': 'No human judgements supplied', 'cases': discovery_cases})
    write_json(output/'adjudication_source_lookup.json', {'scope': 'Source lookup without sampling strata, costs or method decisions.', 'cases': source_lookup})


def run_pilot(cohorts: dict, output: Path, gem_path: Path | None = None) -> dict:
    ssn, usgs = cohorts['ssn'], cohorts['usgs']
    gem_run = validate_gem_run(gem_path, cohorts, output) if gem_path else None
    records = {r.record_id: r for r in ssn+usgs}
    start = time.perf_counter()
    broad = candidate_edges(ssn, usgs, 60, 100)
    candidate_seconds = time.perf_counter()-start
    sensitivity = []
    for seconds in [10, 30, 60]:
        for km in [10, 50, 100]:
            edges = [e for e in broad if in_window(e, seconds, km)]
            summary, assigned, greedy = summarize(edges, len(ssn), len(usgs), seconds, km)
            sensitivity.append(summary)
            if seconds == 30 and km == 50:
                primary, primary_edges, graph, primary_greedy = summary, edges, assigned, greedy
    groups = components(primary_edges)
    by_pair = {e.pair: e for e in primary_edges}
    component_id = {e.pair: 'component-'+str(i).zfill(6) for i, group in enumerate(groups, 1) for e in group}
    component_sizes = {e.pair: len(group) for group in groups for e in group}
    degrees_left, degrees_right = Counter(e.ssn for e in primary_edges), Counter(e.usgs for e in primary_edges)
    edge_rows = [{'ssn_record_id': e.ssn, 'usgs_record_id': e.usgs, 'ssn_minus_usgs_seconds': e.delta_ns/NANOSECOND,
                  'absolute_time_difference_seconds': abs(e.delta_ns)/NANOSECOND, 'distance_km': e.distance_km,
                  'normalized_cost_quantized': cost_units(e, 30, 50)/COST_SCALE,
                  'component_id': component_id[e.pair], 'ambiguous_component': component_sizes[e.pair] > 1,
                  'ssn_degree': degrees_left[e.ssn], 'usgs_degree': degrees_right[e.usgs],
                  'graph_candidate_assignment': e.pair in graph, 'greedy_candidate_assignment': e.pair in primary_greedy}
                 for e in primary_edges]
    fields = ['ssn_record_id', 'usgs_record_id', 'ssn_minus_usgs_seconds', 'absolute_time_difference_seconds', 'distance_km',
              'normalized_cost_quantized', 'component_id', 'ambiguous_component', 'ssn_degree', 'usgs_degree',
              'graph_candidate_assignment', 'greedy_candidate_assignment']
    with (output/'primary_candidate_edges.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(edge_rows)
    write_json(output/'graph_candidate_pairs.json', [{'ssn_record_id': p[0], 'usgs_record_id': p[1]} for p in sorted(graph)])
    write_json(output/'greedy_candidate_pairs.json', [{'ssn_record_id': p[0], 'usgs_record_id': p[1]} for p in sorted(primary_greedy)])
    with (output/'rows_without_primary_candidates.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COHORT_COLUMNS)
        writer.writeheader()
        for r in ssn+usgs:
            if r.record_id not in (degrees_left if r.source == 'ssn' else degrees_right):
                writer.writerow({name: getattr(r, name) for name in COHORT_COLUMNS})
    gem = read_gem_pairs(gem_path, records) if gem_path else None
    gem_comparison = {'status': 'Pending real GEM pair output; no comparator values invented.'}
    if gem is not None:
        gem_left_degrees = Counter(pair[0] for pair in gem)
        gem_right_degrees = Counter(pair[1] for pair in gem)
        gem_cost = sum(cost_units(Edge(pair[0], pair[1], records[pair[0]].time_ns-records[pair[1]].time_ns,
                                       epicentral_distance(records[pair[0]], records[pair[1]])), 30, 50) for pair in gem)/COST_SCALE
        gem_comparison = {'status': 'Real external GEM edge set supplied', 'path': str(gem_path),
                          'sha256': sha256(gem_path.read_bytes()), 'pairs': len(gem),
                          'run_provenance': gem_run,
                          'ssn_rows_with_multiple_gem_associations': sum(n > 1 for n in gem_left_degrees.values()),
                          'usgs_rows_with_multiple_gem_associations': sum(n > 1 for n in gem_right_degrees.values()),
                          'normalized_cost_under_pilot_objective': gem_cost,
                          'primary_components_with_different_assignments': len({component_id[p] for p in graph ^ gem if p in component_id}),
                          'ssn_rows_only_graph': len({p[0] for p in graph}-{p[0] for p in gem}),
                          'ssn_rows_only_gem': len({p[0] for p in gem}-{p[0] for p in graph}),
                          'usgs_rows_only_graph': len({p[1] for p in graph}-{p[1] for p in gem}),
                          'usgs_rows_only_gem': len({p[1] for p in gem}-{p[1] for p in graph}),
                          'outside_primary_candidate_window': len(gem-by_pair.keys()),
                          'graph_gem_concordance': concordance(graph, gem),
                          'note': 'GEM uses strict thresholds and its own geodesia/order; graph window is inclusive.'}
        gem_comparison['harmonization_diagnostic'] = gem_diagnostics(gem_path, records, broad, primary_edges, graph, gem)
        difference_columns = ['ssn_record_id', 'usgs_record_id', 'graph_candidate_assignment', 'gem_candidate_assignment',
                              'ssn_minus_usgs_seconds', 'distance_pilot_radius_km', 'distance_gem_radius_km',
                              'primary_inclusive_eligible', 'gem_strict_model_eligible', 'component_id', 'ambiguous_component']
        with (output/'graph_gem_disagreements.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=difference_columns)
            writer.writeheader()
            for pair in sorted(graph ^ gem):
                a, b = records[pair[0]], records[pair[1]]
                distance = epicentral_distance(a, b)
                gem_distance = distance*6371.0/EARTH_RADIUS_KM
                micro_delta = ((a.time_ns//1000)-(b.time_ns//1000))*1000
                writer.writerow({'ssn_record_id': pair[0], 'usgs_record_id': pair[1],
                                 'graph_candidate_assignment': pair in graph, 'gem_candidate_assignment': pair in gem,
                                 'ssn_minus_usgs_seconds': (a.time_ns-b.time_ns)/NANOSECOND,
                                 'distance_pilot_radius_km': distance, 'distance_gem_radius_km': gem_distance,
                                 'primary_inclusive_eligible': pair in by_pair,
                                 'gem_strict_model_eligible': abs(micro_delta) < 30*NANOSECOND and gem_distance < 50,
                                 'component_id': component_id.get(pair, ''),
                                 'ambiguous_component': component_sizes.get(pair, 0) > 1})
    strata = {'isolated_one_edge_component': {e.pair for g in groups if len(g) == 1 for e in g},
              'ambiguous_component': {e.pair for g in groups if len(g) > 1 for e in g},
              'graph_gem_disagreement': (graph ^ gem) if gem is not None else set(),
              'near_outside_primary_window': {e.pair for e in broad if not in_window(e, 30, 50)}}
    cases, sample_counts = blind_cases(strata)
    export_blind_cases(cases, records, output)
    result = {'schema': 'ssn-usgs-candidate-association-pilot/1', 'physical_identity_validated': False,
              'reference_accuracy_available': False, 'primary': primary, 'sensitivity': sensitivity,
              'broad_candidate_generation_seconds': candidate_seconds, 'gem': gem_comparison,
              'blinded_adjudication': {'labels_supplied': 0, 'cases': len(cases), 'strata': sample_counts,
                                      'gem_stratum_pending': gem is None},
              'limits': ['All edges and assignments are candidate associations, not confirmed duplicate earthquakes.',
                         'No precision, recall, F1, accuracy or unique physical-event count is estimated.',
                         'Missing SSN uncertainties, magnitude type and official IDs are not imputed.',
                         'No source row or web package is deleted, merged or rewritten.']}
    write_json(output/'pilot_results.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--export-only', action='store_true', help='Verify/export cohort before computing any candidate pairs')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--gem-pairs', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT/'outputs').resolve()):
        raise ValueError('Pilot output must stay within this repository\'s private outputs directory')
    output.mkdir(parents=True, exist_ok=True)
    protocol = (output/'protocol_v1_frozen.md').read_bytes()
    freeze = json.loads((output/'protocol_freeze_receipt.json').read_text(encoding='utf-8-sig'))
    if sha256(protocol) != freeze['sha256'] or sha256((ROOT/'docs/pilot_ssn_usgs_protocol.md').read_bytes()) != freeze['sha256']:
        raise ValueError('Frozen protocol differs from its receipt or maintained protocol')
    cohorts, inputs, profile = load_cohorts(ROOT)
    export_cohorts(cohorts, output)
    write_json(output/'cohort_profile.json', profile)
    receipt = {'created_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'export_only' if args.export_only else 'run',
               'protocol_sha256': freeze['sha256'], 'script_sha256': sha256(Path(__file__).read_bytes()),
               'python': platform.python_version(), 'inputs': inputs,
               'cohort_csvs': {source: {'path': source+'_cohort.csv', 'sha256': sha256((output/(source+'_cohort.csv')).read_bytes()),
                                        'rows': len(rows)} for source, rows in cohorts.items()}}
    if args.run:
        result = run_pilot(cohorts, output, args.gem_pairs)
        receipt['exact_copy_control'] = exact_copy_control(ROOT, inputs)
        receipt['outputs'] = {p.name: {'sha256': sha256(p.read_bytes()), 'bytes': p.stat().st_size}
                              for p in sorted(output.iterdir()) if p.is_file() and p.name not in ['execution_receipt.json', 'cohort_profile_before_matching.json']}
        print(json.dumps({'primary': result['primary'], 'gem': result['gem'], 'blinded_adjudication': result['blinded_adjudication']}, indent=2))
    else:
        print(json.dumps(profile, indent=2))
    write_json(output/'execution_receipt.json', receipt)


if __name__ == '__main__':
    main()
