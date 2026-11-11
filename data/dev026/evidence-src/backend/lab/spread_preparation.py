"""Restartable data-free proposal preparation with externally committed batches."""
from pathlib import Path
import gzip,hashlib,json,os,re
from . import spread
from .config import Strategy,canonical,identity
from .research import core_hash,require_current_source

SpreadError=spread.SpreadError

def preparation_contract(settings,binding):
    if not isinstance(binding,str) or not re.fullmatch('[a-f0-9]{64}',binding):raise SpreadError('Preparation requires the original frozen payload binding.')
    return dict(version=1,format='deterministic_gzip_members',settings=settings.model_dump(),binding=binding,
        core_hash=core_hash(),recipe_hash=identity(spread.recipe()),
        total_batches=len(settings.families)*settings.max_batches_per_family,
        planned_proposals=len(settings.families)*settings.max_batches_per_family*settings.batch_size)

def prepare_plan(folder,batch_folder,settings,*,binding,committed,commit,cancel=None,progress=None,expected_plan_id=None):
    """commit(record) must persist ownership-checked authority, not an inferred pass.

    Completed batch files are original artifacts. Final family files concatenate
    those exact gzip members. No market-data callback is accepted by this API.
    """
    require_current_source();folder=Path(folder);batch_folder=Path(batch_folder)
    if folder.parent.resolve()!=batch_folder.parent.resolve() or folder.resolve()==batch_folder.resolve():raise SpreadError('Proposal and batch directories must be distinct owned siblings.')
    owner=folder.parent.resolve();orphans=owner/'preparation-orphans';preserved=[]
    for path in [folder,batch_folder,orphans]:
        if path.is_symlink() or path.is_junction():raise SpreadError('Preparation directories cannot redirect to another location.')
        path.resolve().relative_to(owner);path.mkdir(parents=True,exist_ok=True)
    contract=preparation_contract(settings,binding);contract_hash=identity(contract)
    records=list(committed);total=contract['total_batches'];generated=0
    def check():
        require_current_source()
        if cancel and cancel():raise InterruptedError('Proposal preparation canceled before a committed batch or seal.')
    def owned(path):
        if path.is_symlink() or path.is_junction():raise SpreadError('Preparation artifacts cannot be redirected.')
        path.resolve().relative_to(owner)
    def preserve(path):
        if not path.exists():return
        owned(path);digest=spread.file_hash(path);suffix='.gz' if path.name.endswith('.gz') else '.bin'
        destination=orphans/(digest+suffix);owned(destination)
        if destination.exists():
            if spread.file_hash(destination)!=digest:raise SpreadError('Preserved preparation orphan changed.')
            path.unlink()
        else:path.replace(destination)
        preserved.append(dict(original=path.relative_to(owner).as_posix(),sha256=digest,preserved=destination.relative_to(owner).as_posix()))
    def publish(path,raw):
        owned(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.uncommitted')
        preserve(temporary)
        with temporary.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)
    header=batch_folder/'contract.json'
    owned(header)
    if header.exists():
        try:saved=json.loads(header.read_text(encoding='utf-8'))
        except (OSError,ValueError) as error:raise SpreadError('Preparation contract is unavailable or malformed.') from error
        if saved!=contract:raise SpreadError('Preparation settings/source/binding changed after its first write.')
    else:
        if records:raise SpreadError('Committed batches have no original preparation contract.')
        publish(header,canonical(contract).encode())
    # Reject foreign paths before generating or reusing any proposal batch.
    for path in batch_folder.rglob('*'):
        owned(path)
        if path.is_dir():
            if path.parent!=batch_folder or path.name not in settings.families:raise SpreadError('Unplanned preparation directory.')
        else:
            relative=path.relative_to(batch_folder)
            if relative.as_posix()=='contract.json':continue
            if len(relative.parts)!=2 or relative.parts[0] not in settings.families or not re.fullmatch(r'\d{6}\.json\.gz(?:\.uncommitted)?',relative.parts[1]):raise SpreadError('Foreign preparation artifact.')
            if int(relative.parts[1][:6])>=settings.max_batches_per_family:raise SpreadError('Preparation artifact lies beyond the frozen budget.')
    if len(records)>total:raise SpreadError('Committed proposal batch count exceeds its frozen budget.')
    def coordinate(index):return settings.families[index//settings.max_batches_per_family],index%settings.max_batches_per_family
    def path_for(family,batch):return batch_folder/family/(str(batch).zfill(6)+'.json.gz')
    def validate_record(record,index):
        family,batch=coordinate(index);path=path_for(family,batch)
        required={'contract_hash','core_hash','family','batch','relative_path','bytes','sha256','proposal_count','configurations_hash'}
        if not isinstance(record,dict) or set(record)!=required or record['contract_hash']!=contract_hash or record['core_hash']!=core_hash() or record['family']!=family or type(record['batch']) is not int or record['batch']!=batch or record['relative_path']!=path.relative_to(batch_folder).as_posix() or type(record['proposal_count']) is not int or record['proposal_count']!=settings.batch_size:
            raise SpreadError('Committed proposal coordinate/source/contract changed or is out of order.')
        owned(path)
        try:
            if type(record['bytes']) is not int or path.stat().st_size!=record['bytes'] or spread.file_hash(path)!=record['sha256']:raise SpreadError('Committed proposal batch bytes changed.')
            row=json.loads(gzip.decompress(path.read_bytes()))
            if set(row)!={'family','batch','configurations'} or row['family']!=family or row['batch']!=batch or len(row['configurations'])!=settings.batch_size or identity(row['configurations'])!=record['configurations_hash']:raise SpreadError('Committed proposal batch content changed.')
            for value in row['configurations']:
                cfg=Strategy(**value)
                if cfg.family!=family or cfg.timeframe not in settings.timeframes or canonical(cfg)!=canonical(value):raise SpreadError('Committed proposal configuration changed.')
        except SpreadError:raise
        except (OSError,ValueError,TypeError,KeyError) as error:raise SpreadError('Committed proposal batch is missing or malformed.') from error
    for index,record in enumerate(records):check();validate_record(record,index)
    if expected_plan_id is not None:
        if len(records)!=total:raise SpreadError('A sealed plan requires every committed preparation batch.')
        check();plan=spread.ProposalPlan.open(folder,expected_plan_id)
        if plan.manifest.get('preparation_contract_hash')!=contract_hash:raise SpreadError('Sealed plan preparation binding changed.')
        return dict(plan=plan,generated_batches=0,reused_batches=len(records),preserved_orphans=preserved)
    # A crash may leave an unanchored manifest, but its bytes must agree with
    # the deterministic reconstruction below. An anchored plan is never rebuilt.
    owned(folder/'manifest.json')
    existing_manifest=(folder/'manifest.json').read_bytes() if (folder/'manifest.json').exists() else None
    for index in range(len(records),total):
        check();family,batch=coordinate(index);path=path_for(family,batch);preserve(path)
        configurations=[spread.draw(settings,family,batch,ordinal) for ordinal in range(settings.batch_size)]
        raw=canonical(dict(family=family,batch=batch,configurations=configurations)).encode()+b'\n'
        zipped=gzip.compress(raw,mtime=0);publish(path,zipped)
        record=dict(contract_hash=contract_hash,core_hash=core_hash(),family=family,batch=batch,relative_path=path.relative_to(batch_folder).as_posix(),bytes=len(zipped),sha256=spread.file_hash(path),proposal_count=settings.batch_size,configurations_hash=identity(configurations))
        commit(record);records.append(record);generated+=1
        if progress:progress(len(records),total)
    files={}
    expected_names={'manifest.json',*[family+'.jsonl.gz' for family in settings.families],*[family+'.jsonl.gz.uncommitted' for family in settings.families],'manifest.json.uncommitted'}
    if any(p.name not in expected_names or p.is_dir() for p in folder.iterdir()):raise SpreadError('Unplanned proposal assembly artifact.')
    for family in settings.families:
        check();path=folder/(family+'.jsonl.gz');owned(path);temporary=path.with_name(path.name+'.uncommitted');preserve(temporary)
        with temporary.open('wb') as destination:
            for batch in range(settings.max_batches_per_family):
                check();source=path_for(family,batch)
                owned(source);digest=hashlib.sha256();size=0
                with source.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(65536),b''):check();destination.write(chunk);digest.update(chunk);size+=len(chunk)
                original=records[settings.families.index(family)*settings.max_batches_per_family+batch]
                if size!=original['bytes'] or digest.hexdigest()!=original['sha256']:raise SpreadError('Committed batch changed while assembling the sealed proposal source.')
            destination.flush();os.fsync(destination.fileno())
        if path.exists():
            if spread.file_hash(path)!=spread.file_hash(temporary):preserve(path)
            else:temporary.unlink()
        if temporary.exists():temporary.replace(path)
        files[family]=dict(bytes=path.stat().st_size,sha256=spread.file_hash(path))
    manifest=dict(version=spread.VERSION,settings=settings.model_dump(),core_hash=core_hash(),recipe=spread.recipe(),recipe_hash=identity(spread.recipe()),
        planned_proposals=contract['planned_proposals'],files=files,preparation_contract_hash=contract_hash)
    raw=canonical(manifest).encode()
    if existing_manifest is not None and existing_manifest!=raw:raise SpreadError('Unanchored proposal manifest differs from its committed batches.')
    check();publish(folder/'manifest.json',raw);plan=spread.ProposalPlan(folder,manifest);plan.verify()
    return dict(plan=plan,generated_batches=generated,reused_batches=len(records)-generated,preserved_orphans=preserved)
