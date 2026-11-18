"""Create a compact reading copy; the journal's double-spaced original stays intact.

Only direct paragraph auto-line spacing480 becomes276 (1.15). Every text node,
equation, hyperlink, image and other package part remains identical. This is a
reading format, explicitly not a replacement for the journal submission layout.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, timezone
from copy import deepcopy
import argparse
import hashlib
import json
from lxml import etree as E

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal-docx', type=Path, required=True)
    parser.add_argument('--reading-docx', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    source, target, receipt = [p.resolve() for p in
                              (args.journal_docx, args.reading_docx, args.receipt)]
    if source.suffix.lower() != '.docx' or target.suffix.lower() != '.docx':
        raise ValueError('Expected DOCX source and new DOCX reading target')
    if target.exists() or receipt.exists() or source == target:
        raise FileExistsError('Never replace a journal document, reading copy or receipt')
    with ZipFile(source) as archive:
        infos = archive.infolist()
        parts = {i.filename: archive.read(i.filename) for i in infos}
    document = E.fromstring(parts['word/document.xml'])
    original = E.tostring(document)
    changes = []
    for i, paragraph in enumerate(document.iter(W+'p')):
        spacing = paragraph.find(W+'pPr/'+W+'spacing')
        if spacing is not None and spacing.get(W+'line') == '480' and spacing.get(W+'lineRule') == 'auto':
            changes.append(dict(paragraph_index=i, before=dict(spacing.attrib)))
            spacing.set(W+'line', '276')
    if not changes:
        raise ValueError('No double-spaced source paragraphs found')
    # Restore a clone and compare the complete XML tree, not only visible text.
    restored = deepcopy(document)
    paragraphs = list(restored.iter(W+'p'))
    for change in changes:
        spacing = paragraphs[change['paragraph_index']].find(W+'pPr/'+W+'spacing')
        spacing.attrib.clear(); spacing.attrib.update(change['before'])
    if E.tostring(restored) != original:
        raise AssertionError('Reading variant changed content beyond declared spacing')
    parts['word/document.xml'] = E.tostring(document, xml_declaration=True, encoding='UTF-8', standalone=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, 'x', ZIP_DEFLATED) as out:
        for info in infos:
            out.writestr(info, parts[info.filename])
    with ZipFile(source) as first, ZipFile(target) as second:
        changed = [n for n in first.namelist() if first.read(n) != second.read(n)]
    if changed != ['word/document.xml']:
        raise AssertionError('Only document paragraph spacing may change')
    value = dict(status='PASS_SPACING_ONLY_READING_VARIANT', created_utc=datetime.now(timezone.utc).isoformat(),
                 journal_docx=str(source), journal_sha256=digest(source), reading_docx=str(target),
                 reading_sha256=digest(target), changed_parts=changed, changed_paragraphs=changes,
                 auto_line_spacing=dict(journal=480, reading=276), fonts_images_math_links_unchanged=True,
                 journal_submission_layout=False, scope='Compact reading only; use the double-spaced original for journal submission')
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
    print(json.dumps(dict(status=value['status'], paragraphs=len(changes), sha256=value['reading_sha256'])))


if __name__ == '__main__':
    main()
