import {useEffect,useState} from 'react';
import {api,post} from './api';

function Download({value}:{value:any}){
  const [url,setUrl]=useState('');
  useEffect(()=>{if(!value){setUrl('');return;}const u=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));setUrl(u);return()=>URL.revokeObjectURL(u);},[value]);
  return url?<a className="button" href={url} download="borrowing-scenario.json">Download borrowing scenario JSON</a>:null;
}

export function BorrowEditor({value,onChange,symbols,start,end}:{value:any,onChange:(v:any)=>void,symbols:string[],start:string,end:string}){
  const [draft,setDraft]=useState<any>(value),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  const [offset,setOffset]=useState(0);
  useEffect(()=>{setDraft(value);setOffset(0);},[value]);
  function field(key:string,v:any){setDraft({...draft,[key]:v});setMessage('Changes are not applied yet.');}
  function change(index:number,key:string,v:any){const events=draft.events.map((e:any,i:number)=>i===index?{...e,[key]:v,...(key==='recall'&&v?{available:false}:{})}:e);field('events',events);}
  async function apply(raw?:string){setBusy(true);setError('');try{
    const result=raw===undefined?await post('/borrow-scenarios/validate',draft):await api('/borrow-scenarios/validate',{method:'POST',body:raw});
    onChange(result.scenario);setMessage('Applied borrowing scenario '+result.scenario_id+'. '+(result.scenario.complete?'The exact inputs will be frozen with the run.':'Incomplete coverage remains blocked for runs.'));
  }catch(e){setError((e as Error).message);setMessage('Changes were not applied.');}finally{setBusy(false);}}
  return <section aria-label="Changing short borrowing" className="panel">
    <h3>Changing short borrowing</h3><p>A borrowing rate is the yearly cost of holding a short position. Availability controls new short attempts. A recall requires an existing short to close at the next observed minute opening.</p>
    <p className="caption">These are assumed or synthetic lending conditions. Regular price data does not establish historical availability. Financing uses the documented 365-day research convention, including weekends; exact broker billing and margin are separate.</p>
    <label className="field"><span>Import borrowing scenario JSON</span><input aria-label="Import borrowing scenario JSON" type="file" accept=".json,application/json" disabled={busy} onChange={async e=>{const f=e.target.files?.[0];if(!f)return;if(f.size>2*1024*1024){setError('Borrow scenario JSON exceeds two MiB.');return;}await apply(await f.text());e.target.value='';}}/></label>
    {!draft?<button type="button" onClick={()=>setDraft({name:'Borrowing assumptions',start,end,symbols:symbols.length?symbols:['SPY'],complete:false,mode:'assumed',note:'',events:[]})}>Add changing borrowing scenario</button>:<>
      <div className="fields"><label className="field"><span>Borrow scenario name</span><input aria-label="Borrow scenario name" value={draft.name} onChange={e=>field('name',e.target.value)}/></label>
      <label className="field"><span>Borrowing assumption type</span><select aria-label="Borrowing assumption type" value={draft.mode} onChange={e=>field('mode',e.target.value)}><option value="assumed">Assumed lending conditions</option><option value="synthetic">Synthetic testing scenario</option></select></label>
      <label className="field"><span>Borrow coverage start</span><input aria-label="Borrow coverage start" type="date" value={draft.start} onChange={e=>field('start',e.target.value)}/></label>
      <label className="field"><span>Borrow coverage end</span><input aria-label="Borrow coverage end" type="date" value={draft.end} onChange={e=>field('end',e.target.value)}/></label>
      <label className="field"><span>Covered borrow instruments</span><input aria-label="Covered borrow instruments" value={draft.symbols.join(',')} onChange={e=>field('symbols',e.target.value.split(',').map(v=>v.trim()))}/></label></div>
      <label className="check"><input type="checkbox" checked={draft.complete} onChange={e=>field('complete',e.target.checked)}/>I reviewed borrowing coverage for every declared instrument and date</label>
      <p>Constant availability and annual rate above apply initially. Each event replaces that instrument's full borrowing state from its stated UTC minute. Availability loss alone keeps existing loans open; a recall remains binding on an existing loan even after a later event clears it.</p>
      {draft.events.slice(offset,offset+20).map((event:any,n:number)=>{const i=offset+n;return <fieldset key={i}><legend>Borrow event {i+1}</legend><div className="fields">
        <label className="field"><span>Instrument</span><input aria-label={'Borrow event instrument '+(i+1)} value={event.symbol} onChange={e=>change(i,'symbol',e.target.value)}/></label>
        <label className="field"><span>Effective time (UTC)</span><input aria-label={'Borrow event UTC time '+(i+1)} type="datetime-local" step={60} value={event.effective_at.replace(/(?:Z|\+00:00)$/,'')} onChange={e=>change(i,'effective_at',e.target.value+(e.target.value.length===16?':00Z':'Z'))}/></label>
        <label className="field"><span>Annual rate (%)</span><input aria-label={'Borrow event annual percent '+(i+1)} type="number" min={0} max={500} step="any" value={event.annual_rate==null?'':event.annual_rate*100} onChange={e=>change(i,'annual_rate',e.target.value===''?null:Number(e.target.value)/100)}/></label>
        <label className="check"><input aria-label={'Borrow event available '+(i+1)} type="checkbox" checked={event.available} onChange={e=>change(i,'available',e.target.checked)}/>New shorts available</label>
        <label className="check"><input aria-label={'Borrow event recall '+(i+1)} type="checkbox" checked={event.recall} onChange={e=>change(i,'recall',e.target.checked)}/>Recall existing shorts</label>
        <button type="button" onClick={()=>field('events',draft.events.filter((_:any,k:number)=>i!==k))}>Remove borrow event {i+1}</button>
      </div></fieldset>;})}
      {draft.events.length>20&&<div className="actions"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous borrow events</button><span>{offset+1}–{Math.min(offset+20,draft.events.length)} of {draft.events.length}</span><button disabled={offset+20>=draft.events.length} onClick={()=>setOffset(offset+20)}>Next borrow events</button></div>}
      <label className="field"><span>Borrowing note</span><textarea aria-label="Borrowing note" value={draft.note} maxLength={1000} onChange={e=>field('note',e.target.value)}/></label>
      <div className="actions"><button type="button" disabled={draft.events.length>=10000} onClick={()=>{field('events',[...draft.events,{symbol:draft.symbols[0]||'SPY',effective_at:draft.start+'T14:30:00Z',annual_rate:.03,available:true,recall:false}]);setOffset(Math.floor(draft.events.length/20)*20);}}>Add borrow event</button>
      <button type="button" className="primary" disabled={busy} onClick={()=>apply()}>Apply borrowing scenario</button>
      <button type="button" onClick={()=>{setDraft(null);onChange(null);setMessage('Using constant borrowing assumptions.');}}>Use constant borrowing only</button></div>
    </>}
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}<Download value={value}/>
  </section>;
}

