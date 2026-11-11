import {useState} from 'react';
import {post} from './api';

type Source={job_id:string;part:number|null;window:string};
export function PresenterExport({jobs,current}:{jobs:any[];current:Source|null}){
  const [sources,setSources]=useState<Source[]>([]),[choice,setChoice]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  function add(source:Source){setError('');setMessage('');if(sources.some(s=>s.job_id===source.job_id&&s.part===source.part&&s.window===source.window))return;
    if(sources.length>=16){setError('Choose at most sixteen saved sources.');return;}setSources([...sources,source]);}
  async function download(){setBusy(true);setError('');setMessage('');try{
    const result=await post('/presentations',{sources});
    const blob=new Blob([result.html],{type:'text/html'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='saved-research-presentation.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    setMessage(`Exported ${result.manifest.pages.length} pages; ${result.manifest.audit.facts_checked} source values independently reread. Open the HTML offline. Save provenance inside the presenter for the complete manifest.`);
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <section className="panel" aria-labelledby="presenter-heading"><div className="panel-head"><h2 id="presenter-heading">Offline research presenter</h2></div>
    <p className="muted">Combine completed saved outputs into one self-contained presentation. Daily accounts, comparisons, behavior tables and search summaries retain their own sources and dates. Exporting does not read market prices or reopen final dates.</p>
    <div className="fields"><label className="field"><span>Saved presentation source</span><select aria-label="Saved presentation source" value={choice} onChange={e=>setChoice(e.target.value)}><option value="">Choose a completed study</option>{jobs.filter(j=>j.status==='completed'&&!['download','news_download'].includes(j.kind)).map(j=><option key={j.id} value={j.id}>{j.kind.replaceAll('_',' ')} · {j.payload.name||j.id.slice(0,10)}</option>)}</select></label>
    <button disabled={!choice||busy} onClick={()=>add({job_id:choice,part:null,window:'report'})}>Add complete saved study</button>
    <button disabled={!current||busy} onClick={()=>current&&add(current)}>Add current saved account</button></div>
    <ul>{sources.map((s,i)=><li key={s.job_id+':'+s.part+':'+s.window}><code>{s.job_id.slice(0,12)}</code> · {s.part===null?'Complete saved study':`Account part ${s.part} · ${s.window}`} <button disabled={busy} aria-label={'Remove presentation source '+(i+1)} onClick={()=>setSources(sources.filter((_,n)=>n!==i))}>Remove</button></li>)}</ul>
    {!sources.length&&<p className="empty">Add a saved study or the current account. No sample findings are inserted.</p>}
    <button className="primary" disabled={!sources.length||busy} onClick={download}>{busy?'Checking saved values…':'Download offline presentation'}</button>
    <p className="caption">Arrow keys and Space navigate; M opens sections, R replays and F shows the reserved camera area. Every included value has saved-source provenance. No webcam is opened. Combined sources are not automatically comparable or independent.</p>
    {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  </section>;
}
