import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';
import {DatasetContext} from './DatasetContext';
import {statisticsPolicy} from './SearchStatistics';
import type {StatisticsDraft} from './SearchStatistics';

type Props={input:any;dataset:any;familyLabels:Record<string,string>;statistics:StatisticsDraft;jobs:any[];jobId:string;
  onJob:(id:string)=>void;onRefresh:()=>Promise<void>;onAccount:(id:string)=>void};
const charts=['1m','5m','15m','1h','4h','1d'];
const text=(v:string)=>v.replaceAll('_',' ');
const number=(v:unknown)=>typeof v==='number'?v.toLocaleString():'—';
const live=(s:string)=>['queued','running','canceling'].includes(s);

export function SpreadFlow({input,dataset,familyLabels,statistics,jobs,jobId,onJob,onRefresh,onAccount}:Props){
  const allFamilies=Object.keys(familyLabels);
  const [families,setFamilies]=useState(allFamilies),[frames,setFrames]=useState(charts);
  const [primary,setPrimary]=useState(dataset?.symbols?.[0]||''),[perFamily,setPerFamily]=useState(4000);
  const [batch,setBatch]=useState(400),[batches,setBatches]=useState(8000),[includeNews,setIncludeNews]=useState(false);
  const [minTrades,setMinTrades]=useState(30),[minSharpe,setMinSharpe]=useState(.5);
  const [preview,setPreview]=useState<any>(null),[previewing,setPreviewing]=useState(false),[formError,setFormError]=useState('');
  const [saved,setSaved]=useState<any>(null),[statusError,setStatusError]=useState(''),[actionError,setActionError]=useState('');
  const [acting,setActing]=useState(false),[notice,setNotice]=useState('');
  const [selectionState,setSelection]=useState<any>(null),[selectionFailure,setSelectionError]=useState<any>(null),[selectionBusy,setSelectionBusy]=useState(false);
  const [cursors,setCursors]=useState<number[]>([0]);
  const jobRef=useRef(jobId),mounted=useRef(true),previewVersion=useRef(0),statusVersion=useRef(0),selectionVersion=useRef(0),statusPending=useRef(0),actionPending=useRef(false);
  jobRef.current=jobId;
  const base={dataset_id:input.dataset_id,name:input.name,costs:input.costs,portfolio:input.portfolio,start:input.start,end:input.end,seed:input.seed,
    news_calendar_id:includeNews?(input.news_calendar_id||null):null};
  const settings={families,timeframes:frames,seed:input.seed,per_family:perFamily,batch_size:batch,max_batches_per_family:batches,minimum_signals:40,include_news:includeNews};
  const signature=JSON.stringify({base,primary,settings,minTrades,minSharpe,statistics});
  const signatureRef=useRef(signature);signatureRef.current=signature;
  const cursor=cursors[cursors.length-1];
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;previewVersion.current++;statusVersion.current++;selectionVersion.current++;};},[]);
  useEffect(()=>{setPrimary((old:string)=>dataset?.symbols?.includes(old)?old:(dataset?.symbols?.[0]||''));},[dataset?.id]);
  useEffect(()=>{previewVersion.current++;setPreview(null);setPreviewing(false);setFormError('');},[signature]);

  async function loadStatus(id:string){
    if(!id)return;const revision=++statusVersion.current;statusPending.current=revision;
    try{const value=await api('/spreads/'+id);if(mounted.current&&jobRef.current===id&&revision===statusVersion.current){setSaved(value);setStatusError('');}}
    catch(e:any){if(mounted.current&&jobRef.current===id&&revision===statusVersion.current){setSaved(null);setStatusError(e.message);}}
    finally{if(statusPending.current===revision)statusPending.current=0;}
  }
  useEffect(()=>{
    statusVersion.current++;selectionVersion.current++;statusPending.current=0;setSaved(null);setStatusError('');setActionError('');setNotice('');setSelection(null);setSelectionError(null);setCursors([0]);
    if(!jobId)return;void loadStatus(jobId);const timer=setInterval(()=>{if(!statusPending.current)void loadStatus(jobId);},2500);
    return()=>{clearInterval(timer);statusVersion.current++;selectionVersion.current++;statusPending.current=0;};
  },[jobId]);
  async function loadSelections(id:string,after:number){
    if(!id||id!==jobRef.current)return;const revision=++selectionVersion.current;setSelectionBusy(true);setSelectionError(null);
    try{const value=await api('/spreads/'+id+'/selections?after='+after+'&limit=50');if(mounted.current&&jobRef.current===id&&revision===selectionVersion.current)setSelection({job:id,after,value});}
    catch(e:any){if(mounted.current&&jobRef.current===id&&revision===selectionVersion.current){setSelection(null);setSelectionError({job:id,after,message:e.message});}}
    finally{if(mounted.current&&revision===selectionVersion.current)setSelectionBusy(false);}
  }
  useEffect(()=>{if(jobId&&saved?.job?.id===jobId)void loadSelections(jobId,cursor);},[jobId,cursor,saved?.job?.id,saved?.spread?.selected_versions]);

  function validate(){
    if(!families.length||!frames.length)throw Error('Choose at least one setup family and one chart.');
    for(const [name,value,max] of [['Versions per family',perFamily,100000],['Proposals per batch',batch,400],['Maximum batches per family',batches,100000]] as const){
      if(!Number.isInteger(value)||value<1||value>max)throw Error(name+' must be a whole number from 1 to '+max.toLocaleString()+'.');
    }
    if(perFamily*families.length>100000)throw Error('The selected target must be at most 100,000 versions.');
    if(!Number.isInteger(input.seed)||input.seed<0||input.seed>2147483647)throw Error('Use a whole-number master seed from 0 to 2,147,483,647 in Seed above.');
    if(!Number.isInteger(minTrades)||minTrades<1||minTrades>1000000||!Number.isFinite(minSharpe)||minSharpe<0||minSharpe>10)throw Error('Use a positive whole-number minimum trade count and a minimum Sharpe from 0 to 10.');
    if(includeNews&&!base.news_calendar_id)throw Error('Select a saved news calendar above before including news variants.');
    return statisticsPolicy(statistics,perFamily*families.length);
  }
  async function inspect(){
    const revision=++previewVersion.current,key=signature;setPreviewing(true);setFormError('');
    try{validate();const value=await post('/spreads/preview',settings);if(mounted.current&&revision===previewVersion.current&&key===signatureRef.current)setPreview({key,value});}
    catch(e:any){if(mounted.current&&revision===previewVersion.current&&key===signatureRef.current){setPreview(null);setFormError(e.message);}}
    finally{if(mounted.current&&revision===previewVersion.current)setPreviewing(false);}
  }
  async function queue(){
    if(actionPending.current)return;actionPending.current=true;setActing(true);setFormError('');setNotice('');const selectedAtStart=jobRef.current,requestedSignature=signature;
    try{
      const policy=validate();if(!dataset||!base.dataset_id||!dataset.symbols?.includes(primary))throw Error('Select saved data above and choose its primary instrument.');
      if(!preview||preview.key!==signature)throw Error('Preview the current spread work before queueing it.');
      const job=await post('/spreads',{...base,primary_symbol:primary,settings,statistics:policy,minimum_trades:minTrades,minimum_sharpe:minSharpe});
      if(mounted.current){setNotice('Frozen spread '+job.id+' queued. Its original assumptions remain fixed.');if(jobRef.current===selectedAtStart)onJob(job.id);}
      await onRefresh();
    }catch(e:any){if(mounted.current&&signatureRef.current===requestedSignature&&jobRef.current===selectedAtStart)setFormError(e.message);}
    finally{actionPending.current=false;if(mounted.current)setActing(false);}
  }
  async function control(id:string,command:string){
    if(actionPending.current)return;actionPending.current=true;setActing(true);setActionError('');const selectedAtStart=jobRef.current;
    try{await post('/jobs/'+id+'/'+command);if(mounted.current&&jobRef.current===selectedAtStart)await loadStatus(selectedAtStart);await onRefresh();}
    catch(e:any){if(mounted.current&&jobRef.current===selectedAtStart)setActionError(e.message);}
    finally{actionPending.current=false;if(mounted.current)setActing(false);}
  }
  async function accounts(){
    if(actionPending.current||!saved||saved.job.id!==jobId)return;actionPending.current=true;setActing(true);setActionError('');const selectedAtStart=jobId;
    try{const child=await post('/spreads/'+selectedAtStart+'/accounts',{});if(mounted.current&&jobRef.current===selectedAtStart){setNotice('Original account job '+child.id+' queued. Every selected rule and its assumptions remain frozen.');await loadStatus(selectedAtStart);}await onRefresh();}
    catch(e:any){if(mounted.current&&jobRef.current===selectedAtStart)setActionError(e.message);}
    finally{actionPending.current=false;if(mounted.current)setActing(false);}
  }
  async function repairLink(){
    if(actionPending.current||!jobId)return;actionPending.current=true;setActing(true);setActionError('');const selectedAtStart=jobId;
    try{await post('/spreads/'+selectedAtStart+'/repair-account-link',{});if(mounted.current&&jobRef.current===selectedAtStart)await loadStatus(selectedAtStart);}
    catch(e:any){if(mounted.current&&jobRef.current===selectedAtStart)setActionError(e.message);}
    finally{actionPending.current=false;if(mounted.current)setActing(false);}
  }
  const current=saved?.job?.id===jobId?saved:null,p=current?.spread,frozen=current?.job?.payload,child=current?.account_job;
  const selection=selectionState?.job===jobId&&selectionState?.after===cursor?selectionState.value:null;
  const selectionError=selectionFailure?.job===jobId&&selectionFailure?.after===cursor?selectionFailure.message:'';
  const ready=preview?.key===signature;
  const recent=jobs.filter(j=>j.kind==='spread');
  return <section className="panel" aria-label="Balanced spread workflow">
    <div className="panel-head"><h2>Balanced spread workflow</h2><span className="badge">Frozen discovery cohort</span></div>
    <p>Prepare rule variations, count their primary-instrument signals, then simulate every selected rule in a separately funded account. Proposal counts, signal probes and account simulations are recorded separately.</p>
    <p className="caption">The <a href="https://www.youtube.com/watch?v=z97PnFIPoFg" target="_blank" rel="noreferrer">AI Pathways source video</a> uses 4,000 selected versions per setup and 400 proposals per greedy step. Our equities rules, balance distance and bounded budget are documented adaptations; the private host engine and six named recipes are unavailable.</p>
    <h3>New spread inputs</h3><div className="actions"><button type="button" disabled={acting} onClick={()=>{setFamilies(allFamilies);setFrames(charts);setPerFamily(4000);setBatch(400);setBatches(8000);}}>Use source counts</button><button type="button" disabled={acting} onClick={()=>{setFamilies(['break_of_structure']);setFrames(['1m']);setPerFamily(1);setBatch(40);setBatches(2);}}>Use small functional run</button></div>
    <p className="caption">The small preset requests one structure-break rule on one-minute bars. It tests the workflow; it is separate from the 40,000-version source target.</p>
    <div className="fields">
      <label className="field"><span>Spread primary instrument</span><select aria-label="Spread primary instrument" value={primary} disabled={acting||!dataset} onChange={e=>setPrimary(e.target.value)}><option value="">Choose an instrument</option>{(dataset?.symbols||[]).map((s:string)=><option key={s}>{s}</option>)}</select></label>
      <label className="field"><span>Spread versions per family</span><input aria-label="Spread versions per family" type="number" min={1} max={100000} step={1} value={perFamily} disabled={acting} onChange={e=>setPerFamily(Number(e.target.value))}/></label>
      <label className="field"><span>Spread proposals per batch</span><input aria-label="Spread proposals per batch" type="number" min={1} max={400} step={1} value={batch} disabled={acting} onChange={e=>setBatch(Number(e.target.value))}/></label>
      <label className="field"><span>Spread maximum batches per family</span><input aria-label="Spread maximum batches per family" type="number" min={1} max={100000} step={1} value={batches} disabled={acting} onChange={e=>setBatches(Number(e.target.value))}/></label>
      <label className="field"><span>Spread minimum executed trades</span><input aria-label="Spread minimum executed trades" type="number" min={1} max={1000000} step={1} value={minTrades} disabled={acting} onChange={e=>setMinTrades(Number(e.target.value))}/></label>
      <label className="field"><span>Spread minimum marked Sharpe</span><input aria-label="Spread minimum marked Sharpe" type="number" min={0} max={10} step="any" value={minSharpe} disabled={acting} onChange={e=>setMinSharpe(Number(e.target.value))}/></label>
    </div>
    <p>Current data: {dataset?dataset.symbols.join(', '):'choose saved data above'} · {input.start} – {input.end}. Master seed {input.seed}; use Seed above to change it. Only the primary instrument enters this cohort's signal checks and accounts.</p>
    <fieldset disabled={acting}><legend>Spread setup families</legend><div className="checks">{allFamilies.map(f=><label className="check" key={f}><input type="checkbox" aria-label={'Spread setup '+familyLabels[f]} checked={families.includes(f)} onChange={()=>setFamilies(families.includes(f)?families.filter(v=>v!==f):[...families,f])}/>{familyLabels[f]}</label>)}</div></fieldset>
    <fieldset disabled={acting}><legend>Spread setup charts</legend><div className="checks">{charts.map(tf=><label className="check" key={tf}><input type="checkbox" aria-label={'Spread chart '+tf} checked={frames.includes(tf)} onChange={()=>setFrames(frames.includes(tf)?frames.filter(v=>v!==tf):[...frames,tf])}/>{tf}</label>)}</div></fieldset>
    <label className="check"><input aria-label="Spread news variants" type="checkbox" checked={includeNews} disabled={acting||(!input.news_calendar_id&&!includeNews)} onChange={e=>setIncludeNews(e.target.checked)}/>Include news variants using the saved calendar selected above</label>
    <p>At least 40 discovery-window signals are required for each selected version. Account screening then uses the frozen trade count, positive net profit and Sharpe threshold. Every complete account, including losses and undefined statistics, remains saved.</p>
    <div className="actions"><button type="button" disabled={acting||previewing} onClick={()=>void inspect()}>Preview spread work</button><button type="button" disabled={acting||previewing||!ready||!dataset} onClick={()=>void queue()}>Freeze and qualify spread</button></div>
    {formError&&<p role="alert" className="error-text">{formError}</p>}{notice&&<p role="status">{notice}</p>}
    {ready&&<div aria-label="Spread work preview"><p><b>{number(preview.value.selected_target)} selected versions requested</b> · {number(preview.value.planned_batches)} preparation batches · {number(preview.value.planned_proposals)} proposed variations fixed before the first signal check.</p><p className="caption">Full default resource use and completion time remain unmeasured. A batch selects at most one version; an exhausted budget produces no complete account cohort.</p></div>}
    <hr/><h3>Saved spread</h3><p className="caption">Its original assumptions are shown below and remain independent of the new-spread form above.</p><label className="field"><span>Reopen recent spread</span><select aria-label="Reopen recent spread" value={jobId} onChange={e=>onJob(e.target.value)}><option value="">Choose a saved spread</option>{jobId&&!recent.some(j=>j.id===jobId)&&<option value={jobId}>{jobId}</option>}{recent.map(j=><option key={j.id} value={j.id}>{j.payload?.name||j.id} · {text(j.status)} · {j.id.slice(0,10)}</option>)}</select></label>
    <p className="caption">Older spreads remain reachable through the saved job history on Results.</p>
    {jobId&&<div className="actions"><a href={'/api/jobs/'+jobId+'/inputs'} download>Download frozen spread inputs</a><a href={'/api/spreads/'+jobId+'/result'} download>Download original spread selection</a><a href={'/api/spreads/'+jobId+'/events'} download>Download spread journal page</a><a href={'/api/trials?job_id='+jobId} download>Download spread trial registry page</a><button type="button" disabled={!!statusPending.current} onClick={()=>void loadStatus(jobId)}>Retry saved spread status</button></div>}
    {statusError&&<div role="alert" className="error-text"><p>{statusError}</p><button type="button" disabled={acting} onClick={()=>void repairLink()}>Verify original account link</button><p className="caption">Restores a missing derived link only from intact original parent and child inputs. It cannot replace an account or reconstruct missing original evidence.</p></div>}{actionError&&<p role="alert" className="error-text">{actionError}</p>}
    {current&&<div aria-label="Saved spread progress"><h3>{text(current.job.status)} · {text(p.stage)}</h3><p><code>{jobId}</code> · {frozen?.context?.primary_symbol} · {frozen?.context?.start} – {frozen?.context?.end}. Frozen master seed {frozen?.settings?.seed}.</p><progress aria-label="Spread job progress" value={current.job.progress} max={1}/><p>{current.job.note}</p>{current.job.error&&<p role="alert">{current.job.error}</p>}
      <div className="metrics">{[['Frozen proposals',p.frozen_proposals],['Signal probes committed',p.committed_probes],['Signal computation attempts',p.probe_attempts],['Selected versions',p.selected_versions],['Requested selected versions',p.target_versions],['Below signal threshold',p.rejected_signal_versions]].map(([title,value])=><div key={String(title)}><span>{title}</span><b>{number(value)}</b></div>)}</div>
      <div className="actions">{live(current.job.status)&&<button type="button" disabled={acting||current.job.status==='canceling'} onClick={()=>void control(jobId,'cancel')}>Cancel spread qualification</button>}{['failed','canceled'].includes(current.job.status)&&<button type="button" disabled={acting} onClick={()=>void control(jobId,'resume')}>Resume original spread qualification</button>}</div>
      <DatasetContext value={frozen?.dataset_context}/><details><summary>Original account and screening assumptions</summary><pre className="saved-configs">{JSON.stringify({costs:frozen?.costs??'Not included in this bounded summary; use frozen inputs.',portfolio:frozen?.portfolio??'Use frozen inputs.',statistics:frozen?.statistics,minimum_trades:frozen?.minimum_trades,minimum_sharpe:frozen?.minimum_sharpe,news_calendar_id:frozen?.news_calendar_id??null},null,2)}</pre></details>
      {p.stage==='exhausted'&&<p className="error-text">The frozen budget was exhausted. The incomplete selection remains evidence; it cannot authorize account simulations.</p>}
      {current.job.status==='completed'&&p.qualified_complete&&!child&&<button type="button" disabled={acting} onClick={()=>void accounts()}>Simulate frozen cohort</button>}
      {child&&<section aria-label="Original spread account job"><h3>Original account job · {text(child.status)}</h3><p><code>{child.id}</code>. All selected rules use the original frozen assumptions. Repeated continuation returns this same job.</p><progress aria-label="Spread account progress" value={child.progress} max={1}/><p>{child.note}</p>{child.error&&<p role="alert">{child.error}</p>}<div className="actions">{child.status==='completed'&&<button type="button" disabled={acting} onClick={()=>onAccount(child.id)}>Open saved account results</button>}{live(child.status)&&<button type="button" disabled={acting||child.status==='canceling'} onClick={()=>void control(child.id,'cancel')}>Cancel spread accounts</button>}{['failed','canceled'].includes(child.status)&&<button type="button" disabled={acting} onClick={()=>void control(child.id,'resume')}>Resume original spread accounts</button>}<a href={child.inputs_url} download>Download frozen account inputs</a><a href={'/api/jobs/'+child.id+'/result'} download>Download complete account summary</a></div></section>}
    </div>}
    {current&&<section aria-label="Saved selected rules"><h3>Selected rules</h3>{selectionBusy&&<p role="status">Loading saved selected rules…</p>}{selectionError&&<p role="alert">{selectionError} <button type="button" onClick={()=>void loadSelections(jobId,cursor)}>Retry selected rules</button></p>}
      {selection&&<><p>{selection.versions.length?'Rules '+(selection.offset+1)+'–'+(selection.offset+selection.versions.length):'No selected rules on this page'} · {number(selection.selected_count)} selected in this saved snapshot.</p><div className="table-wrap"><table><thead><tr><th>Family / chart</th><th>Direction</th><th>Primary discovery signals</th><th>Original configuration</th></tr></thead><tbody>{selection.versions.map((v:any)=><tr key={v.event_id}><td>{familyLabels[v.family]||text(v.family)} · {v.configuration.timeframe}</td><td>{v.configuration.direction}</td><td>{v.signal_count}</td><td><code>{v.config_id.slice(0,12)}</code><details><summary>Complete selected rule</summary><pre className="saved-configs">{JSON.stringify(v.configuration,null,2)}</pre></details></td></tr>)}</tbody></table></div><div className="actions"><button type="button" disabled={selectionBusy||cursors.length===1} onClick={()=>setCursors(cursors.slice(0,-1))}>Previous selected rules</button><button type="button" disabled={selectionBusy||!selection.has_more} onClick={()=>setCursors([...cursors,selection.next_after])}>Next selected rules</button><button type="button" disabled={selectionBusy} onClick={()=>void loadSelections(jobId,cursor)}>Refresh selected rules</button></div><p className="caption">{selection.integrity_scope}</p></>}
    </section>}
  </section>;
}
