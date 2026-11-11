"""Fake sentinels only. Financial preservation and fail-closed archive contracts."""
from pathlib import Path
import hashlib
import importlib
import json
import zipfile
import pytest

SECRETS={name:'PA_FAKE_TRACE_'+name.upper()+'_SENTINEL_123456' for name in ['token','authorization','provider_key','provider_secret','cookie','password','query']}
SOURCE=r'C:\Users\fixture\project\frontend\tests\demo.spec.ts'
def raw_json(value):return json.dumps(value,separators=(',',':')).encode()
def resource(raw,suffix='.json'):return 'resources/'+hashlib.sha1(raw).hexdigest()+suffix
def module():return importlib.import_module('verification.trace_privacy')

def archive(path,**changes):
    token=raw_json({'token':SECRETS['token']});finance=raw_json({'net_profit':12.375,'trades':7,'token_count':13,'key':'ordinary','url':'https://prices.example/quotes?symbol=SPY'})
    image=b'\xff\xd8unchanged-authored-image-bytes\xff\xd9'
    records=[dict(type='context-options',version=10),dict(type='before',callId='one',startTime=100,apiName='request.get',class_='APIRequestContext',method='get',params={'headers':{'X-Lab-Token':SECRETS['token'],'Accept':'application/json'}}),
        dict(type='log',callId='one',time=101,message='  x-lab-token: '+SECRETS['token']),
        dict(type='frame-snapshot',snapshot={'html':['INPUT',{'type':'password','value':SECRETS['password']}],'timestamp':103}),
        dict(type='after',callId='one',endTime=104,result={'log':SECRETS['cookie'],'token_count':13})]
    requests=[]
    for index,body in enumerate([token,finance]):
        requests.append(dict(type='resource-snapshot',snapshot={'request':{'method':'GET','url':'https://localhost/api/session?access_token='+SECRETS['query'],
            'headers':[{'name':'X-Lab-Token','value':SECRETS['token']},{'name':'Authorization','value':'Bearer '+SECRETS['authorization']},
                {'name':'APCA-API-KEY-ID','value':SECRETS['provider_key']},{'name':'APCA-API-SECRET-KEY','value':SECRETS['provider_secret']},{'name':'Accept','value':'application/json'}],
            'cookies':[{'name':'sid','value':SECRETS['cookie']}],'queryString':[{'name':'access_token','value':SECRETS['query']}]},
            'response':{'status':200,'headers':[{'name':'Set-Cookie','value':'sid='+SECRETS['cookie']+'; Secure'}],'cookies':[],
                'content':{'_file':resource(body),'mimeType':'application/json','size':len(body)}},'time':12.5}))
    members={'test.trace':b'\n'.join(raw_json(r) for r in records)+b'\n','0-trace.network':b'\n'.join(raw_json(r) for r in requests)+b'\n',
        '0-trace.stacks':raw_json({'files':[SOURCE],'stacks':[]}),
        'src/'+hashlib.sha1(SOURCE.encode()).hexdigest()+'.ts':b'// Embedded source; only aliases may change.\n',resource(token):token,resource(finance):finance,'resources/image.jpeg':image}
    members.update(changes)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in members.items():z.writestr(name,raw)
    return members,finance,image

def read(path):
    with zipfile.ZipFile(path) as z:return {name:z.read(name) for name in z.namelist()}

def test_actual_named_credential_contexts_are_removed_without_touching_financial_values(tmp_path):
    source=tmp_path/'raw.zip';members,finance,image=archive(source);before=source.read_bytes();target=tmp_path/'review.zip'
    result=module().sanitize_archive(source,target,aliases=[(r'C:\Users\fixture\project','<workspace>')])
    assert source.read_bytes()==before and result['source_sha256']==hashlib.sha256(before).hexdigest()
    output=read(target);joined=b'\n'.join(output.values())
    assert all(value.encode() not in joined for value in SECRETS.values())
    assert b'C:\\\\Users\\\\fixture' not in joined
    assert output[resource(finance)]==finance and output['resources/image.jpeg']==image
    events=[json.loads(line) for line in output['0-trace.network'].splitlines()]
    for event in events:
        request=event['snapshot']['request'];response=event['snapshot']['response']
        assert request['headers']==[{'name':'Accept','value':'application/json'}] and request['cookies']==[] and response['headers']==[]
        assert event['snapshot']['time']==12.5 and response['status']==200
        assert response['content']['_file'] in output
    session=json.loads(output[events[0]['snapshot']['response']['content']['_file']]);assert session['token']==module().REDACTED
    expected_source='<workspace>\\frontend\\tests\\demo.spec.ts'
    assert json.loads(output['0-trace.stacks'])['files']==[expected_source]
    assert 'src/'+hashlib.sha1(expected_source.encode()).hexdigest()+'.ts' in output
    audit=module().audit_archive(target);assert audit['privacy_clean'] and audit['unresolved_references']==0

