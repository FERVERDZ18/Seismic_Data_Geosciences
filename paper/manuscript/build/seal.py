"""Seal explicit public manuscript inputs; this does not create or publish a paper."""
import argparse
import json
from pathlib import Path
from integrity import ROOT, BASE, TEMPLATE_PATH, TEMPLATE_BYTES, TEMPLATE_SHA256, collect_inputs, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'BUILD_INPUTS.json')
    parser.add_argument('--replace-if-sha', help='Replace an existing seal only if its current SHA256 is exactly this value')
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError('The input seal must remain within this repository')
    if target.exists() and (not args.replace_if_sha or digest(target) != args.replace_if_sha):
        raise FileExistsError('Use a new target or explicitly identify the previous seal hash')
    payload = dict(schema='public-manuscript-inputs/1',
                   scope='Document reproduction inputs only; scientific-analysis reproduction is separate',
                   source='paper/manuscript/manuscript.md',
                   manifest='paper/manuscript/figures_main.json',
                   builder='paper/manuscript/build/build_manuscript.py',
                   template=dict(path=TEMPLATE_PATH, bytes=TEMPLATE_BYTES, sha256=TEMPLATE_SHA256),
                   inputs=collect_inputs())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(json.dumps(dict(status='SEALED', path=str(target), inputs=len(payload['inputs']), sha256=digest(target))))


if __name__ == '__main__':
    main()
