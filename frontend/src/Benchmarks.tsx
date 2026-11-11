import {DatasetContext} from './DatasetContext';
import {useEffect,useState} from 'react';
import {api,post} from './api';
import {Equity} from './Charts';

const money=(value:number)=>value.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
const pct=(value:number)=>(value*100).toFixed(2)+'%';
function stable(value:any):string {
  if(value===null||typeof value!=='object')return JSON.stringify(value);
  if(Array.isArray(value))return '['+value.map(stable).join(',')+']';
  return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}';
}

export function Benchmarks({inputs,jobs,selected,onSelect,strategyReport,onUseStrategy,onQueued,disabled,currentCore}:{
  inputs:any,jobs:any[],selected:string,onSelect:(id:string)=>void,strategyReport:any,
  onUseStrategy:()=>void,onQueued:()=>Promise<void>,disabled:boolean,currentCore:string
}){
  const [saved,setSaved]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const job=jobs.find(j=>j.id===selected),status=job?.status;
  useEffect(()=>{
    let current=true;setSaved(null);setError('');
    if(selected&&status==='completed')api('/jobs/'+selected+'/report').then(r=>{if(current)setSaved({...r,loaded_job_id:selected});}).catch(e=>current&&setError(e.message));
    return()=>{current=false;};
  },[selected,status]);
  async function queue(){
    setBusy(true);setError('');
    try{const j=await post('/benchmarks',inputs);onSelect(j.id);await onQueued();}
    catch(e:any){setError(e.message);}finally{setBusy(false);}
  }
  const comparable=saved&&strategyReport&&['dataset_id','dataset_manifest_hash','core_hash','start','end','costs','portfolio'].every(k=>stable(saved[k])===stable(strategyReport[k]));
  return <section className="panel" aria-label="Cash and buy-and-hold benchmarks">
    {saved&&saved.loaded_job_id===selected&&<DatasetContext value={saved.dataset_context}/>}
    <div className="panel-head"><h2>Cash & buy-and-hold comparisons</h2></div>
    <p>Run two simple alternatives using the selected dataset, dates, costs and initial account. Cash earns zero interest. Buy-and-hold buys an initially equal-weighted basket, subject to cash, entry exposure and prior-minute volume limits.</p>
    <p className="caption">One entry attempt per instrument; no stops or rebalancing. Risk fraction is not applied to passive holdings. Actual allocations can differ from the requested weights and drift later.</p>
    <div className="actions"><button disabled={disabled||busy} onClick={queue}>Run cash and buy-and-hold</button>{strategyReport&&<button onClick={onUseStrategy}>Use open strategy's inputs</button>}</div>
    <label className="field"><span>Saved benchmark job</span><select value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Choose a benchmark comparison</option>{jobs.filter(j=>j.kind==='benchmark').map(j=><option key={j.id} value={j.id}>{j.payload.name||j.id.slice(0,10)} · {j.status}</option>)}</select></label>
    {error&&<p className="error-text" role="alert">{error}</p>}
    {job&&status!=='completed'&&<p role="status">Benchmark {status}: {job.note}{job.error?' · '+job.error:''}</p>}
    {saved&&<div data-testid="benchmark-output" data-core-hash={saved.core_hash}>
      <p><b>{saved.provenance.input_kind==='synthetic'?'Synthetic':'Historical'}</b> · {saved.start} – {saved.end} · Starting capital {money(saved.portfolio.capital)}</p>
      {saved.core_hash!==currentCore&&<p className="error-text" role="status">This saved benchmark uses an older numerical version. It remains a historical report; run a new comparison for the current engine.</p>}
      <details><summary>Saved dataset and numerical fingerprints</summary><p>Dataset <code>{saved.dataset_id}</code></p><p>Dataset manifest <code>{saved.dataset_manifest_hash}</code></p><p>Numerical version <code>{saved.core_hash}</code></p></details>
      <div className="table-wrap"><table><thead><tr><th>Alternative</th><th>Net profit</th><th>Total return</th><th>Daily drawdown</th><th>Trades</th></tr></thead><tbody>{(['cash','buy_hold'] as const).map(key=>{const m=saved.benchmarks[key].metrics;return <tr key={key}><td>{key==='cash'?'Cash, zero interest':'Buy-and-hold basket'}</td><td>{money(m.net_profit)}</td><td>{pct(m.total_return)}</td><td>{pct(m.max_drawdown)}</td><td>{m.trades}</td></tr>;})}</tbody></table></div>
      {comparable?<p data-testid="benchmark-delta">Open strategy net profit minus buy-and-hold: <b>{money(strategyReport.metrics.net_profit-saved.benchmarks.buy_hold.metrics.net_profit)}</b>. This difference alone does not establish a trading edge or equal risk.</p>:<p className="caption">A strategy difference is shown only when the saved dataset, dates, numerical version, costs and account settings all match the open strategy.</p>}
      <h3>Buy-and-hold daily marked equity</h3><Equity rows={saved.benchmarks.buy_hold.equity} capital={saved.portfolio.capital}/>
      <h3>Actual initial allocations</h3><div className="table-wrap"><table><thead><tr><th>Instrument</th><th>Target weight</th><th>Shares</th><th>Entry notional</th><th>Unused allocation</th></tr></thead><tbody>{saved.benchmarks.buy_hold.allocation.map((a:any)=><tr key={a.symbol}><td>{a.symbol}</td><td>{pct(a.target_initial_weight)}</td><td>{a.entry_quantity}</td><td>{money(a.actual_entry_notional)}</td><td>{money(a.uninvested_initial_allocation)}</td></tr>)}</tbody></table></div>
      {saved.benchmarks.buy_hold.rejected.map((r:any,i:number)=><p className="muted" key={i}>{r.symbol}: {r.reason}</p>)}
      {saved.benchmarks.assumptions.map((s:string)=><p className="caption" key={s}>{s}</p>)}
      <div className="actions"><a className="button primary" href={'/api/jobs/'+selected+'/export/json'} download>Download benchmark JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv'} download>Download passive trade CSV</a></div>
      <details><summary>Benchmark cash ledger and receivables</summary><pre className="saved-configs">{JSON.stringify({ledger:saved.benchmarks.buy_hold.ledger,outstanding_receivables:saved.benchmarks.buy_hold.outstanding_receivables},null,2)}</pre></details>
    </div>}
  </section>;
}
