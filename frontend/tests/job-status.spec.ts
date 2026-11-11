import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';

test('full saved inputs download and real cancel resume cache repair controls',async({page},info)=>{
 test.setTimeout(240000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const origin=new URL(page.url()==='about:blank'?(process.env.PA_BROWSER_BASE_URL||'http://127.0.0.1:8765'):page.url()).origin;
 await page.goto('/');await expect(page.getByRole('heading',{name:'Data',exact:true})).toBeVisible();
 const session=await(await page.request.get('/api/session')).json();const headers={Origin:origin,'X-Lab-Token':session.token};
 const schema=await(await page.request.get('/api/schema')).json();
 const defaults=(spec:any)=>Object.fromEntries(Object.entries(spec.properties).filter(([,v]:any)=>'default'in v).map(([k,v]:any)=>[k,v.default]));
 const created=await page.request.post('/api/searches',{headers,data:{name:'Monitoring control '+info.project.name,dataset_id:'90f347229b2fb03ec112ee71',strategy:defaults(schema.strategy),costs:defaults(schema.costs),portfolio:defaults(schema.portfolio),start:'2022-01-03',end:'2022-01-31',seed:42,count:1000,families:['break_of_structure'],timeframes:['1m'],sampling_policy:{mode:'common_random'},statistics:{effective_trials:[1]}}});
 expect(created.status()).toBe(202);const job=await created.json();const jid=job.id;
 const state=async()=>await(await page.request.get('/api/jobs/'+jid)).json();
 const cancel=async()=>{const r=await page.request.post('/api/jobs/'+jid+'/cancel',{headers});expect(r.status()).toBe(200);await expect.poll(async()=>(await state()).status,{timeout:120000}).toBe('canceled');};
 try{
  await cancel();await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();
  const row=page.locator('tbody tr').filter({has:page.getByText(jid.slice(0,10),{exact:true})});
  await expect(row.getByRole('button',{name:'Resume',exact:true})).toBeVisible();
  const downloading=page.waitForEvent('download');await row.getByRole('link',{name:'Stored inputs',exact:true}).click();const download=await downloading;
  expect(download.suggestedFilename()).toBe(jid+'-stored-inputs.json');const file=await download.path();expect(file).toBeTruthy();
  const full=JSON.parse(await readFile(file!,'utf8'));expect(full.job_id).toBe(jid);expect(full.payload_sha256).toBe(job.payload_sha256);
  expect(full.payload.configurations).toHaveLength(1000);expect(full.payload.sampling.proposals.length).toBeGreaterThanOrEqual(1000);
  expect(full.payload.dataset_context).toEqual(job.payload.dataset_context);expect(full.payload.costs).toEqual(job.payload.costs);
  await writeFile(info.outputPath('downloaded-stored-inputs.json'),JSON.stringify(full,null,2));
  await page.screenshot({path:info.outputPath('stored-inputs-and-resume.png'),fullPage:true});
  const resuming=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+jid+'/resume')&&r.request().method()==='POST');await row.getByRole('button',{name:'Resume',exact:true}).click();expect((await resuming).status()).toBe(200);
  await expect(row.getByRole('button',{name:'Cancel',exact:true})).toBeVisible();const canceling=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+jid+'/cancel')&&r.request().method()==='POST');await row.getByRole('button',{name:'Cancel',exact:true}).click();expect((await canceling).status()).toBe(200);
  await expect.poll(async()=>(await state()).status,{timeout:120000}).toBe('canceled');
  // Deliberately damage only this test-owned derived cache; original inputs/trials/results are untouched.
  execFileSync(resolve('../.venv/Scripts/python.exe'),['-c',"import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); db.execute(\"UPDATE job_input_index SET projection='{}' WHERE job_id=?\",(sys.argv[2],)); db.commit(); db.close()",resolve('../data/lab.sqlite3'),jid]);
  await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();await expect(row.getByText(/Stored input summary is unverified/)).toBeVisible();
  await page.screenshot({path:info.outputPath('visible-derived-cache-failure.png'),fullPage:true});
  const repairing=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+jid+'/repair-index')&&r.request().method()==='POST');await row.getByRole('button',{name:'Repair stored summary',exact:true}).click();expect((await repairing).status()).toBe(200);
  await expect(row.getByRole('button',{name:'Repair stored summary',exact:true})).toHaveCount(0);expect((await state()).index_integrity).toBe(true);
  const after=await(await page.request.get('/api/jobs/'+jid+'/inputs')).json();expect(after.payload).toEqual(full.payload);expect(after.payload_sha256).toBe(full.payload_sha256);
  const registry=await(await page.request.get('/api/trial-registry?job_id='+jid)).json();expect(registry.totals.planned_occurrences).toBe(1000);
  await page.screenshot({path:info.outputPath('repaired-summary-original-inputs-retained.png'),fullPage:true});
  expect(errors).toEqual([]);await writeFile(info.outputPath('job-status-observations.json'),JSON.stringify({job_id:jid,payload_sha256:full.payload_sha256,configurations:1000,proposals:full.payload.sampling.proposals.length,status_bytes:(await(await page.request.get('/api/jobs/'+jid)).body()).length,planned_occurrences:registry.totals.planned_occurrences,computation_attempts:registry.totals.computation_attempts,viewport:page.viewportSize(),errors,scope:'Actual download, cancel/resume and test-owned derived cache corruption/repair; no profitability claim.'},null,2));
 }finally{
  const latest=await state();if(['queued','running','canceling'].includes(latest.status))await cancel();
  if(!(await state()).index_integrity)await page.request.post('/api/jobs/'+jid+'/repair-index',{headers});
 }
});
