"""Private loopback V3 transport. No kernels, browser control, or global services.

Production has one fixed destination, outside the served root. The fixture policy
is deliberately distinct and cannot write into the production result directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import base64
import hashlib
import json
import math
import os
import re
import threading
from urllib.parse import urlsplit, unquote

BASE = Path(__file__).resolve().parent
SERVED_ROOT = BASE / 'browser_harness'
RESULT_DIR = BASE / 'browser_actual_v3_01'
ENDPOINT = '/__results/browser-v3'
MAX_BYTES = 256 * 1024 * 1024
INPUT_SHA = 'd213720df5144a24157348701cdd82a6846852328feba1571a4ed13768ea9119'
KERNEL_SHA = 'ca075af9ac4ac1e7b2b59dfa5898674fdfd3aa52d196e41511f99d08c78f6ea0'
FIELDS = ('parent', 'eta', 'dt', 'distance', 'tn', 'rn', 'logEta', 'logProduct')
PLAN = [dict(n=n, rep=rep, backend=backend)
        for n in (2000, 10000, 50000, 170880) for rep in range(3)
        for backend in (('kd', 'reference') if rep % 2 else ('reference', 'kd'))]
STATIC = {'/v3/': 'v3/index.html', '/v3/index.html': 'v3/index.html',
          '/v3/harness.js': 'v3/harness.js', '/v3/worker.js': 'v3/worker.js',
          '/v3/BROWSER_MANIFEST.json': 'v3/BROWSER_MANIFEST.json',
          '/inputs_ssn_m35.json': 'inputs_ssn_m35.json',
          '/nearest-parent.js': 'nearest-parent.js'}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('Nonstandard JSON constant')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def utc_timestamp(value):
    require(isinstance(value, str), 'Missing UTC timestamp')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0,
            'Timestamp must be UTC')


def validate_payload(payload, manifest, *, fixture_only=False):
    """Transport/schema validation, not numerical scientific certification."""
    require(isinstance(payload, dict), 'JSON object required')
    allowed = {'schema','created_utc','user_agent','location','manifest','plan',
               'initial_load','visibility_observations','cpu_note','scope','cells',
               'transport','evaluation_label','fixture_only'}
    require(set(payload).issubset(allowed), 'Unexpected result property')
    require(payload.get('schema') == 'actual-browser-nearest-parent-cost/1', 'Wrong result schema')
    require(payload.get('fixture_only', False) is fixture_only, 'Fixture/production separation')
    require(payload.get('transport') == 'same-origin-loopback-post-v3', 'Wrong transport label')
    require(payload.get('evaluation_label') == 'V3_TRANSPORT_REPEAT_AFTER_V2_EXPORT_FAILURE', 'Wrong evaluation label')
    utc_timestamp(payload.get('created_utc'))
    require(isinstance(payload.get('user_agent'), str) and bool(payload['user_agent']), 'Missing browser user agent')
    require(isinstance(payload.get('location'), str), 'Missing browser location')
    require(payload.get('manifest') == manifest, 'Manifest differs from sealed V3')
    require(payload.get('plan') == PLAN, 'Predefined plan differs')
    require(manifest.get('planned_cells') == 24 and manifest.get('wall_cap_seconds') == 120
            and manifest.get('repetitions') == 3 and manifest.get('sizes') == [2000,10000,50000,170880]
            and manifest.get('backends') == ['reference','kd'], 'Manifest plan differs')
    assets = {item['file']: item for item in manifest['assets']}
    require(assets['../inputs_ssn_m35.json']['sha256'] == INPUT_SHA, 'Input pin differs')
    require(assets['../nearest-parent.js']['sha256'] == KERNEL_SHA, 'Kernel pin differs')
    load = payload.get('initial_load')
    require(isinstance(load, dict), 'Missing initial-load observations')
    require(load.get('paint_measured') is False and load.get('worker_peak_memory_measured') is False
            and load.get('transfer_time_isolated') is False and finite_number(load.get('total_ms')), 'Invalid load scope')
    utc_timestamp(load.get('started_utc')); utc_timestamp(load.get('completed_utc'))
    observations = load.get('assets')
    require(isinstance(observations, list) and len(observations) == 5, 'Missing load assets')
    require({item.get('file') for item in observations} == set(assets), 'Load assets differ')
    for asset in observations:
        pinned = assets[asset['file']]
        require(asset.get('sha256') == pinned['sha256'] and asset.get('bytes') == pinned['bytes'], 'Observed input digest differs')
        for key in ('fetch_resolution_ms', 'body_read_ms', 'sha256_ms', 'hash_and_size_validation_ms'):
            require(finite_number(asset.get(key)), 'Missing load timing')
    input_load = next(a for a in observations if a['file'] == '../inputs_ssn_m35.json')
    for key in ('utf8_decode_ms', 'json_parse_ms', 'structure_and_count_validation_ms'):
        require(finite_number(input_load.get(key)), 'Missing cohort load timing')
    require(isinstance(payload.get('visibility_observations'), list) and bool(payload['visibility_observations']), 'Missing visibility observations')
    for observation in payload['visibility_observations']:
        require(finite_number(observation.get('elapsed_ms')) and observation.get('state') in ('visible','hidden','prerender'), 'Invalid visibility observation')
    cells = payload.get('cells')
    require(isinstance(cells, list) and len(cells) == 24, 'Exactly 24 completed cells required')
    for spec, cell in zip(PLAN, cells):
        require(isinstance(cell, dict) and all(type(cell.get(k)) is type(v) and cell.get(k) == v for k,v in spec.items()), 'Cell order/spec differs')
        require(cell.get('status') in ('COMPUTED','CENSORED','FAIL'), 'Unexpected cell status')
        require(finite_number(cell.get('cell_wall_ms')), 'Invalid cell wall observation')
        utc_timestamp(cell.get('completed_utc'))
        if cell['status'] == 'CENSORED':
            require(cell.get('wall_limit_ms') == 120000, 'Wrong censoring cap')
            require('fields' not in cell, 'Censored cell cannot provide arrays')
            continue
        if cell['status'] == 'FAIL':
            require(isinstance(cell.get('error'), str), 'Missing failure evidence')
            require('fields' not in cell, 'Failed cell cannot provide arrays')
            continue
        require(isinstance(cell.get('metadata'), dict) and finite_number(cell['metadata'].get('total_ms')), 'Missing Worker timing')
        for key in ('worker_wall_ms','warmup_worker_setup_ms'):
            require(finite_number(cell.get(key)), 'Missing Worker observation')
        require(type(cell.get('id_count')) is int and cell['id_count'] == spec['n'], 'Wrong array row count')
        require(isinstance(cell.get('ids_sha256'), str) and re.fullmatch('[0-9a-f]{64}',cell['ids_sha256']) is not None, 'Wrong ID hash')
        require(set(cell.get('fields', {})) == set(FIELDS) and set(cell.get('hashes', {})) == set(FIELDS), 'Missing output fields')
        for key in FIELDS:
            field = cell['fields'][key]
            require(isinstance(field, dict) and field.get('encoding') == 'base64', 'Wrong field encoding')
            require(field.get('dtype') == ('int32-le' if key == 'parent' else 'float64-le'), 'Wrong dtype')
            require(isinstance(field.get('bytes'), str), 'Missing field bytes')
            raw = base64.b64decode(field['bytes'], validate=True)
            require(len(raw) == spec['n'] * (4 if key == 'parent' else 8), 'Wrong field byte count')
            require(hashlib.sha256(raw).hexdigest() == cell['hashes'][key], 'Field digest differs')
    return payload


@dataclass(frozen=True)
class Policy:
    root: Path
    result_dir: Path
    manifest: dict
    fixture_only: bool = False
    max_bytes: int = MAX_BYTES


def production_policy():
    manifest = strict_json((SERVED_ROOT/'v3/BROWSER_MANIFEST.json').read_bytes())
    for asset in manifest['assets']:
        path = (SERVED_ROOT/'v3'/asset['file']).resolve()
        require(path.is_relative_to(SERVED_ROOT.resolve()), 'Asset escapes served root')
        require(path.stat().st_size == asset['bytes'] and sha_file(path) == asset['sha256'], 'Sealed asset changed')
    return Policy(SERVED_ROOT.resolve(), RESULT_DIR.resolve(), manifest)


def fixture_policy(root, result_dir, manifest, *, max_bytes=MAX_BYTES):
    """Tests only; fixture paths must remain under this dedicated test directory."""
    tests = (BASE/'transport_fixture_tests').resolve()
    root, result_dir = Path(root).resolve(), Path(result_dir).resolve()
    require(root.is_relative_to(tests) and result_dir.is_relative_to(tests), 'Fixture path outside test directory')
    return Policy(root, result_dir, manifest, fixture_only=True, max_bytes=max_bytes)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_):
        pass

    @property
    def origin(self):
        return 'http://127.0.0.1:' + str(self.server.server_address[1])

    def reply(self, code, body, content_type='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body, separators=(',',':'), allow_nan=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)
        self.close_connection = True

    def error(self, code, message):
        self.reply(code, dict(saved=False, error=message))

    def host_ok(self):
        return self.headers.get_all('Host', []) == [urlsplit(self.origin).netloc]

    def do_GET(self):
        if not self.host_ok():
            return self.error(403, 'Wrong Host')
        if self.headers.get('Origin') not in (None, self.origin):
            return self.error(403, 'Wrong Origin')
        # The allowlist excludes directory listings, V1/V2, receipts and context.
        if self.path not in STATIC or unquote(self.path) != self.path:
            return self.error(404, 'Unknown resource')
        path = (self.server.policy.root/STATIC[self.path]).resolve()
        if not path.is_relative_to(self.server.policy.root) or not path.is_file():
            return self.error(404, 'Unknown resource')
        content_type = {'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8',
                        'json':'application/json'}.get(path.suffix[1:], 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(path.stat().st_size))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.end_headers()
        if self.command != 'HEAD':
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    self.wfile.write(block)
        self.close_connection = True

    do_HEAD = do_GET

    def do_POST(self):
        if self.path != ENDPOINT:
            return self.error(404, 'Unknown endpoint')
        if not self.host_ok() or self.headers.get_all('Origin', []) != [self.origin]:
            return self.error(403, 'Exact same-loopback Origin/Host required')
        if self.headers.get_all('Content-Type', []) != ['application/json']:
            return self.error(415, 'application/json required')
        if self.headers.get('Transfer-Encoding') is not None:
            return self.error(400, 'Content-Length required; no transfer encoding')
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1 or re.fullmatch('[0-9]+', lengths[0]) is None:
            return self.error(411, 'One valid Content-Length required')
        length = int(lengths[0])
        if length < 2 or length > self.server.policy.max_bytes:
            return self.error(413, 'Body exceeds fixed size limit')
        self.connection.settimeout(120)
        try:
            raw = self.rfile.read(length)
            require(len(raw) == length, 'Truncated request body')
            payload = validate_payload(strict_json(raw), self.server.policy.manifest,
                                       fixture_only=self.server.policy.fixture_only)
            require(payload['location'] == self.origin+'/v3/' or
                    payload['location'] == self.origin+'/v3/index.html', 'Browser location differs from exact server origin')
        except (ValueError, KeyError, TypeError, UnicodeError, TimeoutError, RecursionError, OSError):
            return self.error(422, 'Result schema, plan, bytes or pinned metadata rejected')
        digest = hashlib.sha256(raw).hexdigest()
        destination = self.server.policy.result_dir/'observed.json'
        receipt = self.server.policy.result_dir/'receipt.json'
        with self.server.save_lock:
            if destination.exists() or receipt.exists():
                if not destination.is_file() or not receipt.is_file():
                    return self.error(409, 'Incomplete prior evidence exists; never overwrite')
                try:
                    previous = strict_json(receipt.read_bytes())
                    same = previous['sha256'] == digest and previous['bytes'] == len(raw) and sha_file(destination) == digest
                except (ValueError, KeyError, TypeError, OSError):
                    same = False
                if not same:
                    return self.error(409, 'Different existing result; never overwrite')
                return self.reply(200, receipt.read_bytes())
            self.server.policy.result_dir.mkdir(parents=True, exist_ok=True)
            ack = dict(schema='private-browser-v3-local-receipt/1', saved=True,
                       sha256=digest, bytes=len(raw), received_utc=now(),
                       pid=os.getpid(), host='127.0.0.1',port=self.server.server_address[1],
                       endpoint=ENDPOINT, observed_file=str(destination),
                       fixture_only=self.server.policy.fixture_only,
                       validation='Transport/schema/plan/byte hashes only; array parity requires independent validator')
            ack_bytes = (json.dumps(ack, indent=2, allow_nan=False)+'\n').encode('utf-8')
            try:
                with destination.open('xb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                with receipt.open('xb') as stream:
                    stream.write(ack_bytes); stream.flush(); os.fsync(stream.fileno())
            except (FileExistsError, OSError):
                return self.error(409, 'Evidence could not be exclusively persisted; never overwrite')
            self.reply(201, ack_bytes)

    def do_OPTIONS(self):
        self.error(403, 'Cross-origin requests are not enabled')


def make_server(policy):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.policy = policy
    server.save_lock = threading.Lock()
    server.timeout = .25
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9_]+', args.label) is not None, 'Invalid owned-server label')
    directory = BASE/'server_v3_receipts'
    directory.mkdir(exist_ok=True)
    receipt = directory/(args.label+'.json')
    stop = receipt.with_suffix('.stop')
    if receipt.exists() or stop.exists():
        raise FileExistsError('Never reuse a server receipt/stop label')
    seal = BASE/'BROWSER_EXECUTION_SEAL_V3.json'
    require(seal.is_file(), 'Seal V3 with a fresh execution profile before opening the browser')
    sealed = strict_json(seal.read_bytes())
    for item in sealed['entries']:
        path = (BASE.parents[3]/item['path']).resolve()
        require(path.is_file() and sha_file(path) == item['sha256'] and path.stat().st_size == item['bytes'], 'Sealed V3 file changed')
    server = make_server(production_policy())
    payload = dict(pid=os.getpid(),host='127.0.0.1',port=server.server_address[1],
                   directory=str(SERVED_ROOT),url='http://127.0.0.1:'+str(server.server_address[1])+'/v3/',
                   fixed_post_endpoint=ENDPOINT,fixed_result=str(RESULT_DIR/'observed.json'),
                   stop_file=str(stop),started_utc=now(),publication=False,
                   execution_seal_sha256=sha_file(seal))
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(payload,stream,indent=2)
    print(json.dumps(payload),flush=True)
    try:
        while not stop.exists():
            server.handle_request()
    finally:
        server.server_close()
        print('Owned V3 loopback server stopped',flush=True)


if __name__ == '__main__':
    main()
