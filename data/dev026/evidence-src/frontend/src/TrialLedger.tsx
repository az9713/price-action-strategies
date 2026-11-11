import {useEffect,useRef,useState} from 'react';
import {api} from './api';

const label=(s:string)=>s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
export function TrialLedger({selected,onSelect}:{selected:string,onSelect:(id:string)=>void}){
  const [value,setValue]=useState<any>(null),[draft,setDraft]=useState(selected),[offset,setOffset]=useState(0),[limit,setLimit]=useState(20);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);const generation=useRef(0);
  useEffect(()=>{setDraft(selected);setOffset(0);},[selected]);
  useEffect(()=>{
    let active=true;
    async function refresh(){
      const version=++generation.current;setBusy(true);
      try{const query=new URLSearchParams({limit:String(limit),offset:String(offset)});if(selected)query.set('job_id',selected);
        const r=await api('/trial-registry?'+query);if(active&&version===generation.current){setValue({...r,loaded_job_id:selected,loaded_offset:offset,loaded_limit:limit});setError('');}}
      catch(e:any){if(active&&version===generation.current){setError(e.message);setValue(null);}}
      finally{if(active&&version===generation.current)setBusy(false);}
    }
    setValue(null);refresh();const timer=setInterval(refresh,3000);
    return()=>{active=false;generation.current++;clearInterval(timer);};
  },[selected,offset,limit]);
  const current=value?.loaded_job_id===selected&&value?.loaded_offset===offset&&value?.loaded_limit===limit?value:null;
  const totals=current?.totals,page=current?.pagination;
  return <section className="panel" aria-label="Research trial ledger">
    <div className="panel-head"><h2>Research trial ledger</h2></div>
    <p>See which research plans were registered, which computations actually ran, and what failed, stopped or reused verified saved work. Repeating a configuration creates another occurrence; it does not create another independent idea.</p>
    <p className="caption">Controls, passive benchmarks, portfolios and price measurements have separate counts. Legacy records were reconstructed after their original runs and remain unverified. Counts here are not an effective number of independent trials for statistical correction. Records outside this application are unknown.</p>
    <form onSubmit={e=>{e.preventDefault();onSelect(draft.trim());}}><div className="fields"><label className="field"><span>Filter trial ledger by job ID</span><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Leave blank for all history"/></label><button>Apply trial filter</button><button type="button" onClick={()=>onSelect('')}>Show all trial history</button><label className="field"><span>Trial ledger page size</span><select value={limit} onChange={e=>{setLimit(Number(e.target.value));setOffset(0);}}>{[10,20,50,100,200].map(n=><option key={n}>{n}</option>)}</select></label></div></form>
    {error&&<p role="alert" className="error-text">{error}</p>}
    {current&&<div data-testid="trial-ledger-output" data-job-id={selected}>
      <p data-testid="trial-ledger-counts"><b>{totals.planned_occurrences}</b> planned occurrences · <b>{totals.computation_attempts}</b> account/chart computation attempts · <b>{totals.job_execution_attempts}</b> worker job attempts · <b>{totals.prespecified_occurrences}</b> prespecified / <b>{totals.legacy_occurrences}</b> legacy occurrences.</p>
      <p className="caption">A queued or never-started plan is not a completed test. A worker attempt can fail while preparing inputs before an account computation begins. No-match random replicas can remain explicitly ungenerated with zero computation attempts.</p>
      <div className="table-wrap"><table><thead><tr><th>Research role</th><th>Planned occurrences</th><th>Distinct configurations within role</th></tr></thead><tbody>{Object.entries(totals.roles).map(([role,v]:any)=><tr key={role}><td>{label(role)}</td><td>{v.occurrences}</td><td>{v.distinct_configurations}</td></tr>)}</tbody></table></div>
      <p>Generator proposals: <b>{totals.generation.proposals}</b>; accepted <b>{totals.generation.accepted}</b>; duplicates <b>{totals.generation.duplicates}</b>; rejected <b>{totals.generation.rejected}</b>. Complete selected-job JSON retains the proposal records, including generation failures.</p>
      <div className="table-wrap" data-testid="trial-occurrences"><table><thead><tr><th>Job / role</th><th>Part / window</th><th>Plan state / job state</th><th>Computations / saved-work reuses</th><th>Provenance</th><th>Configuration / output hash</th><th/></tr></thead><tbody>{current.rows.map((r:any)=><tr key={r.id}><td><code>{r.job_id.slice(0,10)}</code><small className="block">{label(r.job_kind)} · {label(r.role)}</small></td><td>{r.part} · {r.window}</td><td>{label(r.state)} / {label(r.job_status)}{r.note&&<small className="block">{r.note}</small>}</td><td>{r.attempts} / {r.reuses}</td><td>{r.provenance==='prespecified'?'Prespecified':'Legacy snapshot · unverified'}</td><td><code>{r.config_id?.slice(0,12)||'Unclassified'}</code><code className="block">{r.artifact_sha256?.slice(0,12)||'No durable output'}</code></td><td><button onClick={()=>onSelect(r.job_id)}>Filter this job</button><details><summary>Attempt history</summary><pre className="saved-configs">{JSON.stringify(r.attempt_history,null,2)}</pre></details></td></tr>)}</tbody></table></div>
      {!current.rows.length&&<p>No trial occurrences in this selection.</p>}
      <div className="actions"><button disabled={busy||offset===0} onClick={()=>setOffset(Math.max(0,offset-limit))}>Previous trial page</button><span>{page.total?offset+1:0}–{Math.min(offset+limit,page.total)} of {page.total}</span><button disabled={busy||offset+limit>=page.total} onClick={()=>setOffset(offset+limit)}>Next trial page</button></div>
      {selected&&page.total>0&&<div className="actions"><a className="button primary" href={'/api/trial-registry/export/json?job_id='+encodeURIComponent(selected)} download>Download complete job trial JSON</a><a className="button" href={'/api/trial-registry/export/csv?job_id='+encodeURIComponent(selected)} download>Download complete job trial CSV</a><small>Exports include every occurrence for this job, beyond the current page.</small></div>}
    </div>}
  </section>;
}
