"""Restore the pinned official C&G template locally; do not redistribute or edit it."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
PROVENANCE = ROOT/'paper/templates/provenance.json'
EXPECTED_SHA256 = '8f46981fb4e73b6ffeb911f1078529d0e38844213d32fbfab8e762cddfdfb95f'


def restore(local_source=None, permit_download=False):
    value = json.loads(PROVENANCE.read_text(encoding='utf8'))
    if value['sha256'] != EXPECTED_SHA256:
        raise ValueError('Unexpected official template provenance')
    target = PROVENANCE.parent/value['filename']
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != EXPECTED_SHA256:
            raise ValueError('Existing template differs; it was not overwritten')
        return target
    if local_source is not None:
        payload = Path(local_source).read_bytes()
    else:
        if not permit_download:
            raise FileNotFoundError('Template missing; use --download-template or provide --template-source')
        url = 'https://raw.githubusercontent.com/cageo/CAGEO_WordTemplate/'+value['commit']+'/'+quote(value['filename'])
        request = urllib.request.Request(url, headers={'User-Agent':'Seismic-Data-Geosciences-manuscript-reproduction'})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    if len(payload) != 321715 or hashlib.sha256(payload).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Template size or SHA256 differs; no file was installed')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(payload)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-file', type=Path)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    target = restore(args.from_file, args.download)
    print(json.dumps(dict(status='RESTORED_VERIFIED_TEMPLATE', path=str(target), sha256=EXPECTED_SHA256)))


if __name__ == '__main__':
    main()
