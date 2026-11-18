"""Inspect maintained pictures, links, native mathematics and retained template parts.

This is a structural document check, not a substitute for PDF page inspection.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from integrity import ROOT, BASE, TEMPLATE_PATH, digest
from build_manuscript import blocks, placement_plan, INLINE

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
SVG = 'http://schemas.microsoft.com/office/drawing/2016/SVG/main'
NS = dict(w=W, wp=WP, a=A, pic=PIC, m=M, asvg=SVG)


def verify(path):
    manifest = json.loads((BASE/'figures_main.json').read_text(encoding='utf8'))
    _, captions = placement_plan(list(blocks((BASE/'manuscript.md').read_text(encoding='utf8'))),
                                manifest['ordered_figures'], 'Figure ')
    with ZipFile(path) as archive:
        parts = {n:archive.read(n) for n in archive.namelist()}
    document = E.fromstring(parts['word/document.xml'])
    drawings = document.findall('.//w:drawing', NS)
    if len(drawings) != 25:
        raise ValueError('Expected all twenty-five article pictures')
    rels = E.fromstring(parts['word/_rels/document.xml.rels'])
    relmap = {node.get('Id'):node for node in rels}
    picture_links = []
    expected_links = []
    for spec in manifest['ordered_figures']:
        if spec.get('panels'):
            expected_links += [image['url'] for image in spec['panels']]
        else:
            expected_links.append(next((match.group(2) for match in INLINE.finditer(captions[spec['label']])
                                        if match.group(1)), None))
    for drawing in drawings:
        docpr = drawing.find('.//wp:docPr', NS)
        cnv = drawing.find('.//pic:cNvPr', NS)
        if docpr is None or cnv is None:
            raise ValueError('Missing native picture property anchors')
        one, two = docpr.find('a:hlinkClick', NS), cnv.find('a:hlinkClick', NS)
        if one is None or two is None or one.get('{'+R+'}id') != two.get('{'+R+'}id'):
            raise ValueError('Both picture hyperlink anchors must use the same target')
        target = relmap[one.get('{'+R+'}id')]
        if target.get('TargetMode') != 'External' or not target.get('Target','').startswith('https://gabrielhuav.github.io/Seismic_Data_Geosciences/'):
            raise ValueError('Picture must target its implemented observatory view')
        picture_links.append(dict(name=docpr.get('name'), url=target.get('Target')))
    if [item['url'] for item in picture_links] != expected_links:
        raise ValueError('Picture links differ from the exact ordered manifest views')
    expected_media = {}
    for i, spec in enumerate(manifest['ordered_figures'], 1):
        if spec.get('panels'):
            for j, panel in enumerate(spec['panels'], 1):
                name=f'word/media/sequence_figure_{i}_panel_{j}'
                expected_media[name+'.png']=panel['sha256']
                if panel.get('svg_path'):
                    expected_media[name+'.svg']=panel['svg_sha256']
        else:
            expected_media[f'word/media/sequence_figure_{i}.png']=spec['sha256']
    for name, expected in expected_media.items():
        if name not in parts or hashlib.sha256(parts[name]).hexdigest() != expected:
            raise ValueError('Missing or changed embedded figure: '+name)
    if len(document.findall('.//asvg:svgBlip', NS)) != 6:
        raise ValueError('Expected six native SVG map/timeline panels')
    if len(document.findall('.//m:oMathPara', NS)) != 2 or len(document.findall('.//m:oMath', NS)) != 16:
        raise ValueError('Expected two display equations and fourteen inline equations')
    allowed = {'[Content_Types].xml', 'docProps/core.xml', 'word/_rels/document.xml.rels',
               'word/document.xml', 'word/footer2.xml', 'word/footer4.xml'}
    with ZipFile(ROOT/TEMPLATE_PATH) as template:
        retained = [name for name in template.namelist() if name not in allowed]
        if len(retained) != 16 or any(template.read(name) != parts.get(name) for name in retained):
            raise ValueError('A preserve-only official template part changed')
    return dict(status='PASS_DOCUMENT_STRUCTURE_REQUIRES_VISUAL_QA',
                docx_sha256=digest(path), pictures=25, native_svg_panels=6,
                display_equations=2, inline_equations=14,
                preserve_only_template_parts=len(retained), picture_links=picture_links,
                visual_qa='Not assessed by this structural checker')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docx', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError('Never replace a structure-check receipt')
    result=verify(args.docx)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items()if k!='picture_links'}))


if __name__ == '__main__':
    main()