def test_deterministic_and_idempotent_review_archives(tmp_path):
    source=tmp_path/'raw.zip';archive(source)
    a,b,c=[tmp_path/name for name in ['a.zip','b.zip','c.zip']]
    module().sanitize_archive(source,a);module().sanitize_archive(source,b)
    assert a.read_bytes()==b.read_bytes()
    module().sanitize_archive(a,c);assert a.read_bytes()==c.read_bytes()

def test_short_credentials_do_not_globally_replace_numbers_or_ordinary_words(tmp_path):
    source=tmp_path/'raw.zip';archive(source,**{'resources/short.json':raw_json({'token':'1','count':1,'text':'price1','token_count':1})})
    target=tmp_path/'review.zip';module().sanitize_archive(source,target)
    bodies=[json.loads(raw) for name,raw in read(target).items() if name.startswith('resources/') and name.endswith('.json')]
    value=next(v for v in bodies if isinstance(v,dict) and 'count' in v)
    assert value=={'token':module().REDACTED,'count':1,'text':'price1','token_count':1}

def test_nested_json_and_encoded_urls_are_sanitized(tmp_path):
    source=tmp_path/'raw.zip';extra={'message':json.dumps({'access_token':SECRETS['token']}),'url':'https://localhost/?access%5Ftoken=short&symbol=SPY','ordinary':99}
    archive(source,**{'resources/nested.json':raw_json(extra)})
    target=tmp_path/'review.zip';module().sanitize_archive(source,target)
    joined=b'\n'.join(read(target).values());assert SECRETS['token'].encode() not in joined and b'access%5Ftoken=short' not in joined
    assert module().audit_archive(target)['privacy_clean']

