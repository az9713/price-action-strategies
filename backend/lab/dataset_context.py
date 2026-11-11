"""Minimal immutable dataset identity; never price reads or arbitrary metadata export."""
import json
import re
from .config import identity
from .data import DataError

FIELDS={'policy_version','dataset_id','dataset_manifest_hash','input_kind','source','symbols'}
CSV_COLUMNS=['input_kind','data_source','symbols','dataset_manifest_hash']

def validate_context(value,*,manifest=None):
    def text(v,limit):
        return isinstance(v,str) and 0<len(v)<=limit and not any(ord(c)<32 or ord(c)==127 for c in v)
    valid=isinstance(value,dict) and set(value)==FIELDS
    if valid:
        symbols=value['symbols']
        valid=(type(value['policy_version']) is int and value['policy_version']==1 and
            isinstance(value['dataset_id'],str) and re.fullmatch('[a-f0-9]{24}',value['dataset_id']) is not None and
            isinstance(value['dataset_manifest_hash'],str) and re.fullmatch('[a-f0-9]{64}',value['dataset_manifest_hash']) is not None and
            text(value['input_kind'],128) and text(value['source'],240) and isinstance(symbols,list) and len(symbols)>0 and
            all(isinstance(s,str) and re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',s) for s in symbols) and
            symbols==sorted(set(symbols)))
    if not valid:raise DataError('Dataset context is malformed or has unsupported fields.')
    if manifest is not None and value!=freeze_context(manifest):raise DataError('Dataset context differs from the verified immutable manifest.')
    return {**value,'symbols':list(value['symbols'])}

def freeze_context(manifest):
    metadata=manifest.get('metadata',{})
    value=dict(policy_version=1,dataset_id=manifest['id'],dataset_manifest_hash=identity(manifest),
        input_kind=metadata.get('input_kind','unknown'),source=metadata.get('provider',metadata.get('source','Not recorded')),
        symbols=sorted(manifest['quality']['symbols']))
    return validate_context(value)

def csv_safe(value):
    return "'"+value if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')) else value

def csv_context(value):
    if value is None:return dict.fromkeys(CSV_COLUMNS,'not_recorded')
    c=validate_context(value)
    return {k:csv_safe(v) for k,v in dict(input_kind=c['input_kind'],data_source=c['source'],
        symbols=json.dumps(c['symbols'],separators=(',',':')),dataset_manifest_hash=c['dataset_manifest_hash']).items()}
