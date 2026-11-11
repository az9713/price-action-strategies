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
            if result is None or result['bytes']>4096 or json.loads(result['details']).get('sha256')!=event['result_sha256']:raise StateError('Original qualification result binding changed.')
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
