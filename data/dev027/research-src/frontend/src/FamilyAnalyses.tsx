import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';

const names:Record<string,string>={marked:'Marked account equity',realized_exit_day_compatibility:'Exit-day realized P&L (source compatibility)'};
function exact(value:any){return value?value.numerator+' / '+value.denominator:'Unavailable';}

function FamilyPage({jobId,table,parentId}:{jobId:string,table:string,parentId:string}){
  const [offset,setOffset]=useState(0),[page,setPage]=useState<any>(null),[error,setError]=useState('');
  useEffect(()=>{
    let active=true;setPage(null);setError('');
    const query=table==='members'?'/members?':'/daily?convention='+table+'&';
    void api('/jobs/'+jobId+'/family-analysis'+query+'limit=50&offset='+offset)
      .then(v=>{if(active)setPage(v);}).catch(e=>{if(active)setError(e.message);});
    return()=>{active=false;};
  },[jobId,table,offset]);
  return <section aria-label={table==='members'?'Complete family membership':'Family daily records'}>
    <h3>{table==='members'?'Every frozen version':names[table]}</h3>
    {error&&<p role="alert">{error}</p>}
    {!page&&!error&&<p role="status">Verifying original saved evidence…</p>}
    {page&&<><p>Records {page.rows.length?offset+1:0}–{offset+page.rows.length} of {page.pagination.total}.</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={table==='members'?'Family membership table':'Family daily P&L table'}>
        {table==='members'?<table><thead><tr><th>Original part</th><th>Configuration</th><th>Original account</th></tr></thead><tbody>{page.rows.map((r:any)=><tr key={r.config_id}><td>{r.source_part}</td><td><code>{r.config_id}</code></td><td><a download href={'/api/jobs/'+parentId+'/report?part='+r.source_part}>Download source account</a></td></tr>)}</tbody></table>:
          <table><thead><tr><th>Exchange session</th><th>Exact mean P&L (USD)</th></tr></thead><tbody>{page.rows.map((r:any)=><tr key={r.date}><td>{r.date}</td><td><code>{exact(r.mean_pnl)}</code></td></tr>)}</tbody></table>}
      </div>
      <div className="actions"><button type="button" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous family page</button><button type="button" disabled={offset+page.rows.length>=page.pagination.total} onClick={()=>setOffset(offset+50)}>Next family page</button></div>
    </>}
  </section>;
}

