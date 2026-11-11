"""Build an allowlisted privacy-derived publication tree, without copying user data."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import ast,hashlib,json,os,re,subprocess,sys

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'data/publication/price-action-strategies'
assert DEST.resolve().is_relative_to((ROOT/'data/publication').resolve())
REFRESH='--refresh' in sys.argv
assert not DEST.exists() or (REFRESH and not (DEST/'.git').exists()), 'Inspect an existing publication tree; refresh is limited to the pre-Git owned snapshot.'
sys.path.insert(0,str(ROOT))
from verification.record_check import source_paths

EXT={'.py','.ts','.tsx','.js','.mjs','.json','.md','.txt','.html','.css','.csv','.ps1','.toml','.lock','.yml','.yaml','.svg'}
SKIP={'.git','.venv','node_modules','dist','__pycache__','.pytest_cache','.hypothesis','test-results','playwright-report','htmlcov'}
selected=set()


def add(path):
    if path.is_file():
        if path==ROOT/'docs/pause/PRIVACY-REPORT.json':return
        path.resolve().relative_to(ROOT)
        assert path.name=='.env.example' or not path.name.startswith('.env')
        selected.add(path)


def tree(folder,skip_dated=False):
    if not folder.exists():return
    for current,dirs,files in os.walk(folder):
        dirs[:]=[x for x in dirs if x not in SKIP and not (skip_dated and re.match(r'^\d{8}T\d+Z-',x))]
        for name in files:
            p=Path(current)/name
            if p.suffix.lower() in EXT and not name.startswith('.env') and p.stat().st_size<20*1024*1024:add(p)


for p in source_paths(ROOT):add(p)
for name in ['.gitignore','.env.example','PAUSE_STATE.json','STATUS.md','DEVELOPMENT-JOURNEY.md','DEVELOPMENT-JOURNEY-2.md','DEVELOPMENT-JOURNEY-3.md','DEVELOPMENT-JOURNEY-4.md','VIDEO_REVIEW.md','SCREENSHOT_FINDINGS.md']:add(ROOT/name)
for folder in ['docs','verification/fixtures','verification/receipts','verification/planning_receipts']:tree(ROOT/folder)
tree(ROOT/'verification/runs',skip_dated=True)
for folder in ['data/dev026/src','data/dev026/next-src','data/dev026/evidence-src','data/dev027/research-src']:
    source=ROOT/folder
    for p in source_paths(source):add(p)
    tree(source/'verification/fixtures')
    for name in ['STATUS.md']:add(source/name)
for name in ['source-manifest.json','screenshot-manifest.json','capture_screenshots.py','make_contact_sheets.py','probe_alpaca.py','transcribe.py']:add(ROOT/'research'/name)

# Values stay in process memory. The populated .env itself is never copied,
# printed, hashed, archived or included in publication metadata.
live_secrets=[]
environment_file=ROOT/'.env'
if environment_file.exists():
    for line in environment_file.read_text(encoding='utf-8-sig').splitlines():
        match=re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)',line)
        if match and any(word in match[1].upper() for word in ['KEY','SECRET','TOKEN','PASSWORD']):
            value=match[2].strip().strip('"\'')
            if len(value)>=8:live_secrets.append(value)
names={Path.home().name,os.environ.get('USERNAME','')}
result=subprocess.run(['git','config','--global','user.name'],capture_output=True,text=True)
if result.returncode==0 and result.stdout.strip():names.add(result.stdout.strip())
aliases=[(str(ROOT),'<workspace>'),(str(Path.home()),'<user-home>')]
machine=os.environ.get('COMPUTERNAME','')
if machine:aliases.append((machine,'<device>'))
aliases.append(('<chat-id>','<chat-id>'))
expanded=[]
for before,after in aliases:
    for variant in {before,before.replace('\\','/'),json.dumps(before)[1:-1]}:expanded.append((variant,after))
expanded.sort(key=lambda x:len(x[0]),reverse=True)
redactions=Counter()


def scrub(text):
    for secret in live_secrets:
        for value in {secret,json.dumps(secret)[1:-1]}:
            count=text.count(value)
            if count:text=text.replace(value,'[REDACTED-LIVE-CREDENTIAL]');redactions['live_credential_occurrences']+=count
    for before,after in expanded:
        count=text.count(before)
        if count:text=text.replace(before,after);redactions['path_device_or_chat_occurrences']+=count
    for name in sorted(names,key=len,reverse=True):
        if not name or len(name)<3:continue
        pattern=r'(?i)(?<![\w@.\-])'+re.escape(name)+r'(?![\w@.\-])'
        text,count=re.subn(pattern,'[redacted-user]',text);redactions['personal_name_occurrences']+=count
        text,count=re.subn(r'(?i)pytest-of-'+re.escape(name), 'pytest-of-user',text);redactions['temporary_username_occurrences']+=count
    text,count=re.subn(r'(?i)\b'+re.escape(Path.home().name)+r'_laptop\b','[redacted-device]',text);redactions['device_occurrences']+=count
    # Scrub other absolute user-profile prefixes in historical diagnostics.
    pattern=r'''(?i)[A-Z]:[/\\]+Users[/\\]+[^/\\\s"'<>]+'''
    def profile(match):
        # Preserve explicitly synthetic usernames in privacy regression fixtures.
        if re.split(r'[/\\]+',match[0])[-1].lower() in {'private','user','example','tester','test-user','sandbox','fixture'}:return match[0]
        redactions['other_profile_occurrences']+=1
        return '<user-home>'
    text=re.sub(pattern,profile,text)
    return text


DEST.mkdir(parents=True,exist_ok=REFRESH)
manifest=[]
for source in sorted(selected):
    relative=source.relative_to(ROOT);raw=source.read_bytes()
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:raise RuntimeError('Nontext file in publication allowlist: '+relative.as_posix())
    public=scrub(text).encode('utf-8')
    target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(public)
    if target.suffix=='.py':ast.parse(public,filename=relative.as_posix())
    if target.suffix=='.json':json.loads(public)
    manifest.append(dict(path=relative.as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),published_sha256=hashlib.sha256(public).hexdigest(),original_bytes=len(raw),published_bytes=len(public),privacy_changed=raw!=public))

# Actual tokens or personal values must not survive into even ignored files in
# this dedicated publication tree. Emails are explicitly permitted.
violations=[]
for item in manifest:
    text=(DEST/item['path']).read_text(encoding='utf-8')
    if any(secret in text for secret in live_secrets):violations.append(dict(path=item['path'],kind='live credential'))
    for before,_ in expanded:
        if before and before in text:violations.append(dict(path=item['path'],kind='private path/device/chat value'))
    profiles=re.findall(r'''(?i)[A-Z]:[/\\]+Users[/\\]+[^/\\\s"'<>]+''',text)
    if any(re.split(r'[/\\]+',x)[-1].lower() not in {'private','user','example','tester','test-user','sandbox','fixture'} for x in profiles):violations.append(dict(path=item['path'],kind='absolute user profile'))
assert not violations, json.dumps(violations)
report=dict(status='passed automated allowlist and known-personal-value checks',generated_at_utc=datetime.now(timezone.utc).isoformat(),files=len(manifest),
    redaction_counts=dict(redactions),emails_permitted=True,live_credential_values_reported=False,populated_environment_file_copied_or_hashed=False,
    original_market_cache_or_user_database_copied=False,raw_logs_traces_or_source_video_copied=False,
    original_private_evidence_retained_locally=True,public_receipts='privacy-derived historical copies; original artifact hashes remain historical, not a certificate for redacted source',
    git_history_audit='Pending: inspect staged tree and all reachable blobs after creating the first commit.',
    limitations=['Known-value and structural scanning is not an inference engine for every possible private fact.','Authored synthetic secrets, public source attribution and license author names are not live owner credentials.','Historical receipt references can identify local artifacts that are intentionally excluded from publication.'])
(DEST/'docs/pause/PRIVACY-REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(DEST/'PUBLICATION-MANIFEST.json').write_text(json.dumps(dict(scope='Allowlisted privacy-derived source/document/evidence snapshot; not original immutable receipt bytes or final acceptance.',files=manifest),indent=2)+'\n',encoding='utf-8')
(DEST/'docs/.nojekyll').write_text('',encoding='utf-8')
# Preserve a local publication audit without exposing the private values.
(ROOT/'docs/pause/PRIVACY-REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
inventory=ROOT/'data/publication/stage-paths.txt'
inventory.write_text('\n'.join([x['path'] for x in manifest]+['docs/pause/PRIVACY-REPORT.json','PUBLICATION-MANIFEST.json','docs/.nojekyll'])+'\n',encoding='utf-8')
print(json.dumps(dict(publication_root=DEST.relative_to(ROOT).as_posix(),files=len(manifest),source_bytes=sum(x['original_bytes'] for x in manifest),published_bytes=sum(x['published_bytes'] for x in manifest),redactions=dict(redactions),private_values_in_output=False)))
