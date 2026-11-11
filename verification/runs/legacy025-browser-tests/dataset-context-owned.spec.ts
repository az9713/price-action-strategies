import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('owned synthetic aggregate context survives an unrelated synthetic dataset selection',async({page,context},info)=>{
 test.setTimeout(300000);const fixture=JSON.parse(await readFile('../verification/fixtures/dataset-context-browser-contract.json','utf8'));
 fixture.unrelated_historical_dataset=process.env.PA_SPREAD_DATASET!;fixture.required='Owned generated synthetic context remains frozen while selecting another synthetic dataset. Genuine historical selection and original legacy evidence are checked separately in place.';
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await expect.poll(async()=>{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;},{timeout:60000}).toBe(true);
 const symbol=fixture.symbols[info.project.name];let csv='symbol,timestamp,open,high,low,close,volume\n';
 for(const [dayIndex,day] of fixture.sessions.entries())for(let minute=0;minute<390;minute++){
  const at=new Date(day+'T13:30:00Z');at.setUTCMinutes(at.getUTCMinutes()+minute);const close=1000+10*dayIndex-.1*minute+8*Math.sin(2*Math.PI*minute/64);
  csv+=[symbol,at.toISOString(),close+.02,close+.2,close-.1,close,10000].join(',')+'\n';
 }
 await page.goto('/');await page.getByLabel('Price file',{exact:true}).setInputFiles({name:'synthetic-context-'+symbol+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await page.getByLabel('Start',{exact:true}).fill(fixture.sessions[0]);await page.getByLabel('End',{exact:true}).fill(fixture.sessions.at(-1));
 await page.getByRole('combobox',{name:'Input type',exact:true}).selectOption('synthetic');
 const importing=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Import & audit',exact:true}).click();
 const importedResponse=await importing;expect(importedResponse.status()).toBe(201);const manifest=await importedResponse.json();expect(manifest.quality.eligible).toBe(true);
 await writeFile(info.outputPath('imported-manifest.json'),JSON.stringify(manifest,null,2));
 await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(manifest.id);
 await page.getByLabel('Experiment name',{exact:true}).fill('Dataset context synthetic control '+info.project.name);
 const panel=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Reproducible parameter search',exact:true})});
 await panel.getByLabel('Change of character',{exact:true}).uncheck();await panel.getByLabel('Break of structure',{exact:true}).check();
 await panel.getByLabel('1h',{exact:true}).uncheck();await panel.getByLabel('1m',{exact:true}).check();await panel.getByLabel('Sampling method',{exact:true}).selectOption('common_random');
 await panel.getByRole('spinbutton',{name:/^Unique configurations\b/}).fill('1');
 await panel.getByText('Search-bias assumptions',{exact:true}).click();await panel.getByLabel('Assumed independent trial counts',{exact:true}).fill('1');
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/searches')&&r.request().method()==='POST');await panel.getByRole('button',{name:'Queue parameter search',exact:true}).click();
 const createdResponse=await pending;expect(createdResponse.status()).toBe(202);const created=await createdResponse.json(),jid=created.id;
 await expect.poll(async()=>{const j=await(await page.request.get('/api/jobs/'+jid)).json();return j.status;},{timeout:120000}).toBe('completed');
 const saved=await(await page.request.get('/api/jobs/'+jid+'/result')).json();expect(saved.dataset_context).toEqual(created.payload.dataset_context);
 expect(saved.dataset_context).toMatchObject({policy_version:1,dataset_id:manifest.id,input_kind:'synthetic',source:'User import',symbols:[symbol]});
 const jobRow=(id:string)=>page.locator('tbody tr').filter({has:page.getByText(id.slice(0,10),{exact:true})});await jobRow(jid).getByRole('button',{name:'Open results',exact:true}).click();
 const provenance=page.getByRole('region',{name:'Saved dataset context',exact:true});await expect(provenance).toContainText('Synthetic input');await expect(provenance).toContainText(symbol);
 await provenance.getByText('Saved dataset fingerprints',{exact:true}).click();await expect(provenance).toContainText(saved.dataset_context.dataset_manifest_hash);
 await page.screenshot({path:info.outputPath('new-synthetic-context.png'),fullPage:true});
 await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(fixture.unrelated_historical_dataset);
 await page.getByRole('button',{name:'04 Results',exact:true}).click();await expect(provenance).toContainText('Synthetic input');await expect(provenance).toContainText(symbol);await expect(provenance).not.toContainText('SPY');
 await page.screenshot({path:info.outputPath('saved-context-after-unrelated-dataset-selection.png'),fullPage:true});
 const statistics=page.getByRole('region',{name:'Search-bias sensitivity',exact:true});
 const download=async(region:any,label:string,file:string)=>{const event=page.waitForEvent('download');await region.getByRole('link',{name:label,exact:true}).click();await(await event).saveAs(info.outputPath(file));};
 await download(statistics,'Download saved search summary JSON','saved-summary.json');await download(statistics,'Download search presentation','new-presentation.html');
 await download(page.getByRole('region',{name:'Initial discovery funnel',exact:true}),'Download all initial discovery CSV','saved-screen.csv');
 for(const [path,file] of [['/report?part=0','saved-account.json'],['/export/csv?part=0','saved-account.csv']]){const response=await page.request.get('/api/jobs/'+jid+path);expect(response.status()).toBe(200);await writeFile(info.outputPath(file),await response.body());}
 const app=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await app.close();await context.setOffline(true);
 const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});const layouts:any[]=[];const decks:any[]=[];
 for(const prefix of ['new']){
  await page.goto(pathToFileURL(info.outputPath(prefix+'-presentation.html')).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  if(prefix==='new')expect(Object.values(deck.facts).filter((f:any)=>f.path[0]==='dataset_context').length).toBe(7);
  else expect(deck.pages.some((p:any)=>p.title==='Dataset context not recorded')).toBe(true);
  for(let n=0;n<deck.pages.length;n++){
   if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
   const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,out:string[]=[];
    for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)out.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)out.push('camera overlap');}if(document.documentElement.scrollWidth>innerWidth)out.push('horizontal scroll');return out;});
   expect.soft(issues).toEqual([]);layouts.push({prefix,page:n+1,issues});await page.screenshot({path:info.outputPath(prefix+'-page-'+(n+1)+'.png')});
  }
  decks.push({prefix,pages:deck.pages.length,facts:Object.keys(deck.facts).length});
 }
 expect(errors).toEqual([]);expect(network).toEqual([]);
 await writeFile(info.outputPath('dataset-context-observations.json'),JSON.stringify({job_id:jid,dataset_id:manifest.id,core_hash:saved.core_hash,expected_context:saved.dataset_context,unrelated_selection:fixture.unrelated_historical_dataset,decks,layouts,network,errors,viewport:page.viewportSize(),scope:fixture.required},null,2));
});
