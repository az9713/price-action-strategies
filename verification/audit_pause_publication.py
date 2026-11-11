"""Audit actual staged or reachable Git blobs for known owner secrets and private identifiers."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,re,subprocess,sys

ROOT=Path(__file__).resolve().parent.parent
REPO=Path(sys.argv[1]).resolve()
HISTORY='--history' in sys.argv
assert (REPO/'.git').is_dir()


def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)


secrets=[]
env=ROOT/'.env'
if env.exists():
    for line in env.read_text(encoding='utf-8-sig').splitlines():
        match=re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)',line)
        if match and any(x in match[1].upper() for x in ['KEY','SECRET','TOKEN','PASSWORD']):
            value=match[2].strip().strip('"\'')
            if len(value)>=8:secrets.append(value)
private=[str(ROOT),str(Path.home()),os.environ.get('COMPUTERNAME','')]
names={Path.home().name,os.environ.get('USERNAME','')}
name=subprocess.run(['git','config','--global','user.name'],capture_output=True,text=True).stdout.strip()
if name:names.add(name)
records=git('ls-files','--stage','-z').decode('utf-8').split('\0')
paths=[];objects=set()
for record in records:
    if not record:continue
    metadata,path=record.split('\t',1);mode,oid,stage=metadata.split()
    assert stage=='0' and mode in {'100644','100755'},'Unmerged or nonregular staged file.'
    parts=Path(path).parts
    assert not any(p in {'.git','.venv','node_modules','__pycache__','test-results','playwright-report'} for p in parts)
    assert not (Path(path).name.startswith('.env') and Path(path).name!='.env.example')
    assert Path(path).suffix.lower() not in {'.db','.sqlite','.sqlite3','.parquet','.arrow','.mp4','.mp3','.webm','.zip','.log'}
    if path.startswith('data/'):assert path.startswith(('data/dev026/src/','data/dev026/next-src/','data/dev026/evidence-src/','data/dev027/research-src/'))
    paths.append(path);objects.add(oid)
commits=[]
if HISTORY:
    commits=git('rev-list','--all').decode().splitlines()
    for line in git('rev-list','--objects','--all').decode('utf-8').splitlines():objects.add(line.split(' ',1)[0])
    for line in git('log','--all','--format=%an%x00%cn').decode('utf-8').splitlines():
        assert line.split('\0')==['Project Maintainer','Project Maintainer'],'Personal Git author or committer name.'
output=subprocess.check_output(['git','cat-file','--batch'],cwd=REPO,input=('\n'.join(sorted(objects))+'\n').encode())
cursor=0;scanned=0;total=0;violations=[]
while cursor<len(output):
    end=output.index(b'\n',cursor);header=output[cursor:end].decode().split();assert len(header)==3
    oid,kind,length=header;length=int(length);raw=output[end+1:end+1+length];cursor=end+length+2
    assert len(raw)==length and output[cursor-1:cursor]==b'\n'
    if kind!='blob':continue
    scanned+=1;total+=length
    for value in secrets:
        if value.encode() in raw:violations.append(dict(object=oid,kind='live credential'))
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:
        assert raw.startswith(b'\x89PNG\r\n\x1a\n'),'Unexpected binary publication object.'
        continue
    for value in private:
        if not value:continue
        for variant in {value,value.replace('\\','/'),json.dumps(value)[1:-1]}:
            if variant.lower() in text.lower():violations.append(dict(object=oid,kind='private path or device'))
    without_emails=re.sub(r'[A-Za-z0-9_.+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}','[permitted-email]',text)
    for value in names:
        if value and len(value)>=3 and re.search(r'(?i)(?<![\w@.\-])'+re.escape(value)+r'(?![\w@.\-])',without_emails):violations.append(dict(object=oid,kind='personal name'))
    if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text):violations.append(dict(object=oid,kind='private key material'))
assert not violations,json.dumps(violations)
result=dict(passed=True,scope='All actual staged blobs plus all reachable Git objects' if HISTORY else 'All actual staged Git blobs',
    audited_at_utc=datetime.now(timezone.utc).isoformat(),staged_files=len(paths),unique_blob_objects=scanned,total_blob_bytes=total,
    reachable_commit_count=len(commits),reachable_commits=commits,generic_git_author_and_committer=bool(commits),emails_permitted=True,
    populated_env_read_only_for_in_memory_matching=True,populated_env_copied_hashed_or_reported=False,
    live_credentials_or_known_private_identifiers_found=0,forbidden_data_paths_found=0,
    limitations=['Known-value and structural checks, not a proof against arbitrary undisclosed private facts.','Authored synthetic credentials/user paths and public license/source attribution remain.'])
destination=ROOT/'docs/pause'/('git-history-audit.json' if HISTORY else 'staged-privacy-audit.json')
destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