export function FamilyAnalyses({sourceJobId,sourceKind,familyLabels,jobs,jobId,onSelect,onRefresh}:{sourceJobId:string,sourceKind?:string,familyLabels:Record<string,string>,jobs:any[],jobId:string,onSelect:(id:string)=>void,onRefresh:()=>Promise<void>}){
  const [family,setFamily]=useState('change_of_character'),[job,setJob]=useState<any>(null),[summary,setSummary]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[retry,setRetry]=useState(0);
  const creation=useRef(0),selection=useRef(jobId),source=useRef(sourceJobId);
  selection.current=jobId;source.current=sourceJobId;
  useEffect(()=>()=>{creation.current++;},[]);
  useEffect(()=>{
    let active=true,loading=false,done=false;setJob(null);setSummary(null);setError('');
    async function load(){
      if(!jobId||loading||!active)return;loading=true;
      try{
        const current=await api('/jobs/'+jobId);
        if(!active)return;setJob(current);
        if(current.kind!=='family_analysis')throw Error('Choose a saved family analysis.');
        if(current.status==='completed'){
          const result=await api('/jobs/'+jobId+'/family-analysis');
          if(active){setSummary(result);setError('');done=true;}
        }else if(['failed','canceled'].includes(current.status)){done=true;}
      }catch(e:any){if(active){setSummary(null);setError(e.message);done=true;}}
      finally{loading=false;}
    }
    void load();const timer=setInterval(()=>{if(!done)void load();},2500);
    return()=>{active=false;clearInterval(timer);};
  },[jobId,retry]);
  async function start(){
    if(busy||!sourceJobId)return;const version=++creation.current,parent=sourceJobId,selected=jobId;
    setBusy(true);setError('');
    try{
      const value=await post('/jobs/'+parent+'/family-analyses',{family});
      if(version===creation.current&&source.current===parent&&selection.current===selected)onSelect(value.id);
      await onRefresh();
    }catch(e:any){if(version===creation.current&&source.current===parent)setError(e.message);}
    finally{if(version===creation.current)setBusy(false);}
  }
  async function control(command:string){
    if(busy||!jobId)return;const id=jobId;setBusy(true);setError('');
    try{await post('/jobs/'+id+'/'+command);if(selection.current===id)setRetry(n=>n+1);await onRefresh();}
    catch(e:any){if(selection.current===id)setError(e.message);}
    finally{setBusy(false);}
  }
  const eligible=['search','spread_accounts'].includes(sourceKind||'');
  return <section className="panel" aria-label="All-version family research">
    <div className="panel-head"><h2>All-version family research</h2><span className="badge">Equal weight · complete frozen membership</span></div>
    <p>Average the daily results of every version in one saved strategy family, including losing and zero-trade versions. This research average is separate from a shared-capital portfolio.</p>
    <p className="caption">Open a completed parameter search or spread-account cohort to choose its source. This is one saved window; separate era, instrument and final-test qualification is still required.</p>
    {eligible&&<div className="fields"><label className="field"><span>Family to analyze</span><select aria-label="Family to analyze" value={family} onChange={e=>setFamily(e.target.value)}>{Object.entries(familyLabels).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label><button type="button" disabled={busy} onClick={()=>void start()}>Queue complete family analysis</button><p>Original source: <code>{sourceJobId}</code></p></div>}
    <label className="field"><span>Saved family analysis</span><select aria-label="Saved family analysis" value={jobId} onChange={e=>onSelect(e.target.value)}><option value="">Choose a saved family analysis</option>{jobId&&!jobs.some(j=>j.id===jobId)&&<option value={jobId}>{jobId}</option>}{jobs.filter(j=>j.kind==='family_analysis').map(j=><option key={j.id} value={j.id}>{j.id} · {j.status}</option>)}</select></label>
    {error&&<p role="alert">{error}</p>}
    {jobId&&<button type="button" onClick={()=>setRetry(n=>n+1)}>Reload family evidence</button>}
    {job?.id===jobId&&<div><p aria-live="polite">Family job: {job.status}. {job.note}</p>{job.error&&<p role="alert">{job.error}</p>}
      {['queued','running','canceling'].includes(job.status)&&<button type="button" disabled={busy||job.status==='canceling'} onClick={()=>void control('cancel')}>Cancel family analysis</button>}
      {['failed','canceled'].includes(job.status)&&<button type="button" disabled={busy} onClick={()=>void control('resume')}>Resume original family analysis</button>}
    </div>}
    {summary?.job_id===jobId&&<div data-testid="family-analysis-output" data-job-id={jobId}>
      <h3>{familyLabels[summary.family]||summary.family} · {summary.version_count} complete versions</h3>
      <p>Source: <code>{summary.family_parent.original_job_id}</code>. Financial accounts rerun: {summary.financial_accounts_recomputed}. Final dates accessed: {summary.final_dates_accessed?'Yes':'No'}.</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Family convention comparison"><table><thead><tr><th>Convention</th><th>Sessions</th><th>Exact total P&L (USD)</th><th>Sharpe</th><th>Window gate</th></tr></thead><tbody>{Object.keys(names).map(key=>{const s=summary[key];return <tr key={key}><td>{names[key]}</td><td>{s.sessions}</td><td><code>{exact(s.net_profit)}</code></td><td>{s.sharpe===null?'Undefined':s.sharpe.toFixed(4)}</td><td>{s.gate_pass?'Pass':'Fail'}</td></tr>;})}</tbody></table></div>
      <p>Each window gate requires positive annualized mean profit and Sharpe ≥ 0.5. It does not certify the full research funnel or future profitability. The host's private engine and exact recipes remain unverified.</p>
      <div className="actions"><a download href={summary.complete_json_url}>Download complete family JSON</a><a download href={summary.daily_csv_url}>Download both daily conventions CSV</a><a download href={'/api/jobs/'+jobId+'/inputs'}>Download frozen analysis inputs</a><a href={summary.source_video} target="_blank" rel="noreferrer">Source YouTube video</a></div>
      <FamilyPage key={jobId+'members'} jobId={jobId} table="members" parentId={summary.family_parent.original_job_id}/>
      {Object.keys(names).map(key=><FamilyPage key={jobId+key} jobId={jobId} table={key} parentId={summary.family_parent.original_job_id}/>)}
    </div>}
  </section>;
}
