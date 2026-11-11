"""Derived study summaries/scopes; original registration and lifecycle events remain authority."""
from datetime import date
import hashlib,json
from .config import canonical,identity
from .job_index import small,DETAIL_BYTES,LIST_BYTES

MUTABLE={'screening_report_hash','candidates','candidate_hash','final_job_id','reserved_final_job_id'}
def input_hash(spec):return identity({k:v for k,v in spec.items() if k not in MUTABLE})

def scope_fields(spec):
    if not isinstance(spec,dict):raise ValueError('Protected scope must be an object.')
    symbols=spec['symbols'];holdout=spec['holdout']
    if not isinstance(symbols,list) or not symbols or not all(isinstance(s,str) and s for s in symbols):raise ValueError('Invalid protected instrument scope.')
    if not isinstance(holdout,dict) or date.fromisoformat(holdout['start'])>date.fromisoformat(holdout['end']):raise ValueError('Invalid protected dates.')
    if spec.get('final_job_id') is not None and not isinstance(spec['final_job_id'],str):raise ValueError('Invalid final job identity.')
    return dict(symbols=sorted(set(symbols)),holdout=holdout,final_job_id=spec.get('final_job_id'))

def projections(spec):
    scope=scope_fields(spec);symbols=spec['symbols']
    detail=dict(configuration_count=len(spec['configurations']),candidate_count=len(spec['candidates']) if 'candidates' in spec else None,instrument_count=len(set(symbols)))
    omitted=[]
    for key in ['study_mode','discovery','validation','holdout','core_hash','dataset_manifest_hash','dataset_context','symbols','costs','portfolio','seed','minimum_trades','minimum_sharpe','news_calendar_id','candidate_hash','screening_report_hash','reserved_final_job_id','final_job_id']:
        if key not in spec:continue
        if small(spec[key]):detail[key]=spec[key]
        else:omitted.append(key)
    if omitted:detail['omitted_fields']=omitted
    while len(canonical(detail).encode())>DETAIL_BYTES:
        key=max((k for k in detail if k not in {'omitted_fields','configuration_count','candidate_count','instrument_count','holdout','study_mode','reserved_final_job_id','final_job_id'}),key=lambda k:len(canonical(detail[k]).encode()))
        detail.pop(key);omitted.append(key);detail['omitted_fields']=omitted
    listed={k:detail[k] for k in ['study_mode','holdout','configuration_count','candidate_count','instrument_count','reserved_final_job_id','final_job_id'] if k in detail}
    if len(canonical(listed).encode())>LIST_BYTES:raise ValueError('Lifecycle projection exceeds its budget.')
    return detail,listed,scope

def binding(spec_hash,projection,listed,scope_hash,provenance):
    return identity(dict(spec_hash=spec_hash,projection=projection,list_projection=listed,scope_sha256=scope_hash,provenance=provenance))

