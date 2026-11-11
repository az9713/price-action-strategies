import {DatasetContext} from './DatasetContext';
import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {Candles} from './Charts';

const measureNames:Record<string,string>={hold_fraction:'Hold fraction · all complete touches',hold_fraction_resolved_only:'Hold fraction · resolved only',wall_hold_fraction:'Wall hold fraction · all complete touches',wall_hold_fraction_resolved_only:'Wall hold fraction · resolved only',through_excursion_ATR:'Movement through the feature · ATR',successive_excursion_change_ATR:'Change in successive bounce size · ATR',full_fill_fraction:'Full gap-fill fraction',forward_close_move_ATR:'Forward closing-price movement · ATR',not_observed:'No observations'};
const frames=['1m','5m','15m','1h','4h','1d'];
const numeric=(v:number|null)=>v==null?'Undefined':v.toLocaleString('en-US',{maximumFractionDigits:5});
export function Behavior({inputs,jobs,selected,onSelect,onQueued,disabled,currentCore}:{
  inputs:any,jobs:any[],selected:string,onSelect:(id:string)=>void,onQueued:()=>Promise<void>,disabled:boolean,currentCore:string
}){
  const [timeframes,setTimeframes]=useState(['5m','15m','1h','4h','1d']),[replicas,setReplicas]=useState(20);
  const [saved,setSaved]=useState<any>(null),[chart,setChart]=useState<any>(null),[part,setPart]=useState<number|null>(null);
  const [table,setTable]=useState('levels_vs_shifted'),[scope,setScope]=useState('pooled'),[symbol,setSymbol]=useState('');
  const [eventIndex,setEventIndex]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const version=useRef(0),job=jobs.find(j=>j.id===selected),status=job?.status;
  useEffect(()=>{
    let current=true;version.current++;setSaved(null);setChart(null);setPart(null);setError('');setBusy(false);setEventIndex(0);
    if(selected&&status==='completed')api('/jobs/'+selected+'/report').then(r=>current&&setSaved({...r,loaded_job_id:selected})).catch(e=>current&&setError(e.message));
    return()=>{current=false;version.current++;};
  },[selected,status]);
  async function queue(){setBusy(true);setError('');try{const j=await post('/behavior',{...inputs,timeframes,shift_replicas:replicas});onSelect(j.id);await onQueued();}catch(e:any){setError(e.message);}finally{setBusy(false);}}
  async function openChart(index:number){
    const generation=++version.current;setBusy(true);setError('');setChart(null);setPart(null);setEventIndex(0);
    try{const r=await api('/jobs/'+selected+'/report?part='+index);if(generation!==version.current)return;setChart(r);setPart(index);setSymbol(Object.keys(r.bars)[0]||'');}
    catch(e:any){if(generation===version.current)setError(e.message);}finally{if(generation===version.current)setBusy(false);}
  }
  const chosen=saved?.tables[table],rows=chosen?.rows.filter((r:any)=>r.scope===scope)||[];
  const touches=chart?.touches.filter((t:any)=>t.symbol===symbol)||[],event=touches[eventIndex];
  return <section className="panel" aria-label="Price behavior experiments">
    {saved&&saved.loaded_job_id===selected&&<DatasetContext value={saved.dataset_context}/>}
    <div className="panel-head"><h2>Price behavior experiments</h2></div>
    <p>Measure how prices behave around confirmed features, using shifted stand-ins and matched random moments. ATR means average true range, a measure of recent candle movement. The 17 diagnostics follow the inventory visible in the source video.</p>
    <p className="caption">These are price measurements, not trades or account returns. Full 50-bar follow-up is required for touch outcomes. Short paths remain censored; complete undecided paths remain unresolved. A hold fraction includes unresolved cases in its denominator; the resolved-only fraction is separate.</p>
    <p>Selected dates: <b>{inputs.start} – {inputs.end}</b>. Select the dataset and dates above. Default charts are 5m/15m/1h/4h/daily; 1m is an additional equity adaptation.</p>
    <div className="checks" role="group" aria-label="Behavior charts">{frames.map(frame=><label className="check" key={frame}><input type="checkbox" aria-label={'Behavior '+frame} checked={timeframes.includes(frame)} onChange={()=>setTimeframes(timeframes.includes(frame)?timeframes.filter(x=>x!==frame):[...timeframes,frame])}/>{frame}</label>)}</div>
    <label className="field"><span>Shifted stand-ins per feature</span><input aria-label="Shifted stand-ins per feature" aria-describedby="behavior-shift-help" type="number" min={2} max={20} value={replicas} onChange={e=>setReplicas(Number(e.target.value))}/><small id="behavior-shift-help">Default 20. Shift 1–3 birth ATR; avoid known real features by 0.5 ATR. Each stand-in has its own visits and invalidation. Larger requests take longer.</small></label>
    <button disabled={disabled||busy||!timeframes.length} onClick={queue}>Run price behavior study</button>
    <label className="field"><span>Saved behavior job</span><select value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Choose saved behavior</option>{jobs.filter(j=>j.kind==='behavior').map(j=><option value={j.id} key={j.id}>{j.payload.name||j.id.slice(0,10)} · {j.status}</option>)}</select></label>
    {error&&<p className="error-text" role="alert">{error}</p>}
    {job&&status!=='completed'&&<p role="status">Behavior {status}: {job.note}{job.error?' · '+job.error:''}</p>}
    {saved&&<div data-testid="behavior-output" data-job-id={selected} data-core-hash={saved.core_hash}>
      <p><b>{saved.provenance.input_kind==='synthetic'?'Synthetic':'Historical'}</b> · {saved.start} – {saved.end} · {saved.settings.shift_replicas} stand-ins · {saved.settings.timeframes.join(', ')}</p>
      {saved.core_hash!==currentCore&&<p role="status" className="error-text">This saved behavior study uses an older numerical version. Run a new study for the current engine.</p>}
      <p data-testid="behavior-counts">{saved.counts.real_touches} real touches; {saved.counts.control_touches} shifted touches; {saved.counts.censored_touches} censored touches. {saved.counts.unshiftable_features} features have no complete matched shift set. {saved.counts.censored_forward_measures} censored and {saved.counts.unmatched_forward_measures} unmatched real forward measurements.</p>
      <div className="fields"><label className="field"><span>Behavior diagnostic</span><select value={table} onChange={e=>setTable(e.target.value)}>{Object.entries(saved.tables).map(([key,value]:any)=><option key={key} value={key}>{value.title}</option>)}</select></label><label className="field"><span>Behavior grouping</span><select value={scope} onChange={e=>setScope(e.target.value)}>{['pooled','timeframe','instrument','era'].map(x=><option key={x}>{x}</option>)}</select></label></div>
      <h3>{chosen?.title}</h3><p className="caption">Real minus pooled random mean. Fractions use 0–1; forward moves and excursions use ATR units. Marginal groups are descriptive. At least two sessions and 2000 valid whole-session draws are needed for an interval. Overlapping events and wider searches limit inference.</p>
      <div className="table-wrap" data-testid="behavior-table"><table><thead><tr><th>Group / category</th><th>Measure / bars</th><th>Real / random mean</th><th>Difference / 95% interval</th><th>Matched N real / random</th><th>Censored / unresolved real:random</th><th>Evidence</th></tr></thead><tbody>{rows.map((r:any,i:number)=><tr key={i}><td>{r.subset}<small className="block">{r.category}</small></td><td>{measureNames[r.metric]||r.metric}<small className="block">{r.horizon??'—'} bars · {r.unit??'—'}</small></td><td>{numeric(r.real_mean)} / {numeric(r.control_mean)}</td><td>{numeric(r.difference)}<small className="block">{r.interval_low==null?'Interval unavailable':numeric(r.interval_low)+' to '+numeric(r.interval_high)}</small></td><td>{r.real_n} / {r.control_n}<small className="block">Full real: {r.real_full_sample_n}</small></td><td>{r.real_censored}:{r.control_censored} / {r.real_unresolved}:{r.control_unresolved}</td><td>{r.status}<small className="block">{r.valid_resamples}/{r.resamples} valid draws</small></td></tr>)}</tbody></table></div>
      {!rows.length&&<p>No observations for this grouping. No comparison was established.</p>}
      <div className="actions"><a className="button primary" href={'/api/jobs/'+selected+'/export/json'} download>Download behavior-study JSON</a><a className="button" href={'/api/jobs/'+selected+'/export/csv?table='+table} download>Download diagnostic CSV</a></div>
      <details><summary>Behavior assumptions and fingerprints</summary><pre className="saved-configs">{JSON.stringify({settings:saved.settings,counts:saved.counts,era_split:saved.era_split,core_hash:saved.core_hash,dataset_manifest_hash:saved.dataset_manifest_hash,assumptions:saved.assumptions},null,2)}</pre></details>
      <div className="actions">{saved.charts.map((r:any)=><button key={r.part} disabled={busy} onClick={()=>openChart(r.part)}>Inspect {r.timeframe} behavior chart</button>)}</div>
      {chart&&<div data-testid="behavior-chart" data-timeframe={chart.timeframe}>
        <h3>{chart.timeframe} price chart and recorded geometry</h3>
        <label className="field"><span>Behavior chart instrument</span><select value={symbol} onChange={e=>{setSymbol(e.target.value);setEventIndex(0);}}>{Object.keys(chart.bars).map(s=><option key={s}>{s}</option>)}</select></label>
        <p className="caption">Normalized price candles. Feature geometry and touch availability are recorded below; no trade fills or profit annotations are implied.</p>
        <Candles bars={chart.bars[symbol]||[]}/>
        <label className="field"><span>Recorded behavior touch</span><select value={eventIndex} onChange={e=>setEventIndex(Number(e.target.value))}>{touches.map((t:any,i:number)=><option value={i} key={t.id}>{t.available_at} · {t.kind} · {t.shape} · {t.group}{t.replica==null?'':' '+(t.replica+1)} · {t.outcome}</option>)}</select></label>
        {!touches.length&&<p>No qualifying touches on this instrument/chart. Forward event and feature records remain in the JSON.</p>}
        {event&&<pre className="saved-configs" data-testid="behavior-touch">{JSON.stringify(event,null,2)}</pre>}
        <a className="button" href={'/api/jobs/'+selected+'/export/json?part='+part} download>Download behavior-chart JSON</a>
      </div>}
    </div>}
  </section>;
}
