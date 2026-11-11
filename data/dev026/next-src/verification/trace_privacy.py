"""Deterministic derived Playwright10 evidence; never overwrite raw inputs.

Recognized credential contexts and discovered long-value propagation are covered.
Unknown secrets in arbitrary user media cannot be inferred by this policy.
"""
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,quote,quote_plus
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile

REDACTED='[REDACTED]'
MARKER=b'PA_SANITIZED_TRACE_V1'
MANIFEST='pa-redaction.json'
MAX_ARCHIVE_BYTES=256*1024*1024
MAX_MEMBER_BYTES=64*1024*1024
MAX_MEMBERS=20000
MAX_CAPTURE_BYTES=1024*1024*1024
MAX_CAPTURE_FILES=40000
HEADERS={'authorization','proxyauthorization','xlabtoken','xapikey','apikey','apcaapikeyid','apcaapisecretkey','cookie','setcookie'}
FIELDS={'token','accesstoken','refreshtoken','idtoken','csrftoken','xsrftoken','password','passwd','secret','clientsecret','secretkey','apikey','apcaapikeyid','apcaapisecretkey','alpacaapikey','alpacasecretkey'}
AUTH=HEADERS|FIELDS
TEXT={'.json','.trace','.network','.stacks','.txt','.log','.md','.xml','.html','.css','.js','.ts','.csv'}
LOG_HEADER=re.compile(r'(?im)^.*?\b(?:x-lab-token|authorization|proxy-authorization|x-api-key|apca-api-key-id|apca-api-secret-key|cookie|set-cookie)\s*:\s*([^\r\n]+).*$')
REPR_FIELD=re.compile(r'''(?i)(?P<prefix>\b(?:x[-_]lab[-_]token|authorization|proxy[-_]authorization|x[-_]api[-_]key|apca[-_]api[-_](?:key[-_]id|secret[-_]key)|alpaca[-_](?:api[-_]key|secret[-_]key)|api[-_]?key|access[-_]?token|refresh[-_]?token|csrf[-_]?token|token|password|passwd|secret)["']?\s*[:=]\s*)(?P<q>["'])(?P<value>[^"'\r\n]*)(?P=q)''')
URL=re.compile(r'https?://[^\s\"\'<>]+')

