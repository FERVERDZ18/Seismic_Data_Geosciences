"""Native editable OMML cloned from the retained C&G equation paragraph pattern.

The only supported tree vocabulary is explicitly specified in equations.json.
This module never writes a document; the sealed manuscript builder owns output.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import re
from lxml import etree as E

M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
DEFINITIONS = Path(__file__).with_name('equations.json')
NS = {'m':M,'w':W}
INLINE_MATH = re.compile(r'\{\{math:([a-z][a-z0-9-]*)\}\}')


def m(tag, **attrs):
    el = E.Element('{'+M+'}'+tag)
    for key,value in attrs.items():el.set('{'+M+'}'+key,str(value))
    return el


def w(tag, **attrs):
    el = E.Element('{'+W+'}'+tag)
    for key,value in attrs.items():el.set('{'+W+'}'+key,str(value))
    return el


def definitions():
    spec = json.loads(DEFINITIONS.read_text(encoding='utf-8'))
    if spec['schema_version'] != 1 or spec['ordered_ids'] != ['metric','bound']:
        raise ValueError('Unknown equation contract')
    if spec['base_half_points'] != 20 or spec['font'] != 'Cambria Math':
        raise ValueError('Native mathematics must retain its explicit 10-point base')
    return spec


def tree(ast, spec):
    """Render a small declarative mathematical AST into native Office Math XML."""
    kind,*args = ast
    if kind == 'run':
        if len(args) not in (1,2):raise ValueError('Invalid math run')
        run = m('r');pr=m('rPr');pr.append(m('sty',val='p' if len(args)==2 and args[1]=='plain' else 'i'));run.append(pr)
        rp=w('rPr');rp.append(w('rFonts',ascii=spec['font'],hAnsi=spec['font'],cs=spec['font']))
        rp.append(w('sz',val=spec['base_half_points']));rp.append(w('szCs',val=spec['base_half_points']));run.append(rp)
        text=m('t');text.set('{http://www.w3.org/XML/1998/namespace}space','preserve');text.text=args[0];run.append(text)
        return [run]
    if kind == 'seq':
        return [el for child in args for el in tree(child,spec)]
    slots = {'sub':('sSub',('e','sub')), 'sup':('sSup',('e','sup')),
             'subsup':('sSubSup',('e','sub','sup')), 'frac':('f',('num','den'))}
    if kind in slots:
        tag,names=slots[kind]
        if len(args)!=len(names):raise ValueError('Invalid native math slot count')
        result=m(tag)
        for name,child in zip(names,args):
            wrapper=m(name);wrapper.extend(tree(child,spec));result.append(wrapper)
        return [result]
    if kind == 'delim':
        if len(args)<3:raise ValueError('Delimiter needs content')
        left,right,*children=args
        result=m('d');pr=m('dPr');pr.extend([m('begChr',val=left),m('endChr',val=right),m('grow',val=1)]);result.append(pr)
        content=m('e')
        for child in children:content.extend(tree(child,spec))
        result.append(content);return [result]
    raise ValueError('Unknown native math operation: '+kind)


def equation_paragraph(template_pattern, equation_id):
    spec=definitions()
    if equation_id not in spec['equations']:raise ValueError('Unknown equation id')
    paragraph=deepcopy(template_pattern)
    # The scientific paragraph is cloned; old paragraph identity is not content.
    for name in list(paragraph.attrib):
        if E.QName(name).localname in ('paraId','textId'):del paragraph.attrib[name]
    for child in list(paragraph):
        if child.tag != '{'+W+'}pPr':paragraph.remove(child)
    pr=paragraph.find('w:pPr',NS)
    if pr is None:raise ValueError('The retained native equation paragraph has no properties')
    for name in ('numPr','sectPr','pageBreakBefore','keepNext','jc'):
        for old in pr.findall('w:'+name,NS):pr.remove(old)
    pr.append(w('jc',val='center'));pr.append(w('keepLines'));pr.append(w('widowControl'))
    # CT_PPr order is significant. Reorder only this newly cloned equation's
    # paragraph properties; no retained package/style part is rewritten.
    ppr_order=('pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl',
               'numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens',
               'kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE',
               'autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind',
               'contextualSpacing','mirrorIndents','suppressOverlap','jc',
               'textDirection','textAlignment','textboxTightWrap','outlineLvl',
               'divId','cnfStyle','rPr','sectPr','pPrChange')
    if any(E.QName(child).localname not in ppr_order for child in pr):
        raise ValueError('Unrecognized retained native equation paragraph property')
    pr[:]=sorted(pr,key=lambda child:ppr_order.index(E.QName(child).localname))
    math_para=m('oMathPara');math_pr=m('oMathParaPr');math_pr.append(m('jc',val='center'));math_para.append(math_pr)
    math=m('oMath')
    for ast in spec['equations'][equation_id]['ast']:math.extend(tree(ast,spec))
    math_para.append(math);paragraph.append(math_para)
    return paragraph


def inline_equation(equation_id):
    spec=definitions()
    item=spec.get('inline_equations',{}).get(equation_id)
    if item is None:raise ValueError('Unknown inline mathematical declaration: '+equation_id)
    math=m('oMath')
    for ast in item['ast']:math.extend(tree(ast,spec))
    return math


def inline_plain(equation_id):
    """The exact text-node sequence used only for structural paragraph matching."""
    return ''.join(el.text or '' for el in inline_equation(equation_id).iter('{'+M+'}t'))


def add_inline_aliases(text):
    spec=definitions();items=spec.get('inline_equations',{})
    # Long alternatives win over symbols contained within a larger expression.
    patterns={item['literal']:key for key,item in items.items()}
    expression=re.compile('|'.join((r'(?<![\w])'+re.escape(literal)+r'(?![\w])')
                                   if literal in ('ti','ηij') else re.escape(literal)
                                   for literal in sorted(patterns,key=len,reverse=True)))
    aliased=expression.sub(lambda match:'{{math:'+patterns[match.group()]+'}}',text)
    restored=INLINE_MATH.sub(lambda match:items[match.group(1)]['literal'],aliased)
    if restored!=text:raise ValueError('Inline math replacement is not losslessly reversible')
    return aliased


def math_signature(math):
    """Namespace-independent semantic signature, ignoring property serialization."""
    tag=E.QName(math.tag).localname
    if tag in ('rPr','ctrlPr','oMathParaPr'):return None
    children=[s for c in math if (s:=math_signature(c)) is not None]
    attrs=tuple(sorted((E.QName(k).localname,v) for k,v in math.attrib.items()))
    return (tag,math.text or '',attrs,tuple(children))


def validate_document_math(document, inline_ids=None):
    spec=definitions();actual=document.findall('.//m:oMathPara',NS)
    if len(actual)!=len(spec['ordered_ids']):raise ValueError('Exactly two editable display equations are required')
    for equation_id,element in zip(spec['ordered_ids'],actual):
        expected=m('oMath')
        for ast in spec['equations'][equation_id]['ast']:expected.extend(tree(ast,spec))
        if math_signature(element.find('m:oMath',NS))!=math_signature(expected):
            raise ValueError('Native equation semantics differ from maintained definition: '+equation_id)
        for run in element.findall('.//m:r',NS):
            rp=run.find('w:rPr',NS)
            if rp is None or rp.find('w:sz',NS).get('{'+W+'}val')!='20':
                raise ValueError('An equation lacks the explicit 10-point base')
            if rp.find('w:rFonts',NS).get('{'+W+'}ascii')!='Cambria Math':
                raise ValueError('Unexpected native mathematical font')
    inline_ids=[] if inline_ids is None else inline_ids
    inline_actual=document.findall('.//w:p/m:oMath',NS)
    if len(inline_actual)!=len(inline_ids):raise ValueError('Inline native mathematics count differs from maintained source')
    for key,actual_math in zip(inline_ids,inline_actual):
        if math_signature(actual_math)!=math_signature(inline_equation(key)):
            raise ValueError('Inline native mathematics differs from its source declaration: '+key)
        for run in actual_math.findall('.//m:r',NS):
            rp=run.find('w:rPr',NS)
            if rp is None or rp.find('w:sz',NS).get('{'+W+'}val')!='20' or rp.find('w:rFonts',NS).get('{'+W+'}ascii')!='Cambria Math':
                raise ValueError('Inline mathematics does not use the explicit 10-point mathematical base')
    return {'count':len(actual),'ordered_ids':spec['ordered_ids'],
            'linear_equations':[spec['equations'][key]['linear'] for key in spec['ordered_ids']],
            'inline_count':len(inline_actual),'inline_ids':inline_ids,
            'base_points':10,'font':'Cambria Math',
            'superscripts':'native Office Math, conventional script reduction'}
