import {useEffect,useState} from 'react';
import {api} from './api';

// Tag both requests and responses. A changed job/page hides the previous rows
// immediately, before the effect starts the next request.
export function useSavedAccounts(source:any,jobId:string){
  const owner=jobId+'|'+(source?.accounts_page_url||'legacy');
  const [selection,setSelection]=useState({owner:'',page:1});
  const page=selection.owner===owner?selection.page:1;
  const [attempt,setAttempt]=useState(0);
  const key=owner+'|'+page+'|'+attempt;
  const [response,setResponse]=useState<{key:string,value?:any,error?:string}>({key:''});
  const url=source?.accounts_page_url;
  useEffect(()=>{
    if(!url)return;
    let current=true;
    api(url.replace(/^\/api/,'')+'?limit=20&offset='+((page-1)*20))
      .then(value=>{if(current)setResponse({key,value});})
      .catch(error=>{if(current)setResponse({key,error:error.message});});
    return()=>{current=false;};
  },[key,url]);
  const total=source?.accounts_total??source?.accounts?.length??0;
  const value=response.key===key?response.value:null;
  return {page,pages:Math.max(1,Math.ceil(total/20)),total,
    accounts:url?(value?.accounts||[]):(source?.accounts||[]).slice((page-1)*20,page*20),
    pending:!!url&&response.key!==key,error:response.key===key?response.error:undefined,
    move:(next:number)=>setSelection({owner,page:next}),retry:()=>setAttempt(v=>v+1)};
}

export function SavedJobHistory({open}:{open:(id:string)=>void}){
  const [offset,setOffset]=useState(0),[attempt,setAttempt]=useState(0);
  const key=offset+'|'+attempt;
  const [response,setResponse]=useState<{key:string,rows?:any[],error?:string}>({key:''});
  useEffect(()=>{
    let current=true;
    api('/jobs?limit=50&offset='+offset).then(rows=>{if(current)setResponse({key,rows});})
      .catch(error=>{if(current)setResponse({key,error:error.message});});
    return()=>{current=false;};
  },[key,offset]);
  const owned=response.key===key,rows=owned?response.rows||[]:[],pending=!owned;
  return <section className="panel" aria-label="Saved job history"><h2>Saved job history</h2>
    <p className="muted">Browse older jobs independently of the current report and its export links.</p>
    {pending&&<p role="status">Loading saved job history…</p>}
    {owned&&response.error&&<p role="alert">{response.error}</p>}
    <nav className="actions" aria-label="Saved job history pages">
      <button disabled={offset===0} onClick={()=>setOffset(0)}>Newest job history</button>
      <button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-50))}>Newer job history</button>
      <span aria-live="polite">{rows.length?'Records '+(offset+1)+' to '+(offset+rows.length):pending?'Loading':'No records on this page'}</span>
      <button disabled={pending||!!response.error||rows.length<50} onClick={()=>setOffset(offset+50)}>Older job history</button>
      <button onClick={()=>setAttempt(v=>v+1)}>Refresh job history</button>
    </nav>
    <div className="table-wrap"><table><thead><tr><th>Job</th><th>Type</th><th>State</th><th>Action</th></tr></thead><tbody>{rows.map(job=><tr key={job.id}><td><code>{job.id}</code><small className="block">{job.payload?.name||''}</small></td><td>{job.kind.replaceAll('_',' ')}</td><td>{job.status}</td><td>{job.status==='completed'&&!['download','news_download'].includes(job.kind)&&<button onClick={()=>open(job.id)}>Open historical results</button>}</td></tr>)}</tbody></table></div>
  </section>;
}
