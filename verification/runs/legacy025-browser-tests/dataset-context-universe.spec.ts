import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('a preexisting larger import keeps every instrument through pagination and saved-only reports',async({page,context},info)=>{
 test.setTimeout(300000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;}catch{return false;}},{timeout:60000}).toBe(true);
 const prefix=info.project.name==='desktop1920'?'UPA':'UPB',symbols=Array.from({length:21},(_,i)=>prefix+String(i).padStart(2,'0'));
 let csv='symbol,timestamp,open,high,low,close,volume\n';
 for(const [index,symbol] of symbols.entries())for(let minute=0;minute<390;minute++){
  const at=new Date('2026-10-05T13:30:00Z');at.setUTCMinutes(at.getUTCMinutes()+minute);const close=1000+index*5+.05*minute+Math.sin(minute/8);
  csv+=[symbol,at.toISOString(),close,close+.1,close-.1,close,10000].join(',')+'\n';
 }
 await page.goto('/');await page.getByLabel('Price file',{exact:true}).setInputFiles({name:'synthetic-large-context-'+prefix+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await page.getByLabel('Start',{exact:true}).fill('2026-10-05');await page.getByLabel('End',{exact:true}).fill('2026-10-05');await page.getByRole('combobox',{name:'Input type',exact:true}).selectOption('synthetic');
 const importing=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Import & audit',exact:true}).click();const imported=await importing;expect(imported.status()).toBe(201);const manifest=await imported.json();expect(manifest.quality.eligible).toBe(true);expect(manifest.quality.symbols).toEqual(symbols);
 await writeFile(info.outputPath('universe-manifest.json'),JSON.stringify(manifest,null,2));
 await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(manifest.id);await page.getByLabel('Experiment name',{exact:true}).fill('Synthetic larger-universe provenance '+info.project.name);
 const queuing=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');await page.getByRole('button',{name:'Run single configuration',exact:true}).click();const createdResponse=await queuing;expect(createdResponse.status()).toBe(202);const created=await createdResponse.json(),jid=created.id;expect(created.payload.dataset_context.symbols).toEqual(symbols);
 await expect.poll(async()=>{const j=await(await page.request.get('/api/jobs/'+jid)).json();return j.status;},{timeout:120000}).toBe('completed');
 await page.locator('tbody tr').filter({has:page.getByText(jid.slice(0,10),{exact:true})}).getByRole('button',{name:'Open results',exact:true}).click();
 const region=page.getByRole('region',{name:'Saved dataset context',exact:true});await expect(region).toContainText('Showing 1–20 of 21 instruments');await expect(region).toContainText(symbols[0]);await expect(region).not.toContainText(symbols[20]);
 await region.getByRole('button',{name:'Next instruments',exact:true}).click();await expect(region).toContainText('Showing 21–21 of 21 instruments');await expect(region).toContainText(symbols[20]);await expect(region).not.toContainText(symbols[0]);await expect(region.getByRole('button',{name:'Next instruments',exact:true})).toBeDisabled();await page.screenshot({path:info.outputPath('universe-last-page.png'),fullPage:true});
 await region.getByRole('button',{name:'Previous instruments',exact:true}).click();await expect(region).toContainText(symbols[0]);await expect(region.getByRole('button',{name:'Previous instruments',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'07 Reports',exact:true}).click();await expect(region).toContainText('Synthetic input');await expect(region).toContainText('Showing 1–20 of 21 instruments');await region.getByRole('button',{name:'Next instruments',exact:true}).click();await expect(region).toContainText(symbols[20]);await page.screenshot({path:info.outputPath('universe-saved-report.png'),fullPage:true});
 for(const [label,file] of [['Download full JSON evidence','universe-report.json'],['Download current presentation','universe-presentation.html']]){const download=page.waitForEvent('download');await page.getByRole('link',{name:label,exact:true}).click();await(await download).saveAs(info.outputPath(file));}
 const source=await(await page.request.get('/api/jobs/'+jid+'/report')).json();expect(source.dataset_context.symbols).toEqual(symbols);expect(source.dataset_context.input_kind).toBe('synthetic');
 const app=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await app.close();await context.setOffline(true);const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
 await page.goto(pathToFileURL(info.outputPath('universe-presentation.html')).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);const contextFacts=Object.values(deck.facts).filter((f:any)=>f.path[0]==='dataset_context');expect(contextFacts).toHaveLength(27);
 const whole:any=contextFacts.find((f:any)=>f.path.length===2&&f.path[1]==='symbols');expect(whole.value).toEqual(symbols);expect(whole.text).toBe('21 instruments; see indexed pages');const layouts:any[]=[];
 for(let n=0;n<deck.pages.length;n++){
  if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
  const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,out:string[]=[];for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)out.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)out.push('camera overlap');}if(document.documentElement.scrollWidth>innerWidth)out.push('horizontal scroll');return out;});expect.soft(issues).toEqual([]);layouts.push(issues);await page.screenshot({path:info.outputPath('universe-page-'+(n+1)+'.png')});
 }
 expect(network).toEqual([]);expect(errors).toEqual([]);await writeFile(info.outputPath('universe-observations.json'),JSON.stringify({job_id:jid,dataset_id:manifest.id,symbols,core_hash:source.core_hash,pages:deck.pages.length,context_facts:contextFacts.length,layouts,network,errors,trades:source.trades.length,viewport:page.viewportSize(),scope:'Actual eligible21-instrument synthetic import and worker, paginated UI/all saved facts, no financial-selection criterion or final access.'},null,2));
});
