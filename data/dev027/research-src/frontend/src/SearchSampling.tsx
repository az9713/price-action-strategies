import {useSavedAccounts} from './SavedPages';
import {useEffect,useRef,useState} from 'react';
import {post} from './api';
import {NewsAssumptions} from './NewsCalendars';
export type SamplingDraft={mode:'legacy'|'common_grid'|'common_random',include_news:boolean};
export const defaultSampling:SamplingDraft={mode:'legacy',include_news:false};
const names:Record<string,string>={generated:'Generated rules',signal_qualified:'Enough signals',enough_trades:'Enough executed trades',profitable:'Positive net profit',sharpe_passed:'Sharpe threshold'};
const failures:Record<string,string>={signal_qualified:'Too few signals',enough_trades:'Too few executed trades',profitable:'No positive net profit',sharpe_passed:'Sharpe below threshold',undefined_sharpe:'Sharpe undefined'};

export function SearchSamplingInputs({value,onChange,families,frames,calendar,count,onCount,onReady}:{value:SamplingDraft,onChange:(v:SamplingDraft)=>void,families:string[],frames:string[],calendar:string,count:number,onCount:(n:number)=>void,onReady:(v:boolean)=>void}){
  const [preview,setPreview]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);const version=useRef(0);
  const key=JSON.stringify([value.mode,value.include_news,families,frames]);
  useEffect(()=>{version.current++;setPreview(null);setError('');setBusy(false);onReady(value.mode!=='common_grid');},[key]);
  async function inspect(){const current=++version.current;setBusy(true);setError('');try{
    const result=await post('/searches/preview',{families,timeframes:frames,include_news:value.include_news});
    if(current!==version.current)return;setPreview(result);if(value.mode==='common_grid')onCount(result.grid_count);onReady(true);
  }catch(e:any){if(current===version.current){setError(e.message);onReady(false);}}finally{if(current===version.current)setBusy(false);}}
  return <section aria-label="Sampling plan"><div className="fields"><label>Sampling method<select aria-label="Sampling method" value={value.mode} onChange={e=>onChange({mode:e.target.value as SamplingDraft['mode'],include_news:e.target.value==='legacy'?false:value.include_news})}><option value="legacy">Existing seeded parameter sample</option><option value="common_grid">Complete published common grid</option><option value="common_random">Common-style random sample · 40 / 40 / 20</option></select></label>
    {value.mode!=='legacy'&&<><label className="check"><input type="checkbox" aria-label="Include news filter variants" checked={value.include_news} disabled={!calendar&&!value.include_news} onChange={e=>onChange({...value,include_news:e.target.checked})}/>Include news variants from the selected calendar</label><button disabled={busy||!families.length||!frames.length} onClick={inspect}>Preview published recipe</button></>}
  </div>{error&&<p role="alert" className="error-text">{error}</p>}
  {value.mode!=='legacy'&&<><p className="muted">This search uses the published recipe instead of the single rule above. The complete grid enumerates every declared combination. The random mode allocates 40% with no filters, 40% with one and 20% with two within each family, with explicit rounding for small samples.</p>
    <p>Initial discovery gates: at least 40 signals, 30 executed trades, positive net profit, and marked-equity Sharpe of at least 0.5. Signals are opportunities; orders may never fill. These gates do not create a final-test candidate.</p>
    <p className="caption">Our equities grid and variants differ from the host's private 14,016-rule grid. Next-open entries replace its usual close-entry assumption. Futures New York-only sessions become an equity open-session variant. A small random sample can omit a permitted filter type. Six named host recipes remain unavailable. Balanced spread, trade twins, era and replication stages remain separate.</p>
    {value.mode==='common_grid'&&!preview&&<p>Preview the recipe before queueing the complete grid.</p>}
    {preview&&<details open><summary>Published recipe · {preview.grid_count.toLocaleString()} complete grid configurations</summary><p>{value.mode==='common_grid'?'The full grid count is fixed at '+count+'.':'Random requested count: '+count+'. The full grid count above is a separate reference.'} Recipe hash <code>{preview.recipe_hash}</code>.</p><pre className="saved-configs">{JSON.stringify(preview,null,2)}</pre></details>}
  </>}
  </section>;
}