export function BorrowRateOverride({policy}:{policy:any}){
  return policy?<section className="panel" aria-label="Applied borrowing rate override"><h2>Applied borrowing rate override</h2><p>This account applies {(policy.annual_rate*100).toFixed(0)}% annually to both the initial state and every scheduled event. Availability and recalls retain their saved states. Scenario names and notes describe the original context; this explicit override determines the charges.</p><p className="caption">Original costs fingerprint: <code>{policy.original_costs_id}</code>. This is a lending assumption, not observed historical lending data.</p></section>:null;
}

export function BorrowAssumptions({costs}:{costs:any}){
  const spec=costs?.borrow_scenario;const [offset,setOffset]=useState(0);
  useEffect(()=>setOffset(0),[spec]);
  return spec?<section className="panel" aria-label="Saved short borrowing scenario"><h2>Saved short borrowing scenario</h2>
    <p><b>{spec.name}</b> · {spec.mode==='synthetic'?'Synthetic lending scenario':'Assumed lending conditions'} · {spec.start} to {spec.end}</p>
    <p>Historical availability is not established. Initial annual rate: {(costs.borrow_annual*100).toFixed(2)}%; initial new-short availability: {costs.borrow_available?'available':'unavailable'}. Events replace each instrument's state. Recall exits occur at the next observed opening; calendar-time financing uses 365 days.</p>
    <p>Covered instruments: {spec.symbols.join(', ')}. {spec.note}</p>
    <div className="table-wrap"><table><thead><tr><th>Instrument</th><th>Effective UTC</th><th>Annual rate</th><th>New shorts</th><th>Recall</th></tr></thead><tbody>{spec.events.slice(offset,offset+50).map((e:any,i:number)=><tr key={i}><td>{e.symbol}</td><td>{e.effective_at}</td><td>{(e.annual_rate*100).toFixed(2)}%</td><td>{e.available?'Available':'Unavailable'}</td><td>{e.recall?'Required':'No new recall'}</td></tr>)}</tbody></table></div>
    {spec.events.length>50&&<div className="actions"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous saved borrow events</button><span>{offset+1}–{Math.min(offset+50,spec.events.length)} of {spec.events.length}</span><button disabled={offset+50>=spec.events.length} onClick={()=>setOffset(offset+50)}>Next saved borrow events</button></div>}
    <Download value={spec}/></section>:null;
}
