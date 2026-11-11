"""Second saved-output reader. No builder helpers or numerical engine imports.

This verifies provenance/formatting, not the scientific truth of saved results.
JSON is decoded separately with Decimal; lookup and formatting are independent.
"""
from decimal import Decimal,InvalidOperation,ROUND_HALF_EVEN,localcontext
import hashlib
import json
import re


class PresentationAuditError(ValueError):pass


def independent_format(value,style):
    if style=='symbol_list':
        if type(value) is not list or not value:raise PresentationAuditError('Invalid instrument list.')
        rendered=[]
        for symbol in value:
            if type(symbol) is not str or not re.fullmatch('[A-Z][A-Z0-9.\\-]{0,14}',symbol):raise PresentationAuditError('Invalid instrument symbol.')
            rendered.append(symbol)
        if value!=sorted(set(value)):raise PresentationAuditError('Instrument list is not canonical.')
        if len(rendered)>20:return format(len(rendered),',')+' instruments; see indexed pages'
        return ', '.join(rendered)
    if style=='text':
        if not isinstance(value,str):raise PresentationAuditError('Text provenance requires a string.')
        return value
    if style=='boolean':
        if type(value) is not bool:raise PresentationAuditError('Boolean provenance requires a boolean.')
        return {True:'Enabled',False:'Disabled'}[value]
    if style not in {'currency','percent','number','integer','exact_number'}:raise PresentationAuditError('Unknown display format.')
    if value is None:return 'Undefined'
    if isinstance(value,bool) or not isinstance(value,(int,float,Decimal)):
        raise PresentationAuditError('Numeric provenance requires a finite number.')
    try:
        number=Decimal(str(value))
        if not number.is_finite():raise PresentationAuditError('Nonfinite provenance value.')
        with localcontext() as context:
            context.prec=400
            if style=='exact_number':
                return format(number.normalize(),'f') if number else '0'
            if style=='integer':
                if number!=number.to_integral_value():raise PresentationAuditError('Fractional count.')
                return format(number,',.0f')
            if style=='percent':number=number*100
            if style not in {'currency','percent','number'}:raise PresentationAuditError('Unknown display format.')
            rounded=number.quantize(Decimal('0.01'),rounding=ROUND_HALF_EVEN)
            sign='-' if rounded<0 else ''
            digits=format(abs(rounded),',.2f')
            return sign+('$' if style=='currency' else '')+digits+('%' if style=='percent' else '')
    except (InvalidOperation,ValueError,OverflowError) as exc:
        raise PresentationAuditError('Invalid display number.') from exc


def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise PresentationAuditError('Duplicate source field.')
        result[key]=value
    return result


def _resolve(document,path):
    node=document
    if not isinstance(path,list) or not path:raise PresentationAuditError('Missing provenance path.')
    try:
        for step in path:
            if isinstance(node,list):
                if type(step) is not int or not 0<=step<len(node):raise PresentationAuditError('Invalid source row.')
            elif isinstance(node,dict):
                if not isinstance(step,str):raise PresentationAuditError('Invalid source field.')
            else:raise PresentationAuditError('Invalid source traversal.')
            node=node[step]
    except (KeyError,IndexError,TypeError) as exc:raise PresentationAuditError('Missing source cell.') from exc
    return node


def audit_deck(sources,deck):
    try:
        if deck.get('version')!=1 or not isinstance(deck['facts'],dict) or not deck['pages']:
            raise PresentationAuditError('Invalid presentation manifest.')
        source_meta=deck['sources']
        if len(source_meta)!=len(sources) or {s['name'] for s in source_meta}!=set(sources):
            raise PresentationAuditError('Source inventory differs.')
        documents={}
        for entry in source_meta:
            raw=sources[entry['name']]
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise PresentationAuditError('Source fingerprint differs.')
            documents[entry['name']]=json.loads(raw,parse_float=Decimal,parse_int=Decimal,object_pairs_hook=_pairs,
                parse_constant=lambda _:(_ for _ in ()).throw(PresentationAuditError('Nonfinite source.')))
            for field in ['core_hash','dataset_manifest_hash']:
                if field in entry and entry[field]!=documents[entry['name']].get(field):
                    raise PresentationAuditError('Source subject identity differs.')
        used=set()
        def inspect(value,key=''):
            if isinstance(value,dict):
                if set(value)=={'fact'}:
                    if value['fact'] not in deck['facts']:raise PresentationAuditError('Unattributed presentation value.')
                    used.add(value['fact']);return
                for k,v in value.items():inspect(v,k)
            elif isinstance(value,list):
                for v in value:inspect(v,key)
            elif isinstance(value,str):
                # Research text must be either fixed digit-free copy or a fact.
                if re.search(r'\d',value):raise PresentationAuditError('A displayed digit has no source.')
                if '\u2014' in value:raise PresentationAuditError('Em dash in presentation copy.')
            elif isinstance(value,(int,float)):
                raise PresentationAuditError('A presentation number has no source.')
        for page in deck['pages']:
            if len(page.get('stats',[]))>2:raise PresentationAuditError('Too many large statistics.')
            inspect(page)
        if used!=set(deck['facts']):raise PresentationAuditError('Unused or missing provenance facts.')
        for fact in deck['facts'].values():
            value=_resolve(documents[fact['source']],fact['path'])
            shown=fact['value']
            if isinstance(value,Decimal):
                if type(shown) not in (int,float) or Decimal(str(shown))!=value:raise PresentationAuditError('Source numeric value differs.')
            elif type(value)!=type(shown) or value!=shown:raise PresentationAuditError('Source value differs.')
            if fact['text']!=independent_format(value,fact['format']):raise PresentationAuditError('Source display text differs.')
            expected_row=next((x for x in reversed(fact['path']) if type(x) is int),None)
            if type(fact['row']) is not type(expected_row) or fact['row']!=expected_row or type(fact['column']) is not type(fact['path'][-1]) or fact['column']!=fact['path'][-1]:
                raise PresentationAuditError('Source row or column differs.')
        return dict(facts_checked=len(used),sources_checked=len(documents),pages_checked=len(deck['pages']),
            reader='separate Decimal JSON reader, independent path traversal and half-even formatter',
            scope='Saved-output provenance and formatting; not independent certification of the underlying research.')
    except PresentationAuditError:raise
    except (KeyError,TypeError,ValueError,RecursionError) as exc:
        raise PresentationAuditError('Malformed presentation provenance.') from exc
