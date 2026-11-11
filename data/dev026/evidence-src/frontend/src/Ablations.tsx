import {DatasetContext} from './DatasetContext';
import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {Candles,Equity} from './Charts';

const label=(s:string)=>s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const display=(v:any)=>v===null?'Auto':typeof v==='boolean'?(v?'On':'Off'):String(v);
const money=(v:number|null)=>v==null?'Undefined':v.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
function options(spec:any):any[]|null{
  if(spec?.enum)return spec.enum;
  if(spec?.type==='boolean')return [false,true];
  if(spec?.anyOf){const choices=spec.anyOf.find((s:any)=>s.enum)?.enum;if(choices)return [...choices,...(spec.anyOf.some((s:any)=>s.type==='null')?[null]:[])];}
  return null;
}

export function Ablations({inputs,schema,jobs,selected,onSelect,onQueued,onLedger,disabled,currentCore}:{
  inputs:any,schema:any,jobs:any[],selected:string,onSelect:(id:string)=>void,onQueued:()=>Promise<void>,onLedger:(id:string)=>void,disabled:boolean,currentCore:string
}){
  const [field,setField]=useState('target'),[alternatives,setAlternatives]=useState<any[]>(['2R','3R']),[numbers,setNumbers]=useState('');
  const [saved,setSaved]=useState<any>(null),[book,setBook]=useState<any>(null),[part,setPart]=useState<number|null>(null),[trade,setTrade]=useState<any>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[loadedJob,setLoadedJob]=useState<any>(null);
  const version=useRef(0),job=jobs.find(j=>j.id===selected)||(loadedJob?.id===selected?loadedJob:null),status=job?.status;
  const spec=schema.properties[field],choices=options(spec),baseline=inputs.strategy[field];
  useEffect(()=>{const choices=options(schema.properties[field]);setAlternatives(choices?(field==='target'?['2R','3R'].filter(v=>v!==baseline):choices.filter(v=>v!==baseline).slice(0,2)):[]);setNumbers('');},[field,baseline,schema]);
  useEffect(()=>{let active=true;setLoadedJob(null);if(selected)api('/jobs/'+selected).then(j=>active&&setLoadedJob(j)).catch(e=>active&&setError(e.message));return()=>{active=false;};},[selected]);
  useEffect(()=>{
    let active=true;version.current++;setSaved(null);setBook(null);setPart(null);setTrade(null);setError('');setBusy(false);
    if(selected&&status==='completed')api('/jobs/'+selected+'/report').then(r=>active&&setSaved({...r,loaded_job_id:selected})).catch(e=>active&&setError(e.message));
    return()=>{active=false;version.current++;};
  },[selected,status]);
  async function queue(){
    setBusy(true);setError('');
    try{
      const values=choices?alternatives:numbers.split(',').filter(s=>s.trim()!=='').map(s=>Number(s.trim()));
      if(!values.length||values.some(v=>typeof v==='number'&&!Number.isFinite(v)))throw Error('Choose alternative values, or enter valid numbers separated by commas.');
      const j=await post('/ablations',{...inputs,field,alternatives:values});onSelect(j.id);await onQueued();
    }catch(e:any){setError(e.message);}finally{setBusy(false);}
  }
  async function inspect(index:number){
    const generation=++version.current;setBusy(true);setError('');setBook(null);setPart(null);setTrade(null);
    try{const r=await api('/jobs/'+selected+'/report?part='+index);if(generation!==version.current)return;setBook({...r,loaded_job_id:selected});setPart(index);setTrade(r.trades[0]||null);}
    catch(e:any){if(generation===version.current)setError(e.message);}finally{if(generation===version.current)setBusy(false);}
  }
  return <section className="panel" aria-label="Paired rule comparisons">
    {saved&&saved.loaded_job_id===selected&&<DatasetContext value={saved.dataset_context}/>}
    <div className="panel-head"><h2>Change one rule, compare the result</h2></div>
    <p>Run your baseline and alternatives on the same data, dates, costs and starting account. Each alternative changes one declared strategy setting. Each account generates its own signals, fills and position sizes.</p>
    <p className="caption">The comparison pairs daily dollar profit on the complete session calendar, including days without trades. Changing a rule can change which trades occur; matching different trade lists by row would be misleading. These are descriptive comparisons, not a claim that a rule will work in the future.</p>
    <p>Baseline: <b>{label(inputs.strategy.family)} · {inputs.strategy.timeframe}</b> · {inputs.start} – {inputs.end}. Select the baseline rule on Strategies and the data/dates above.</p>
    <label className="field"><span>Rule to vary</span><select value={field} onChange={e=>setField(e.target.value)}>{Object.keys(schema.properties).map(name=><option key={name} value={name}>{label(name)}</option>)}</select></label>
    <p>Baseline {label(field)}: <b>{display(baseline)}</b></p>
    {choices?<div className="checks" role="group" aria-label="Alternative rule values">{choices.filter(v=>v!==baseline).map(v=><label className="check" key={JSON.stringify(v)}><input aria-label={'Compare '+field+' '+display(v)} type="checkbox" checked={alternatives.some(a=>a===v)} onChange={()=>setAlternatives(alternatives.some(a=>a===v)?alternatives.filter(a=>a!==v):[...alternatives,v])}/>{display(v)}</label>)}</div>:
      <label className="field"><span>Alternative numeric values</span><input aria-label="Alternative numeric values" value={numbers} onChange={e=>setNumbers(e.target.value)} placeholder="For example: 1, 3, 5"/><small>Use 1–32 distinct alternatives. Every complete configuration is validated; dependent settings are never silently reset.</small></label>}
    <p className="caption">Some settings depend on others. Invalid combinations are rejected with a reason. News alternatives require the selected complete versioned calendar. Changing a chart or trigger may also change the inferred trigger; saved comparisons display both effective triggers.</p>
    <button disabled={disabled||busy} onClick={queue}>Run paired rule comparison</button>
    <label className="field"><span>Saved rule-comparison job</span><select value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Choose saved comparison</option>{jobs.filter(j=>j.kind==='ablation').map(j=><option key={j.id} value={j.id}>{j.payload.name||j.id.slice(0,10)} · {j.status}</option>)}</select></label>
    {selected&&<button onClick={()=>onLedger(selected)}>Show this study's trial records</button>}
    {error&&<p className="error-text" role="alert">{error}</p>}
    {job&&status!=='completed'&&<p role="status">Comparison {status}: {job.note}{job.error?' · '+job.error:''}</p>}
    {saved&&saved.loaded_job_id===selected&&<div data-testid="ablation-output" data-job-id={selected} data-core-hash={saved.core_hash}>
      <p><b>{saved.provenance.input_kind==='synthetic'?'Synthetic':'Historical'}</b> · {saved.start} – {saved.end} · {saved.arms.length} separate accounts · Changed setting: <b>{label(saved.field)}</b></p>
      <p>Saved baseline: <b>{label(saved.arms[0].config.family)} · {saved.arms[0].config.timeframe}</b>. The form above describes the inputs for a new run.</p>
      {saved.core_hash!==currentCore&&<p className="error-text" role="status">This saved comparison uses an older numerical version. Run a new study for the current engine.</p>}
      <div className="table-wrap"><table><thead><tr><th>Alternative / baseline</th><th>Net profit: alternative / baseline</th><th>Difference / 95% paired interval</th><th>Signals: alternative / baseline / shared</th><th>Trades: alternative / baseline</th><th>Effective trigger</th><th>Evidence</th></tr></thead><tbody>{saved.comparisons.map((r:any)=><tr key={r.alternative_config_id}><td>{display(r.alternative_value)} / {display(r.baseline_value)}</td><td>{money(r.alternative_net_profit)} / {money(r.baseline_net_profit)}</td><td>{money(r.net_difference)}<small className="block">{r.paired_pnl_interval?money(r.paired_pnl_interval.low)+' to '+money(r.paired_pnl_interval.high):'Interval unavailable'}</small></td><td>{r.alternative_signals} / {r.baseline_signals} / {r.common_decision_signals}</td><td>{r.alternative_trades} / {r.baseline_trades}</td><td>{r.alternative_trigger} / {r.baseline_trigger}</td><td>{r.status}<small className="block">{r.sessions} sessions</small></td></tr>)}</tbody></table></div>
      <p className="caption">Dollar difference is alternative minus baseline. The five-session block interval needs at least six sessions and executed trades in both accounts. This minimum avoids a mechanical zero-width interval; it does not establish adequate statistical power or correct for trying many alternatives.</p>
      <div className="actions"><a className="button primary" href={'/api/jobs/'+selected+'/export/json'} download>Download comparison JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv'} download>Download comparison CSV</a></div>
      <div className="table-wrap"><table><thead><tr><th>Account</th><th>Rule value</th><th>Trades</th><th>Net profit</th><th/></tr></thead><tbody>{saved.arms.map((r:any)=><tr key={r.part}><td>{r.role==='baseline'?'Baseline':'Alternative '+r.part}</td><td>{display(r.value)}</td><td>{r.metrics.trades}</td><td>{money(r.metrics.net_profit)}</td><td><button disabled={busy} onClick={()=>inspect(r.part)}>Inspect {r.role==='baseline'?'baseline':'alternative '+r.part}</button></td></tr>)}</tbody></table></div>
      <details><summary>Frozen assumptions and fingerprints</summary><pre className="saved-configs">{JSON.stringify({field:saved.field,arms:saved.arms.map((a:any)=>({role:a.role,config_id:a.config_id,config:a.config})),baseline_config_id:saved.baseline_config_id,core_hash:saved.core_hash,dataset_manifest_hash:saved.dataset_manifest_hash,costs:saved.costs,portfolio:saved.portfolio,assumptions:saved.assumptions},null,2)}</pre></details>
      {book&&book.loaded_job_id===selected&&<div data-testid="ablation-account" data-part={part}>
        <h3>{part===0?'Baseline':'Alternative '+part} · {money(book.metrics.net_profit)}</h3><Equity rows={book.equity} capital={book.portfolio.capital}/>
        <div className="actions"><a className="button" href={'/api/jobs/'+selected+'/export/json?part='+part} download>Download selected rule-account JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv?part='+part} download>Download selected rule-account CSV</a></div>
        {!book.trades.length&&<p>No executed trades in this account. This is not a passing strategy result.</p>}
        <div className="table-wrap trades-table"><table><thead><tr><th>Instrument / side</th><th>Entry UTC</th><th>Exit</th><th>Net profit</th><th/></tr></thead><tbody>{book.trades.map((t:any)=><tr key={t.id}><td>{t.symbol} · {t.side===1?'Long':'Short'}</td><td>{t.entry_at}</td><td>{t.exit_reason}</td><td>{money(t.net_pnl)}</td><td><button onClick={()=>setTrade(t)}>Inspect rule-comparison trade</button></td></tr>)}</tbody></table></div>
        {trade&&<><h3>{trade.symbol} · {trade.side===1?'Long':'Short'} · {money(trade.net_pnl)}</h3><Candles bars={book.charts[trade.symbol]||[]} trade={trade}/><details><summary>Selected account trade ledger</summary><pre className="saved-configs">{JSON.stringify(book.ledger.filter((r:any)=>r.trade_id===trade.id),null,2)}</pre></details></>}
      </div>}
    </div>}
  </section>;
}
