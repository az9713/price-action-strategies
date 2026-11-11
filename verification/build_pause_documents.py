"""Build static, self-contained pause documents and the complete metadata run ledger."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import html,json,re,hashlib,os,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
DOCS=ROOT/'docs'
REPO='https://github.com/[redacted-user]/price-action-strategies'
PAUSE=json.loads((ROOT/'PAUSE_STATE.json').read_text(encoding='utf-8'))


def clean(text):
    for value in [str(ROOT),str(Path.home()),os.environ.get('COMPUTERNAME','')]:
        if not value:continue
        alias='<workspace>' if value==str(ROOT) else '<user-home>' if value==str(Path.home()) else '<device>'
        for variant in {value,value.replace('\\','/'),json.dumps(value)[1:-1]}:text=text.replace(variant,alias)
    text=re.sub(r'(?i)\b'+re.escape(Path.home().name)+r'(?:_laptop)?\b','[redacted-user]',text)
    return text


def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    def link(match):
        label,url=match.groups();url=html.unescape(url)
        if not url.startswith(('https://','http://','#','mailto:')):url=REPO+'/blob/main/'+url
        if not url.startswith(('https://','http://','#','mailto:')):return label
        return '<a href="'+html.escape(url,quote=True)+'">'+label+'</a>'
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)


def markdown(text):
    lines=clean(text).splitlines();output=[];paragraph=[];listing=None;code=None;i=0
    def flush():
        if paragraph:output.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    def close_list():
        nonlocal listing
        if listing:output.append('</'+listing+'>');listing=None
    while i<len(lines):
        line=lines[i]
        if code is not None:
            if line.startswith('```'):output.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code=None
            else:code.append(line)
            i+=1;continue
        if line.startswith('```'):flush();close_list();code=[];i+=1;continue
        if line.startswith('|') and i+1<len(lines) and re.match(r'^\|[\s:|-]+\|\s*$',lines[i+1]):
            flush();close_list();header=[x.strip() for x in line.strip().strip('|').split('|')]
            output.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in header)+'</tr></thead><tbody>');i+=2
            while i<len(lines) and lines[i].startswith('|'):
                output.append('<tr>'+''.join('<td>'+inline(x.strip())+'</td>' for x in lines[i].strip().strip('|').split('|'))+'</tr>');i+=1
            output.append('</tbody></table></div>');continue
        if not line.strip():flush();close_list();i+=1;continue
        if line.startswith('#'):
            flush();close_list();match=re.match(r'^(#{1,6})\s+(.*)',line)
            if match:
                level=min(6,len(match[1])+1);output.append(f'<h{level}>'+inline(match[2])+f'</h{level}>');i+=1;continue
        item=re.match(r'^\s*(?:([-*])\s+|(\d+)\.\s+)(.*)',line)
        if item:
            flush();kind='ul' if item[1] else 'ol'
            if listing!=kind:close_list();listing=kind;output.append('<'+kind+'>')
            output.append('<li>'+inline(item[3])+'</li>');i+=1;continue
        if line.startswith('>'):flush();close_list();output.append('<blockquote>'+inline(line[1:].strip())+'</blockquote>');i+=1;continue
        paragraph.append(line);i+=1
    flush();close_list()
    if code is not None:output.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(output)


CSS='''*{box-sizing:border-box}html{color-scheme:dark;scroll-behavior:smooth}body{margin:0;background:#0b1018;color:#dbe4ef;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#70d9cf;text-underline-offset:3px}a:hover{color:#bdfaf2}nav{background:#101927;border-bottom:1px solid #283549;padding:14px 5%;display:flex;gap:20px;flex-wrap:wrap}main{max-width:1160px;margin:auto;padding:42px 26px 85px}h1{font-size:clamp(30px,5vw,54px);line-height:1.1;letter-spacing:-.03em;color:#f4f7fc;margin:20px 0}h2{font-size:26px;line-height:1.3;margin-top:45px;color:#f0f5fc}h3{font-size:21px;color:#d1dfef;margin-top:30px}h4{font-size:18px;color:#c8d9ed}.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#e9bd71}.lead{font-size:20px;color:#b6c7d9;max-width:930px}.notice{border:1px solid #876a39;border-left:4px solid #edbc65;background:#211c14;padding:18px 22px;border-radius:8px;margin:24px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:16px;margin:28px 0}.card{background:#121d2b;border:1px solid #2b3b50;border-radius:12px;padding:22px}.card strong{display:block;font-size:30px;color:#f3f8ff}.card span{color:#aebed0}.table-wrap{overflow-x:auto;border:1px solid #2b3b50;border-radius:8px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:13px 15px;border-bottom:1px solid #263548}th{background:#172333;color:#dceaf7}tr:nth-child(even){background:#0f1825}td{overflow-wrap:anywhere}p,li{overflow-wrap:anywhere}li{margin:8px 0}code{font-size:.88em;background:#172332;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}pre{padding:20px;background:#101a27;border:1px solid #27394e;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}pre code{background:transparent;padding:0}blockquote{margin:24px 0;padding:12px 24px;border-left:3px solid #58b7c3;color:#b9cddd;background:#111e2b}footer{border-top:1px solid #263548;margin-top:50px;padding-top:20px;color:#8fa3b9;font-size:13px}.muted{color:#99acc0}.filters{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:24px 0}input,select{font:inherit;padding:10px 14px;background:#152235;color:#e5edf6;border:1px solid #486078;border-radius:6px;max-width:100%}input{flex:1;min-width:200px}.pill{display:inline-block;border-radius:5px;padding:2px 8px;background:#203649;font-size:12px}.bad{color:#ffb7a8}.good{color:#91dfc2}.unknown{color:#e1c489}details{background:#101b29;padding:14px 18px;border:1px solid #29394d;border-radius:8px;margin:16px 0}summary{cursor:pointer;color:#b6e5df}section{scroll-margin-top:15px}.run-command{font-size:12px;color:#91a5bb;max-width:440px}button{cursor:pointer;font:inherit;background:#193b42;color:#d5fff7;border:1px solid #4a8a87;border-radius:5px;padding:9px 14px}@media(max-width:650px){main{padding:25px 16px}nav{gap:13px;padding:12px 16px}h2{font-size:23px}.lead{font-size:18px}th,td{padding:10px;font-size:12px}.run-command{max-width:230px}.card{padding:16px}}'''


def page(title,body,script=''):
    nav='<nav aria-label="Documentation"><a href="index.html">Overview</a><a href="handoff.html">Handoff</a><a href="development-journey.html">Full journey</a><a href="verification-history.html">Run ledger</a><a href="'+REPO+'">Source repository</a></nav>'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>'+html.escape(title)+' — Price Action Research Lab</title><style>'+CSS+'</style></head><body>'+nav+'<main>'+body+'<footer>Paused development snapshot. No final product acceptance certificate. Static documentation; no market-data credentials or trading backend are embedded.</footer></main>'+script+'</body></html>'


def build_ledger():
    entries={};source_rows=[]
    for path in sorted((ROOT/'verification/receipts').glob('*.json')):
        raw=path.read_bytes();receipt=json.loads(raw);rid=receipt['receipt_id'];command=receipt.get('command',{})
        counts=None;junit=[]
        for item in receipt.get('artifacts',[]):
            name=item.get('path','')
            if name.endswith('.xml') and 'junit' in name.lower():
                p=(ROOT/name).resolve()
                if p.is_relative_to(ROOT) and p.is_file() and p.stat().st_size<12*1024*1024:
                    try:
                        tree=ET.parse(p).getroot();suites=[tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
                        got={key:sum(int(float(s.get(key,'0'))) for s in suites) for key in ['tests','failures','errors','skipped']}
                        junit.append(got)
                    except (ET.ParseError,ValueError,OSError):pass
        if junit:counts=junit[0]
        exit_code=command.get('exit_code');notes=receipt.get('notes',[])
        coherent=not any('Source changed during command' in str(x) for x in notes)
        status='exit zero' if exit_code==0 and coherent else 'source changed' if exit_code==0 else 'nonzero'
        entries[rid]=dict(id=rid,label=re.sub(r'^\d{8}T\d+Z-','',rid),started=receipt.get('started_at_utc'),finished=receipt.get('finished_at_utc'),
            status=status,exit_code=exit_code,command=clean(' '.join(map(str,command.get('argv',[])))),notes=clean(json.dumps(notes,ensure_ascii=False)),
            original_receipt_sha256=hashlib.sha256(raw).hexdigest(),receipt='verification/receipts/'+path.name,artifact_count=len(receipt.get('artifacts',[])),junit=counts,terminal_receipt=True)
        source_rows.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    for directory in sorted((ROOT/'verification/runs').iterdir()):
        if not directory.is_dir() or not re.match(r'^\d{8}T\d+Z-',directory.name) or directory.name in entries:continue
        progress=None;p=directory/'full-regression-progress.json'
        if p.exists():
            try:progress=json.loads(p.read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
        entries[directory.name]=dict(id=directory.name,label=re.sub(r'^\d{8}T\d+Z-','',directory.name),started=None,finished=None,status='no terminal receipt',exit_code=None,command='',notes='Run directory exists, but no terminal receipt is present. No completed execution is inferred.',artifact_count=None,junit=None,terminal_receipt=False,observed_progress=progress)
    result=dict(scope='Complete receipt and timestamped run-directory inventory at documentation build. Exit-zero is not final acceptance; absent receipts and interrupted runs remain unverified.',
        built_at_utc=datetime.now(timezone.utc).isoformat(),build_pause_utc=PAUSE['paused_at_utc'],receipt_count=len(source_rows),run_directory_or_receipt_count=len(entries),status_counts=dict(Counter(x['status'] for x in entries.values())),runs=[entries[k] for k in sorted(entries)],receipt_inventory=source_rows)
    (DOCS/'verification-history.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    ledger=build_ledger();a=json.loads((DOCS/'pause/journey-accounting.json').read_text());state=PAUSE
    cards='<div class="cards"><div class="card"><strong>Paused</strong><span>November 10, 2026 Pacific</span></div><div class="card"><strong>86 passed</strong><span>Latest completed focused regression</span></div><div class="card"><strong>787 / 829</strong><span>Interrupted run; no full pass</span></div><div class="card"><strong>0 / 422</strong><span>Final certified acceptance cases</span></div></div>'
    intro='<p class="eyebrow">Price Action Research Lab / pause handoff</p><h1>A working research prototype.<br>A release still to verify.</h1><p class="lead">The implementation goal is paused at the user\'s request. This record names what exists, what was actually tested, what failed and what the next maintainer must do.</p>'+cards
    warning='<div class="notice"><strong>No final-release claim.</strong> The newest research source is uninstalled. The latest 10,000 run failed; the complete regression, controls, stress, coverage and case-level release audit remain open. GitHub Pages serves these documents, not the Python trading app.</div>'
    overview=intro+warning+'<h2>Start here</h2><div class="cards"><div class="card"><h3><a href="handoff.html">Current handoff</a></h3><p>Exact source, passing evidence, failures, remaining dependencies and resume order.</p></div><div class="card"><h3><a href="development-journey.html">Complete journey</a></h3><p>All four journals, from the first video investigation through the explicit pause.</p></div><div class="card"><h3><a href="verification-history.html">Verification ledger</a></h3><p>'+str(ledger['receipt_count'])+' receipts, plus run directories lacking terminal evidence. Search every recorded attempt.</p></div></div><h2>Inspiration and fidelity</h2><p><a href="https://www.youtube.com/watch?v=z97PnFIPoFg&amp;t=401s">AI Pathways: Claude Tested 100,000 Price Action Strategies</a>. US equities/ETFs adapt a futures-oriented presentation. Private engine and complete preset recipes remain unavailable. Automated decoding covered 30,920 frames; visual review sampled 1,031 frames plus 37 focused captures and 15 prompt pages.</p><h2>Build time and usage</h2><p>75h 44m 24s calendar elapsed through the pause. Recorded uncached input plus output: <strong>15,722,844 tokens</strong>. All input/output including cached context: 1,163,094,748. Actual dollar cost is unavailable. <a href="pause/journey-accounting.json">Exact accounting</a>.</p>'
    (DOCS/'index.html').write_text(page('Project paused',overview),encoding='utf-8')
    remain=''.join('<li>'+html.escape(x)+'</li>' for x in state['remaining'])
    handoff=intro+warning+'<h2>1. Exact source and installation state</h2><p>Root application: historical 0.25 development checkpoint (package manifests 0.1.0). Latest research source: <code>data/dev027/research-src</code>, uninstalled. Original local core before privacy publication: <code>'+state['original_local_core']+'</code>. Public redaction may alter source bytes; historical receipts do not silently certify that rewritten tree.</p><p>Authoritative resume record: <a href="'+REPO+'/blob/main/PAUSE_STATE.json">PAUSE_STATE.json</a>. The managed pipeline exited after Ctrl+C. A bounded subsequent process inventory found no matching project Python workers. No responding application server is promised.</p>'
    handoff+='<h2>2. Latest evidence, with its actual scope</h2><div class="table-wrap"><table><thead><tr><th>Check</th><th>Observed result</th><th>Interpretation</th></tr></thead><tbody>'
    evidence=[('Current focused regression','86 passed / 244.93 seconds','64/65/128 complete-account equality, fault rollback, scoped connection behavior. Not complete release evidence.'),('Current broad regression','787 reported passes / 829 collected; interrupted','No terminal receipt; unreported cases remain unknown.'),('Additional news cases','24 passed / 3 failed','Logic cases passed. Missing HTML fixtures prevented three intended actual crash boundaries.'),('Latest real 10,000 capacity','5,488 committed / 903.85 seconds','Failed the original 900-second limit on prior d2f1e593 source; originals preserved.'),('Prior numerical revision','675 passed; 120 baseline combinations reconciled','Historical d2f1e593 component evidence. Not a certificate for current 010175e4.'),('Prior real 1,000 capacity','65.68 seconds','Historical bounded one-session SPY measurement, not a full-history guarantee.'),('Final acceptance','0 / 422 certified','Substantial code/tests exist; final coherent case-level proof remains incomplete.')]
    for row in evidence:handoff+='<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>'
    handoff+='</tbody></table></div><h2>3. First resume blocker: fixture inventory</h2><p><code>news-bls-2022-01.html</code> and <code>news-fomc.html</code> exist in root fixtures but are absent from the research stage. The fresh-clone verifier copies JSON fixtures only. Stored job errors are <code>Internal FileNotFoundError</code>. This has not been fixed after pausing.</p><p>On explicit resume, inventory and hash all required fixture types, supply the missing HTML fixtures to the stage, correct the clean clone inventory, then rerun the real acquisition deaths and parser/recovery checks. Retain the first failure. Do not lower assertions or relabel the failed crash tests as passed.</p><h2>4. Remaining work in dependency order</h2><ol>'+remain+'</ol>'
    handoff+='<h2>5. Contracts that must survive the next fix</h2><ul><li>83 requirements; 422 mandatory cases; 120 baseline combinations; all 51 declared numerical modules.</li><li>Unchanged 95% statements and 90% branches per numerical module, reconciled from actual coverage data without rounding.</li><li>Original real-data workload bounds: 900 seconds, 3 GiB peak working set, 2 GiB output per count. The separate 100,000 financial stress is not satisfied by its 60-account smoke.</li><li>Fresh source/price/manifest/protected-window authority; actual independent computations, attempts, original parts and event chains.</li><li>Both complete 10,000-set control policies, frozen qualification, both final instruments, all original versions and complete exports.</li><li>Preserve zero/loss/unavailable/no-candidate outcomes. No supplied totals or partial parts may masquerade as completed financial evidence.</li></ul>'
    handoff+='<h2>6. What exists and how useful it is</h2><p>Data audits/imports, strategy versions, searches, independent/shared accounts, ledgers/charts, studies, controls/ablations, news, borrowing scenarios and saved/offline exports support exploratory research. Current large-search reliability, full research-funnel evidence and final conformance are unfinished. The host\'s undisclosed private strategies and futures profits are not reproduced.</p><h2>7. Safe resumption</h2><p>Read <a href="'+REPO+'/blob/main/PLAN.md">PLAN.md</a>, <a href="'+REPO+'/blob/main/VERIFICATION_PLAN.md">VERIFICATION_PLAN.md</a>, the rulebook, pause state and current evidence. Recheck actual processes; session IDs and PIDs are historical. Do not auto-launch archived coordinators. Keep user credentials, original databases and market caches local. Use isolated verification stores and headless checks; do not take over the user\'s desktop. Resume only after an explicit user instruction.</p><h2>8. Privacy and evidence provenance</h2><p>The public snapshot excludes populated environment files, price caches, original user databases, raw logs/traces, source video and full transcript. Email is permitted. Public receipt copies are privacy-derived, with original/published hashes in the manifest. Source-license attribution remains. See <a href="pause/PRIVACY-REPORT.json">the privacy report</a>.</p>'
    (DOCS/'handoff.html').write_text(page('Current handoff',handoff),encoding='utf-8')
    journey='<p class="eyebrow">Complete development journey</p><h1>From a video to an unfinished research system.</h1><p class="lead">Four chronological journals, preserved with their original cutoffs, followed through the explicit pause. Earlier sections are reconstructed from retained source records; later results never retroactively certify an older claim.</p>'+warning+'<p><a href="#journal-1">Initial investigation and application</a> · <a href="#journal-2">Financial trade twins</a> · <a href="#journal-3">Research funnel and contention</a> · <a href="#journal-4">Performance corrections and pause</a></p>'
    for number,name in enumerate(['DEVELOPMENT-JOURNEY.md','DEVELOPMENT-JOURNEY-2.md','DEVELOPMENT-JOURNEY-3.md','DEVELOPMENT-JOURNEY-4.md'],1):
        journey+='<section id="journal-'+str(number)+'">'+markdown((ROOT/name).read_text(encoding='utf-8'))+'</section>'
    (DOCS/'development-journey.html').write_text(page('Complete development journey',journey),encoding='utf-8')
    rows=[]
    for item in ledger['runs']:
        css='good' if item['status']=='exit zero' else 'unknown' if not item['terminal_receipt'] else 'bad'
        counts=item.get('junit');counts_text='—' if counts is None else ', '.join(str(counts[k])+' '+k for k in ['tests','failures','errors','skipped'])
        receipt='<a href="'+REPO+'/blob/main/'+item['receipt']+'">Privacy-derived receipt</a>' if item.get('receipt') else 'No terminal receipt'
        progress=item.get('observed_progress')
        if progress:counts_text='Last observation: '+str(progress.get('passed'))+' passed / '+str(progress.get('collected'))+' collected; terminal '+str(progress.get('terminal'))
        rows.append('<tr data-status="'+item['status']+'"><td><code>'+html.escape(item['id'])+'</code><p class="muted">'+html.escape(item.get('started') or 'No terminal timestamp')+'</p></td><td class="'+css+'">'+html.escape(item['status'])+'<p>Exit '+html.escape(str(item['exit_code']))+'</p></td><td>'+html.escape(counts_text)+'<p>'+receipt+'</p><details><summary>Recorded command and notes</summary><pre>'+html.escape(item['command'] or 'Command unavailable without terminal receipt')+'</pre><p>'+html.escape(item['notes'])+'</p></details></td></tr>')
    ledgerbody='<p class="eyebrow">All recorded verification attempts</p><h1>The complete run ledger.</h1><p class="lead">'+str(ledger['receipt_count'])+' original receipts; '+str(len(ledger['runs']))+' receipt/run-directory entries. Failures and missing terminal evidence are included.</p><div class="notice">Exit zero means the recorded command completed successfully on its recorded subject. It does not automatically certify a requirement. Repeats across source revisions are not independent coverage. Public receipts are privacy-derived; private artifacts referenced by historical hashes are not all distributed.</div><p><a href="verification-history.json">Download the full metadata ledger</a> · <a href="handoff.html">Current pause state</a></p><div class="filters"><label for="query">Search</label><input id="query" type="search" placeholder="Run ID, topic, status, command…"><label for="status">Status</label><select id="status"><option value="">All entries</option><option>exit zero</option><option>nonzero</option><option>source changed</option><option>no terminal receipt</option></select><span id="count" role="status"></span></div><div class="table-wrap"><table id="runs"><thead><tr><th>Run / timestamp</th><th>Outcome</th><th>Available evidence</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    js='''<script>const q=document.getElementById('query'),s=document.getElementById('status'),rows=[...document.querySelectorAll('#runs tbody tr')],count=document.getElementById('count');function filter(){const query=q.value.toLowerCase();let shown=0;for(const row of rows){const ok=(!s.value||row.dataset.status===s.value)&&(!query||row.textContent.toLowerCase().includes(query));row.hidden=!ok;if(ok)shown++}count.textContent=shown+' / '+rows.length+' entries'}q.addEventListener('input',filter);s.addEventListener('change',filter);filter();</script>'''
    (DOCS/'verification-history.html').write_text(page('Verification history',ledgerbody,js),encoding='utf-8')
    print(json.dumps(dict(receipts=ledger['receipt_count'],entries=len(ledger['runs']),status=ledger['status_counts'],html_pages=4)))


if __name__=='__main__':main()
