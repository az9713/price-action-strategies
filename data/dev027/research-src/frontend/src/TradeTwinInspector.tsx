import {useEffect,useRef,useState} from 'react';
import {api,post} from './api';

function useSaved(path:string|null,revision:number){
  const key=(path||'')+'|'+revision;
  const [state,setState]=useState<{key:string;value?:any;error?:string}>({key:''});
  useEffect(()=>{
    let current=true;const controller=new AbortController();setState({key});
    if(path)api(path,{signal:controller.signal}).then(value=>{if(current)setState({key,value});}).catch(error=>{if(current)setState({key,error:error.message});});
    return()=>{current=false;controller.abort();};
  },[path,revision]);
  return state.key===key?state:{key};
}

function Pages({page,busy,move,label}:{page:any;busy:boolean;move:(offset:number)=>void;label:string}){
  return <nav className="actions" aria-label={label}>
    <button type="button" disabled={busy||!page||page.offset===0} onClick={()=>move(Math.max(0,page.offset-page.limit))}>Previous {label}</button>
    <span aria-live="polite">{page?(page.total?`${page.offset+1}–${Math.min(page.offset+page.limit,page.total)} of ${page.total}`:'No records'):'Loading saved records'}</span>
    <button type="button" disabled={busy||page?.next_offset==null} onClick={()=>move(page.next_offset)}>Next {label}</button>
  </nav>;
}

const text=(value:any)=>value==null?'Unavailable':typeof value==='object'?JSON.stringify(value):String(value);

