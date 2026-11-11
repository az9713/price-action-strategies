"""Extend the preserved HTTP-owner verifier with bounded probes of known obsolete app endpoints."""
from pathlib import Path
source=Path('verification/runs/check-search-statistics-runtime-v3.py').read_text(encoding='utf-8')
before='value=dict(scope=__doc__'
addition='''
import urllib.error
obsolete_http={}
for port in [8768,8769,8770,8771]:
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/health',timeout=2) as response:
   raise AssertionError('Known obsolete endpoint still answers: '+str(port))
 except urllib.error.HTTPError:
  raise AssertionError('Known obsolete endpoint returned an HTTP error response: '+str(port))
 except urllib.error.URLError as error:
  obsolete_http[port]=dict(status='no HTTP response within the bounded probe',error_type=type(error.reason).__name__)
'''
assert source.count(before)==1
source=source.replace(before,addition+'\nvalue=dict(known_obsolete_http_endpoints=obsolete_http,scope=__doc__')
exec(compile(source,'search-statistics-runtime-v4-resolved.py','exec'))