class PrivacyError(ValueError):pass
def norm(value):return re.sub('[^a-z0-9]','',str(value).lower())
def digest(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()
def _bad(*args):raise PrivacyError('Malformed or unsupported structured trace data.')
def _pairs(values):
    result={}
    for key,value in values:
        if key in result:_bad()
        result[key]=value
    return result
def loads(text):
    try:return json.loads(text,object_pairs_hook=_pairs,parse_constant=_bad)
    except (ValueError,TypeError,RecursionError):_bad()
def dump(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def text_of(name,raw):
    if b'\x00' in raw:return None
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:return None
    return text if Path(name).suffix.lower() in TEXT or not Path(name).suffix else None

def parsed(name,raw):
    text=text_of(name,raw)
    if text is None:return None,None
    if name.endswith(('.trace','.network')):
        values=[loads(line) for line in text.splitlines() if line.strip()]
        if not all(isinstance(v,dict) for v in values):_bad()
        return 'lines',values
    if name.endswith(('.json','.stacks')):return 'json',loads(text)
    return 'text',text

def read_archive(path):
    path=Path(path)
    if path.name.startswith('.env') or path.stat().st_size>MAX_ARCHIVE_BYTES*2:raise PrivacyError('Unsafe or oversized trace input.')
    try:
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist()
            if len(infos)>MAX_MEMBERS or sum(i.file_size for i in infos)>MAX_ARCHIVE_BYTES:raise PrivacyError('Trace exceeds declared archive bounds.')
            names=set();members={}
            for info in infos:
                name=info.filename;parts=PurePosixPath(name).parts
                if (not parts or name.startswith('/') or '\\' in name or '..' in parts or re.match(r'^[A-Za-z]:',name) or '\x00' in name or any(p.startswith('.env') for p in parts)
                    or name in names or info.flag_bits&1 or (info.external_attr>>16)&0o170000==0o120000 or info.file_size>MAX_MEMBER_BYTES):
                    raise PrivacyError('Unsafe, duplicate, encrypted or oversized trace member.')
                names.add(name)
                if not info.is_dir():members[name]=archive.read(info)
            marker=archive.comment==MARKER
    except (zipfile.BadZipFile,RuntimeError,NotImplementedError,OSError) as error:
        raise PrivacyError('Trace archive cannot be read safely.') from None
    versions=set()
    for name,raw in members.items():
        kind,value=parsed(name,raw)
        if name.endswith('.trace'):
            versions.update(v.get('version') for v in value if v.get('type')=='context-options')
    if versions!={10}:raise PrivacyError('Only the inspected Playwright10 trace schema is supported.')
    if MANIFEST in members and not marker:raise PrivacyError('Unmarked trace contains reserved privacy metadata.')
    return members,marker

class Sanitizer:
    def __init__(self,aliases=()):
        self.aliases=[]
        for before,after in aliases:
            if not before or before==after:continue
            for variant in {str(before),str(before).replace('\\','/'),json.dumps(str(before))[1:-1]}:self.aliases.append((variant,after))
        self.aliases.sort(key=lambda pair:len(pair[0]),reverse=True)
        self.secrets=set();self.counts=dict(headers_removed=0,cookies_removed=0,fields_redacted=0,header_logs_redacted=0,queries_redacted=0,path_occurrences_aliased=0)
    def add(self,value):
        if not isinstance(value,str) or not value or value==REDACTED:return
        self.secrets.add(value)
        if value.lower().startswith(('bearer ','basic ')):self.secrets.add(value.split(' ',1)[1])
    def learn(self,value,parent=''):
        if isinstance(value,dict):
            if norm(value.get('name','')) in AUTH:self.add(value.get('value'))
            if str(value.get('type','')).lower()=='password':self.add(value.get('value'))
            for key,item in value.items():
                if norm(key) in AUTH:self.add(item)
                if parent=='cookies' and key=='value':self.add(item)
                self.learn(item,norm(key))
        elif isinstance(value,list):
            for item in value:self.learn(item,parent)
        elif isinstance(value,str):
            for match in LOG_HEADER.finditer(value):self.add(match.group(1).strip())
            for match in REPR_FIELD.finditer(value):self.add(match.group('value'))
            for match in URL.finditer(value):
                try:
                    for key,item in parse_qsl(urlsplit(match.group()).query,keep_blank_values=True):
                        if norm(key) in AUTH:self.add(item)
                except ValueError:pass
            if value.lstrip().startswith(('{','[')):
                try:nested=loads(value)
                except PrivacyError:return
                self.learn(nested)
    def learn_members(self,members):
        for name,raw in members.items():
            kind,value=parsed(name,raw)
            if kind in {'json','lines'}:self.learn(value)
            elif kind=='text' and Path(name).suffix in {'.log','.txt','.md'}:self.learn(value)
    def variants(self):
        result=set()
        for secret in self.secrets:
            if len(secret)<8:continue
            result.update([secret,json.dumps(secret)[1:-1],quote(secret,safe=''),quote_plus(secret,safe='')])
        return sorted(result,key=len,reverse=True)
    def replace(self,text,logs=False,track=True):
        if logs:
            def field(match):
                if track:self.counts['fields_redacted']+=1
                return match.group('prefix')+match.group('q')+REDACTED+match.group('q')
            text=REPR_FIELD.sub(field,text)
            def header(match):
                if track:self.counts['header_logs_redacted']+=1
                return '[credential header redacted]'
            text=LOG_HEADER.sub(header,text)
        def url(match):
            original=match.group()
            try:
                parts=urlsplit(original);items=parse_qsl(parts.query,keep_blank_values=True)
                if not any(norm(k) in AUTH and v!=REDACTED for k,v in items):return original
                clean=[]
                for k,v in items:
                    if norm(k) in AUTH and v!=REDACTED:
                        v=REDACTED
                        if track:self.counts['queries_redacted']+=1
                    clean.append((k,v))
                return urlunsplit(parts._replace(query=urlencode(clean)))
            except ValueError:return original
        text=URL.sub(url,text)
        for secret in self.variants():text=text.replace(secret,REDACTED)
        for before,after in self.aliases:
            if track:self.counts['path_occurrences_aliased']+=text.count(before)
            text=text.replace(before,after)
        return text
    def clean(self,value,parent=''):
        if isinstance(value,list):
            if parent=='cookies':self.counts['cookies_removed']+=len(value);return []
            output=[]
            for item in value:
                if parent=='headers' and isinstance(item,dict) and norm(item.get('name','')) in AUTH:
                    self.counts['headers_removed']+=1;continue
                output.append(self.clean(item,parent))
            return output
        if isinstance(value,dict):
            output={};named=norm(value.get('name','')) in AUTH;password=str(value.get('type','')).lower()=='password'
            for key,item in value.items():
                if parent=='headers' and norm(key) in AUTH:self.counts['headers_removed']+=1;continue
                if norm(key) in AUTH or key=='value' and (named or password):
                    output[key]=REDACTED
                    if item!=REDACTED:self.counts['fields_redacted']+=1
                else:output[key]=self.clean(item,norm(key))
            return output
        if isinstance(value,str):
            if value.lstrip().startswith(('{','[')):
                try:nested=loads(value)
                except PrivacyError:nested=None
                if nested is not None:
                    changed=self.clean(nested)
                    if changed!=nested:return dump(changed)
            return self.replace(value,logs=True)
        return value
    def bytes(self,name,raw):
        kind,value=parsed(name,raw)
        if kind is None:
            if any(v.encode() in raw for v in self.variants()):raise PrivacyError('Known credential occurs in unsupported binary evidence.')
            return raw
        if kind=='text':clean=self.replace(value,logs=Path(name).suffix in {'.log','.txt','.md'})
        else:clean=self.clean(value)
        if clean==value:return raw
        if kind=='lines':return ('\n'.join(dump(v) for v in clean)+'\n').encode()
        return (dump(clean) if kind=='json' else clean).encode()
    def assert_absent(self,raw):
        if any(v.encode() in raw for v in self.variants()):raise PrivacyError('Known credential remains in derived evidence.')

def redirect(value,mapping):
    if isinstance(value,dict):return {k:redirect(v,mapping) for k,v in value.items()}
    if isinstance(value,list):return [redirect(v,mapping) for v in value]
    return mapping.get(value,value) if isinstance(value,str) else value

def references(members):
    found=[]
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in {'file','_file'} and isinstance(item,str) and item.startswith(('resources/','src/')):found.append(item)
                walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    for name,raw in members.items():
        kind,value=parsed(name,raw)
        if kind in {'lines','json'}:walk(value)
    return found

def derive_members(members,sanitizer):
    sanitized={name:sanitizer.bytes(name,raw) for name,raw in members.items() if name!=MANIFEST};mapping={}
    for name,raw in members.items():
        if name.startswith('resources/') and sanitized.get(name)!=raw:
            # Resource identifiers are opaque to the inspected loader. This
            # avoids a false content-hash promise or circular resource hashes.
            mapping[name]='resources/pa-redacted-'+hashlib.sha1(name.encode()).hexdigest()+Path(name).suffix
        if name.endswith('.stacks'):
            for path in loads(raw.decode()).get('files',[]):
                if not isinstance(path,str):continue
                changed=sanitizer.replace(path,track=False)
                if changed==path:continue
                old='src/'+hashlib.sha1(path.encode()).hexdigest();new='src/'+hashlib.sha1(changed.encode()).hexdigest()
                for member in members:
                    if member.startswith(old+'.'):mapping[member]=new+member[len(old):]
    output={}
    for name,raw in sanitized.items():
        sanitizer.assert_absent(name.encode())
        kind,value=parsed(name,raw)
        if kind in {'lines','json'}:
            changed=redirect(value,mapping)
            if changed!=value:raw=(('\n'.join(dump(v) for v in changed)+'\n') if kind=='lines' else dump(changed)).encode()
        target=mapping.get(name,name)
        if target in output:raise PrivacyError('Derived trace member collision.')
        sanitizer.assert_absent(raw);output[target]=raw
    return output,mapping

def archive_bytes(output,manifest,target):
    output=output|{MANIFEST:dump(manifest).encode()};target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.privacy-',suffix='.tmp',dir=target.parent);os.close(fd);temporary=Path(name)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            z.comment=MARKER
            for name,raw in sorted(output.items()):
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=3;info.external_attr=0o100644<<16
                z.writestr(info,raw)
        audit_archive(temporary);os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()

def sanitize_archive(source,target,aliases=(),_sanitizer=None):
    source,target=Path(source),Path(target)
    if source.resolve()==target.resolve() or target.exists():raise PrivacyError('Derived evidence requires a distinct unused destination.')
    members,marked=read_archive(source)
    if marked:
        audit_archive(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        return dict(status='already_sanitized',source_sha256=file_sha(source),sanitized_sha256=file_sha(target))
    sanitizer=_sanitizer or Sanitizer(aliases);sanitizer.learn_members(members);output,mapping=derive_members(members,sanitizer)
    missing=sum(ref not in output for ref in references(output))
    manifest=dict(policy_version=1,trace_schema=10,source_sha256=file_sha(source),counts=sanitizer.counts.copy(),credential_values_discovered=len(sanitizer.secrets),resource_mapping=mapping,
        unresolved_references=missing,scope='Derived privacy-redacted evidence; original protocol sizes/times preserved. Resource identifiers are opaque; source-path identifiers are remapped. Unknown secrets in arbitrary media are outside this policy.')
    archive_bytes(output,manifest,target)
    return manifest|dict(sanitized_sha256=file_sha(target))

def audit_archive(path):
    members,marked=read_archive(path)
    if not marked or MANIFEST not in members:raise PrivacyError('Raw/unmarked trace is not accepted review evidence.')
    manifest=loads(members[MANIFEST].decode())
    if (not isinstance(manifest,dict) or type(manifest.get('policy_version')) is not int or manifest['policy_version']!=1 or manifest.get('trace_schema')!=10
        or not isinstance(manifest.get('source_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',manifest['source_sha256'])):raise PrivacyError('Unsupported privacy derivation policy.')
    sanitizer=Sanitizer();sanitizer.learn_members(members)
    for name,raw in members.items():
        if sanitizer.bytes(name,raw)!=raw:raise PrivacyError('Recognized credential remains in marked trace.')
        sanitizer.assert_absent(raw)
    missing=sum(ref not in members for ref in references(members))
    return dict(privacy_clean=True,unresolved_references=missing,members=len(members),source_sha256=manifest['source_sha256'])

def sanitize_capture(source,target,child_exit_code,aliases=()):
    if Path(source).is_symlink():raise PrivacyError('Unsafe private capture root.')
    source,target=Path(source).resolve(),Path(target).resolve()
    if target.exists() or source==target or source.is_relative_to(target) or target.is_relative_to(source):raise PrivacyError('Capture derivation needs separate private and review trees.')
    items=list(source.rglob('*'))
    if any(p.is_symlink() or p.is_junction() or not p.resolve().is_relative_to(source) or p.name.startswith('.env') for p in items):raise PrivacyError('Unsafe private capture member.')
    files=sorted(p for p in items if p.is_file())
    if len(files)>MAX_CAPTURE_FILES or sum(p.stat().st_size for p in files)>MAX_CAPTURE_BYTES:raise PrivacyError('Capture exceeds declared derivation bounds.')
    sanitizer=Sanitizer(aliases);raw_manifest=[]
    for path in files:
        name=path.relative_to(source).as_posix();raw_manifest.append(dict(path=name,sha256=file_sha(path),bytes=path.stat().st_size))
        if path.suffix=='.zip':sanitizer.learn_members(read_archive(path)[0])
        else:
            kind,value=parsed(name,path.read_bytes())
            if kind is not None:sanitizer.learn(value)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.privacy-review-',dir=target.parent) as temp:
        staging=Path(temp).resolve();assert staging.is_relative_to(target.parent) and staging.name.startswith('.privacy-review-')
        output=[]
        for path,record in zip(files,raw_manifest):
            if file_sha(path)!=record['sha256']:raise PrivacyError('Private capture changed during derivation.')
            name=record['path'];sanitizer.assert_absent(name.encode());destination=staging/name;destination.parent.mkdir(parents=True,exist_ok=True)
            if path.suffix=='.zip':sanitize_archive(path,destination,_sanitizer=sanitizer)
            else:
                raw=sanitizer.bytes(name,path.read_bytes());sanitizer.assert_absent(raw);destination.write_bytes(raw)
            output.append(dict(path=name,source_sha256=record['sha256'],sanitized_sha256=file_sha(destination),bytes=destination.stat().st_size))
        manifest=dict(policy_version=1,child_exit_code=child_exit_code,raw_retained_private=True,source_files=raw_manifest,files=output,counts=sanitizer.counts,credential_values_discovered=len(sanitizer.secrets))
        (staging/'privacy-derivation.json').write_text(dump(manifest),encoding='utf-8');os.replace(staging,target)
    return manifest