@pytest.mark.parametrize('mode',['traversal','absolute','windows','symlink','duplicate','schema','malformed','encrypted','size'])
def test_unsupported_or_unsafe_trace_fails_closed_and_preserves_original(tmp_path,mode,monkeypatch):
    source=tmp_path/'raw.zip';archive(source)
    if mode in {'traversal','absolute','windows','symlink','duplicate'}:
        with zipfile.ZipFile(source,'a') as z:
            if mode=='symlink':
                info=zipfile.ZipInfo('resources/link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,b'../secret')
            else:z.writestr({'traversal':'../escape','absolute':'/escape','windows':'C:/escape','duplicate':'test.trace'}[mode],b'bad')
    if mode=='schema':archive(source,**{'test.trace':raw_json(dict(type='context-options',version=999))+b'\n'})
    if mode=='malformed':archive(source,**{'0-trace.network':b'{invalid\n'})
    if mode=='encrypted':
        original=zipfile.ZipFile.infolist
        def infos(z):
            out=original(z);out[0].flag_bits|=1;return out
        monkeypatch.setattr(zipfile.ZipFile,'infolist',infos)
    if mode=='size':monkeypatch.setattr(module(),'MAX_ARCHIVE_BYTES',20)
    before=source.read_bytes();target=tmp_path/'review.zip'
    with pytest.raises(module().PrivacyError):module().sanitize_archive(source,target)
    assert source.read_bytes()==before and not target.exists()

def test_known_credential_in_unsupported_binary_fails_without_copying_it(tmp_path):
    source=tmp_path/'raw.zip';archive(source,**{'resources/opaque.bin':b'\x00\xff'+SECRETS['token'].encode()})
    with pytest.raises(module().PrivacyError):module().sanitize_archive(source,tmp_path/'review.zip')
    assert not (tmp_path/'review.zip').exists()

def test_raw_trace_cannot_masquerade_as_a_review_artifact(tmp_path):
    source=tmp_path/'raw.zip';archive(source)
    with pytest.raises(module().PrivacyError):module().audit_archive(source)

def test_capture_derivation_keeps_raw_and_preserves_child_exit_and_images(tmp_path):
    source=tmp_path/'private';source.mkdir();archive(source/'trace.zip')
    (source/'junit.xml').write_text('<testsuites><testsuite tests="1" failures="1"/></testsuites>',encoding='utf-8')
    (source/'observations.json').write_text(json.dumps({'path':SOURCE,'profit':12.375}),encoding='utf-8')
    (source/'stderr.log').write_text('x-lab-token: '+SECRETS['token'],encoding='utf-8')
    target=tmp_path/'review';result=module().sanitize_capture(source,target,child_exit_code=1,aliases=[(r'C:\Users\fixture\project','<workspace>')])
    assert result['child_exit_code']==1 and result['raw_retained_private'] is True
    assert (source/'trace.zip').exists() and (target/'junit.xml').read_bytes()==(source/'junit.xml').read_bytes()
    assert SECRETS['token'] not in (target/'stderr.log').read_text(encoding='utf-8')
    assert json.loads((target/'observations.json').read_text(encoding='utf-8'))['profit']==12.375

def test_failed_capture_derivation_does_not_publish_a_partial_unsafe_tree(tmp_path):
    source=tmp_path/'private';source.mkdir();archive(source/'trace.zip');(source/'opaque.bin').write_bytes(b'\x00'+SECRETS['token'].encode())
    target=tmp_path/'review'
    with pytest.raises(module().PrivacyError):module().sanitize_capture(source,target,child_exit_code=0)
    assert not target.exists() and (source/'opaque.bin').exists()

def test_reserved_privacy_metadata_and_tampered_marked_manifest_fail_closed(tmp_path):
    source=tmp_path/'raw.zip';archive(source,**{'pa-redaction.json':b'{}'})
    with pytest.raises(module().PrivacyError):module().sanitize_archive(source,tmp_path/'refused.zip')
    archive(source);target=tmp_path/'review.zip';module().sanitize_archive(source,target)
    members=read(target);manifest=json.loads(members['pa-redaction.json']);manifest['token']=SECRETS['token'];members['pa-redaction.json']=raw_json(manifest)
    tampered=tmp_path/'tampered.zip'
    with zipfile.ZipFile(tampered,'w') as z:
        z.comment=module().MARKER
        for name,raw in members.items():z.writestr(name,raw)
    with pytest.raises(module().PrivacyError):module().audit_archive(tampered)

def test_capture_size_limit_and_existing_destination_preserve_private_source(tmp_path,monkeypatch):
    source=tmp_path/'private';source.mkdir();(source/'huge.txt').write_bytes(b'x'*1024)
    target=tmp_path/'review';monkeypatch.setattr(module(),'MAX_CAPTURE_BYTES',512)
    with pytest.raises(module().PrivacyError):module().sanitize_capture(source,target,0)
    assert not target.exists() and (source/'huge.txt').stat().st_size==1024
    target.mkdir();(target/'keep.txt').write_text('keep',encoding='utf-8')
    with pytest.raises(module().PrivacyError):module().sanitize_capture(source,target,0)
    assert (target/'keep.txt').read_text(encoding='utf-8')=='keep'

def test_credentials_learned_from_private_logs_are_removed_from_other_artifacts(tmp_path):
    source=tmp_path/'private';source.mkdir()
    (source/'stderr.log').write_text('Authorization: Bearer '+SECRETS['authorization']+'\nordinary number1\n',encoding='utf-8')
    (source/'data.json').write_text(json.dumps({'ordinary_field':SECRETS['authorization'],'number':1}),encoding='utf-8')
    target=tmp_path/'review';module().sanitize_capture(source,target,child_exit_code=1)
    assert SECRETS['authorization'] not in (target/'data.json').read_text(encoding='utf-8')
    assert json.loads((target/'data.json').read_text(encoding='utf-8'))['number']==1
    assert 'ordinary number1' in (target/'stderr.log').read_text(encoding='utf-8')
