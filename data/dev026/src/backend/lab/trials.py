"""Transactional research plans and computation attempts; never market-price IO."""
import json
import time
import csv
import hashlib
import sqlite3
from io import StringIO
from .config import identity,canonical,Strategy


class TrialLedger:
    def __init__(self,store,error):
        self.store=store;self.error=error
        with store.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS trial_plans(
              id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES jobs(id),part INTEGER NOT NULL,
              window TEXT NOT NULL,role TEXT NOT NULL,config_id TEXT,plan_hash TEXT NOT NULL,
              provenance TEXT NOT NULL,state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
              reuses INTEGER NOT NULL DEFAULT 0,computed_sha256 TEXT,artifact_sha256 TEXT,note TEXT,
              created REAL NOT NULL,updated REAL NOT NULL,UNIQUE(job_id,part,window));
            CREATE INDEX IF NOT EXISTS trials_job ON trial_plans(job_id,part,window);
            CREATE INDEX IF NOT EXISTS trials_role_config ON trial_plans(role,config_id);
            CREATE TABLE IF NOT EXISTS trial_attempts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,trial_id TEXT NOT NULL REFERENCES trial_plans(id),
              ordinal INTEGER NOT NULL,owner TEXT NOT NULL,started REAL NOT NULL,finished REAL,
              state TEXT NOT NULL,error TEXT,computed_sha256 TEXT,artifact_sha256 TEXT,
              UNIQUE(trial_id,ordinal));
            CREATE TABLE IF NOT EXISTS trial_generations(
              job_id TEXT PRIMARY KEY REFERENCES jobs(id),attempts INTEGER NOT NULL,
              accepted INTEGER NOT NULL,duplicates INTEGER NOT NULL,rejected INTEGER NOT NULL,
              details TEXT NOT NULL);
            ''')
            db.execute('BEGIN IMMEDIATE')
            # Reconstruct legacy plans once. No price or old output file is read,
            # and no prespecified event or computation attempt is fabricated.
            jobs=db.execute("SELECT * FROM jobs j WHERE j.kind NOT IN ('download','news_download','spread') AND NOT EXISTS(SELECT 1 FROM trial_plans t WHERE t.job_id=j.id)")
            for row in jobs:
                db.execute('SAVEPOINT legacy_job_plan')
                try:self.freeze(dict(row),db,legacy=True)
                except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as error:
                    db.execute('ROLLBACK TO legacy_job_plan')
                    raw=row['payload'];raw_bytes=raw.encode() if isinstance(raw,str) else bytes(raw)
                    raw_hash=hashlib.sha256(raw_bytes).hexdigest()
                    recorded=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='legacy_trial_plan_unrecoverable' AND json_extract(details,'$.raw_payload_sha256')=? LIMIT 1",(row['id'],raw_hash)).fetchone()
                    if recorded is None:
                        self.store.event('legacy_trial_plan_unrecoverable',row['id'],dict(raw_payload_sha256=raw_hash,error_type=type(error).__name__,provenance='unverified_original_inputs'),db)
                finally:db.execute('RELEASE legacy_job_plan')
            db.execute('COMMIT')

    def entries(self,job,db):
        p=json.loads(job['payload']) if isinstance(job['payload'],str) else job['payload']
        if not isinstance(p,dict):raise self.error('Stored trial inputs must be an object.')
        kind=job['kind'];entries=[];payload_hash=identity(p)
        def add(part,window,role,config):
            cid=None if config is None else identity(config)
            if cid is None:role='unclassified'
            entries.append(dict(part=part,window=window,role=role,config_id=cid,
                plan_hash=identity(dict(payload_hash=payload_hash,part=part,window=window,role=role,config_id=cid))))
        if kind in {'download','news_download','spread'}:return []
        if kind=='experiment':add(0,'report','strategy',p.get('strategy'))
        elif kind=='borrow_sensitivity':
            for arm in p.get('cost_arms',[]):add(arm['part'],'report','borrow_sensitivity',dict(strategy=p['strategy'],costs=arm['costs']))
        elif kind in {'search','ablation','spread_accounts'}:
            for i,c in enumerate(p.get('configurations',[])):add(i,'report','strategy',c)
        elif kind in {'screen','final'}:
            configs=p.get('trial_configurations');windows=p.get('trial_windows')
            mode=p.get('study_mode','independent')
            if configs is None:
                row=db.execute('SELECT spec FROM studies WHERE id=?',(p.get('study_id'),)).fetchone();spec={} if row is None else json.loads(row['spec'])
                mode=spec.get('study_mode','independent')
                configs=spec.get('configurations' if kind=='screen' else 'candidates',[])
                if kind=='screen' and mode=='portfolio':configs=[configs]
                windows={k:spec.get(k,{}) for k in ['discovery','validation']} if kind=='screen' else {'report':spec.get('holdout',{})}
            for i,c in enumerate(configs):
                for window in windows:add(i,window,'portfolio' if mode=='portfolio' else 'strategy',c)
        elif kind=='portfolio':add(0,'report','portfolio',p.get('configurations'))
        elif kind=='benchmark':
            for i,name in enumerate(['cash','buy_hold']):add(i,'report','benchmark',dict(benchmark=name))
        elif kind=='controls':
            add(0,'report','strategy',p.get('strategy'));add(1,'report','matched_source',p.get('strategy'))
            for i in range(p.get('replicas',0)):add(i+2,'report','random_control',p.get('strategy'))
        elif kind=='behavior':
            for i,tf in enumerate(p.get('timeframes',[])):add(i,'report','price_behavior',dict(policy=1,timeframe=tf))
        if not entries:add(0,'report','unclassified',None)
        return entries

    def freeze(self,job,db,legacy=False):
        p=json.loads(job['payload']) if isinstance(job['payload'],str) else job['payload'];entries=self.entries(job,db);now=time.time()
        rows=[]
        for e in entries:
            tid=identity(dict(job_id=job['id'],part=e['part'],window=e['window']))
            rows.append((tid,job['id'],e['part'],e['window'],e['role'],e['config_id'],e['plan_hash'],
                'legacy_posthoc' if legacy else 'prespecified','legacy_unverified' if legacy else 'planned',
                'Reconstructed from saved current plan; original attempt history is not certified.' if legacy else None,now,now))
        db.executemany('INSERT INTO trial_plans(id,job_id,part,window,role,config_id,plan_hash,provenance,state,note,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',rows)
        sampling=p.get('sampling')
        if sampling is not None and not isinstance(sampling,dict):raise self.error('Stored sampler evidence must be an object.')
        if sampling:
            if not legacy:self.validate_generation(p,sampling,entries)
            db.execute('INSERT INTO trial_generations VALUES(?,?,?,?,?,?)',(job['id'],sampling.get('attempts',0),sampling.get('unique',0),sampling.get('duplicates',sampling.get('attempts',0)-sampling.get('unique',0)),sampling.get('rejected',0),canonical(sampling)))
        provenance='legacy_posthoc' if legacy else 'prespecified'
        self.store.event('legacy_trial_plan_reconstructed' if legacy else 'trial_plan_frozen',job['id'],
            dict(payload_hash=identity(p),plan_hash=identity(sorted([e|dict(provenance=provenance) for e in entries],key=lambda e:(e['part'],e['window']))),occurrences=len(entries),provenance=provenance),db)

    def validate_generation(self,payload,sampling,entries):
        records=sampling.get('proposals');counts={key:sampling.get(key) for key in ['attempts','unique','duplicates','rejected']}
        if (not isinstance(records,list) or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in counts.values()) or
            counts['attempts']!=len(records) or counts['attempts']!=counts['unique']+counts['duplicates']+counts['rejected']):
            raise self.error('Frozen sampler counts require every classified proposal.')
        accepted=[];seen=set();duplicates=0;invalid=0
        for number,row in enumerate(records,1):
            if not isinstance(row,dict):raise self.error('Each sampler proposal needs a structured record.')
            if row.get('attempt')!=number:raise self.error('Frozen sampler proposal sequence is incomplete.')
            state=row.get('status');cid=row.get('config_id')
            if state in {'accepted','duplicate'} and 'configuration' in row:
                try:configuration=Strategy(**row['configuration'])
                except (ValueError,TypeError) as error:raise self.error('Saved sampler proposal is not a valid configuration.') from error
                if identity(configuration)!=cid:raise self.error('Saved sampler proposal configuration identity changed.')
            if state=='accepted':
                if not cid or cid in seen:raise self.error('Accepted sampler proposals must be unique.')
                accepted.append(cid);seen.add(cid)
            elif state=='duplicate':
                if cid not in seen:raise self.error('Duplicate proposal does not refer to an earlier accepted configuration.')
                duplicates+=1
            elif state=='invalid':
                if not isinstance(row.get('configuration'),dict):raise self.error('An invalid proposal needs its complete proposed configuration.')
                try:Strategy(**row['configuration'])
                except (ValueError,TypeError):pass
                else:raise self.error('An invalid proposal must identify an invalid complete configuration.')
                if not row.get('reason'):raise self.error('Invalid proposal needs its rejection reason.')
                invalid+=1
            else:raise self.error('Unknown sampler proposal classification.')
        expected=[e['config_id'] for e in entries if e['role']=='strategy']
        if accepted!=expected or len(accepted)!=counts['unique'] or duplicates!=counts['duplicates'] or invalid!=counts['rejected']:
            raise self.error('Frozen sampler proposal identities or counters do not match its selected plan.')

    def verify(self,job_id,db=None):
        if db is None:
            with self.store.db() as c:return self.verify(job_id,c)
        job=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='trial_plan_frozen' ORDER BY id LIMIT 1",(job_id,)).fetchone()
        if job is None or event is None:raise self.error('No original frozen trial plan; create a new research job.')
        frozen=json.loads(event['details']);payload=json.loads(job['payload'])
        entries=[dict(r) for r in db.execute("SELECT part,window,role,config_id,plan_hash,provenance FROM trial_plans WHERE job_id=? AND provenance!='staged_prespecified' ORDER BY part,window",(job_id,))]
        for r in db.execute('SELECT id,part,window FROM trial_plans WHERE job_id=?',(job_id,)):
            if r['id']!=identity(dict(job_id=job_id,part=r['part'],window=r['window'])):raise self.error('Frozen trial occurrence identity changed.')
        if identity(payload)!=frozen['payload_hash'] or identity(entries)!=frozen['plan_hash']:
            raise self.error('Frozen trial plan or payload changed; execution is refused.')
        if job['kind']=='spread':
            from .spread_jobs import verify_staged
            verify_staged(self.store,dict(job),db)
        elif db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND provenance='staged_prespecified' LIMIT 1",(job_id,)).fetchone():raise self.error('Staged signal occurrences belong only to a spread job.')

    def owned(self,db,job_id,owner):
        row=db.execute('SELECT status,owner FROM jobs INDEXED BY jobs_live_control WHERE id=?',(job_id,)).fetchone()
        if row is None or row['owner']!=owner or row['status'] not in {'running','canceling'}:
            raise self.error('Trial update belongs to another worker.')

    def row(self,db,job_id,part,window):
        row=db.execute('SELECT * FROM trial_plans WHERE job_id=? AND part=? AND window=?',(job_id,part,window)).fetchone()
        if row is None:raise self.error('Unknown frozen trial occurrence.')
        return row

    def start(self,job_id,part,window,owner):
        with self.store.db() as db:
            # Worker verifies the full immutable plan before execution and before
            # publication. Per-arm work must not rehash an entire100000-arm plan.
            db.execute('BEGIN IMMEDIATE');self.owned(db,job_id,owner);r=self.row(db,job_id,part,window)
            if r['state']=='running':raise self.error('Trial computation already running.')
            n=r['attempts']+1;now=time.time()
            db.execute('INSERT INTO trial_attempts(trial_id,ordinal,owner,started,state) VALUES(?,?,?,?,?)',(r['id'],n,owner,now,'running'))
            db.execute("UPDATE trial_plans SET state='running',attempts=?,computed_sha256=NULL,artifact_sha256=NULL,note=NULL,updated=? WHERE id=?",(n,now,r['id']))
            self.store.event('trial_computation_started',job_id,dict(trial_id=r['id'],part=part,window=window,attempt=n),db);db.execute('COMMIT')
            return n

    def computed(self,job_id,part,window,owner,report):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self.owned(db,job_id,owner);r=self.row(db,job_id,part,window)
            if r['state']!='running':raise self.error('Trial was not started before its computation.')
            digest=identity(report);now=time.time()
            db.execute("UPDATE trial_plans SET state='computed',computed_sha256=?,updated=? WHERE id=?",(digest,now,r['id']))
            db.execute("UPDATE trial_attempts SET state='computed',computed_sha256=? WHERE trial_id=? AND ordinal=?",(digest,r['id'],r['attempts']))
            db.execute('COMMIT')

    def checkpoint(self,job_id,part,window,owner,report,artifact):
        self.artifact(artifact)
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self.owned(db,job_id,owner);r=self.row(db,job_id,part,window);digest=identity(report);now=time.time()
            if r['computed_sha256'] and r['computed_sha256']!=digest:raise self.error('Trial output differs from its recorded computation.')
            if r['artifact_sha256'] and r['artifact_sha256']!=artifact:raise self.error('Recorded trial checkpoint artifact was changed.')
            reused=r['state'] not in {'running','computed'}
            db.execute("UPDATE trial_plans SET state='checkpointed',computed_sha256=?,artifact_sha256=?,reuses=reuses+?,updated=? WHERE id=?",(digest,artifact,int(reused),now,r['id']))
            if not reused:
                db.execute("UPDATE trial_attempts SET state='checkpointed',artifact_sha256=?,finished=? WHERE trial_id=? AND ordinal=?",(artifact,now,r['id'],r['attempts']))
            self.store.event('trial_checkpoint_reused' if reused else 'trial_checkpoint_saved',job_id,dict(trial_id=r['id'],part=part,window=window,sha256=artifact),db);db.execute('COMMIT')

    def bind_result(self,job_id,owner,digest):
        self.artifact(digest)
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self.owned(db,job_id,owner);now=time.time()
            for r in db.execute("SELECT * FROM trial_plans WHERE job_id=? AND state='computed'",(job_id,)).fetchall():
                db.execute("UPDATE trial_plans SET state='checkpointed',artifact_sha256=?,updated=? WHERE id=?",(digest,now,r['id']))
                db.execute("UPDATE trial_attempts SET state='checkpointed',artifact_sha256=?,finished=? WHERE trial_id=? AND ordinal=?",(digest,now,r['id'],r['attempts']))
            db.execute('COMMIT')

    def artifact(self,digest):
        if not isinstance(digest,str) or len(digest)!=64 or set(digest)-set('0123456789abcdef'):
            raise self.error('A trial checkpoint requires a complete SHA-256 artifact digest.')

    def skip(self,job_id,part,window,owner,reason):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self.owned(db,job_id,owner);r=self.row(db,job_id,part,window)
            if r['role']!='random_control' or r['attempts'] or r['state'] not in {'planned','not_started','not_generated'}:
                raise self.error('Only an unstarted random replica without a matched source may be ungenerated.')
            if r['state']=='not_generated':db.execute('COMMIT');return
            db.execute("UPDATE trial_plans SET state='not_generated',note=?,updated=? WHERE id=?",(reason,time.time(),r['id']))
            self.store.event('trial_not_generated',job_id,dict(trial_id=r['id'],reason=reason),db);db.execute('COMMIT')

    def terminal(self,db,job_id,status,error=None):
        now=time.time()
        if status=='completed':
            invalid=db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND provenance IN ('prespecified','staged_prespecified') AND config_id IS NOT NULL AND (state NOT IN ('checkpointed','completed','not_generated') OR (state IN ('checkpointed','completed') AND artifact_sha256 IS NULL)) LIMIT 1",(job_id,)).fetchone()
            if invalid:raise self.error('A completed research job requires durable outputs for every generated numeric trial.')
        next_state='interrupted' if status=='queued' else status
        db.execute("UPDATE trial_attempts SET state=?,finished=?,error=? WHERE EXISTS(SELECT 1 FROM trial_plans t WHERE t.job_id=? AND t.id=trial_attempts.trial_id AND t.attempts=trial_attempts.ordinal AND t.state IN ('running','computed'))",(next_state,now,error,job_id))
        db.execute("UPDATE trial_plans SET state=?,note=?,updated=? WHERE job_id=? AND state IN ('running','computed')",(next_state,error,now,job_id))
        if status=='completed':
            db.execute("UPDATE trial_plans SET state='completed',note=?,updated=? WHERE job_id=? AND state='checkpointed'",(error,now,job_id))
        if status in {'failed','canceled','completed'}:
            db.execute("UPDATE trial_plans SET state='not_started',note=?,updated=? WHERE job_id=? AND state='planned'",(error,now,job_id))

    def listing(self,limit=20,offset=0,job_id=None):
        if not isinstance(limit,int) or not 1<=limit<=200 or not isinstance(offset,int) or offset<0:raise self.error('Choose registry page size1–200 and a nonnegative offset.')
        with self.store.db() as db:
            db.execute('BEGIN')
            where='' if job_id is None else ' WHERE t.job_id=?';args=() if job_id is None else (job_id,)
            total=db.execute('SELECT COUNT(*) FROM trial_plans t'+where,args).fetchone()[0]
            legacy=db.execute("SELECT COUNT(*) FROM trial_plans t"+where+(' AND ' if where else ' WHERE ')+"provenance='legacy_posthoc'",args).fetchone()[0]
            roles={r['role']:dict(occurrences=r['n'],distinct_configurations=r['distinct_configs']) for r in db.execute('SELECT role,COUNT(*) n,COUNT(DISTINCT config_id) distinct_configs FROM trial_plans t'+where+' GROUP BY role',args)}
            states={r['state']:r['n'] for r in db.execute('SELECT state,COUNT(*) n FROM trial_plans t'+where+' GROUP BY state',args)}
            attempts=db.execute('SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id'+where,args).fetchone()[0]
            job_attempts=db.execute("SELECT COUNT(*) FROM events e WHERE e.kind='job_claimed' AND EXISTS(SELECT 1 FROM trial_plans t WHERE t.job_id=e.entity_id"+('' if job_id is None else ' AND t.job_id=?')+')',args).fetchone()[0]
            rows=[]
            query='SELECT t.*,j.kind job_kind,j.status job_status,i.payload_sha256 index_payload_sha256,substr(i.projection,1,24577) index_projection,substr(i.list_projection,1,1025) index_list_projection,i.projection_sha256 index_projection_sha256,i.provenance index_provenance FROM trial_plans t JOIN jobs j ON t.job_id=j.id LEFT JOIN job_input_index i ON i.job_id=j.id'+where+' ORDER BY t.created,t.job_id,t.part,t.window LIMIT ? OFFSET ?'
            for r in db.execute(query,(*args,limit,offset)):
                value=dict(r)
                index={key:value.pop('index_'+key) for key in ['payload_sha256','projection','list_projection','projection_sha256','provenance']}
                try:
                    projection,_=self.store._input_index.checked(index)
                    value.update(job_name=projection.get('name'),job_index_integrity=True)
                except (ValueError,TypeError,KeyError):value.update(job_name=None,job_index_integrity=False)
                value['attempt_history']=[dict(a) for a in db.execute('SELECT ordinal,started,finished,state,error,computed_sha256,artifact_sha256 FROM trial_attempts WHERE trial_id=? ORDER BY ordinal',(r['id'],))];rows.append(value)
            genwhere='' if job_id is None else ' WHERE job_id=?'
            generation=dict(db.execute('SELECT COUNT(*) jobs,COALESCE(SUM(attempts),0) proposals,COALESCE(SUM(accepted),0) accepted,COALESCE(SUM(duplicates),0) duplicates,COALESCE(SUM(rejected),0) rejected FROM trial_generations'+genwhere,args).fetchone())
            return dict(rows=rows,pagination=dict(limit=limit,offset=offset,total=total),totals=dict(planned_occurrences=total,legacy_occurrences=legacy,prespecified_occurrences=total-legacy,roles=roles,states=states,computation_attempts=attempts,job_execution_attempts=job_attempts,generation=generation,
                interpretation='Occurrences, unique configurations, control replicas and computation attempts are distinct. None is automatically an effective independent trial count. Legacy post-hoc plans have no certified original attempt history.'))

    def export(self,job_id,format):
        """Stream one stable SQLite read snapshot; never truncate to a UI page."""
        # Starlette iterates synchronous streams via a thread pool. Each next()
        # is sequential but can run on another thread. This private read-only
        # connection permits that handoff; normal write connections stay bound.
        with self.store.db(thread_handoff=True) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            generation=db.execute('SELECT details FROM trial_generations WHERE job_id=?',(job_id,)).fetchone()
            count=db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',(job_id,)).fetchone()[0]
            if format=='json':
                provenance=db.execute('SELECT provenance FROM trial_plans WHERE job_id=? LIMIT 1',(job_id,)).fetchone()
                header=dict(schema_version=1,job_id=job_id,as_of=time.time(),occurrences=count,plan_provenance=None if provenance is None else provenance[0],
                    generation=None if generation is None else json.loads(generation['details']))
                yield canonical(header)[:-1]+',"rows":['
            output=StringIO();writer=None;first=True
            for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part,window',(job_id,)):
                value=dict(r)
                value['attempt_history']=[dict(a) for a in db.execute('SELECT ordinal,started,finished,state,error,computed_sha256,artifact_sha256 FROM trial_attempts WHERE trial_id=? ORDER BY ordinal',(r['id'],))]
                if format=='json':yield ('' if first else ',')+canonical(value)
                else:
                    if writer is None:writer=csv.DictWriter(output,fieldnames=list(value));writer.writeheader()
                    value['attempt_history']=canonical(value['attempt_history'])
                    writer.writerow({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) else v) for k,v in value.items()})
                    yield output.getvalue();output.seek(0);output.truncate(0)
                first=False
            if format=='json':yield ']}'
