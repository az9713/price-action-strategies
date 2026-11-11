"""Post-download independent cell reread, visible-value and evidence reconciliation."""
from pathlib import Path
import hashlib,json,os,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from backend.lab.service import Lab
from backend.lab.config import canonical
from backend.lab.presentation_audit import audit_deck

root=Path.cwd();lab=Lab(root)
browser=root/'verification/runs/20261108T141439549029Z-presenter-signed-zero-and-expanded-controls-two-desktop-every-page/browser'
rows=[]
for folder in sorted((browser/'artifacts').iterdir()):
    if not folder.is_dir():continue
    observation=json.loads((folder/'presenter-observations.json').read_text(encoding='utf-8'))
    deck=json.loads((folder/'downloaded-presentation-provenance.json').read_text(encoding='utf-8'))
    document=(folder/'saved-research-presentation.html').read_text(encoding='utf-8')
    embedded=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',document,re.S).group(1))
    # Canonical comparison keeps Python's signed-zero JSON representation.
    assert json.dumps(embedded,sort_keys=True,allow_nan=False)==json.dumps(deck,sort_keys=True,allow_nan=False)
    sources={}
    for source in deck['sources']:
        jid,filename=source['name'].split('/');assert filename=='report.json' and re.fullmatch('[0-9a-f]{32}',jid)
        sources[source['name']]=canonical(lab.report(jid)).encode()
    audit=audit_deck(sources,deck)
    assert observation['pages']==len(deck['pages'])==169 and observation['facts']==audit['facts_checked']==12175
    assert observation['networkRequests']==[] and observation['consoleErrors']==[]
    layouts=json.loads((folder/'presenter-layouts.json').read_text(encoding='utf-8'))
    assert layouts==observation['layouts'] and len(layouts)==169
    screenshots=[];visible=0
    for i,(layout,page) in enumerate(zip(layouts,deck['pages'])):
        assert layout['issues']==[] and layout['title']==page['title'] and layout['conclusion']==page['conclusion']
        subtitle=''.join(deck['facts'][p['fact']]['text'] if isinstance(p,dict) else p for p in page['subtitle'])
        assert layout['subtitle']==subtitle
        title_variants={}
        for point in page['chart'].get('points',[]):
            title_variants[point['y']['fact']]=deck['facts'][point['x']['fact']]['text']+' : '+deck['facts'][point['y']['fact']]['text']
        for cell in layout['facts']:
            f=deck['facts'][cell['id']]
            assert cell['text'] in {f['text'],'',title_variants.get(cell['id'],f['text'])}
            visible+=1
        p=folder/('page-'+str(i+1).zfill(3)+'.png');raw=p.read_bytes()
        assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        width,height=struct.unpack('>II',raw[16:24]);assert {'width':width,'height':height}==observation['viewport']
        screenshots.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),width=width,height=height))
    for name in ['presenter-export.png','presenter-menu.png','presenter-camera-guide.png','presenter-highlight.png']:
        assert (folder/name).is_file()
    rows.append(dict(profile=folder.name,source_count=len(sources),audit=audit,pages=len(layouts),visible_fact_occurrences=visible,
        signed_zero_json_preserved=True,network_requests=0,console_errors=0,screenshots=screenshots))
assert len(rows)==2
output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
(output/'presenter-reconciliation.json').write_text(json.dumps(dict(scope='Actual saved-output/browser-export provenance and layout evidence; no new market edge or global release claim.',profiles=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=len(rows),page_screenshots=sum(len(r['screenshots']) for r in rows),facts_per_profile=12175,
    independently_reconciled_sources_per_profile=6,signed_zero_preserved=True)))