export function SearchSamplingResults({screen,sampling,jobId,calendar,metadataComplete}:{screen:any,sampling:any,jobId:string,calendar:any,metadataComplete:boolean}){
  const saved=useSavedAccounts(screen,jobId);if(!screen)return null;
  const {page:current,pages}=saved;
  return <section className="panel" aria-label="Initial discovery funnel"><h2>Initial discovery funnel</h2><p>Every count below is cumulative. An initial pass is not a surviving strategy or final validation.</p>
    {!metadataComplete&&<p className="muted">This original summary predates complete sampling and news export metadata. Its frozen job inputs and saved account parts remain available. New searches record the complete assumptions.</p>}
    <p>News filter variants {screen.settings.include_news?'permitted':'disabled'}. {metadataComplete?(calendar?'The attached calendar is frozen with this search.':'No calendar is attached.'):'Calendar attachment was not recorded in this original summary.'}</p><NewsAssumptions calendar={calendar}/>
    <p>Frozen thresholds: {screen.settings.minimum_signals} signals; {screen.settings.minimum_trades} executed trades; profit strictly above $0; marked Sharpe at least {screen.settings.minimum_sharpe}.</p>
    <div className="metrics">{Object.entries(names).map(([key,title])=><div key={key}><span>{title}</span><b>{screen.counts[key]}</b></div>)}</div>
    <div className="table-wrap"><table><thead><tr><th>Family / chart</th>{Object.values(names).map(title=><th key={title}>{title}</th>)}</tr></thead><tbody>{(screen.groups||[]).map((g:any)=><tr key={g.family+g.timeframe}><td>{g.family.replaceAll('_',' ')} · {g.timeframe}</td>{Object.keys(names).map(k=><td key={k}>{g.counts[k]}</td>)}</tr>)}</tbody></table></div>
    <p>Trade twins, era checks, other-instrument replication, family ensembles and the final window have not run in this initial screen. No final dates are consumed by these gates.</p>
    <div className="table-wrap"><table><thead><tr><th>Part / rule</th><th>Signals</th><th>Executed trades</th><th>Net profit</th><th>Initial gates met</th><th>Unmet gates</th></tr></thead><tbody>{saved.accounts.map((a:any)=><tr key={a.part}><td>{a.part} · <code>{a.config_id.slice(0,12)}</code></td><td>{a.signal_count}</td><td>{a.trades}</td><td>{a.net_profit.toLocaleString('en-US',{style:'currency',currency:'USD'})}</td><td>{a.initial_gates_passed?'Yes · initial only':'No'}</td><td>{a.failures.map((f:string)=>failures[f]||f).join('; ')||'None at this stage'}</td></tr>)}</tbody></table></div>
    {saved.pending&&<p role="status">Loading saved accounts…</p>}{saved.error&&<p role="alert">{saved.error} <button onClick={saved.retry}>Retry saved accounts</button></p>}
    <div className="actions"><button disabled={current===1} onClick={()=>saved.move(current-1)}>Previous discovery accounts</button><span>Page {current} of {pages}; complete outcomes remain in the downloads.</span><button disabled={current===pages} onClick={()=>saved.move(current+1)}>Next discovery accounts</button></div>
    {metadataComplete&&<div className="actions"><a className="button" href={'/api/jobs/'+jobId+'/search-screen/export/json'} download>Download initial discovery JSON</a><a className="button" href={'/api/jobs/'+jobId+'/search-screen/export/csv'} download>Download all initial discovery CSV</a></div>}
    <details><summary>Frozen sampling recipe and generation history</summary>{sampling?<pre className="saved-configs">{JSON.stringify(sampling,null,2)}</pre>:<p>The complete recipe and every proposal are in the <a href={'/api/jobs/'+jobId+'/result'} download>original saved result download</a>.</p>}</details>
  </section>;
}
