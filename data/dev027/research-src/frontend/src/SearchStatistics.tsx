import {useSavedAccounts} from './SavedPages';

export type StatisticsDraft={trials:string,mode:'empirical'|'assumed',dispersion:string};
export const defaultStatisticsDraft:StatisticsDraft={trials:'',mode:'empirical',dispersion:''};
function grid(count:number){
  if(!Number.isInteger(count)||count<1||count>100000)return [];
  const values=[1];for(let power=10;power<count;power*=10)values.push(power);
  return [...new Set([...values,count])];
}
export function statisticsPolicy(value:StatisticsDraft,count:number){
  if(!grid(count).length)throw Error('Choose an integer configuration count between 1 and 100000.');
  const trials=value.trials.trim()?value.trials.split(',').map(s=>s.trim()?Number(s):NaN):null;
  if(trials&&(!trials.length||trials.length>16||new Set(trials).size!==trials.length||trials.some(n=>!Number.isInteger(n)||n<1||n>count)))throw Error('Trial assumptions must be distinct integers between 1 and the configuration count; use at most 16.');
  const dispersion=value.mode==='assumed'&&value.dispersion.trim()?Number(value.dispersion):null;
  if(value.mode==='assumed'&&(dispersion===null||!Number.isFinite(dispersion)||dispersion<0||dispersion>1000))throw Error('Enter a finite nonnegative daily Sharpe standard deviation, at most 1000.');
  return {effective_trials:trials,dispersion_mode:value.mode,trial_sharpe_std:dispersion};
}
export function SearchStatisticsInputs({value,onChange,count}:{value:StatisticsDraft,onChange:(v:StatisticsDraft)=>void,count:number}){
  return <details><summary>Search-bias assumptions</summary><p className="muted">Finding the best rule among many can reward chance. Compare assumed independent trial counts; the raw number of rules does not estimate independence. These settings are frozen before the search.</p><div className="fields">
    <label>Assumed independent trial counts<input aria-label="Assumed independent trial counts" maxLength={200} value={value.trials} placeholder={'Automatic: '+grid(count).join(', ')} onChange={e=>onChange({...value,trials:e.target.value})}/><small>Comma-separated integers. Blank uses the displayed automatic sensitivity grid within this search.</small></label>
    <label>Trial Sharpe dispersion<select aria-label="Trial Sharpe dispersion" value={value.mode} onChange={e=>onChange({...value,mode:e.target.value as StatisticsDraft['mode']})}><option value="empirical">Measure across every completed account</option><option value="assumed">Use an explicit assumption</option></select></label>
    {value.mode==='assumed'&&<label>Assumed daily Sharpe standard deviation<input aria-label="Assumed daily Sharpe standard deviation" type="number" min={0} max={1000} step="any" value={value.dispersion} onChange={e=>onChange({...value,dispersion:e.target.value})}/></label>}
  </div><p className="caption">Dispersion and Sharpe inputs use daily units. Earlier experiments, manual selection and serial dependence are not corrected by this diagnostic. It does not change candidate gates.</p></details>;
}

const numeric=(value:number|null)=>value===null?'Undefined':value.toPrecision(6);
const reasons:Record<string,string>={insufficient_observations:'Needs at least four sessions',zero_return_variance:'No return variation',invalid_returns:'Missing or invalid returns',nonfinite_moments:'Unstable or nonfinite moments',dispersion_unavailable:'Cross-trial spread unavailable',invalid_model_variance:'Model variance is undefined'};
export function SearchStatisticsResults({data,jobId,start,end,isSearch}:{data:any,jobId:string,start:string,end:string,isSearch:boolean}){
  const saved=useSavedAccounts(data,jobId);
  if(!data)return isSearch?<section className="panel" aria-label="Search-bias sensitivity"><h2>Search-bias sensitivity</h2><p>This saved search predates the diagnostic. Its original evidence is unchanged. A new search freezes its assumptions before execution.</p></section>:null;
  const {page:current,pages}=saved;
  return <section className="panel" aria-label="Search-bias sensitivity"><h2>Search-bias sensitivity</h2>
    <p>{start} – {end}. {data.raw_configurations} complete configurations; {data.finite_sharpe_accounts} accounts with finite daily Sharpe estimates.</p>
    <p>Dispersion: {data.settings.dispersion_mode}; daily Sharpe standard deviation {numeric(data.trial_sharpe_std)}. Assumed independent trials: {data.settings.effective_trials.join(', ')}.</p>
    <p>Generated proposals {data.raw_generation.attempts??'Unknown'}; unique {data.raw_generation.unique??'Unknown'}; duplicates {data.raw_generation.duplicates??'Unknown'}; invalid {data.raw_generation.rejected??'Unknown'}. The diagnostic adds no independent trial.</p>
    <p className="muted">The DSR model score is a diagnostic under these assumptions. A high score does not establish profit or a surviving strategy. Null scores stay undefined; no account is removed.</p>
    <div className="table-wrap"><table><thead><tr><th>Part / configuration</th><th>Net profit</th><th>Sessions</th><th>Daily Sharpe</th><th>Assumed trials</th><th>DSR model score</th><th>Undefined reason</th></tr></thead><tbody>
      {saved.accounts.flatMap((a:any)=>a.sensitivity.map((v:any)=><tr key={a.part+'-'+v.effective_trials}><td>{a.part} · <code>{a.config_id.slice(0,12)}</code></td><td>{a.net_profit.toLocaleString('en-US',{style:'currency',currency:'USD'})}</td><td>{a.observations}</td><td>{numeric(a.daily_sharpe)}</td><td>{v.effective_trials}</td><td>{numeric(v.score)}</td><td>{reasons[v.undefined_reason]||v.undefined_reason||'Defined'}</td></tr>))}
    </tbody></table></div>
    {saved.pending&&<p role="status">Loading saved accounts…</p>}{saved.error&&<p role="alert">{saved.error} <button onClick={saved.retry}>Retry saved accounts</button></p>}
    <div className="actions"><button disabled={current===1} onClick={()=>saved.move(current-1)}>Previous statistic accounts</button><span>Page {current} of {pages}; all accounts remain in the downloads.</span><button disabled={current===pages} onClick={()=>saved.move(current+1)}>Next statistic accounts</button></div>
    <ul>{data.limitations.map((s:string)=><li key={s}>{s}</li>)}</ul>
    <div className="actions"><a className="button" href={'/api/jobs/'+jobId+'/search-statistics/export/json'} download>Download search statistics JSON</a><a className="button" href={'/api/jobs/'+jobId+'/search-statistics/export/csv'} download>Download all search statistics CSV</a><a className="button" href={'/api/jobs/'+jobId+'/export/html'} download>Download search presentation</a><a className="button" href={'/api/jobs/'+jobId+'/result'} download>Download saved search summary JSON</a></div>
    <p className="caption">Definition: <a href={data.source} target="_blank" rel="noreferrer">Bailey and López de Prado, Deflated Sharpe Ratio</a>. No effective independent count or global error guarantee is inferred here.</p>
  </section>;
}
