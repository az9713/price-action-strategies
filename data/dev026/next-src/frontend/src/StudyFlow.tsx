export function StudyUnit({mode,onMode,rules,selected,onSelected,config,families,disabled}:{
  mode:string,onMode:(v:string)=>void,rules:any[],selected:string[],onSelected:(v:string[])=>void,config:any,families:any,disabled:boolean
}){
  const chosen=rules.filter(r=>selected.includes(r.id));
  return <div aria-label="Study selection unit">
    <label className="field"><span>Study selection unit</span><select value={mode} disabled={disabled} onChange={e=>onMode(e.target.value)}><option value="independent">Independent rule accounts</option><option value="portfolio">One frozen shared-capital portfolio</option></select></label>
    {mode==='independent'?<p>Current candidate rule: <b>{families[config.family]} · {config.timeframe}</b>. Each candidate has a separately funded account.</p>:<>
      <p>Choose one fixed set of saved rules. Discovery, validation and the final test each execute this whole set in one shared account. The set passes or fails as a whole; members are never selected separately and recombined.</p>
      {rules.length?<div className="checks">{rules.map(r=>{const checked=selected.includes(r.id),duplicate=chosen.some(c=>c.id!==r.id&&JSON.stringify(c.config)===JSON.stringify(r.config));return <label className="check" key={r.id}><input type="checkbox" aria-label={'Freeze portfolio member '+r.name+' '+r.id.slice(0,8)} checked={checked} disabled={disabled||duplicate||(!checked&&chosen.length>=64)} onChange={()=>onSelected(checked?selected.filter(id=>id!==r.id):[...selected,r.id])}/><span>{r.name} · {families[r.config.family]} · {r.config.timeframe}<small className="block">Version {r.id.slice(0,8)}{duplicate?' · Identical rules already selected':''}</small></span></label>;})}</div>:<p>Save immutable rule sets on Strategies, then select members here.</p>}
      <p>{chosen.length} unique portfolio member(s) selected; maximum 64. The capital, execution costs and borrowing assumptions selected on Experiments apply to the whole account.</p>
      <details><summary>Portfolio members to freeze</summary><pre className="saved-configs">{JSON.stringify(chosen.map(r=>({name:r.name,saved_version_id:r.id,config:r.config})),null,2)}</pre></details>
    </>}
    <p>Positive net profit, the minimum trade count and a defined minimum marked Sharpe are required in both screening windows. These gates do not certify a trading edge.</p>
  </div>;
}

export function StudyContext({value}:{value:any}){
  return value?<section className="panel" aria-label="Frozen study account"><h2>Frozen study account</h2>
    <p><b>{value.study_mode==='portfolio'?'One shared-capital portfolio':'Independent rule account'}</b> · {value.phase==='final'?'Final dates consumed':value.phase+' screening window'}</p>
    <p>Study <code>{value.study_id}</code>. This saved account belongs to the original frozen selection unit. Inspection and export use saved outputs.</p>
    <details><summary>Frozen study account fingerprints</summary><pre className="saved-configs">{JSON.stringify(value,null,2)}</pre></details>
  </section>:null;
}
