"""Compare every decoded package part, ignoring ZIP timestamps/compression only."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError('Never replace a comparison receipt')
    with ZipFile(args.reference) as one, ZipFile(args.candidate) as two:
        names_one, names_two = set(one.namelist()), set(two.namelist())
        common = sorted(names_one & names_two)
        mismatches = [name for name in common if one.read(name) != two.read(name)]
        parts = [dict(name=name, bytes=len(one.read(name)),
                      sha256=hashlib.sha256(one.read(name)).hexdigest()) for name in common]
    result = dict(status='PASS_ALL_DECODED_PARTS_IDENTICAL' if names_one==names_two and not mismatches else 'FAIL',
                  compared_parts=len(common), missing=sorted(names_one-names_two),
                  extra=sorted(names_two-names_one), changed=mismatches, parts=parts,
                  scope='All decoded ZIP parts; no allowances for metadata, paths, content or layout differences')
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items()if k!='parts'}))
    if result['status'] != 'PASS_ALL_DECODED_PARTS_IDENTICAL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
