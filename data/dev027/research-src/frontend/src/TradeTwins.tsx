import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {TradeTwinInspector} from './TradeTwinInspector';

const policies:Record<string,string>={barrier_capped_elapsed_v1:'Barriers with original elapsed-time cap',fixed_elapsed_v1:'Original elapsed holding time'};
const percent=(v:unknown)=>typeof v==='number'?(100*v).toFixed(4)+'%':'Unavailable';
const live=(s:string)=>['queued','running','canceling'].includes(s);

export function StartTradeTwins({parent,part,source,currentCore,onCreated}:{parent:string;part:number|null;source:any;currentCore:string;onCreated:(id:string)=>void}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const mounted=useRef(false),pending=useRef(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const compatible=source.core_hash===currentCore&&source.cashflow_audit?.policy==='decimal80-observed-fills-v1';
  async function start(){
    if(pending.current)return;pending.current=true;setBusy(true);setError('');
    try{const job=await post('/jobs/'+parent+'/trade-twins',{part:part??0});if(mounted.current)onCreated(job.id);}
    catch(e:any){if(mounted.current)setError(e.message);}
    finally{pending.current=false;if(mounted.current)setBusy(false);}
  }
  return <section className="panel" aria-label="Compare original account with random entries">
    <h2>Does the entry rule beat random entries?</h2>
    <p>Compare every executed trade in this saved account with 10,000 whole-cohort random-entry sets. The original quantities, costs, borrowing assumptions and holding times stay frozen. Both interpretations use the same random draws.</p>
    <p className="caption">This diagnoses entry timing under independently financed simulated books. It does not establish a tradable portfolio or future profitability. Canceled or failed work resumes the original child study.</p>
    {!compatible&&<p>A new account under the current numerical contract is required. This saved report remains readable.</p>}
    <button type="button" disabled={busy||!compatible} onClick={()=>void start()}>Compare saved account with random entries</button>
    {error&&<p role="alert">{error}</p>}
  </section>;
}

export function TradeTwins({jobId,jobs,onSelect,onRefresh,onLedger}:{jobId:string;jobs:any[];onSelect:(id:string)=>void;onRefresh:()=>Promise<void>;onLedger:(id:string)=>void}){
  const [job,setJob]=useState<any>(null),[report,setReport]=useState<any>(null),[error,setError]=useState(''),[acting,setActing]=useState(false);
  const revision=useRef(0),selected=useRef(jobId),pending=useRef(false),actingRef=useRef(false),mounted=useRef(false),loaded=useRef<any>(null);
  loaded.current=job;
  selected.current=jobId;
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;revision.current++;};},[]);
  async function load(id:string){
    if(!id||pending.current)return;
    const version=revision.current;pending.current=true;
    try{
      const value=await api('/jobs/'+id);
      const saved=value.status==='completed'?await api('/jobs/'+id+'/report'):null;
      if(mounted.current&&selected.current===id&&version===revision.current){setJob(value);setReport(saved);setError('');}
    }catch(e:any){if(mounted.current&&selected.current===id&&version===revision.current){setJob(null);setReport(null);setError(e.message);}}
    finally{if(version===revision.current)pending.current=false;}
  }
  useEffect(()=>{
    revision.current++;pending.current=false;setJob(null);setReport(null);setError('');setActing(false);
    if(!jobId)return;
    void load(jobId);const timer=setInterval(()=>{if(!pending.current&&loaded.current?.status!=='completed')void load(jobId);},2500);
    return()=>{clearInterval(timer);revision.current++;pending.current=false;};
  },[jobId]);
  async function control(command:string){
    if(actingRef.current||!jobId)return;actingRef.current=true;setActing(true);setError('');
    const id=jobId,version=revision.current;
    try{await post('/jobs/'+id+'/'+command);if(mounted.current&&selected.current===id&&revision.current===version)await load(id);await onRefresh();}
    catch(e:any){if(mounted.current&&selected.current===id&&revision.current===version)setError(e.message);}
    finally{actingRef.current=false;if(mounted.current&&selected.current===id&&revision.current===version)setActing(false);}
  }
  const current=job?.id===jobId?job:null;
  const output=current?.status==='completed'&&report?.report_type==='trade_twins'?report:null;
  const recent=jobs.filter(j=>j.kind==='trade_twins');
  return <section className="panel" aria-label="Saved trade-twin comparisons">
    <div className="panel-head"><h2>Trade-twin comparisons</h2><span className="badge">10,000 paired sets per interpretation</span></div>
    <p>Open a saved single-strategy account on Results to start its comparison. This workflow uses that account's complete executed-trade cohort and frozen assumptions.</p>
    <label className="field"><span>Saved trade-twin job</span><select aria-label="Saved trade-twin job" value={jobId} onChange={e=>onSelect(e.target.value)}><option value="">Choose a saved comparison</option>{jobId&&!recent.some(j=>j.id===jobId)&&<option value={jobId}>{jobId}</option>}{recent.map(j=><option key={j.id} value={j.id}>{j.name||j.id} · {j.status}</option>)}</select></label>
    {error&&<p role="alert">{error}</p>}
    {jobId&&<button type="button" onClick={()=>void load(jobId)}>Retry saved comparison</button>}
    {current&&<div data-testid="trade-twin-job" data-job-id={current.id}>
      <h3>Original comparison · {current.status}</h3><code>{current.id}</code>
      <progress aria-label="Trade-twin progress" max={1} value={current.progress}/><p aria-live="polite">{current.note}</p>
      {current.error&&<p role="alert">{current.error}</p>}
      <div className="actions">
        {live(current.status)&&<button type="button" disabled={acting||current.status==='canceling'} onClick={()=>void control('cancel')}>Cancel trade-twin comparison</button>}
        {['canceled','failed'].includes(current.status)&&<button type="button" disabled={acting} onClick={()=>void control('resume')}>Resume original trade-twin comparison</button>}
        <button type="button" onClick={()=>onLedger(current.id)}>Inspect original trial registry</button>
        <a href={'/api/jobs/'+current.id+'/inputs'} download>Download frozen comparison inputs</a>
        {output&&<a href={'/api/jobs/'+current.id+'/report'} download>Download comparison summary</a>}
      </div>
      {!output&&<p>No final score is published before both complete 10,000-set interpretations have been verified. An ineligible original cohort produces no financial sets.</p>}
    </div>}
    {output&&<div data-testid="trade-twin-output" data-job-id={jobId}>
      <p>Original source: <code>{output.source_parent.job_id}</code> · part {output.source_parent.part}. Source trades: {output.source.source_count}. Financial set occurrences: {output.financial_occurrences}. Unique saved books: {output.unique_committed_books}.</p>
      <p>Canonical original profit: <code>{output.source.source_profit}</code>. Original reported profit: <code>{output.source.reported_source_profit}</code>. Precision reconciliation difference: <code>{output.source.cashflow_precision_difference}</code>.</p>
      <p className="caption">Exact Decimal amounts determine ties and grading. The original float report is preserved separately. A strict pass requires fewer than 500 of 10,000 random sets to tie or beat the original.</p>
      <div className="table-wrap" role="region" aria-label="Trade-twin interpretation comparison" tabIndex={0}><table><thead><tr><th>Interpretation</th><th>State</th><th>Complete / required</th><th>Ties or better</th><th>Raw fraction</th><th>Plus-one diagnostic</th><th>Conditional 95% interval</th><th>Adapted gate</th></tr></thead><tbody>{Object.entries(output.summaries).map(([policy,s]:[string,any])=><tr key={policy}><td>{policies[policy]||policy}</td><td>{s.state}</td><td>{s.complete_sets} / {s.expected_sets}</td><td>{s.exceedances}</td><td>{percent(s.raw_exceedance_fraction)}</td><td>{percent(s.plus_one_diagnostic)}</td><td>{s.monte_carlo_interval_95?s.monte_carlo_interval_95.map(percent).join(' to '):'Unavailable'}</td><td>{s.adapted_pass===null?'Unavailable':s.adapted_pass?'Pass':'Fail'}</td></tr>)}</tbody></table></div>
      <p>The interval describes Monte Carlo uncertainty conditional on the saved history and matching rules. It does not correct strategy selection or establish future trading edge.</p>
      <details><summary>Frozen assumptions and implementation differences</summary><p>{output.assumptions.dataset_id} · {output.assumptions.start} through {output.assumptions.end} · seed {output.assumptions.seed}.</p><pre>{JSON.stringify(output.assumptions.strategy,null,2)}</pre>{output.limitations.map((s:string)=><p key={s}>{s}</p>)}<p>Historical short availability remains an explicit assumption. Exact reproduction of the host's private engine is unverified.</p></details>
      <TradeTwinInspector key={jobId} jobId={jobId} protocol={output.protocol}/>
      <p className="caption">This comparison summary is separate from the complete saved-evidence ZIP.</p>
    </div>}
  </section>;
}
