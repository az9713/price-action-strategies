import {DatasetContext} from './DatasetContext';
import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {Candles,Equity} from './Charts';

const money=(v:number|null)=>v==null?'Undefined':v.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
const role=(row:any)=>row.role==='full_real'?'Full real account':row.role==='matched_real'?'Matched real account':'Random account '+(row.replica+1);

export function RandomControls({inputs,jobs,selected,onSelect,onQueued,disabled,currentCore,useOpenStrategy}:{
  inputs:any,jobs:any[],selected:string,onSelect:(id:string)=>void,onQueued:()=>Promise<void>,disabled:boolean,
  currentCore:string,useOpenStrategy:(()=>void)|null
}){
  const [replicas,setReplicas]=useState(20),[saved,setSaved]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [book,setBook]=useState<any>(null),[part,setPart]=useState<number|null>(null),[trade,setTrade]=useState<any>(null);
  const loadVersion=useRef(0);
  const job=jobs.find(j=>j.id===selected),status=job?.status;
  useEffect(()=>{
    let current=true;loadVersion.current++;setSaved(null);setBook(null);setPart(null);setTrade(null);setError('');setBusy(false);
    if(selected&&status==='completed')api('/jobs/'+selected+'/report').then(r=>current&&setSaved({...r,loaded_job_id:selected})).catch(e=>current&&setError(e.message));
    return()=>{current=false;loadVersion.current++;};
  },[selected,status]);
  async function queue(){setBusy(true);setError('');try{const j=await post('/controls',{...inputs,replicas});onSelect(j.id);await onQueued();}catch(e:any){setError(e.message);}finally{setBusy(false);}}
  async function openPart(index:number){
    const version=loadVersion.current;setBusy(true);setError('');
    try{const r=await api('/jobs/'+selected+'/report?part='+index);if(version!==loadVersion.current)return;setBook(r);setPart(index);setTrade(r.trades[0]||null);}
    catch(e:any){if(version===loadVersion.current)setError(e.message);}
    finally{if(version===loadVersion.current)setBusy(false);}
  }
  return <section className="panel" aria-label="Matched random controls">
    {saved&&saved.loaded_job_id===selected&&<DatasetContext value={saved.dataset_context}/>}
    <div className="panel-head"><h2>Matched random entries</h2></div>
    <p>Compare your selected rule with random moments on the same instrument and chart, matched by direction, 30-minute time-of-day bucket, candle duration and prior volatility. Every random account uses the same matched source sample and execution costs.</p>
    <p className="caption">This is a retrospective conditional comparison. It transfers the source event's ATR-relative stop/level/target geometry to each matched candle's known close and prior ATR. It does not create a new tradable strategy or establish a trading edge.</p>
    <p>Source rule: <b>{inputs.strategy.family.replaceAll('_',' ')} · {inputs.strategy.timeframe}</b> · {inputs.start} – {inputs.end}</p>
    <label className="field"><span>Random control accounts</span><input aria-label="Random control accounts" aria-describedby="random-control-count-help" type="number" min={2} max={200} value={replicas} onChange={e=>setReplicas(Number(e.target.value))}/><small id="random-control-count-help">The source uses20. These are separate simulated accounts; larger requests take longer and checkpoint after each complete account.</small></label>
    <div className="actions"><button disabled={disabled||busy} onClick={queue}>Run matched random controls</button>{useOpenStrategy&&<button onClick={useOpenStrategy}>Use open single-strategy inputs</button>}</div>
    <label className="field"><span>Saved random-control job</span><select value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Choose saved controls</option>{jobs.filter(j=>j.kind==='controls').map(j=><option key={j.id} value={j.id}>{j.payload.name||j.id.slice(0,10)} · {j.status}</option>)}</select></label>
    {error&&<p className="error-text" role="alert">{error}</p>}
    {job&&status!=='completed'&&<p role="status">Controls {status}: {job.note}{job.error?' · '+job.error:''}</p>}
    {saved&&<div data-testid="random-controls-output" data-job-id={selected} data-core-hash={saved.core_hash}>
      <p><b>{saved.provenance.input_kind==='synthetic'?'Synthetic':'Historical'}</b> · {saved.start} – {saved.end} · Starting capital {money(saved.portfolio.capital)}</p>
      {saved.core_hash!==currentCore&&<p role="status" className="error-text">This saved control study uses an older numerical version. Run a new study for the current engine.</p>}
      <p data-testid="matching-counts"><b>{saved.matching.matched_count}</b> matched source signals of <b>{saved.matching.source_count}</b>. Unmatched: <b>{saved.matching.unmatched.length}</b>. Signals and executed trades are different denominators.</p>
      {!saved.matching.matched_count&&<p role="status">Insufficient evidence: no matched source signals. No random comparison was certified.</p>}
      <dl><dt>Matched real net profit</dt><dd>{money(saved.comparison.real_net_profit)}</dd><dt>Mean random-account net profit</dt><dd>{money(saved.comparison.mean_control_net_profit)}</dd><dt>Real minus mean random profit</dt><dd>{money(saved.comparison.net_difference)}</dd><dt>Randomization exceedance fraction</dt><dd>{saved.comparison.exceedance_fraction==null?'Undefined':saved.comparison.exceedance_fraction.toFixed(4)} ({saved.comparison.control_at_least_real} of {saved.comparison.control_accounts} accounts at least as profitable; plus-one formula)</dd><dt>95% paired dollar P&amp;L interval</dt><dd>{saved.comparison.paired_pnl_interval?money(saved.comparison.paired_pnl_interval.low)+' to '+money(saved.comparison.paired_pnl_interval.high):'Insufficient observations or executed trades'}</dd></dl>
      {saved.comparison.limitations.map((text:string)=><p className="caption" key={text}>{text}</p>)}
      <div className="table-wrap"><table><thead><tr><th>Account / sample</th><th>Executed trades</th><th>Net profit</th><th>Daily drawdown</th><th/></tr></thead><tbody>{saved.books.map((row:any)=><tr key={row.part}><td>{role(row)}</td><td>{row.metrics.trades}</td><td>{money(row.metrics.net_profit)}</td><td>{(row.metrics.max_drawdown*100).toFixed(2)}%</td><td><button disabled={busy} onClick={()=>openPart(row.part)}>Inspect {role(row).toLowerCase()}</button></td></tr>)}</tbody></table></div>
      <p className="caption">The full real account is context only. The matched real account is the comparison denominator. Low trade counts and many dependent tests limit interpretation.</p>
      <details><summary>Unmatched source events and reasons</summary><pre className="saved-configs">{JSON.stringify(saved.matching.unmatched,null,2)}</pre></details>
      <details><summary>Frozen rules, matching streams and fingerprints</summary><pre className="saved-configs">{JSON.stringify({config:saved.config,seed:saved.seed,core_hash:saved.core_hash,dataset_manifest_hash:saved.dataset_manifest_hash,matching:saved.matching},null,2)}</pre></details>
      <a className="button primary" href={'/api/jobs/'+selected+'/export/json'} download>Download control-study JSON</a>
      {book&&<div data-testid="control-book" data-role={book.role}>
        <h3>{role(book)} · {money(book.metrics.net_profit)}</h3><Equity rows={book.equity} capital={book.portfolio.capital}/>
        <div className="actions"><a className="button" href={'/api/jobs/'+selected+'/export/json?part='+part} download>Download selected account JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv?part='+part} download>Download selected account CSV</a></div>
        <div className="table-wrap trades-table"><table><thead><tr><th>Instrument / side</th><th>Entry UTC</th><th>Exit</th><th>Net profit</th><th/></tr></thead><tbody>{book.trades.map((t:any)=><tr key={t.id}><td>{t.symbol} · {t.side===1?'Long':'Short'}</td><td>{t.entry_at}</td><td>{t.exit_reason}</td><td>{money(t.net_pnl)}</td><td><button onClick={()=>setTrade(t)}>Inspect control trade</button></td></tr>)}</tbody></table></div>
        {!book.trades.length&&<p>No executed trades in this account. This is not a passing strategy badge.</p>}
        {trade&&<><h3>{trade.symbol} · {trade.side===1?'Long':'Short'} · {money(trade.net_pnl)}</h3><Candles bars={book.charts[trade.symbol]||[]} trade={trade}/><details><summary>Selected trade ledger</summary><pre className="saved-configs">{JSON.stringify(book.ledger.filter((e:any)=>e.trade_id===trade.id),null,2)}</pre></details></>}
      </div>}
    </div>}
  </section>;
}
