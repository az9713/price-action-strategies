"""Publish only completed D039 component evidence while the full unchanged rerun is pending."""
from pathlib import Path
import json
root=Path.cwd()
labels={
 'browser':'common-sampling-complete-assumptions-grid-random-calendar-two-desktop-workflows',
 'audit':'common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions-project-runtime',
 'mutations':'common-sampling-twelve-isolated-critical-source-mutations',
 'build':'common-sampling-current-subject-typed-frontend-build',
 'full_fail':'common-sampling-current-full-regression-and-seventeen-module-coverage',
 'startup':'common-sampling-startup-failure-unchanged-isolated-pass-and-concurrent-run-timeline',
 'runtime':'common-sampling-current-managed-main-duplicate-refusal-and-served-assets',
 'plan':'common-sampling-current-422-plan-inventory',
 'release':'common-sampling-current-422-release-remains-incomplete',
}
paths={k:sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1] for k,label in labels.items()}
for k,p in paths.items():assert json.loads(p.read_text(encoding='utf-8'))['command']['exit_code']==(1 if k in {'full_fail','release'} else 0)
def text(base):
 def link(k,title):return '['+title+']('+('verification/' if base=='status' else '')+'receipts/'+paths[k].name+')'
 return '\n\n'.join([
 '## Current0.19 — common sampling verification in progress',
 'The managed app is available at http://127.0.0.1:8767, with current numerical core `a3eb52616e294d6fe770dec5b8efc6cfc33e2bae9b7ad70da51adf1ef4876b91` and frontend `index-DF4wP8DW.js`. The project remains active and **not ready for final release**. The0.18 evidence below is historical.',
 'D039 adds published equities common-grid and common-random sampling, exact40/40/20 filter quotas, full proposal history and initial40-signal/30-trade/positive-profit/Sharpe>=0.5 gates. The complete declared ten-family/six-chart grid contains24480 configurations without news and32640 with news. These are our published rules, not the host private14016 grid. News-enabled generation requires an explicitly frozen calendar. Initial gates do not unlock final data.',
 link('browser','Two actual desktop workflows')+' passed at1920x1080 and1280x720. '+link('audit','All120 saved browser account instances')+' independently reconcile with supplied-signal Decimal execution, complete initial-gate CSVs, saved offline facts and438 screenshots. Synthetic controls establish software behavior, not a market edge. The exact-input Sharpe formula oracle and complete independent account oracle retain original tolerances.',
 link('mutations','Twelve isolated source mutations')+' were killed by explicit assertions; baseline53 passed, originals unchanged. '+link('build','Typed frontend build')+' passed; the large-bundle warning remains. These component results do not certify all422 mandatory cases.',
 link('full_fail','First full1579-case run')+' passed1578 and failed one actual spawned-worker readiness deadline. '+link('startup','Unchanged isolated diagnostic and timeline')+' passed with5.135s startup and1.452s job execution. The original60/20-second limits remain. Browser/mutation execution overlapped, but the timeout root cause is unproved. A full unchanged rerun is still required; no full0.19 regression pass is claimed here.',
 link('runtime','Current managed owner, duplicate-store refusal and byte-identical served assets')+' passed. Session35409 owns the main; HTTP46448/worker31904 were the observed identities. Old verification servers and missing exceptional-exit cleanup caused the earlier proliferation. D037 supplies an OS store lease and finally cleanup. A launcher/HTTP/worker tree is expected. Agent-managed Ctrl+C replaces manual taskkill requests. Native inventory omitted a known live endpoint, so OS-wide closed-port status is not certified.',
 link('plan','Planning inventory')+' remains83 requirements/422 mandatory cases/120 baseline combinations. '+link('release','Release gate')+' correctly rejects completion:0/422 final-certified means no coherent final acceptance certificate, not zero implemented or tested behavior. Every original requirement remains binding.',
 'Source: [AI Pathways/Brendan YouTube video](https://www.youtube.com/watch?v=z97PnFIPoFg). Automated analysis covered30920 decoded frames; visual review sampled1031 frames plus37 focused4K captures and15 prompt pages. This was not manual inspection of every frame. Ten families and visible dials have explicit equities rules; private detector details and six complete named recipes remain unknown. US stocks/ETFs, free Alpaca data, next-open execution and explicit borrowing replace futures-specific choices. Futures, forex and crypto remain later options.',
 'Mandatory remaining work includes outcome-qualified balanced spread,10000 matched trade-twin sets, eras/instrument replication/stability/family ensembles, detector/dial/critical-branch adequacy, complete study lifecycle, actual10000/bounded100000 capacity, polling/result bounds, mobile/keyboard/accessibility/security/privacy, locked clean reproduction and final422-case conformance. Current20 conditional controls are not matched trade twins. Prior real SPY/QQQ screening remains no_candidates; protected final data was not consumed. Aggregate instrument/synthetic provenance is an additional observed gap to fix before the broader funnel.',
 ('See [defects](verification/defects.json) and [next acceptance notes](verification/runs/common-sampling-next-acceptance-notes.md).' if base=='status' else 'See [defects](defects.json) and [next acceptance notes](runs/common-sampling-next-acceptance-notes.md).')+' The first warm-up24-versus8 error,11 omitted export assumptions and verifier failures remain retained; corrections did not widen numerical tolerances or alter the source cohort.',
 ])+'\n\n'
for name,marker,base in [('STATUS.md','## Historical0.18','status'),('verification/evidence-index.md','## Historical0.18','evidence')]:
 p=root/name;old=p.read_text(encoding='utf-8');assert marker in old
 historical=old[old.index(marker):]
 p.write_text(text(base)+historical,encoding='utf-8')
print('Updated current D039 evidence/status; retained original full timeout and historical checkpoint.')