export function TradeTwinInspector({jobId,protocol}:{jobId:string;protocol:any}){
  const [policy,setPolicy]=useState('barrier_capped_elapsed_v1'),[offset,setOffset]=useState(0),[selected,setSelected]=useState<number|null>(null);
  const [memberOffset,setMemberOffset]=useState(0),[member,setMember]=useState<number|null>(null),[kind,setKind]=useState('ledger'),[recordOffset,setRecordOffset]=useState(0);
  const [revision,setRevision]=useState(0),[repairing,setRepairing]=useState(false),[repairError,setRepairError]=useState('');
  const mounted=useRef(false),repairPending=useRef(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const available=protocol?.version===2&&protocol?.book_evidence_version===1;
  const base='/jobs/'+jobId+'/trade-twins',query='?policy='+encodeURIComponent(policy);
  const sets=useSaved(available?base+'/sets'+query+'&offset='+offset+'&limit=25':null,revision);
  const members=useSaved(available&&selected!==null?base+'/sets/'+selected+'/members'+query+'&offset='+memberOffset+'&limit=25':null,revision);
  const records=useSaved(available&&selected!==null&&member!==null?base+'/sets/'+selected+'/books/'+member+query+'&kind='+kind+'&offset='+recordOffset+'&limit=25':null,revision);
  async function repair(){
    if(repairPending.current)return;repairPending.current=true;setRepairing(true);setRepairError('');
    try{await post(base+'/repair-view');if(mounted.current)setRevision(v=>v+1);}
    catch(error:any){if(mounted.current)setRepairError(error.message);}
    finally{repairPending.current=false;if(mounted.current)setRepairing(false);}
  }
  function choosePolicy(next:string){setPolicy(next);setOffset(0);setSelected(null);setMember(null);setMemberOffset(0);setRecordOffset(0);}
  function chooseSet(index:number){setSelected(index);setMember(null);setMemberOffset(0);setRecordOffset(0);}
  function chooseMember(index:number){setMember(index);setKind('ledger');setRecordOffset(0);}
  if(!available)return <p className="caption">This saved comparison predates bounded book inspection. Its original summary remains available. A new compatible comparison is required for this inspector.</p>;
  const book=records.value?.book,trade=book?.trade;
  return <section aria-label="Original saved trade-twin evidence" data-testid="trade-twin-inspector" data-job-id={jobId}>
    <h3>Inspect original saved financial evidence</h3>
    <p>Browse all sets, every source-trade assignment and complete event histories. Reopening and preparing these pages performs no new simulation.</p>
    <div className="actions"><button type="button" disabled={repairing} onClick={()=>void repair()}>Prepare saved inspection</button><button type="button" onClick={()=>setRevision(v=>v+1)}>Retry saved evidence pages</button><a href={'/api'+base+'/export'} download>Download complete saved evidence ZIP</a></div>
    {repairError&&<p role="alert">{repairError}</p>}
    <label className="field"><span>Saved interpretation</span><select aria-label="Saved interpretation" value={policy} onChange={e=>choosePolicy(e.target.value)}><option value="barrier_capped_elapsed_v1">Barriers with original elapsed-time cap</option><option value="fixed_elapsed_v1">Original elapsed holding time</option></select></label>
    {sets.error&&<p role="alert">{sets.error}</p>}
    <Pages page={sets.value?.pagination} busy={!sets.value} move={setOffset} label="financial sets"/>
    <div className="table-wrap" role="region" aria-label="Original financial sets" tabIndex={0}><table><thead><tr><th>Set</th><th>State</th><th>Exact net profit</th><th>Source members</th><th>Inspect</th></tr></thead><tbody>{sets.value?.rows.map((row:any)=><tr key={row.outcome.set_index}><td>{row.outcome.set_index+1}</td><td>{row.outcome.state}</td><td><code>{text(row.outcome.net_profit)}</code></td><td>{row.member_count}</td><td><button type="button" onClick={()=>chooseSet(row.outcome.set_index)}>Inspect set {row.outcome.set_index+1}</button></td></tr>)}</tbody></table></div>
    {selected!==null&&<section aria-label="Original set members" data-testid="trade-twin-members" data-set-index={selected}>
      <h4>Set {selected+1} · whole original source cohort</h4>
      {members.error&&<p role="alert">{members.error}</p>}
      {members.value&&<p>Saved state: {members.value.outcome.state}. Exact whole-set profit: <code>{text(members.value.outcome.net_profit)}</code>.</p>}
      <Pages page={members.value?.pagination} busy={!members.value} move={setMemberOffset} label="source members"/>
      <div className="table-wrap" role="region" aria-label="Original set assignments" tabIndex={0}><table><thead><tr><th>Member</th><th>Symbol / direction</th><th>Saved entry</th><th>Original elapsed cutoff</th><th>Shares</th><th>Inspect</th></tr></thead><tbody>{members.value?.rows.map((row:any)=><tr key={row.index}><td><code>{row.member.source_id}</code></td><td>{row.assignment.symbol} · {row.assignment.side===1?'Long':'Short'}</td><td>{row.assignment.entry_at}</td><td>{row.assignment.cutoff_at}</td><td>{row.assignment.quantity}</td><td><button type="button" onClick={()=>chooseMember(row.index)}>Inspect original book {row.index+1}</button></td></tr>)}</tbody></table></div>
    </section>}
    {selected!==null&&member!==null&&<section aria-label="Original financial book" data-testid="trade-twin-book" data-set-index={selected} data-member-index={member}>
      <h4>Original book · member {member+1}</h4>
      {records.error&&<p role="alert">{records.error}</p>}
      {book&&<><p>Saved financial outcome: {book.status}. {book.failure||''}</p><dl><dt>Exact net profit</dt><dd><code>{text(book.net_profit)}</code></dd>{trade&&<><dt>Executed entry / exit</dt><dd><code>{text(trade.entry_price)} / {text(trade.exit_price)}</code></dd><dt>Entry / exit shares</dt><dd><code>{text(trade.entry_quantity)} / {text(trade.exit_quantity)}</code></dd><dt>Fees / borrowing / distributions</dt><dd><code>{text(trade.fees)} / {text(trade.borrow)} / {text(trade.distributions)}</code></dd><dt>Exit</dt><dd>{trade.exit_at} · {trade.exit_reason}</dd></>}</dl></>}
      <label className="field"><span>Original event history</span><select aria-label="Original event history" value={kind} onChange={e=>{setKind(e.target.value);setRecordOffset(0);}}><option value="ledger">Cash ledger</option><option value="equity">Marked equity</option><option value="encounters">Barrier encounters</option><option value="rejected">Rejected executions</option></select></label>
      <Pages page={records.value?.pagination} busy={!records.value} move={setRecordOffset} label="financial events"/>
      <div className="table-wrap" role="region" aria-label="Original financial records" tabIndex={0}><table><thead><tr><th>Original order</th><th>Time</th><th>Event</th><th>Exact cash change / equity</th><th>Complete saved record</th></tr></thead><tbody>{records.value?.rows.map((row:any,index:number)=><tr key={recordOffset+index}><td>{recordOffset+index+1}</td><td>{row.timestamp||row.date||'As saved'}</td><td>{row.kind||kind}</td><td><code>{text(row.cash_change??row.equity)}</code></td><td><details><summary>All original fields</summary><pre>{JSON.stringify(row,null,2)}</pre></details></td></tr>)}</tbody></table></div>
    </section>}
    <p className="caption">Amounts remain exact saved strings. Each page is checked against original computation/member bindings. The ZIP contains full original parts and all financial histories; page sizes do not truncate the exported cohort.</p>
  </section>;
}
