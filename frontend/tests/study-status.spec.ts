import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

test('complete thousand-rule study download and test-owned protection-cache repair',async({page},info)=>{
 test.setTimeout(240000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const symbol='ST'+(info.project.name==='desktop1920'?'A':'B')+Date.now().toString(36).slice(-6).toUpperCase();
 const days=['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06'];let csv='symbol,timestamp,open,high,low,close,volume\n';
 for(const day of days)for(let n=0;n<390;n++){const at=new Date(day+'T14:30:00Z');at.setUTCMinutes(at.getUTCMinutes()+n);const p=100+Math.sin(n/20);csv+=[symbol,at.toISOString(),p,p+.1,p-.1,p,10000].join(',')+'\n';}
 await page.goto('/');await page.getByLabel('Price file',{exact:true}).setInputFiles({name:'synthetic-study-'+symbol+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await page.getByLabel('Start',{exact:true}).fill(days[0]);await page.getByLabel('End',{exact:true}).fill(days.at(-1)!);await page.getByRole('combobox',{name:'Input type',exact:true}).selectOption('synthetic');
 const importing=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Import & audit',exact:true}).click();const imported=await importing;expect(imported.status()).toBe(201);const manifest=await imported.json();expect(manifest.quality.eligible).toBe(true);
 const session=await(await page.request.get('/api/session')).json(),origin=new URL(page.url()).origin,headers={Origin:origin,'X-Lab-Token':session.token};
 const schema=await(await page.request.get('/api/schema')).json();const defaults=(spec:any)=>Object.fromEntries(Object.entries(spec.properties).filter(([,v]:any)=>'default'in v).map(([k,v]:any)=>[k,v.default]));
 const configurations=Array.from({length:1000},(_,i)=>({...defaults(schema.strategy),family:'trend_pullback',timeframe:'1m',pullback_min:(i+1)/1000}));
 const created=await page.request.post('/api/studies',{headers,data:{name:'Metadata-only study download '+symbol,dataset_id:manifest.id,configurations,costs:defaults(schema.costs),portfolio:defaults(schema.portfolio),discovery:{start:days[0],end:days[1]},validation:{start:days[2],end:days[2]},holdout:{start:days[3],end:days[4]},seed:42,minimum_trades:1,minimum_sharpe:0}});
 expect(created.status()).toBe(201);expect((await created.body()).length).toBeLessThanOrEqual(65536);const projected=await created.json(),sid=projected.id;
 const state=async()=>await(await page.request.get('/api/studies/'+sid)).json();
 try{
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();
  const row=()=>page.locator('tbody tr').filter({has:page.getByText(sid.slice(0,12),{exact:true})});await expect(row()).toContainText('1000 frozen rules');
  const downloading=page.waitForEvent('download');await row().getByRole('link',{name:'Frozen study inputs',exact:true}).click();const download=await downloading;expect(download.suggestedFilename()).toBe(sid+'-stored-study-inputs.json');const path=await download.path();expect(path).toBeTruthy();
  const raw=await readFile(path!,'utf8'),full=JSON.parse(raw);expect(full.study.id).toBe(sid);expect(full.spec_hash).toBe(projected.spec_hash);expect(full.study.spec.configurations).toHaveLength(1000);
  expect(full.study.spec.configurations.map((c:any)=>c.pullback_min)).toEqual(configurations.map(c=>c.pullback_min));expect(full.study.spec.dataset_context.symbols).toEqual([symbol]);
  await writeFile(info.outputPath('complete-original-study-inputs.json'),raw);await row().scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('thousand-rule-study-input-download.png')});
  execFileSync(resolve('../.venv/Scripts/python.exe'),['-c',"import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); db.execute(\"UPDATE study_input_index SET projection='{}' WHERE study_id=?\",(sys.argv[2],)); db.commit(); db.close()",resolve('../data/lab.sqlite3'),sid]);
  await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();await expect(row().getByRole('button',{name:'Screen candidates',exact:true})).toBeDisabled();await expect(row()).toContainText('Unverified protected scope');await expect(row()).toContainText('Stored study summary/protection is unverified');
  const preview=(start:string)=>'/api/datasets/'+manifest.id+'/preview?'+new URLSearchParams({symbol,start,end:start});expect((await page.request.get(preview(days[0]))).status()).toBe(409);
  await row().scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('visible-study-corruption-and-disabled-control.png')});
  const repairing=page.waitForResponse(r=>r.url().endsWith('/api/studies/'+sid+'/repair-index')&&r.request().method()==='POST');await row().getByRole('button',{name:'Repair study summary',exact:true}).click();expect((await repairing).status()).toBe(200);
  await expect(row().getByRole('button',{name:'Repair study summary',exact:true})).toHaveCount(0);await expect(row().getByRole('button',{name:'Screen candidates',exact:true})).toBeEnabled();expect((await state()).index_integrity).toBe(true);
  const after=await(await page.request.get('/api/studies/'+sid+'/inputs')).json();expect(after).toEqual(full);expect((await page.request.get(preview(days[0]))).status()).toBe(200);expect((await page.request.get(preview(days[4]))).status()).toBe(409);
  const jobs=await(await page.request.get('/api/jobs')).json();expect(jobs.filter((j:any)=>j.payload.study_id===sid)).toHaveLength(0);expect(errors).toEqual([]);
  await row().scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('repaired-study-original-inputs-and-final-protection.png')});
  await writeFile(info.outputPath('study-status-observations.json'),JSON.stringify({study_id:sid,dataset_id:manifest.id,symbol,configurations:1000,spec_hash:full.spec_hash,viewport:page.viewportSize(),errors,price_accounts_executed:0,scope:'Actual synthetic import/registration, complete original-byte download, test-owned cache corruption/repair and discovery/final HTTP guards. No numerical account or untouched-market evidence.'},null,2));
 }finally{if(!(await state()).index_integrity)await page.request.post('/api/studies/'+sid+'/repair-index',{headers});}
});

