"""Derived bounded job metadata. Original inputs and financial trial authority stay separate."""
import hashlib
import json
from .config import canonical,identity

DETAIL_BYTES=24576
LIST_BYTES=1024
SCALARS=['name','dataset_id','dataset_manifest_hash','core_hash','start','end','seed','count','news_calendar_id',
         'study_id','study_mode','study_input_hash','candidate_hash','sampling_failure','original_costs_id','rate_policy']

def small(value,budget=4096):
    """Stop before traversing a huge source document or configuration array."""
    pending=[value];nodes=0;characters=0
    while pending:
        item=pending.pop();nodes+=1
        if nodes>256:return False
        if isinstance(item,str):characters+=len(item)
        elif isinstance(item,dict):
            if len(item)>64:return False
            pending.extend(item.keys());pending.extend(item.values())
        elif isinstance(item,list):
            if len(item)>128:return False
            pending.extend(item)
        elif item is not None and type(item) not in {int,float,bool}:return False
        if characters>budget:return False
    return len(canonical(value).encode())<=budget

def project(payload):
    if not isinstance(payload,dict):raise ValueError('Stored input plan must be an object.')
    result={};omitted=[]
    for key in SCALARS+['strategy','costs','cost_arms','portfolio','statistics','sampling_policy','families','timeframes','symbols','settings','context','minimum_trades','minimum_sharpe','spread_parent','evaluation_symbols']:
        if key not in payload:continue
        value=payload[key]
        if small(value):result[key]=value
        else:omitted.append(key)
    context=payload.get('dataset_context')
    if isinstance(context,dict):
        if small(context,8192):result['dataset_context']=context
        else:
            summary={k:v for k,v in context.items() if k!='symbols' and small(v,2048)}
            summary.update(instrument_count=len(context.get('symbols',[])),complete=False)
            result['dataset_context_summary']=summary;omitted.append('dataset_context')
    for key in ['configurations','trial_configurations']:
        if isinstance(payload.get(key),list):
            result['configuration_count']=len(payload[key]);break
    sampling=payload.get('sampling')
    if isinstance(sampling,dict):
        result['sampling']={k:sampling[k] for k in ['mode','policy_version','requested','attempts','unique','duplicates','rejected','recipe_hash'] if k in sampling and small(sampling[k],256)}
        result['sampling']['proposal_count']=len(sampling.get('proposals',[]))
    if omitted:result['omitted_fields']=omitted
    # Bound even unusual legacy metadata without claiming that this is a full plan.
    while len(canonical(result).encode())>DETAIL_BYTES:
        key=max((k for k in result if k!='omitted_fields'),key=lambda k:len(canonical(result[k]).encode()))
        result.pop(key);omitted.append(key);result['omitted_fields']=omitted
    listed={k:result[k] for k in ['name','dataset_id','start','end','count','configuration_count','study_id','study_mode','core_hash'] if k in result}
    while len(canonical(listed).encode())>LIST_BYTES:
        key=max(listed,key=lambda k:len(canonical(listed[k]).encode()));listed.pop(key)
    return result,listed

def binding(payload_hash,projection,list_projection,provenance):
    return identity(dict(payload_sha256=payload_hash,projection=projection,list_projection=list_projection,provenance=provenance))

