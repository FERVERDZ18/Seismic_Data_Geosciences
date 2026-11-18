"""Rebuild the maintained journal DOCX from the repository root."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from integrity import ROOT, BASE
from restore_template import restore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New directory below repository outputs/')
    parser.add_argument('--template-source', type=Path,
                        help='Optional local copy of the exact official template')
    parser.add_argument('--download-template', action='store_true',
                        help='Download the pinned official template if it is absent')
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise ValueError('Run this command from the repository root')
    target = (ROOT/args.output_dir).resolve()
    if not target.is_relative_to(ROOT/'outputs'):
        raise ValueError('Output directory must stay under repository outputs/')
    if target.exists():
        raise FileExistsError('Use a new output directory; previous builds are preserved')
    restore(args.template_source, args.download_template)
    layout = json.loads((BASE/'build/layout_contract.json').read_text(encoding='utf8'))
    target.mkdir(parents=True)
    docx = target/'Seismic_CG_sequences_manuscript.docx'
    report = target/'build_report.json'
    command = [sys.executable, str(BASE/'build/build_manuscript.py'),
               '--contract', 'paper/manuscript/BUILD_INPUTS.json',
               '--source', 'paper/manuscript/manuscript.md',
               '--figures', 'paper/manuscript/figures_main.json',
               '--out', docx.relative_to(ROOT).as_posix(),
               '--report', report.relative_to(ROOT).as_posix(),
               '--reference-after-twips', str(layout['builder_arguments']['reference_after_twips']),
               '--figure-after-twips', str(layout['builder_arguments']['figure_after_twips'])]
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(BASE/'build/verify_docx.py'),
                    '--docx', str(docx), '--receipt', str(target/'document_structure.json')],
                   cwd=ROOT, check=True)
    print(json.dumps(dict(status='BUILT_STRUCTURALLY_CHECKED_REQUIRES_VISUAL_QA',
                          journal_docx=str(docx), report=str(report))))


if __name__ == '__main__':
    main()
