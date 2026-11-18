"""Public, local document input checks; no private history or approval records."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'paper/manuscript'
TEMPLATE_PATH = 'paper/templates/C&G_WordTemplate.docx'
TEMPLATE_BYTES = 321715
TEMPLATE_SHA256 = '8f46981fb4e73b6ffeb911f1078529d0e38844213d32fbfab8e762cddfdfb95f'
FIXED_INPUTS = [
    'paper/manuscript/manuscript.md',
    'paper/manuscript/figures_main.json',
    'paper/manuscript/figure_provenance.json',
    'paper/manuscript/author_metadata.json',
    'paper/manuscript/article_view_urls.json',
    'paper/manuscript/README.md',
    'paper/manuscript/THIRD_PARTY_NOTICES.md',
    'paper/manuscript/requirements.txt',
    'paper/manuscript/.gitattributes',
    'paper/templates/provenance.json',
    'paper/templates/.gitattributes',
]
CODE_INPUTS = [
    'build_manuscript.py', 'native_equations.py', 'equations.json',
    'layout_contract.json', 'integrity.py', 'seal.py', 'restore_template.py',
    'rebuild.py', 'verify_docx.py', 'compare_docx_parts.py',
    'export_word_pdf.ps1', 'make_reading_copy.py',
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Input escapes the repository: ' + str(value))
    return path


def entry(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('Expected a file inside the repository: ' + str(path))
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                sha256=digest(path))


def figure_entries(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf8'))
    specs = manifest['ordered_figures']
    if [s['label'] for s in specs] != list(map(str, range(1, 14))):
        raise ValueError('Expected the thirteen maintained figure groups')
    originals = json.loads((BASE/'figure_provenance.json').read_text(encoding='utf8'))['required_original_groups']
    indexed = {s['label']: s for s in specs}
    if len(originals) != 9:
        raise ValueError('Expected nine retained original figure groups')
    for old in originals:
        spec = indexed[old['label']]
        if spec['sha256'] != old['sha256']:
            raise ValueError('Original figure group changed: ' + old['label'])
        if [(p['sha256'], p['url']) for p in spec.get('panels', [])] != [(p['sha256'], p['url']) for p in old['panels']]:
            raise ValueError('Original panel pixels/order/link changed')
    found = {}
    displayed = native = 0
    for spec in specs:
        displayed += len(spec.get('panels', [])) or 1
        for image in [spec] + spec.get('panels', []):
            for field, hash_field in [('path', 'sha256'), ('svg_path', 'svg_sha256')]:
                if field not in image:
                    continue
                path = repo_path(image[field])
                if not path.is_relative_to(BASE/'figures') or digest(path) != image[hash_field]:
                    raise ValueError('Missing/changed article figure: ' + image[field])
                found[image[field]] = entry(path)
                if field == 'svg_path':
                    native += 1
    if displayed != 25 or native != 6:
        raise ValueError('Expected twenty-five pictures and six native SVG panels')
    if sum(x.endswith('.png') for x in found) != 29:
        raise ValueError('Expected twenty-five used PNGs and four provenance composites')
    return sorted(found.values(), key=lambda item: item['path'])


def collect_inputs():
    source = BASE/'manuscript.md'
    text = source.read_text(encoding='utf8')
    metadata = json.loads((BASE/'author_metadata.json').read_text(encoding='utf8'))
    if text.splitlines()[0] != '# '+metadata['title']:
        raise ValueError('Document title and metadata disagree')
    if re.search(r'\b(?:TODO_[A-Z0-9_]+|PENDING[A-Z0-9_]*|TBD|PLACEHOLDER)\b', text):
        raise ValueError('Resolve drafting placeholders before building')
    paths = FIXED_INPUTS + ['paper/manuscript/build/'+name for name in CODE_INPUTS]
    values = [entry(repo_path(path)) for path in paths]
    values += figure_entries(BASE/'figures_main.json')
    return sorted(values, key=lambda item: item['path'])


def verify_contract(contract_path, source_path, manifest_path, builder_path):
    payload = json.loads(Path(contract_path).read_text(encoding='utf8'))
    if payload.get('schema') != 'public-manuscript-inputs/1':
        raise ValueError('Unknown public input seal')
    roles = {'source': source_path, 'manifest': manifest_path, 'builder': builder_path}
    for role, actual in roles.items():
        if Path(actual).resolve() != repo_path(payload[role]):
            raise ValueError('Build path differs from the sealed '+role)
    expected = payload['inputs']
    for item in expected + [payload['template']]:
        path = repo_path(item['path'])
        if not path.is_file() or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('Missing/changed sealed input: ' + item['path'])
    if collect_inputs() != expected:
        raise ValueError('Input set differs from the public seal')
    if payload['template'] != dict(path=TEMPLATE_PATH, bytes=TEMPLATE_BYTES, sha256=TEMPLATE_SHA256):
        raise ValueError('Template identity differs from the retained official template')
    return payload
