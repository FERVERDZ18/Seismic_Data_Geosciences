"""Rebuild the article with the journal-specific retained Word template.

Run from the repository root via paper/manuscript/build/rebuild.py.
Source, assets, metadata and code must match BUILD_INPUTS.json.
The builder does not render, publish or modify an existing artifact.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import struct
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as E

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'paper/manuscript'
TEMPLATE = ROOT / "paper/templates/C&G_WordTemplate.docx"
CONTRACT = BASE / 'build/layout_contract.json'
FIGURE_DIR = BASE / 'figures'
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELNS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_NATIVE_URLS = json.loads((BASE/'article_view_urls.json').read_text(encoding='utf-8'))
VIEW = (r"(?:https://gabrielhuav\.github\.io/Seismic_Data_Geosciences/\?figure=[a-z0-9-]+&lang=en|"
        + '|'.join(re.escape(url) for url in _NATIVE_URLS) + ')')
ARTICLE_LINK = (r'(?:https?://[^\s<>()\[\]"\\]+'
                r"|mailto:[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
INLINE = re.compile(r"\[([^\]]+)\]\((" + ARTICLE_LINK + r")\)|`([^`\n]+)`|\*([^*\n]+)\*|\{\{math:([a-z][a-z0-9-]*)\}\}")
ANCHOR = re.compile(r"<!--\s*figure:\s*(S?[1-9]\d*)\s*-->")
EQUATION = re.compile(r"<!--\s*equation:\s*(metric|bound)\s*-->")
WIDTHS = re.compile(r"<!--\s*table-widths:\s*([\d,\s]+)-->")
MARKER = re.compile(r"<!--")


def w(name):
    return "{" + W + "}" + name


def node(name, **attrs):
    el = E.Element(w(name))
    for key, value in attrs.items():
        el.set(w(key), str(value))
    return el


def sha(data):
    return hashlib.sha256(data).hexdigest()


def typography(text):
    """Thousands separator (digit~digit) becomes a no-break space, as the journal guide asks."""
    text = re.sub(r"(?<=\d)~(?=\d{3})", " ", text)
    superscript = str.maketrans('0123456789-−', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁻')
    text = re.sub(r'\b(\d+)\^([-−]?\d+)', lambda m: m.group(1) + m.group(2).translate(superscript), text)
    return text.replace("**", "")


def plain(text):
    """Text as it appears in the document, without inline markup (used for alt text and counts)."""
    from native_equations import inline_plain
    text = INLINE.sub(lambda m: m.group(1) or m.group(3) or m.group(4) or inline_plain(m.group(5)), text)
    return typography(text)


def blocks(text):
    lines = text.splitlines()
    i = 0
    pending_widths = None
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        anchor = ANCHOR.fullmatch(s)
        equation = EQUATION.fullmatch(s)
        widths = WIDTHS.fullmatch(s)
        if anchor:
            yield ("figure", anchor.group(1)); i += 1
        elif equation:
            yield ("equation", equation.group(1)); i += 1
        elif widths:
            pending_widths = [int(x) for x in widths.group(1).split(",")]; i += 1
        elif MARKER.search(s):
            raise ValueError("Unknown directive: " + s)
        elif s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            yield ("h" + str(level), s.lstrip("# ")); i += 1
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", x) for x in cells):
                    rows.append(cells)
                i += 1
            yield ("table", (rows, pending_widths)); pending_widths = None
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|")) and not MARKER.search(lines[i]):
                para.append(lines[i].strip()); i += 1
            yield ("p", " ".join(para))


def placement_plan(parsed, specs, prefix):
    content, captions, in_captions = [], [], False
    for kind, value in parsed:
        if kind == "h2" and value == "Figure captions":
            if in_captions:
                raise ValueError("Duplicate Figure captions section")
            in_captions = True
            continue
        if in_captions:
            if kind != "p":
                raise ValueError("Figure captions may contain only caption paragraphs")
            captions.append(value)
        else:
            content.append((kind, value))
    if not in_captions or len(captions) != len(specs):
        raise ValueError("Each ordered and hash-verified figure requires exactly one caption")
    labels = [spec["label"] for spec in specs]
    for label, caption in zip(labels, captions):
        if not caption.startswith(f"{prefix}{label}."):
            raise ValueError(f"Caption order differs from figure list at {label}")
    anchors = [value for kind, value in content if kind == "figure"]
    if anchors != labels:
        raise ValueError(f"Figure anchors {anchors} must match the declared order {labels}")
    from native_equations import definitions
    equation_ids = [value for kind, value in content if kind == 'equation']
    if equation_ids != definitions()['ordered_ids']:
        raise ValueError('Equation markers must declare metric and bound once each, in scientific order')
    return content, dict(zip(labels, captions))


def build(args):
    source_path = (ROOT / args.source).resolve()
    out_path = (ROOT / args.out).resolve()
    destination = BASE.resolve()
    report_path = (ROOT / args.report).resolve()
    manifest_path = (ROOT / args.figures).resolve()
    output_base = (ROOT / 'outputs').resolve()
    if not all(p.is_relative_to(destination) for p in (source_path, manifest_path)):
        raise ValueError('Source and figures must stay under paper/manuscript')
    if not all(p.is_relative_to(output_base) for p in (out_path, report_path)):
        raise ValueError('New artifacts and receipts must stay under repository outputs/')
    from integrity import verify_contract
    contract_path = (ROOT / args.contract).resolve()
    if not contract_path.is_relative_to(ROOT):
        raise ValueError('Build contract must remain inside the repository')
    verify_contract(contract_path, source_path, manifest_path, Path(__file__).resolve())
    layout = json.loads(CONTRACT.read_text(encoding='utf-8'))['builder_arguments']
    if (args.reference_after_twips, args.figure_after_twips, args.prefix) != (layout['reference_after_twips'], layout['figure_after_twips'], layout['prefix']):
        raise ValueError('Builder arguments differ from the maintained public layout')
    metadata = json.loads((destination/'author_metadata.json').read_text(encoding='utf-8'))
    if set(metadata) != {'title','creator','last_modified_by'}:
        raise ValueError('Expected only the public document core properties')
    source_bytes = source_path.read_bytes()
    parsed = list(blocks(source_bytes.decode("utf-8")))
    specs = json.loads((ROOT / args.figures).read_text(encoding="utf-8"))["ordered_figures"]
    content, captions = placement_plan(parsed, specs, args.prefix)

    raw = TEMPLATE.read_bytes()
    if sha(raw) != json.loads((TEMPLATE.parent / "provenance.json").read_text())["sha256"]:
        raise ValueError("Retained template hash changed")
    if not CONTRACT.exists():
        raise FileNotFoundError("Public layout contract is required")
    with ZipFile(TEMPLATE) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    doc = E.fromstring(parts["word/document.xml"])
    body = doc.find(w("body"))
    ps = body.findall(w("p"))
    patterns = {"title": ps[43], "author": ps[44], "abstract": ps[65], "heading": ps[68], "body": ps[69], "caption": ps[98]}
    final_sect = deepcopy(body.find(w("sectPr")))
    figure_pattern = next(deepcopy(p) for p in ps if p.find(".//" + w("drawing")) is not None)
    from native_equations import NS as MATH_NS, equation_paragraph, validate_document_math, inline_equation, INLINE_MATH
    # The retained template's numbered native equations are inside table cells,
    # so the mathematical paragraph is a descendant rather than a body sibling.
    equation_pattern = deepcopy(doc.find('.//m:oMathPara/..', MATH_NS))
    if equation_pattern is None:
        raise ValueError('The retained template has no native mathematical paragraph')
    for child in list(body):
        body.remove(child)
    relname = "word/_rels/document.xml.rels"
    rel = E.fromstring(parts[relname])

    def run_properties(role, italic=False, code=False, linked=False):
        rp = node("rPr")
        font = "Consolas" if code else "Times New Roman"
        rp.append(node("rFonts", ascii=font, hAnsi=font, cs=font))
        if role in ("title", "heading"):
            rp.append(node("b"))
        if italic:
            rp.append(node("i"))
        rp.append(node("color", val="155DA0" if linked else "000000"))
        rp.append(node("sz", val=34 if role == "title" else 22 if role == "heading" else 20))
        if linked:
            rp.append(node("u", val="single"))
        rp.append(node("lang", val="en-US"))
        return rp

    def text_run(value, role, parent, **style):
        run = node("r")
        run.append(run_properties(role, **style))
        for j, line in enumerate(typography(value).split("\n")):
            if j:
                run.append(node("br"))
            t = node("t")
            t.set(XML_SPACE, "preserve")
            t.text = line
            run.append(t)
        parent.append(run)

    def paragraph(text, role="body", style=None, keep_next=False):
        p = node("p")
        pattern = patterns.get(role, patterns["body"])
        pr = deepcopy(pattern.find(w("pPr")))
        if pr is None:
            pr = node("pPr")
        for name in ("numPr", "sectPr", "pageBreakBefore"):
            for c in pr.findall(w(name)):
                pr.remove(c)
        if role in ("title", "heading") or keep_next:
            for old in pr.findall(w("keepNext")):
                pr.remove(old)
            pr.append(node("keepNext"))
        if role == "caption":
            if not keep_next:
                for old in pr.findall(w("keepNext")):
                    pr.remove(old)
            if pr.find(w("keepLines")) is None:
                pr.append(node("keepLines"))
        if style:
            for old in pr.findall(w("pStyle")):
                pr.remove(old)
            pr.insert(0, node("pStyle", val=style))
        if role in ("caption", "reference"):
            for old in pr.findall(w("spacing")):pr.remove(old)
            after = args.reference_after_twips if role == "reference" else 60
            pr.append(node("spacing",before=0,after=after,line=240,lineRule="auto"))
        if role in ("body", "abstract", "reference"):
            for old in pr.findall(w("keepNext")):pr.remove(old)
        pr.append(node("widowControl"))
        p.append(pr)
        at = 0
        for match in INLINE.finditer(text):
            if match.start() > at:
                text_run(text[at:match.start()], role, p)
            if match.group(1):
                rid = "rIdArticleView" + str(len(rel) + 1)
                E.SubElement(rel, "{" + RELNS + "}Relationship", Id=rid, Type=R + "/hyperlink", Target=match.group(2), TargetMode="External")
                link = node("hyperlink")
                link.set("{" + R + "}id", rid)
                link.set(w("history"), "1")
                text_run(match.group(1), role, link, linked=True)
                p.append(link)
            elif match.group(3):
                text_run(match.group(3), role, p, code=True)
            elif match.group(5):
                p.append(inline_equation(match.group(5)))
            else:
                text_run(match.group(4), role, p, italic=True)
            at = match.end()
        if at < len(text) or not text:
            text_run(text[at:], role, p)
        return p

    def table(rows, widths):
        columns = len(rows[0])
        if widths is None:
            widths = [9360 // columns] * columns
        if len(widths) != columns or sum(widths) > 9360:
            raise ValueError("Table widths must match the columns and fit 9360 twips")
        t = node("tbl")
        prop = node("tblPr")
        prop.append(node("tblW", w=sum(widths), type="dxa"))
        prop.append(node("tblLayout", type="fixed"))
        borders = node("tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            borders.append(node(edge, val="single" if edge in ("top", "bottom") else "nil", sz=8, color="000000"))
        prop.append(borders)
        margins = node("tblCellMar")
        for edge in ("top", "bottom"):
            margins.append(node(edge, w=70, type="dxa"))
        for edge in ("left", "right"):
            margins.append(node(edge, w=100, type="dxa"))
        prop.append(margins)
        t.append(prop)
        grid = node("tblGrid")
        for width in widths:
            grid.append(node("gridCol", w=width))
        t.append(grid)
        number = re.compile(r"[\d ,./ +−–-]+")
        numeric = [all(number.fullmatch(plain(row[j])) for row in rows[1:]) for j in range(columns)]
        for i, row in enumerate(rows):
            tr = node("tr")
            pr = node("trPr")
            pr.append(node("cantSplit"))
            if i == 0:
                pr.append(node("tblHeader"))
            tr.append(pr)
            for j, cell in enumerate(row):
                tc = node("tc")
                cp = node("tcPr")
                cp.append(node("tcW", w=widths[j], type="dxa"))
                cp.append(node("vAlign", val="center"))
                if i == 0:
                    cb = node("tcBorders")
                    cb.append(node("bottom", val="single", sz=6, color="000000"))
                    cp.append(cb)
                tc.append(cp)
                p = paragraph(cell, "body")
                pp = p.find(w("pPr"))
                if i == 0 or (len(rows) <= 4 and i < len(rows) - 1):
                    pp.append(node("keepNext"))
                for old in pp.findall(w("spacing")):
                    pp.remove(old)
                pp.append(node("spacing", before=70, after=70, line=240, lineRule="auto"))
                if numeric[j]:
                    pp.append(node("jc", val="right"))
                if i == 0:
                    for run in p.iter(w("r")):
                        run.find(w("rPr")).insert(1, node("b"))
                tc.append(p)
                tr.append(tc)
            t.append(tr)
        return t

    pic_ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}

    def picture(payload, rid, target, name, description, width_emu, docpr_id, svg_payload=None, image_url=None):
        px_w, px_h = struct.unpack(">II", payload[16:24])
        fp = deepcopy(figure_pattern)
        pr = fp.find(w("pPr"))
        if pr is None:
            pr = node("pPr")
            fp.insert(0, pr)
        for tag in ("pageBreakBefore", "keepNext"):
            for old in pr.findall(w(tag)):
                pr.remove(old)
        pr.append(node("keepNext"))
        for old in pr.findall(w("spacing")):pr.remove(old)
        pr.append(node("spacing",before=0,after=args.figure_after_twips,line=240,lineRule="auto"))
        for old in fp.findall(".//" + w("br")):
            if old.get(w("type")) == "page":
                old.getparent().remove(old)
        for old in fp.findall(".//" + w("lastRenderedPageBreak")):
            old.getparent().remove(old)
        for old in fp.findall(".//" + w("t")):
            old.text = ""
        for el in fp.findall(".//a:blip", pic_ns):
            el.set("{" + R + "}embed", rid)
        for el in fp.findall(".//wp:extent", pic_ns) + fp.findall(".//a:xfrm/a:ext", pic_ns):
            el.set("cx", str(width_emu))
            el.set("cy", str(round(width_emu * px_h / px_w)))
        for el in fp.findall(".//wp:docPr", pic_ns):
            el.set("id", str(docpr_id)); el.set("name", name); el.set("descr", description)
        if not image_url or not re.fullmatch(VIEW,image_url):
            raise ValueError('Every displayed picture needs its declared native view link')
        view_rid=rid+'View'
        E.SubElement(rel,'{'+RELNS+'}Relationship',Id=view_rid,Type=R+'/hyperlink',Target=image_url,TargetMode='External')
        click_parents=fp.findall('.//wp:docPr',pic_ns)+fp.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/picture}cNvPr')
        if len(click_parents)!=2:raise ValueError('Expected both picture hyperlink anchors')
        for parent in click_parents:
            for previous in list(parent):
                if previous.tag=='{'+pic_ns['a']+'}hlinkClick':parent.remove(previous)
            E.SubElement(parent,'{'+pic_ns['a']+'}hlinkClick',attrib={'{'+R+'}id':view_rid})
        parts["word/" + target] = payload
        E.SubElement(rel, "{" + RELNS + "}Relationship", Id=rid, Type=R + "/image", Target=target)
        if svg_payload is not None:
            svg_target=target.rsplit('.',1)[0]+'.svg';svg_rid=rid+'SVG'
            parts['word/'+svg_target]=svg_payload
            E.SubElement(rel,'{'+RELNS+'}Relationship',Id=svg_rid,Type=R+'/image',Target=svg_target)
            for blip in fp.findall('.//a:blip',pic_ns):
                extensions=blip.find('{'+pic_ns['a']+'}extLst')
                if extensions is None:extensions=E.SubElement(blip,'{'+pic_ns['a']+'}extLst')
                extension=E.SubElement(extensions,'{'+pic_ns['a']+'}ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
                svg_ns='http://schemas.microsoft.com/office/drawing/2016/SVG/main'
                E.SubElement(extension,'{'+svg_ns+'}svgBlip',attrib={'{'+R+'}embed':svg_rid},nsmap={'asvg':svg_ns})
        return fp

    def verified(path_text, digest):
        path = (ROOT / path_text).resolve()
        if not path.is_relative_to(FIGURE_DIR.resolve()):
            raise ValueError("Figure escapes paper/manuscript/figures: " + path_text)
        payload = path.read_bytes()
        if sha(payload) != digest:
            raise ValueError("Figure bytes differ from the declared hash: " + path_text)
        return payload

    figure_nodes = {}
    for i, spec in enumerate(specs, 1):
        label = spec["label"]
        caption = captions[label]
        payload = verified(spec["path"], spec["sha256"])
        width = int(spec.get("width_emu", 5943600))
        if not spec.get("panels"):
            nodes = [picture(payload, f"rIdSequenceFigure{i}", f"media/sequence_figure_{i}.png", f"{args.prefix}{label}", plain(caption)[:250], width, 100 + i, image_url=next((m.group(2) for m in INLINE.finditer(caption) if m.group(1)),None))]
        else:
            # The composite is provenance; native panels are embedded individually
            # so every map/timeline has a working link immediately below it.
            panel_count=len(spec["panels"])
            columns=int(spec.get("panel_columns",2))
            if panel_count not in (2,4,6) or columns not in (1,2) or panel_count%columns:
                raise ValueError("A panel figure requires two/four/six panels and one/two complete columns")
            row_count=panel_count//columns
            letters=[panel.get("letter",chr(65+j)) for j,panel in enumerate(spec["panels"])]
            if set(letters)!={chr(65+j) for j in range(panel_count)} or len(set(letters))!=panel_count:
                raise ValueError("Panel letters must be unique A through the declared panel count")
            # Two panels per row, preserving the original pixels and immediate links.
            layout=node("tbl");prop=node("tblPr")
            prop.append(node("tblCaption",val=f"{args.prefix}{label} panels"))
            prop.append(node("tblW",w=9360,type="dxa"));prop.append(node("tblLayout",type="fixed"))
            borders=node("tblBorders")
            for edge in ("top","bottom","left","right","insideH","insideV"):borders.append(node(edge,val="nil"))
            prop.append(borders);layout.append(prop)
            grid=node("tblGrid")
            for column in range(columns):grid.append(node("gridCol",w=9360//columns))
            layout.append(grid)
            for row_index in range(row_count):
                row=node("tr");rp=node("trPr");rp.append(node("cantSplit"));row.append(rp)
                for column in range(columns):
                    j=row_index*columns+column;panel=spec["panels"][j];panel_letter=letters[j]
                    if not re.fullmatch(VIEW,panel["url"]):raise ValueError("Invalid panel link")
                    cell=node("tc");cp=node("tcPr");cp.append(node("tcW",w=9360//columns,type="dxa"));cell.append(cp)
                    title=paragraph(panel["label"],"caption",keep_next=True)
                    panel_width=int(panel.get('width_emu',5943600 if columns==1 else 2857500))
                    svg_payload=verified(panel['svg_path'],panel['svg_sha256']) if panel.get('svg_path') else None
                    pic=picture(verified(panel["path"],panel["sha256"]),f"rIdSequenceFigure{i}Panel{j+1}",f"media/sequence_figure_{i}_panel_{j+1}.png",f"Figure {label}{panel_letter}",panel["label"],panel_width,1000+i*10+j,svg_payload,panel["url"])
                    link_label=panel.get("link_label",f"Open interactive panel {label}{panel_letter}")
                    link=paragraph(f'[{link_label}]({panel["url"]})',"caption")
                    for item in (title,pic,link):
                        pp=item.find(w("pPr"))
                        for old in pp.findall(w("spacing")):pp.remove(old)
                        pp.append(node("spacing",before=0,after=50,line=240,lineRule="auto"))
                        if item is link and row_index==row_count-1 and pp.find(w("keepNext")) is None:pp.append(node("keepNext"))
                        cell.append(item)
                    row.append(cell)
                layout.append(row)
            nodes=[layout]
        figure_nodes[label] = nodes + [paragraph(caption, "caption")]

    placements = []
    section = None
    for index, (kind, value) in enumerate(content):
        first_new_node = len(body)
        following = content[index + 1][0] if index + 1 < len(content) else None
        if kind == "figure":
            for item in figure_nodes[value]:
                body.append(item)
            placements.append({"figure": value, "content_block_index": index})
        elif kind == "equation":
            body.append(equation_paragraph(equation_pattern, value))
        elif kind == "table":
            rows, widths = value
            body.append(table(rows, widths))
        elif kind == "h1":
            body.append(paragraph(value, "title", "Title"))
        elif kind in ("h2", "h3"):
            if kind == "h2":
                section = value
            body.append(paragraph(value, "heading"))
        elif re.match(r"Table \d+\.", value) and following == "table":
            body.append(paragraph(value, "caption", keep_next=True))
        else:
            body.append(paragraph(value, "abstract" if section == "Abstract" and not value.startswith("Keywords:") else "reference" if section == "References" else "body"))
        # Separate the next element from the table's bottom rule without adding
        # an empty paragraph or changing the body's type size and line spacing.
        if index > 0 and content[index - 1][0] == "table":
            first = body[first_new_node]
            if first.tag == w("p"):
                properties = first.find(w("pPr"))
                spacing = properties.find(w("spacing"))
                if spacing is None:
                    spacing = node("spacing")
                    properties.append(spacing)
                spacing.set(w("before"), "120")
    equation_report = validate_document_math(doc, [match.group(1) for match in INLINE_MATH.finditer(source_bytes.decode('utf-8'))])
    parts[relname] = E.tostring(rel, xml_declaration=True, encoding="UTF-8", standalone=True)
    body.append(final_sect)
    parts["word/document.xml"] = E.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    core = E.fromstring(parts["docProps/core.xml"])
    core_ns = {"dc": "http://purl.org/dc/elements/1.1/", "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"}
    if metadata['title'] != plain(parsed[0][1]):raise ValueError('Closed metadata title differs from source')
    for tag, value in (("dc:creator", metadata['creator']), ("dc:title", metadata['title']), ("cp:lastModifiedBy", metadata['last_modified_by'])):
        el = core.find(tag, core_ns)
        if el is None:
            ns, name = tag.split(":")
            el = E.SubElement(core, "{" + core_ns[ns] + "}" + name)
        el.text = value
    parts["docProps/core.xml"] = E.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)
    modified = {"word/document.xml", "docProps/core.xml", relname}
    native_svg_count=sum(bool(panel.get('svg_path')) for spec in specs for panel in spec.get('panels',[]))
    if native_svg_count:
        content_types=E.fromstring(parts['[Content_Types].xml'])
        ct_ns='http://schemas.openxmlformats.org/package/2006/content-types'
        if any(e.get('Extension')=='svg' for e in content_types):raise ValueError('Unexpected pre-existing SVG content-type')
        E.SubElement(content_types,'{'+ct_ns+'}Default',Extension='svg',ContentType='image/svg+xml')
        parts['[Content_Types].xml']=E.tostring(content_types,xml_declaration=True,encoding='UTF-8',standalone=True)
        modified.add('[Content_Types].xml')
    for name in list(parts):
        if name.startswith("word/footer") and name.endswith(".xml"):
            footer = E.fromstring(parts[name])
            changed = False
            for text_node in footer.findall(".//" + w("t")):
                if text_node.text and "short author name" in text_node.text:
                    text_node.text = ""
                    changed = True
            if changed:
                parts[name] = E.tostring(footer, xml_declaration=True, encoding="UTF-8", standalone=True)
                modified.add(name)
    template_names = set(ZipFile(TEMPLATE).namelist())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() or (ROOT / args.report).exists():
        raise FileExistsError('Never overwrite an existing manuscript build or build receipt; use a new layout directory')
    pending = out_path.with_suffix(".building.docx")
    if pending.exists():
        raise FileExistsError('A previous pending build must be inspected separately')
    with ZipFile(pending, "w", ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    pending.replace(out_path)
    with ZipFile(TEMPLATE) as ref, ZipFile(out_path) as final:
        preserved = [n for n in ref.namelist() if n not in modified]
        if not all(ref.read(n) == final.read(n) for n in preserved):
            raise ValueError("A preserve-only template part changed")

    text = "\n".join(line for line in source_bytes.decode("utf-8").splitlines() if not MARKER.search(line))
    report = {"sealed_contract": args.contract, "sealed_contract_sha256": sha(contract_path.read_bytes()), "source": args.source, "source_sha256": sha(source_bytes), "template_sha256": sha(raw), "output": args.out,
              "output_sha256": sha(out_path.read_bytes()), "preserved_part_count": len(preserved), "modified_parts": sorted(modified),
              "added_media": sorted(n for n in parts if n not in template_names), "figure_count": len(specs),
              "figures": [{"label": s["label"], "path": s["path"], "sha256": s["sha256"], "panels": len(s.get("panels", []))} for s in specs],
              "layout_spacing_twips": {"reference_after":args.reference_after_twips,"single_image_after":args.figure_after_twips},
              "native_equations": equation_report,
              "figure_placements": placements, "render_status": "not rendered by this script; native Word PDF export and page review required"}
    if "## Abstract" in text and "## 1." in text:
        abstract = text.split("## Abstract", 1)[1].split("## 1.", 1)[0].split("Keywords:")[0]
        main = text.split("## 1.", 1)[1].split("## References", 1)[0]
        lines = [l for l in main.splitlines() if l.strip()]
        table_lines = [l for l in lines if l.strip().startswith("|")]
        table_captions = [l for l in lines if re.match(r"Table \d+\.", l.strip())]
        prose = [l for l in lines if l not in table_lines and l not in table_captions]
        count = lambda items: sum(len(plain(re.sub(r"[|#]", " ", l)).split()) for l in items)
        report.update(abstract_words=len(plain(abstract).split()), main_words_prose_and_headings=count(prose),
                      main_words_in_tables=count([l for l in table_lines if not re.fullmatch(r"[|:\- ]+", l.strip())]),
                      table_caption_words_excluded=count(table_captions),
                      word_limit_note="Guide: 5500 words maximum for an original research article; abstract, keywords, highlights, references and captions excluded.")
    (ROOT / args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("figures", "figure_placements", "added_media")}, indent=1, ensure_ascii=True))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--figures", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--reference-after-twips", type=int, choices=(0,20,40,60), default=20)
    parser.add_argument("--figure-after-twips", type=int, choices=(0,20,40,60), default=20)
    parser.add_argument("--prefix", default="Figure ")
    build(parser.parse_args())
