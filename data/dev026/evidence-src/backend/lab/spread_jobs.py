"""Owned append-only spread journal and explicitly staged signal-trial provenance."""
import json,re,time,sqlite3
from .config import canonical,identity
from .store import StateError,SPREAD_SELECTION_PREDICATE,SPREAD_SELECTION_INDEX_SQL
from .research import core_hash,require_current_source
from .spread import SpreadSettings

PROVENANCE='staged_prespecified'
WINDOW='qualification'
def digest(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise StateError('Spread evidence requires a complete SHA-256 identity.')
    return value
def integer(value):
    if type(value) is not int or value<0:raise StateError('Spread counters require nonnegative integers.')
    return value
def coordinate(settings,event):
    family=event.get('family');batch=integer(event.get('batch'));ordinal=integer(event.get('ordinal'))
    if family not in settings.families or batch>=settings.max_batches_per_family or ordinal>=settings.batch_size:raise StateError('Signal coordinate lies outside the frozen proposal plan.')
    digest(event.get('config_id'))
    return settings.families.index(family)*settings.max_batches_per_family*settings.batch_size+batch*settings.batch_size+ordinal
def initial(settings):
    return dict(stage='queued',preparation_contract_hash=None,proposal_plan_id=None,planned_batches=len(settings.families)*settings.max_batches_per_family,
        planned_proposals=len(settings.families)*settings.max_batches_per_family*settings.batch_size,target_versions=len(settings.families)*settings.per_family,
        frozen_batches=0,frozen_proposals=0,probe_plans=0,probe_attempts=0,committed_probes=0,rejected_signal_versions=0,
        selected_versions=0,duplicate_proposals=0,unprobed_proposals=0,selection_manifest_hash=None,qualified_complete=None,
        family_counts={f:0 for f in settings.families},next_family=0,next_batch=0,current_batch=None,current_probe=None)

def projection(previous,event,settings,context):
    p=json.loads(canonical(previous));kind=event.get('kind')
    if kind=='preparation_started':
        if p['stage']!='queued':raise StateError('Preparation was already started.')
        p.update(stage='preparing',preparation_contract_hash=digest(event.get('contract_hash')))
    elif kind=='preparation_batch':
        if p['stage']!='preparing' or p['frozen_batches']>=p['planned_batches']:raise StateError('Preparation batch is out of phase.')
        r=event['record'];index=p['frozen_batches'];family=settings.families[index//settings.max_batches_per_family];batch=index%settings.max_batches_per_family
        if r.get('family')!=family or type(r.get('batch')) is not int or r['batch']!=batch or r.get('contract_hash')!=p['preparation_contract_hash'] or r.get('core_hash')!=core_hash() or type(r.get('proposal_count')) is not int or r['proposal_count']!=settings.batch_size:raise StateError('Preparation checkpoint differs from the frozen coordinate/source.')
        digest(r.get('sha256'));digest(r.get('configurations_hash'));integer(r.get('bytes'))
        if r.get('relative_path')!=family+'/'+str(batch).zfill(6)+'.json.gz':raise StateError('Preparation checkpoint path changed.')
        p['frozen_batches']+=1;p['frozen_proposals']+=r['proposal_count']
    elif kind=='preparation_sealed':
        if p['stage']!='preparing' or p['frozen_batches']!=p['planned_batches']:raise StateError('Every proposal batch must be committed before sealing.')
        p.update(stage='prepared',proposal_plan_id=digest(event.get('plan_id')))
    elif kind=='selection_started':
        if p['stage']!='prepared' or event.get('plan_id')!=p['proposal_plan_id'] or event.get('context')!=context:raise StateError('Qualification does not own the sealed proposal plan/context.')
        p['stage']='selecting'
    elif kind=='batch_started':
        if p['stage']!='selecting' or p['current_batch'] is not None or p['next_family']>=len(settings.families) or event.get('family')!=settings.families[p['next_family']] or event.get('batch')!=p['next_batch']:raise StateError('Qualification batch order changed.')
        digest(event.get('configuration_hash'));p['current_batch']=dict(family=event['family'],batch=event['batch'],winner=None,failed=[]);p['current_probe']=None
    elif kind in {'probe_planned','probe_started','probe_completed','version_selected'}:
        coordinate(settings,event);batch=p['current_batch']
        if p['stage']!='selecting' or batch is None or event['family']!=batch['family'] or event['batch']!=batch['batch']:raise StateError('Signal event does not own the active batch.')
        point={k:event[k] for k in ['family','batch','ordinal','config_id']}
        if kind=='probe_planned':
            if p['current_probe'] is not None and p['current_probe']['state']!='completed':raise StateError('A preceding signal probe has no committed result.')
            p['current_probe']=dict(**point,attempt=0,state='planned',signal_count=None);p['probe_plans']+=1
        else:
            probe=p['current_probe']
            if probe is None or any(probe[k]!=v for k,v in point.items()):raise StateError('Signal attempt identity changed.')
            if kind=='probe_started':
                if type(event.get('attempt')) is not int or event['attempt']!=probe['attempt']+1 or probe['state']=='completed':raise StateError('Signal retry needs its next distinct ordinal.')
                probe.update(state='running',attempt=event['attempt']);p['probe_attempts']+=1
            elif kind=='probe_completed':
                evidence=event.get('evidence',{});count=integer(evidence.get('signal_count'));digest(evidence.get('evidence_sha256'))
                if probe['state']!='running' or event.get('attempt')!=probe['attempt']:raise StateError('Signal result has no matching started attempt.')
                probe.update(state='completed',signal_count=count);p['committed_probes']+=1
                if count<settings.minimum_signals:p['rejected_signal_versions']+=1;batch['failed'].append(event['ordinal'])
            else:
                if probe['state']!='completed' or probe['signal_count']<settings.minimum_signals or event.get('signal_count')!=probe['signal_count'] or batch['winner'] is not None or p['family_counts'][event['family']]>=settings.per_family:raise StateError('Selected version has no eligible committed primary signals.')
                if identity(event.get('configuration'))!=event['config_id']:raise StateError('Selected complete configuration changed.')
                batch['winner']=event['ordinal'];p['selected_versions']+=1;p['family_counts'][event['family']]+=1
    elif kind=='batch_finished':
        b=p['current_batch'];outcomes=event.get('outcomes')
        if b is None or event.get('family')!=b['family'] or event.get('batch')!=b['batch'] or not isinstance(outcomes,list) or len(outcomes)!=settings.batch_size or event.get('selected_ordinal')!=b['winner']:raise StateError('Qualification outcomes differ from the active batch.')
        if p['current_probe'] is not None and p['current_probe']['state']!='completed':raise StateError('An interrupted signal probe cannot disappear from a finished batch.')
        for ordinal,row in enumerate(outcomes):
            if row.get('ordinal')!=ordinal:raise StateError('Every frozen proposal needs one ordered classification.')
            digest(row.get('config_id'));status=row.get('status')
            if status not in {'duplicate','not_probed','insufficient_signals','selected'}:raise StateError('Unknown spread proposal classification.')
            if (status=='selected')!=(ordinal==b['winner']) or (status=='insufficient_signals')!=(ordinal in b['failed']):raise StateError('Probe qualification counts differ from their saved outcomes.')
            p['duplicate_proposals']+=status=='duplicate';p['unprobed_proposals']+=status=='not_probed'
        if p['family_counts'][b['family']]==settings.per_family or b['batch']+1==settings.max_batches_per_family:p['next_family']+=1;p['next_batch']=0
        else:p['next_batch']+=1
        p['current_batch']=None;p['current_probe']=None
    elif kind=='selection_finished':
        exhausted=[f for f in settings.families if p['family_counts'][f]!=settings.per_family];complete=not exhausted
        if p['stage']!='selecting' or p['current_batch'] is not None or p['next_family']!=len(settings.families) or type(event.get('complete')) is not bool or event['complete']!=complete or event.get('selected_count')!=p['selected_versions'] or event.get('exhausted_families')!=exhausted:raise StateError('Qualification finished without the complete declared family outcomes.')
        selected_hash=digest(event.get('selection_manifest_hash')) if complete else None
        if not complete and event.get('selection_manifest_hash') is not None:raise StateError('An exhausted pool has no successful selected-set identity.')
        p.update(stage='qualified' if complete else 'exhausted',qualified_complete=complete,selection_manifest_hash=selected_hash)
    else:raise StateError('Unknown spread journal event.')
    return p

def staged_freeze(store,db,job,payload_hash,plan_id,settings,event):
    part=coordinate(settings,event);tid=identity(dict(job_id=job['id'],part=part,window=WINDOW))
    if db.execute('SELECT 1 FROM trial_plans WHERE job_id=? AND (id=? OR config_id=?)',(job['id'],tid,event['config_id'])).fetchone():raise StateError('A signal configuration/coordinate is already registered.')
    phase=dict(payload_hash=payload_hash,proposal_plan_id=plan_id,part=part,window=WINDOW,role='signal_probe',config_id=event['config_id'],coordinate={k:event[k] for k in ['family','batch','ordinal','config_id']})
    plan_hash=identity(phase);now=time.time()
    db.execute('INSERT INTO trial_plans(id,job_id,part,window,role,config_id,plan_hash,provenance,state,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(tid,job['id'],part,WINDOW,'signal_probe',event['config_id'],plan_hash,PROVENANCE,'planned',now,now))
    store.event('staged_trial_frozen',job['id'],phase|dict(trial_id=tid,plan_hash=plan_hash),db)

def verify_staged(store,job,db):
    payload=json.loads(job['payload']) if isinstance(job['payload'],str) else job['payload'];binding=identity(payload);settings=SpreadSettings(**payload['settings'])
    rows={r['id']:dict(r) for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? AND provenance=?',(job['id'],PROVENANCE))};seen=set();planned={};starts={};completed={};sealed=None
    try:
        for raw in db.execute("SELECT details FROM events WHERE entity_id=? AND kind='spread_protocol' ORDER BY id",(job['id'],)):
            envelope=json.loads(raw['details']);event=envelope['event'];kind=event['kind']
            if kind=='preparation_sealed':
                if sealed is not None:raise StateError('Proposal plan was sealed more than once.')
                sealed=digest(event['plan_id'])
            elif kind in {'probe_planned','probe_started','probe_completed'}:
                if sealed is None:raise StateError('A signal occurrence precedes the proposal seal.')
                part=coordinate(settings,event)
                if kind=='probe_planned':
                    if part in planned:raise StateError('A signal occurrence was frozen more than once.')
                    planned[part]=event['config_id'];starts[part]=[]
                else:
                    if planned.get(part)!=event['config_id']:raise StateError('Signal attempt has no matching protocol plan.')
                    ordinal=integer(event['attempt'])
                    if kind=='probe_started':
                        if ordinal!=len(starts[part])+1 or not isinstance(envelope['owner'],str) or not envelope['owner']:raise StateError('Signal attempt owner/sequence changed.')
                        starts[part].append((ordinal,envelope['owner']))
                    else:
                        if ordinal!=len(starts[part]) or (part,ordinal) in completed:raise StateError('Signal completion has no distinct started attempt.')
                        completed[(part,ordinal)]=(digest(event['evidence']['evidence_sha256']),digest(envelope['artifact_sha256']))
        for raw in db.execute("SELECT details FROM events WHERE entity_id=? AND kind='staged_trial_frozen' ORDER BY id",(job['id'],)):
            phase=json.loads(raw['details']);tid=phase.get('trial_id');base={k:v for k,v in phase.items() if k not in {'trial_id','plan_hash'}}
            if tid not in rows or tid in seen or phase.get('payload_hash')!=binding or phase.get('plan_hash')!=identity(base):raise StateError('Staged signal plan provenance changed.')
            r=rows[tid];part=coordinate(settings,phase['coordinate']);expected=dict(part=part,window=WINDOW,role='signal_probe',config_id=planned.get(part),plan_hash=phase['plan_hash'])
            if phase.get('proposal_plan_id')!=sealed or any(r[k]!=v for k,v in expected.items()) or any(phase.get(k)!=v for k,v in expected.items()):raise StateError('Staged signal occurrence differs from its original protocol parent.')
            attempts=[dict(a) for a in db.execute('SELECT * FROM trial_attempts WHERE trial_id=? ORDER BY ordinal',(tid,))]
            if r['attempts']!=len(starts[part]) or [(a['ordinal'],a['owner']) for a in attempts]!=starts[part]:raise StateError('Recorded signal attempts/owners differ from original protocol starts.')
            for a in attempts:
                result=completed.get((part,a['ordinal']))
                if result is not None and (a['computed_sha256'],a['artifact_sha256'])!=result:raise StateError('Signal attempt artifact differs from the committed protocol.')
            latest=completed.get((part,r['attempts']))
            if latest is not None and (r['computed_sha256'],r['artifact_sha256'])!=latest:raise StateError('Signal occurrence output differs from its committed evidence.')
            seen.add(tid)
        if seen!=set(rows) or {r['part'] for r in rows.values()}!=set(planned):raise StateError('A staged signal occurrence has no original frozen protocol/phase event.')
    except StateError:raise
    except (ValueError,TypeError,KeyError) as error:raise StateError('Staged signal provenance is malformed.') from error

def saved_projection(db,job,settings):
    p=initial(settings);count=0;head=None
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='spread_state'").fetchone():
        r=db.execute('''SELECT substr(payload_sha256,1,65) payload_sha256,
            CASE WHEN typeof(event_count)='integer' THEN event_count ELSE NULL END event_count,
            substr(head_sha256,1,65) head_sha256,substr(projection_sha256,1,65) projection_sha256,
            length(CAST(projection AS BLOB)) bytes,substr(CAST(projection AS BLOB),1,65537) projection
            FROM spread_state WHERE job_id=?''',(job['id'],)).fetchone()
        if r is not None:
            if r['payload_sha256']!=job['payload_sha256'] or r['bytes']>65536:raise StateError('Spread metadata binding or byte budget changed.')
            try:p=json.loads(r['projection'])
            except (ValueError,TypeError) as error:raise StateError('Spread status metadata is malformed.') from error
            if not isinstance(p,dict) or identity(p)!=r['projection_sha256']:raise StateError('Spread status metadata failed verification.')
            count=integer(r['event_count']);head=r['head_sha256']
            if count:digest(head)
            elif head is not None:raise StateError('An empty spread journal has an unexpected saved head.')
    return p,count,head

def saved_account_link(store,db,job,p):
    children=store.spread_children(job['id'],db)
    count=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(job['id'],)).fetchone()[0]
    link=None
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='spread_account_links'").fetchone():
        link=db.execute('SELECT substr(child_id,1,33) child_id,length(CAST(child_id AS BLOB)) bytes FROM spread_account_links WHERE parent_id=?',(job['id'],)).fetchone()
    if count==0 and link is None:
        if children:raise StateError('An original account child remains but its parent relationship is missing; a replacement is not authorized.')
        return None
    if count!=1 or link is None or link['bytes']!=32 or not isinstance(link['child_id'],str) or not re.fullmatch('[a-f0-9]{32}',link['child_id']):raise StateError('Original account relationship metadata is missing or inconsistent; a replacement job is not authorized.')
    if children!=[link['child_id']]:raise StateError('Original child reservation differs from the saved account relationship; a replacement is not authorized.')
    raw=db.execute("SELECT length(CAST(details AS BLOB)) bytes,substr(CAST(details AS BLOB),1,4097) details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(job['id'],)).fetchone()
    if raw['bytes']>4096:raise StateError('Original account relationship metadata exceeds its saved envelope.')
    try:
        event=json.loads(raw['details'])
        if not isinstance(event,dict) or set(event)!={'child_id','job_id','payload_hash','result_sha256','selection_manifest_hash'}:raise StateError('Original account relationship event is malformed.')
        binding={k:v for k,v in event.items() if k!='child_id'}
        if event['child_id']!=link['child_id'] or event['job_id']!=job['id'] or event['payload_hash']!=job['payload_sha256'] or event['selection_manifest_hash']!=p.get('selection_manifest_hash'):raise StateError('Original account relationship binding changed.')
        digest(event['result_sha256']);digest(event['selection_manifest_hash'])
        child=store.job_status(link['child_id'])
        if child['kind']!='spread_accounts' or not child['index_integrity'] or child['payload'].get('spread_parent')!=binding:raise StateError('Saved account metadata differs from its original parent relationship.')
    except StateError:raise
    except (ValueError,TypeError,KeyError) as error:raise StateError('Original account relationship metadata is malformed.') from error
    return child|dict(result_url='/api/jobs/'+child['id']+'/result-summary',registry_url='/api/trials?job_id='+child['id'])

def bounded_status(store,job_id):
    job=store.job_status(job_id)
    if job['kind']!='spread' or not job['index_integrity'] or 'settings' not in job['payload'] or 'context' not in job['payload']:raise StateError('Spread input metadata is unverified; inspect original inputs or repair its derived index.')
    settings=SpreadSettings(**job['payload']['settings'])
    with store.db() as db:
        db.execute('BEGIN');p,count,head=saved_projection(db,job,settings);account=saved_account_link(store,db,job,p)
    status={k:v for k,v in p.items() if k not in {'current_batch','current_probe'}}|dict(event_count=count,head_sha256=head)
    value=dict(job=job,spread=status,account_job=account,integrity_scope='Bounded saved metadata and original account relationship; full signal/artifact integrity is checked before worker reuse.',inputs_url=job['inputs_url'],result_url='/api/spreads/'+job_id+'/result',events_url='/api/spreads/'+job_id+'/events',selections_url='/api/spreads/'+job_id+'/selections',registry_url='/api/trials?job_id='+job_id)
    if len(canonical(value).encode())>65536:raise StateError('Spread status exceeds its64KiB metadata envelope; complete original inputs remain available.')
    return value

def selection_page(store,job_id,after=0,limit=50):
    integer(after)
    if type(limit) is not int or not 1<=limit<=100:raise StateError('Choose a selected-rule page size1–100.')
    status=bounded_status(store,job_id);job=status['job'];settings=SpreadSettings(**job['payload']['settings']);versions=[]
    try:
        with store.db() as db:
            db.execute('BEGIN')
            schema=db.execute("SELECT substr(sql,1,4097) sql,length(CAST(sql AS BLOB)) bytes FROM sqlite_master WHERE type='index' AND name='spread_selected_events'").fetchone()
            if schema is None or schema['bytes']>4096 or ''.join(schema['sql'].split()).lower()!=''.join(SPREAD_SELECTION_INDEX_SQL.split()).lower():raise StateError('Saved selection seek index is unavailable or incompatible; original selection export remains available.')
            p,_,_=saved_projection(db,job,settings);expected=integer(p.get('selected_versions'))
            where='entity_id=? AND '+SPREAD_SELECTION_PREDICATE
            count=db.execute('SELECT COUNT(*) FROM events INDEXED BY spread_selected_events WHERE '+where,(job_id,)).fetchone()[0]
            if count!=expected or count>len(settings.families)*settings.per_family:raise StateError('Saved selected-rule count differs from its original indexed records.')
            offset=db.execute('SELECT COUNT(*) FROM events INDEXED BY spread_selected_events WHERE '+where+' AND id<=?',(job_id,after)).fetchone()[0]
            rows=list(db.execute('SELECT id,length(CAST(details AS BLOB)) bytes,substr(CAST(details AS BLOB),1,16385) details FROM events INDEXED BY spread_selected_events WHERE '+where+' AND id>? ORDER BY id LIMIT ?',(job_id,after,limit+1)))
        for raw in rows[:limit]:
            if raw['bytes']>16384:raise StateError('Saved selected-rule envelope exceeds its16KiB budget.')
            r=json.loads(raw['details']);body={k:r[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']};integer(body['sequence']);event=body['event']
            if set(r)!=set(body)|{'event_sha256'} or identity(body)!=r['event_sha256'] or body['payload_sha256']!=job['payload_sha256'] or not isinstance(event,dict) or event.get('kind')!='version_selected':raise StateError('Saved selected-rule envelope identity changed.')
            cfg=event.get('configuration');cid=digest(event.get('config_id'));signals=integer(event.get('signal_count'))
            if not isinstance(cfg,dict) or identity(cfg)!=cid or cfg.get('family')!=event.get('family') or signals<settings.minimum_signals:raise StateError('Saved selected-rule configuration or primary-signal count changed.')
            versions.append(dict(event_id=raw['id'],sequence=body['sequence'],config_id=cid,configuration=cfg,signal_count=signals,family=event['family'],batch=event['batch'],ordinal=event['ordinal']))
    except StateError:raise
    except (sqlite3.Error,ValueError,TypeError,KeyError) as error:raise StateError('Saved selection list is unavailable or malformed; original selection export remains available.') from error
    value=dict(versions=versions,selected_count=count,offset=offset,has_more=len(rows)>limit,next_after=versions[-1]['event_id'] if versions else after,
        integrity_scope='Requested original envelope/input/configuration identities only; this page is not complete-prefix or final-product certification.')
    if len(canonical(value).encode())>2097152:raise StateError('Saved selected-rule page exceeds its2MiB envelope.')
    return value

def event_page(store,job_id,after=0,limit=20):
    integer(after)
    if type(limit) is not int or not 1<=limit<=20:raise StateError('Choose a journal page size1–20.')
    status=bounded_status(store,job_id);events=[]
    with store.db() as db:
        rows=list(db.execute("SELECT id,length(CAST(details AS BLOB)) bytes,substr(CAST(details AS BLOB),1,65537) details FROM events WHERE entity_id=? AND kind='spread_protocol' AND id>? ORDER BY id LIMIT ?",(job_id,after,limit+1)))
    for raw in rows[:limit]:
        if raw['bytes']>65536:raise StateError('Spread journal record exceeds its64KiB envelope.')
        try:
            r=json.loads(raw['details']);body={k:r[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']}
            integer(r['sequence'])
            if set(r)!=set(body)|{'event_sha256'} or identity(body)!=r['event_sha256'] or r['payload_sha256']!=status['job']['payload_sha256']:raise StateError('Spread journal page integrity failed.')
        except StateError:raise
        except (ValueError,TypeError,KeyError) as error:raise StateError('Spread journal page is malformed.') from error
        events.append(dict(id=raw['id'],**r))
    return dict(events=events,has_more=len(rows)>limit,next_after=events[-1]['id'] if events else after,integrity_scope='Requested original envelopes; this page is not complete-prefix or final-product certification.')

class SpreadJournal:
    def __init__(self,store,job,owner,stream=False):
        self.store=store;self.job=job;self.owner=owner;self.streaming=stream;self.binding=identity(job['payload']);self.settings=SpreadSettings(**job['payload']['settings']);self.context=job['payload']['context']
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS spread_state(job_id TEXT PRIMARY KEY REFERENCES jobs(id),payload_sha256 TEXT NOT NULL,event_count INTEGER NOT NULL,head_sha256 TEXT,projection TEXT NOT NULL,projection_sha256 TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE');self._binding(db)
            if db.execute('SELECT 1 FROM spread_state WHERE job_id=?',(job['id'],)).fetchone() is None:
                store._trials.owned(db,job['id'],owner);p=initial(self.settings)
                db.execute('INSERT INTO spread_state VALUES(?,?,?,?,?,?)',(job['id'],self.binding,0,None,canonical(p),identity(p)))
            db.execute('COMMIT')
        self.load()

    def _binding(self,db):
        r=db.execute('SELECT * FROM job_input_index WHERE job_id=?',(self.job['id'],)).fetchone()
        if r is None or r['payload_sha256']!=self.binding:raise StateError('Spread original input index binding changed.')
        try:self.store._input_index.checked({k:r[k] for k in ['payload_sha256','projection','list_projection','projection_sha256','provenance']})
        except (ValueError,TypeError,KeyError) as error:raise StateError('Spread original input metadata is unverified.') from error
        original=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='trial_plan_frozen' ORDER BY id LIMIT 1",(self.job['id'],)).fetchone()
        if original is None or json.loads(original['details']).get('payload_hash')!=self.binding:raise StateError('Spread original frozen payload event changed.')

    def _state(self,db):
        r=db.execute('SELECT * FROM spread_state WHERE job_id=?',(self.job['id'],)).fetchone()
        if r is None or r['payload_sha256']!=self.binding:raise StateError('Spread state belongs to different inputs.')
        try:p=json.loads(r['projection'])
        except (ValueError,TypeError) as error:raise StateError('Spread bounded projection is malformed.') from error
        if identity(p)!=r['projection_sha256']:raise StateError('Spread bounded projection changed.')
        return dict(r),p

    def load(self):
        require_current_source()
        with self.store.db() as db:
            db.execute('BEGIN');self._binding(db);self.store._trials.verify(self.job['id'],db);state,p=self._state(db)
            head=None;count=0;through=0;events=[];envelopes=[];derived=initial(self.settings)
            for raw in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_protocol' ORDER BY id",(self.job['id'],)):
                try:r=json.loads(raw['details']);body={k:r[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']}
                except (KeyError,ValueError,TypeError) as error:raise StateError('Spread journal envelope is malformed.') from error
                if set(r)!=set(body)|{'event_sha256'} or type(r.get('sequence')) is not int or r['sequence']!=count or r.get('previous')!=head or r.get('payload_sha256')!=self.binding or r.get('event_sha256')!=identity(body):raise StateError('Spread journal sequence/hash chain changed.')
                derived=projection(derived,r['event'],self.settings,self.context);count+=1;through=raw['id'];head=r['event_sha256']
                if not self.streaming:events.append(r['event']);envelopes.append(r)
            if state['event_count']!=count or state['head_sha256']!=head or derived!=p:raise StateError('Spread journal head/count/projection differs from its original events.')
        self.count=count;self.head=head;self.replay_count=count;self.replay_head=head;self.replay_through=through;self.envelopes=envelopes;self.events=events
        return self.iter_events(through_id=through) if self.streaming else events

    def iter_envelopes(self,through_id=None):
        if through_id is not None:
            if through_id!=self.replay_through:raise StateError('Replay requires the fully validated original cutoff.')
            cutoff=through_id;expected_count=self.replay_count;expected_head=self.replay_head
        else:
            with self.store.db() as db:
                db.execute('BEGIN');state,_=self._state(db)
                cutoff=db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE entity_id=? AND kind='spread_protocol'",(self.job['id'],)).fetchone()[0]
            expected_count=state['event_count'];expected_head=state['head_sha256']
        cursor=0;count=0;head=None
        while True:
            with self.store.db() as db:rows=list(db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_protocol' AND id>? AND id<=? ORDER BY id LIMIT 16",(self.job['id'],cursor,cutoff)))
            if not rows:break
            for raw in rows:
                try:r=json.loads(raw['details']);body={k:r[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']}
                except (ValueError,TypeError,KeyError) as error:raise StateError('Streamed spread journal envelope is malformed.') from error
                if set(r)!=set(body)|{'event_sha256'} or type(r['sequence']) is not int or r['sequence']!=count or r['previous']!=head or r['payload_sha256']!=self.binding or identity(body)!=r['event_sha256']:raise StateError('Streamed spread journal chain changed after validation.')
                count+=1;head=r['event_sha256'];cursor=raw['id'];yield r
        if count!=expected_count or head!=expected_head:raise StateError('Streamed spread replay cutoff/head changed.')

    def iter_events(self,through_id=None):
        for envelope in self.iter_envelopes(through_id):yield envelope['event']

    def status(self):
        with self.store.db() as db:self._binding(db);state,p=self._state(db)
        return {k:v for k,v in p.items() if k not in {'current_batch','current_probe'}}|dict(event_count=state['event_count'],head_sha256=state['head_sha256'])

    def append(self,event,expected_count=None,artifact_sha256=None):
        require_current_source();event=json.loads(canonical(event));expected=integer(self.count if expected_count is None else expected_count)
        if event.get('kind')!='probe_completed' and artifact_sha256 is not None:raise StateError('Only completed signal evidence carries an artifact binding.')
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self.store._trials.owned(db,self.job['id'],self.owner);self._binding(db);state,p=self._state(db)
            if state['event_count']!=expected or state['head_sha256']!=self.head:raise StateError('Another append changed the spread journal head.')
            following=projection(p,event,self.settings,self.context);kind=event['kind']
            if kind=='probe_planned':staged_freeze(self.store,db,self.job,self.binding,p['proposal_plan_id'],self.settings,event)
            elif kind in {'probe_started','probe_completed'}:
                part=coordinate(self.settings,event);r=self.store._trials.row(db,self.job['id'],part,WINDOW);now=time.time()
                if r['role']!='signal_probe' or r['config_id']!=event['config_id']:raise StateError('Signal attempt does not own its staged occurrence.')
                if kind=='probe_started':
                    if r['state'] in {'running','computed'} or event['attempt']!=r['attempts']+1:raise StateError('Signal attempt is already active or has a changed ordinal.')
                    db.execute('INSERT INTO trial_attempts(trial_id,ordinal,owner,started,state) VALUES(?,?,?,?,?)',(r['id'],event['attempt'],self.owner,now,'running'))
                    db.execute("UPDATE trial_plans SET state='running',attempts=?,updated=? WHERE id=?",(event['attempt'],now,r['id']))
                else:
                    digest(artifact_sha256);evidence=event['evidence']
                    if r['state']!='running' or r['attempts']!=event['attempt']:raise StateError('Signal completion has no owned running attempt.')
                    db.execute("UPDATE trial_plans SET state='checkpointed',computed_sha256=?,artifact_sha256=?,updated=? WHERE id=?",(evidence['evidence_sha256'],artifact_sha256,now,r['id']))
                    db.execute("UPDATE trial_attempts SET state='checkpointed',computed_sha256=?,artifact_sha256=?,finished=? WHERE trial_id=? AND ordinal=?",(evidence['evidence_sha256'],artifact_sha256,now,r['id'],event['attempt']))
            body=dict(sequence=state['event_count'],previous=state['head_sha256'],payload_sha256=self.binding,event=event,artifact_sha256=artifact_sha256,owner=self.owner)
            head=identity(body);self.store.event('spread_protocol',self.job['id'],body|dict(event_sha256=head),db)
            db.execute('UPDATE spread_state SET event_count=?,head_sha256=?,projection=?,projection_sha256=? WHERE job_id=?',(state['event_count']+1,head,canonical(following),identity(following),self.job['id']));db.execute('COMMIT')
        self.count=state['event_count']+1;self.head=head
        if not self.streaming:self.events.append(event);self.envelopes.append(body|dict(event_sha256=head))


def repair_account_link(store,job_id):
    """Restore only a missing derived link, without qualification or price reads."""
    try:
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            job,binding_hash,_=store._input_index.verified_inputs(job_id,db)
            if job['kind']!='spread':raise StateError('Choose an original spread parent.')
            job=job|dict(payload_sha256=binding_hash)
            settings=SpreadSettings(**job['payload']['settings']);p,_,_=saved_projection(db,job,settings)
            rows=list(db.execute("SELECT length(CAST(details AS BLOB)) bytes,substr(CAST(details AS BLOB),1,4097) details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen' ORDER BY id LIMIT 2",(job_id,)))
            if len(rows)!=1 or rows[0]['bytes']>4096:raise StateError('Exactly one intact original account relationship is required; no replacement is authorized.')
            event=json.loads(rows[0]['details'])
            if not isinstance(event,dict) or set(event)!={'child_id','job_id','payload_hash','result_sha256','selection_manifest_hash'}:raise StateError('Original account relationship is malformed.')
            cid=event['child_id'];binding={k:v for k,v in event.items() if k!='child_id'}
            if not isinstance(cid,str) or not re.fullmatch('[a-f0-9]{32}',cid) or event['job_id']!=job_id or event['payload_hash']!=binding_hash or event['selection_manifest_hash']!=p.get('selection_manifest_hash'):raise StateError('Original account relationship binding changed.')
            digest(event['result_sha256']);digest(event['selection_manifest_hash'])
            child,_,_=store._input_index.verified_inputs(cid,db)
            if child['kind']!='spread_accounts' or child['payload'].get('spread_parent')!=binding:raise StateError('Original child inputs differ from the saved relationship.')
            result=db.execute("SELECT length(CAST(details AS BLOB)) bytes,substr(CAST(details AS BLOB),1,4097) details FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id DESC LIMIT 1",(job_id,)).fetchone()
            if result is None or result['bytes']>4096:raise StateError('Original qualification result binding is missing or oversized.')
            result_event=json.loads(result['details'])
            if not isinstance(result_event,dict) or result_event.get('sha256')!=event['result_sha256']:raise StateError('Original qualification result binding changed.')
            db.execute('CREATE TABLE IF NOT EXISTS spread_account_links(parent_id TEXT PRIMARY KEY REFERENCES jobs(id),child_id TEXT NOT NULL UNIQUE REFERENCES jobs(id))')
            existing=db.execute('SELECT child_id FROM spread_account_links WHERE parent_id=?',(job_id,)).fetchone()
            if existing is not None and existing['child_id']!=cid:raise StateError('A conflicting saved relationship is retained for inspection; no account was replaced.')
            if existing is None:db.execute('INSERT INTO spread_account_links VALUES(?,?)',(job_id,cid))
            saved_account_link(store,db,job,p)
            if existing is None:store.event('spread_account_link_repaired',job_id,dict(child_id=cid,parent_payload_sha256=binding_hash),db)
            db.execute('COMMIT')
    except StateError:raise
    except (sqlite3.Error,ValueError,TypeError,KeyError) as error:raise StateError('Original account relationship could not be verified; no replacement was authorized.') from error
    return bounded_status(store,job_id)