test('study history owns delayed success and failure and serializes long periodic refresh',async({page},info)=>{
 test.setTimeout(180000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const actual=await(await page.request.get('/api/studies')).json();expect(actual.length).toBeGreaterThan(0);const template=actual[0];
 const first=Array.from({length:500},(_,i)=>({...template,id:'controlled-first-'+i,name:'Controlled first history '+i}));const second=Array.from({length:5},(_,i)=>({...template,id:'controlled-older-'+i,name:'Controlled older history '+i}));
 let holdNext=false,held=false,release!:()=>void,gate=Promise.resolve(),fault='success',requests=0,failCurrent=false;
 await page.route('**/api/studies*',async route=>{
  const u=new URL(route.request().url());if(u.pathname!=='/api/studies'||route.request().method()!=='GET'){await route.continue();return;}
  requests++;const offset=Number(u.searchParams.get('offset')||0);if(offset===500&&failCurrent){await route.abort('failed');return;}
  if(offset===0&&holdNext){holdNext=false;held=true;await gate;if(fault==='failure'){await route.abort('failed');return;}}
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(offset===0?first:second)});
 });
 try{
  await page.goto('/');await page.getByRole('button',{name:'06 Validation',exact:true}).click();const nav=page.getByRole('navigation',{name:'Study history pages',exact:true});const registry=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Study registry',exact:true})});await expect(nav).toContainText('Records 1 to 500');const observations=[];
  for(const mode of ['success','failure']){
   fault=mode;held=false;gate=new Promise<void>(resolve=>{release=resolve;});holdNext=true;await expect.poll(()=>held,{timeout:10000}).toBe(true);
   await nav.getByRole('button',{name:'Older study history',exact:true}).click();await expect(nav).toContainText('Records 501 to 505');release();await page.waitForTimeout(800);
   await expect(nav).toContainText('Records 501 to 505');await expect(page.getByRole('alert')).toHaveCount(0);await expect(registry.getByRole('row').filter({hasText:'Controlled older history 0'})).toHaveCount(1);await expect(registry.getByRole('row').filter({hasText:'Controlled older history 0'})).toBeVisible();await expect(registry.getByRole('row')).toHaveCount(6);await expect(registry.getByRole('row').filter({hasText:'Controlled first history 0'})).toHaveCount(0);
   await nav.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('study-page-owned-'+mode+'.png')});observations.push({stale:mode,shown_records:'501 to 505',stale_error_visible:false});
   await nav.getByRole('button',{name:mode==='success'?'Newer study history':'Newest study history',exact:true}).click();await expect(nav).toContainText('Records 1 to 500');
  }
  held=false;fault='success';gate=new Promise<void>(resolve=>{release=resolve;});holdNext=true;await expect.poll(()=>held,{timeout:10000}).toBe(true);const atHold=requests;await page.waitForTimeout(5500);const additionalWhileHeld=requests-atHold;expect(additionalWhileHeld).toBe(0);const finishing=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/studies');release();await finishing;await expect(nav).toContainText('Records 1 to 500');failCurrent=true;await nav.getByRole('button',{name:'Older study history',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(nav).toContainText('Records 1 to 500');await expect(registry.getByRole('row')).toHaveCount(501);await nav.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('current-study-history-error-preserved-page.png')});failCurrent=false;await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();await expect(nav).toContainText('Records 501 to 505');await expect(page.getByRole('alert')).toHaveCount(0);expect(errors).toEqual([]);
  await writeFile(info.outputPath('study-history-transport-observations.json'),JSON.stringify({viewport:page.viewportSize(),observations,long_refresh_additional_requests:additionalWhileHeld,current_failure_preserved_last_verified_page:true,current_failure_recovered:true,errors,scope:'Controlled metadata-only transport records exercise pagination/ownership/periodic serialization; names/IDs are not actual registrations or financial evidence.'},null,2));
 }finally{release?.();await page.unroute('**/api/studies*');}
});
