import {DatasetContext} from './DatasetContext';
import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {Equity} from './Charts';
import {BorrowAssumptions,BorrowRateOverride} from './Borrowing';

const money=(v:number|null)=>v==null?'Undefined':v.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
const rate=(v:number)=>(v*100).toFixed(0)+'%';

export function BorrowSensitivity({inputs,jobs,selected,onSelect,onQueued,onLedger,onOpen,disabled,currentCore}:{
  inputs:any,jobs:any[],selected:string,onSelect:(id:string)=>void,onQueued:()=>Promise<void>,onLedger:(id:string)=>void,
  onOpen:(job:string,part:number)=>Promise<void>,disabled:boolean,currentCore:string
}){
  const [saved,setSaved]=useState<any>(null),[book,setBook]=useState<any>(null),[part,setPart]=useState<number|null>(null);
  const [offset,setOffset]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loadedJob,setLoadedJob]=useState<any>(null);
  const version=useRef(0),job=jobs.find(j=>j.id===selected)||(loadedJob?.id===selected?loadedJob:null),status=job?.status;
  useEffect(()=>{let active=true;setLoadedJob(null);if(selected)api('/jobs/'+selected).then(j=>active&&setLoadedJob(j)).catch(e=>active&&setError(e.message));return()=>{active=false;};},[selected]);
  useEffect(()=>{
    let active=true;version.current++;setSaved(null);setBook(null);setPart(null);setOffset(0);setError('');setBusy(false);
    if(selected&&status==='completed')api('/jobs/'+selected+'/report').then(r=>active&&setSaved({...r,loaded_job_id:selected})).catch(e=>active&&setError(e.message));
    return()=>{active=false;version.current++;};
  },[selected,status]);
  async function queue(){setBusy(true);setError('');try{const j=await post('/borrow-sensitivity',inputs);onSelect(j.id);await onQueued();}catch(e:any){setError(e.message);}finally{setBusy(false);}}
  async function control(action:string){setBusy(true);setError('');try{await post('/jobs/'+selected+'/'+action);await onQueued();}catch(e:any){setError(e.message);}finally{setBusy(false);}}
  async function inspect(index:number){
    const generation=++version.current;setBusy(true);setError('');setBook(null);setPart(null);setOffset(0);
    try{const r=await api('/jobs/'+selected+'/report?part='+index);if(generation!==version.current)return;setBook({...r,loaded_job_id:selected});setPart(index);}
    catch(e:any){if(generation===version.current)setError(e.message);}finally{if(generation===version.current)setBusy(false);}
  }
  const daily=part===null?null:saved?.daily_differences.find((r:any)=>r.part===part);
  return <section className="panel" aria-label="Borrowing cost comparison">
    {saved&&saved.loaded_job_id===selected&&<DatasetContext value={saved.dataset_context}/>}
    <h2>Compare borrowing costs</h2>
    <p>Run four separate accounts at annual borrowing rates of <b>0%, 3%, 10% and 30%</b>. Each account executes its own fills, whole-share sizes and cash movements. A higher charge can change later position sizes; profits are never scaled from another account.</p>
    <p>Each rate replaces both the initial rate and every scheduled event rate. Short availability, recalls and all other inputs stay fixed. Your original costs remain saved separately. Existing scenario names and notes are context; the explicit rate override determines the applied charges.</p>
    <p className="caption">These are assumed lending conditions. Differences are descriptive, scenario minus the zero-rate account. No new difference interval, significance or independent-trial count is inferred. Ordinary research cannot access protected final-test dates.</p>
    <p>New run: <b>{inputs.strategy.family.replaceAll('_',' ')} · {inputs.strategy.timeframe}</b> · {inputs.start} – {inputs.end}.</p>
    <button disabled={disabled||busy} onClick={queue}>Run four borrowing-rate accounts</button>
    <label className="field"><span>Saved borrowing-cost comparison</span><select value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Choose saved borrowing comparison</option>{jobs.filter(j=>j.kind==='borrow_sensitivity').map(j=><option key={j.id} value={j.id}>{j.payload.name||j.id.slice(0,10)} · {j.status}</option>)}</select></label>
    {selected&&<div className="actions"><button onClick={()=>onLedger(selected)}>Show borrowing comparison trial records</button>
      {['queued','running','canceling'].includes(status)&&<button disabled={busy||status==='canceling'} onClick={()=>control('cancel')}>Cancel borrowing comparison</button>}
      {['failed','canceled'].includes(status)&&<button disabled={busy} onClick={()=>control('resume')}>Resume borrowing comparison</button>}</div>}
    {error&&<p className="error-text" role="alert">{error}</p>}
    {job&&status!=='completed'&&<p role="status">Borrowing comparison {status}: {job.note}{job.error?' · '+job.error:''}</p>}
    {saved&&saved.loaded_job_id===selected&&<div data-testid="borrow-sensitivity-output" data-job-id={selected} data-core-hash={saved.core_hash}>
      <p><b>{saved.provenance.input_kind==='synthetic'?'Synthetic':'Historical'} price inputs</b> · {saved.start} – {saved.end} · four complete accounts. Lending conditions remain assumptions.</p>
      <p>Saved rule: <b>{saved.config.family.replaceAll('_',' ')} · {saved.config.timeframe}</b>. The form above describes a new run.</p>
      {saved.core_hash!==currentCore&&<p className="error-text" role="status">This comparison uses an older numerical version. Run a new comparison for the current engine.</p>}
      <div className="table-wrap"><table aria-label="Borrowing rate account outcomes"><thead><tr><th>Annual rate</th><th>Net profit</th><th>Difference from zero rate</th><th>Borrow paid</th><th>Other fees</th><th>Signals / trades / shorts</th><th>Outcome</th><th/></tr></thead><tbody>{saved.comparison_rows.map((r:any)=><tr key={r.part} data-part={r.part}><td>{rate(r.annual_rate)}</td><td>{money(r.net_profit)}</td><td>{money(r.delta_from_zero)}</td><td>{money(r.borrow_paid)}</td><td>{money(r.fees_paid)}</td><td>{r.signals} / {r.trades} / {r.short_trades}</td><td>{r.no_short_trades?'No short trades':r.net_profit>0?'Profitable simulation':r.net_profit<0?'Losing simulation':'Flat simulation'}</td><td><button disabled={busy} onClick={()=>inspect(r.part)}>Inspect {rate(r.annual_rate)} account</button></td></tr>)}</tbody></table></div>
      <p className="caption">No short trades is a visible outcome, not evidence that borrowing costs are immaterial to other strategies. Each account's uncertainty remains separate from these differences.</p>
      <div className="actions"><a className="button" href={'/api/jobs/'+selected+'/export/json'} download>Download borrowing comparison JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv'} download>Download borrowing comparison CSV</a><a className="button" href={'/api/jobs/'+selected+'/export/html'} download>Download borrowing comparison presentation</a></div>
      <details><summary>Original costs and frozen comparison inputs</summary><pre className="saved-configs">{JSON.stringify({original_costs:saved.original_costs,original_costs_id:saved.original_costs_id,rate_policy:saved.rate_policy,arms:saved.arms.map((a:any)=>({part:a.part,annual_rate:a.annual_rate,costs:a.costs,costs_id:a.costs_id,account_id:a.account_id})),config:saved.config,config_id:saved.config_id,portfolio:saved.portfolio,dataset_manifest_hash:saved.dataset_manifest_hash,core_hash:saved.core_hash,news_calendar:saved.news_calendar,limitations:saved.limitations},null,2)}</pre></details>
      {book&&book.loaded_job_id===selected&&<div data-testid="borrow-sensitivity-account" data-part={part}>
        <h3>{rate(book.borrow_sensitivity.annual_rate)} annual borrowing · {money(book.metrics.net_profit)}</h3>
        <BorrowRateOverride policy={book.borrow_sensitivity}/><BorrowAssumptions costs={book.costs}/>
        <Equity rows={book.equity} capital={book.portfolio.capital}/>
        {!book.trades.length&&<p>No executed trades in this account. This does not establish a trading edge.</p>}
        <div className="actions"><button disabled={busy} onClick={async()=>{setError('');try{await onOpen(selected,part!);}catch(e:any){setError(e.message);}}}>Open selected account and trade inspector</button><a className="button" href={'/api/jobs/'+selected+'/export/json?part='+part} download>Download selected borrowing-account JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv?part='+part} download>Download selected borrowing-account CSV</a></div>
        {daily&&<><h3>Daily difference from the zero-rate account</h3><p>Every eligible session is included, even without trades. Dollar values are marked daily profit; difference is selected account minus zero-rate account.</p>
          <div className="table-wrap"><table aria-label="Daily borrowing cost differences"><thead><tr><th>Session</th><th>Zero-rate profit</th><th>Selected-account profit</th><th>Difference</th></tr></thead><tbody>{daily.rows.slice(offset,offset+50).map((r:any)=><tr key={r.date}><td>{r.date}</td><td>{money(r.baseline_profit)}</td><td>{money(r.scenario_profit)}</td><td>{money(r.difference)}</td></tr>)}</tbody></table></div>
          {daily.rows.length>50&&<div className="actions"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous daily differences</button><span>{offset+1}–{Math.min(offset+50,daily.rows.length)} of {daily.rows.length}</span><button disabled={offset+50>=daily.rows.length} onClick={()=>setOffset(offset+50)}>Next daily differences</button></div>}</>}
      </div>}
    </div>}
  </section>;
}
