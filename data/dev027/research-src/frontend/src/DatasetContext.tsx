import {useEffect,useState} from 'react';
type Context={policy_version:number;dataset_id:string;dataset_manifest_hash:string;input_kind:string;source:string;symbols:string[]};

export function inputLabel(kind:unknown){
  if(kind==='synthetic')return 'Synthetic input';
  if(kind==='historical'||kind==='historical_market_data')return 'Historical input';
  if(kind==='user_import')return 'Unverified import';
  return 'Input classification unknown';
}

export function DatasetContext({value}:{value:Context|undefined}){
  const [offset,setOffset]=useState(0);
  useEffect(()=>setOffset(0),[value?.dataset_id]);
  if(!value)return <section className="dataset-context" aria-label="Saved dataset context"><h3>Dataset context not recorded</h3><p>This version did not save the complete dataset context. Inspect its original account evidence.</p></section>;
  const start=Math.min(offset,Math.floor((value.symbols.length-1)/20)*20),end=Math.min(start+20,value.symbols.length);
  return <section className="dataset-context" aria-label="Saved dataset context">
    <h3>{inputLabel(value.input_kind)}</h3>
    <dl><dt>Instruments</dt><dd>{value.symbols.slice(start,end).join(', ')}{value.symbols.length>20&&<div><p>Showing {start+1}–{end} of {value.symbols.length} instruments</p><button type="button" disabled={start===0} onClick={()=>setOffset(start-20)}>Previous instruments</button> <button type="button" disabled={end===value.symbols.length} onClick={()=>setOffset(start+20)}>Next instruments</button></div>}</dd><dt>Data source</dt><dd>{value.source}</dd><dt>Declared input kind</dt><dd>{value.input_kind}</dd></dl>
    <details><summary>Saved dataset fingerprints</summary><dl><dt>Dataset</dt><dd><code>{value.dataset_id}</code></dd><dt>Manifest</dt><dd><code>{value.dataset_manifest_hash}</code></dd></dl></details>
  </section>;
}