class StudyIndex:
    def __init__(self,store,error):
        self.store=store;self.error=error
        with store.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS study_input_index(
                study_id TEXT PRIMARY KEY REFERENCES studies(id),spec_hash TEXT NOT NULL,
                projection TEXT NOT NULL,list_projection TEXT NOT NULL,scope TEXT NOT NULL,
                scope_sha256 TEXT NOT NULL,projection_sha256 TEXT NOT NULL,provenance TEXT NOT NULL)''')
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute('SELECT s.id,s.spec FROM studies s LEFT JOIN study_input_index i ON s.id=i.study_id WHERE i.study_id IS NULL ORDER BY s.created,s.id'):
                try:self.add(db,row['id'],json.loads(row['spec']),'backfilled_verified_registration')
                except (ValueError,TypeError,KeyError):
                    db.execute('INSERT INTO study_input_index VALUES(?,?,?,?,?,?,?,?)',(row['id'],'','','','','','','unverified_original_inputs'))
            db.execute('COMMIT')

    def anchor(self,db,sid,spec):
        if not isinstance(spec,dict):raise ValueError('Study inputs must be an object.')
        digest=input_hash(spec)
        def event(kind,latest=False):
            row=db.execute('SELECT details FROM events WHERE entity_id=? AND kind=? ORDER BY id '+('DESC' if latest else 'ASC')+' LIMIT 1',(sid,kind)).fetchone()
            value={} if row is None else json.loads(row['details'])
            if not isinstance(value,dict):raise ValueError('Stored study event must be an object.')
            return value
        if event('study_registered').get('spec_hash')!=digest:raise ValueError('Original registration hash differs.')
        if 'candidates' in spec or 'candidate_hash' in spec:
            frozen=event('candidates_frozen',latest=True);candidates=spec.get('candidates')
            if not isinstance(candidates,list) or identity(candidates)!=spec.get('candidate_hash') or frozen.get('candidate_hash')!=spec.get('candidate_hash') or frozen.get('count')!=len(candidates) or frozen.get('screening_report_hash')!=spec.get('screening_report_hash'):raise ValueError('Candidate evidence differs.')
        if spec.get('reserved_final_job_id'):
            reserved=event('portfolio_final_reserved')
            if reserved.get('job_id')!=spec['reserved_final_job_id'] or reserved.get('candidate_hash')!=spec.get('candidate_hash'):raise ValueError('Final reservation differs.')
        if spec.get('final_job_id') and event('final_unlock_consumed').get('job_id')!=spec['final_job_id']:raise ValueError('Consumed final identity differs.')
        return digest

    def add(self,db,sid,spec,provenance='verified_registration'):
        try:digest=self.anchor(db,sid,spec);detail,listed,scope=projections(spec)
        except (ValueError,TypeError,KeyError) as error:raise self.error('Study evidence differs from its frozen registration or lifecycle; no new final reservation was certified.') from error
        raw=canonical(scope);scope_hash=hashlib.sha256(raw.encode()).hexdigest()
        db.execute('INSERT OR REPLACE INTO study_input_index VALUES(?,?,?,?,?,?,?,?)',(sid,digest,canonical(detail),canonical(listed),raw,scope_hash,binding(digest,detail,listed,scope_hash,provenance),provenance))

    def checked(self,row):
        if any(not isinstance(row.get(k),str) or not row[k] for k in ['projection','list_projection','scope']):raise ValueError('Missing or invalid study index.')
        if len(row['projection'].encode())>DETAIL_BYTES or len(row['list_projection'].encode())>LIST_BYTES:raise ValueError('Study index exceeds its budget.')
        detail=json.loads(row['projection']);listed=json.loads(row['list_projection'])
        if not isinstance(detail,dict) or not isinstance(listed,dict) or hashlib.sha256(row['scope'].encode()).hexdigest()!=row['scope_sha256'] or binding(row['spec_hash'],detail,listed,row['scope_sha256'],row['provenance'])!=row['projection_sha256']:raise ValueError('Study index checksum differs.')
        scope=json.loads(row['scope'])
        if scope_fields(scope)!=scope or ('holdout' in detail and detail['holdout']!=scope['holdout']) or detail.get('instrument_count')!=len(scope['symbols']) or ('final_job_id' in detail and detail['final_job_id']!=scope['final_job_id']):raise ValueError('Protected scope shape or projection differs.')
        return detail,listed,scope

    def query(self):
        return f'''SELECT s.id,substr(s.name,1,100) name,s.dataset_id,s.status,s.created,s.updated,
            i.spec_hash,substr(i.projection,1,{DETAIL_BYTES+1}) projection,
            substr(i.list_projection,1,{LIST_BYTES+1}) list_projection,i.scope,i.scope_sha256,
            i.projection_sha256,i.provenance FROM studies s LEFT JOIN study_input_index i ON s.id=i.study_id'''

    def statuses(self,sid=None,limit=500,offset=0):
        if type(limit) is not int or not 1<=limit<=500 or type(offset) is not int or offset<0:raise self.error('Invalid study history page.')
        query=self.query()+(' WHERE s.id=?' if sid is not None else ' ORDER BY s.created DESC,s.id DESC LIMIT ? OFFSET ?')
        result=[]
        with self.store.db() as db:
            for r in db.execute(query,(sid,) if sid is not None else (limit,offset)):
                row=dict(r);value={k:row[k] for k in ['id','name','dataset_id','status','created','updated']}
                value.update(inputs_url='/api/studies/'+row['id']+'/inputs',projection_policy=1,index_provenance=row['provenance'])
                try:
                    detail,listed,_=self.checked(row);value.update(spec=detail if sid is not None else listed,index_integrity=True,spec_hash=row['spec_hash'])
                except (ValueError,TypeError,KeyError):value.update(spec={},index_integrity=False,integrity_error='Stored study summary/protection is unverified. Restore original inputs or repair the derived index.')
                result.append(value)
        if sid is not None:
            if not result:raise self.error('Study does not exist.')
            return result[0]
        return result

    def scopes(self,db):
        for raw in db.execute(self.query()+" WHERE s.status!='abandoned' ORDER BY s.id"):
            row=dict(raw)
            try:_,_,scope=self.checked(row)
            except (ValueError,TypeError,KeyError) as error:raise self.error('Protected study scope is unverified. Repair its derived index from the original registration before accessing data.') from error
            yield row,scope

    def verified(self,db,sid):
        row=db.execute('SELECT * FROM studies WHERE id=?',(sid,)).fetchone()
        if row is None:raise self.error('Study does not exist.')
        try:
            study=self.store.decode(row);digest=self.anchor(db,sid,study['spec']);projections(study['spec'])
        except (ValueError,TypeError,KeyError) as error:raise self.error('Stored study inputs or lifecycle evidence differ from their frozen registration; no export or repair was certified.') from error
        return study,digest

    def inputs(self,sid):
        with self.store.db() as db:
            db.execute('BEGIN');study,digest=self.verified(db,sid)
            return dict(study=study,spec_hash=digest,input_provenance='verified_registration')

    def repair(self,sid):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');study,digest=self.verified(db,sid);self.add(db,sid,study['spec'],'rebuilt_verified_registration')
            self.store.event('study_input_index_repaired',sid,dict(spec_hash=digest),db);db.execute('COMMIT')
        return self.statuses(sid)