class JobIndex:
    def __init__(self,store,error):
        self.store=store;self.error=error
        with store.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS job_input_index(
                job_id TEXT PRIMARY KEY REFERENCES jobs(id),payload_sha256 TEXT NOT NULL,
                projection TEXT NOT NULL,list_projection TEXT NOT NULL,projection_sha256 TEXT NOT NULL,
                provenance TEXT NOT NULL)''')
            db.execute('BEGIN IMMEDIATE')
            # One raw legacy plan at a time, never fetchall of large input BLOBs.
            cursor=db.execute('SELECT j.id,j.payload FROM jobs j LEFT JOIN job_input_index i ON i.job_id=j.id WHERE i.job_id IS NULL ORDER BY j.created,j.id')
            for row in cursor:
                try:
                    payload=json.loads(row['payload']);self.anchor(db,row['id'],payload)
                    self.add(db,row['id'],payload,'backfilled_stored_inputs')
                except (ValueError,TypeError,KeyError):
                    db.execute('INSERT INTO job_input_index VALUES(?,?,?,?,?,?)',(row['id'],'','','','','unreadable_stored_inputs'))
            db.execute('COMMIT')

    def add(self,db,job_id,payload,provenance='prespecified'):
        projection,listed=project(payload);digest=identity(payload)
        db.execute('INSERT OR REPLACE INTO job_input_index VALUES(?,?,?,?,?,?)',
            (job_id,digest,canonical(projection),canonical(listed),binding(digest,projection,listed,provenance),provenance))

    def checked(self,row):
        if not row.get('projection') or not row.get('list_projection'):raise ValueError('Missing cached input summary.')
        if len(row['projection'].encode())>DETAIL_BYTES or len(row['list_projection'].encode())>LIST_BYTES:raise ValueError('Cached summary exceeds its budget.')
        p=json.loads(row['projection']);listed=json.loads(row['list_projection'])
        if not isinstance(p,dict) or not isinstance(listed,dict) or binding(row['payload_sha256'],p,listed,row['provenance'])!=row['projection_sha256']:
            raise ValueError('Cached input summary failed verification.')
        return p,listed

    def anchor(self,db,job_id,payload):
        if not isinstance(payload,dict):raise ValueError('Stored input plan must be an object.')
        digest=identity(payload)
        event=db.execute("SELECT kind,details FROM events WHERE entity_id=? AND kind IN ('trial_plan_frozen','legacy_trial_plan_reconstructed') ORDER BY id LIMIT 1",(job_id,)).fetchone()
        if event is None or json.loads(event['details']).get('payload_hash')!=digest:raise ValueError('Frozen input hash differs.')
        return digest,'prespecified' if event['kind']=='trial_plan_frozen' else 'legacy_posthoc'

    def statuses(self,job_id=None,limit=500,offset=0):
        if type(limit) is not int or not 1<=limit<=500 or type(offset) is not int or offset<0:raise self.error('Invalid job history page.')
        preview=2048 if job_id is not None else 128
        fields=f'''j.id,j.kind,j.status,j.created,j.updated,j.progress,j.checkpoint,j.cancel_requested,
            substr(j.note,1,{preview}) note,substr(j.error,1,{preview}) error,
            length(j.note)>{preview} note_truncated,length(j.error)>{preview} error_truncated,
            i.payload_sha256,substr(i.projection,1,{DETAIL_BYTES+1}) projection,
            substr(i.list_projection,1,{LIST_BYTES+1}) list_projection,i.projection_sha256,i.provenance'''
        query='SELECT '+fields+' FROM jobs j LEFT JOIN job_input_index i ON i.job_id=j.id'
        query+= ' WHERE j.id=?' if job_id is not None else ' ORDER BY j.created DESC,j.id DESC LIMIT ? OFFSET ?'
        args=(job_id,) if job_id is not None else (limit,offset)
        result=[]
        with self.store.db() as db:
            for raw in db.execute(query,args):
                row=dict(raw);value={k:row[k] for k in ['id','kind','status','created','updated','progress','checkpoint','cancel_requested','note','error','note_truncated','error_truncated']}
                value.update(inputs_url='/api/jobs/'+row['id']+'/inputs',projection_policy=1,index_provenance=row['provenance'])
                try:
                    detail,listed=self.checked(row);value.update(payload=detail if job_id is not None else listed,index_integrity=True,payload_sha256=row['payload_sha256'])
                except (ValueError,TypeError,KeyError):
                    value.update(payload={},index_integrity=False,integrity_error='Stored input summary is unverified. Inspect stored inputs or repair its derived index.')
                result.append(value)
        if job_id is not None:
            if not result:raise self.error('Job does not exist.')
            return result[0]
        return result

    def verified_inputs(self,job_id,db):
        row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None:raise self.error('Job does not exist.')
        try:
            job=self.store.decode(row);digest,provenance=self.anchor(db,job_id,job['payload'])
        except (ValueError,TypeError,KeyError) as error:raise self.error('Stored inputs differ from their frozen registration; no export or repair was certified.') from error
        return job,digest,provenance

    def inputs(self,job_id):
        with self.store.db() as db:
            db.execute('BEGIN');job,digest,provenance=self.verified_inputs(job_id,db)
            return dict(job_id=job_id,kind=job['kind'],payload=job['payload'],payload_sha256=digest,input_provenance=provenance,
                stored_diagnostics={k:job[k] for k in ['status','note','error','created','updated','checkpoint']})

    def repair(self,job_id):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');job,digest,_=self.verified_inputs(job_id,db)
            self.add(db,job_id,job['payload'],'rebuilt_verified_inputs')
            self.store.event('job_input_index_repaired',job_id,dict(payload_sha256=digest),db);db.execute('COMMIT')
        return self.statuses(job_id)

    def pending_study(self,kind,study_id,db):
        rows=db.execute("SELECT i.* FROM jobs j LEFT JOIN job_input_index i ON i.job_id=j.id WHERE j.kind=? AND j.status IN ('queued','running','canceling')",(kind,))
        for raw in rows:
            try:projection,_=self.checked(dict(raw))
            except (ValueError,TypeError,KeyError) as error:raise self.error('Pending study input index is unverified; repair it before queueing another study job.') from error
            if projection.get('study_id')==study_id:return True
        return False
