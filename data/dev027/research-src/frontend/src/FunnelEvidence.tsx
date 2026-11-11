import {useEffect,useState} from 'react';
import {api} from './api';
const tables:Record<string,string>={versions:'Every frozen version',accounts:'Every instrument account',gates:'Qualification gates and control counts',family_summary:'Complete family means',family_daily:'Exact family daily means',family_members:'Every original family member',stability:'Descriptive frozen-neighbor stability',attrition:'Qualification attrition and missingness',original_accounts:'Original account files and hashes',metadata:'Source and frozen assumptions'};
const label=(s:string)=>s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
function cell(key:string,value:any){
  if(value===null||value===undefined)return 'Unavailable';
  if(typeof value==='boolean')return value?'Yes':'No';
  if(key.endsWith('_json')){
    let parsed=value;try{parsed=JSON.parse(value);}catch{/* Original scalar text remains visible. */}
    return <details><summary>View complete {label(key.slice(0,-5)).toLowerCase()}</summary><pre>{JSON.stringify(parsed,null,2)}</pre></details>;
  }
  return String(value);
}
export function FunnelEvidence({jobId}:{jobId:string}){
  const [table,setTable]=useState(''),[offset,setOffset]=useState(0),[page,setPage]=useState<any>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
  useEffect(()=>{let active=true;const controller=new AbortController();setPage(null);setError('');if(table)void api('/jobs/'+jobId+'/funnel-evidence/'+table+'?limit=50&offset='+offset,{signal:controller.signal}).then(v=>{if(active)setPage(v);}).catch(e=>{if(active){setPage(null);setError(e.message);}});return()=>{active=false;controller.abort();};},[jobId,table,offset,retry]);
  const current=page?.job_id===jobId&&page?.table===table?page:null;
  return <section aria-label="Complete cohort export tables"><h3>Complete cohort evidence and offline exports</h3><p>Inspect every frozen version, including losses, zero-trade accounts and unavailable values. Candidate and family selection remain fixed before final results. A numerator and denominator together preserve an exact fraction; unavailable values are not replaced by zero.</p>
    <label className="field"><span>Saved evidence table</span><select value={table} onChange={e=>{setTable(e.target.value);setOffset(0);}}><option value="">Choose an evidence table</option>{Object.entries(tables).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label>
    <button type="button" disabled={!table} onClick={()=>{setPage(null);setRetry(n=>n+1);}}>Reload complete evidence table</button>
    {!table&&<p>Select a table to inspect its complete original records and download the evidence.</p>}{error&&<p role="alert">{error}</p>}{table&&!current&&!error&&<p role="status">Verifying complete original evidence...</p>}
    {current&&<><p>Records {current.rows.length?offset+1:0} to {offset+current.rows.length} of {current.pagination.total}. {current.available?'Complete original table.':'This table belongs to qualification; open the saved qualification result to inspect it.'}</p>
      <div className="actions"><a download href={'/api/jobs/'+jobId+'/funnel-export/csv?table='+table}>Download complete table CSV</a><a download href={'/api/jobs/'+jobId+'/funnel-export/zip'}>Download complete cohort ZIP</a><a download href={'/api/jobs/'+jobId+'/funnel-export/html'}>Download standalone offline report</a></div>
      <p>The ZIP includes all tables, full original inputs/results and every original account file for this phase. The standalone HTML contains all cohort summary records and family daily means, with paging and search; complete per-version daily arrays and trade evidence remain in the ZIP originals. Exporting runs no new financial accounts or qualification calculations.</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Complete original cohort evidence table"><table><thead><tr>{current.columns.map((key:string)=><th key={key}>{label(key)}</th>)}</tr></thead><tbody>{current.rows.map((row:any,index:number)=><tr key={offset+index}>{current.columns.map((key:string)=><td key={key}>{cell(key,row[key])}</td>)}</tr>)}</tbody></table></div>
      <div className="actions"><button type="button" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-50))}>Previous evidence records</button><button type="button" disabled={offset+current.rows.length>=current.pagination.total} onClick={()=>setOffset(offset+50)}>Next evidence records</button></div>
    </>}
  </section>;
}
