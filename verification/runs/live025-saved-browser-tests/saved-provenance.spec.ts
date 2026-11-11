import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const synthetic='20d37c0992984a44bdb103bd0d0c3b0a',legacy='4e851c9015634b7a9dbf06619770d894';
test('saved synthetic context survives historical selection and genuine original legacy results remain unclassified',async({page,context},info)=>{
 test.setTimeout(240000);const errors:string[]=[],forbidden:string[]=[],repairs:string[]=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),method=request.method();
  const allowedRepair=method==='POST'&&[synthetic,legacy].some(id=>url.pathname==='/api/jobs/'+id+'/result-view/repair');
  if((!['GET','HEAD','OPTIONS'].includes(method)&&!allowedRepair)||/\/api\/datasets\/[^/]+\/(preview|chart|bars)/.test(url.pathname)){
   forbidden.push(method+' '+url.pathname);await route.abort();return;
  }
  if(allowedRepair)repairs.push(url.pathname);await route.continue();
 });
 await page.goto('/');const nav=page.getByRole('navigation',{name:'Research sections'});
 async function openSaved(id:string){
  await nav.getByRole('button',{name:'04 Results',exact:true}).click();const history=page.getByRole('region',{name:'Saved job history',exact:true});
  const newest=history.getByRole('button',{name:'Newest job history',exact:true});if(await newest.isEnabled())await newest.click();
  let found=false;
  for(let n=0;n<12;n++){
   await expect(history.locator('tbody tr').first()).toBeVisible();const row=history.locator('tbody tr').filter({has:page.getByText(id,{exact:true})});
   if(await row.count()){await row.getByRole('button',{name:'Open historical results',exact:true}).click();found=true;break;}
   const older=history.getByRole('button',{name:'Older job history',exact:true});await expect(older).toBeEnabled();
   const previous=await history.locator('tbody tr').first().innerText();await older.click();await expect(history.locator('tbody tr').first()).not.toHaveText(previous);
  }
  expect(found,'Original saved job must be reachable through actual history').toBe(true);
  const builder=page.getByRole('button',{name:'Build saved result view',exact:true});
  await expect.poll(async()=>await builder.count()||await page.getByRole('link',{name:'Download search presentation',exact:true}).count()).toBeGreaterThan(0);
  if(await builder.count()){await builder.click();await expect(builder).toHaveCount(0,{timeout:60000});}
  await expect(page.getByRole('region',{name:'Search-bias sensitivity',exact:true})).toBeVisible();
 }
 await openSaved(synthetic);const provenance=page.getByRole('region',{name:'Saved dataset context',exact:true});
 await expect(provenance).toContainText('Synthetic input');await expect(provenance).toContainText('ZCGB');
 await nav.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
 await nav.getByRole('button',{name:'04 Results',exact:true}).click();await expect(provenance).toContainText('Synthetic input');await expect(provenance).toContainText('ZCGB');await expect(provenance).not.toContainText('Historical input');
 await page.screenshot({path:info.outputPath('original-synthetic-context-after-historical-selection.png'),fullPage:true});
 const files:string[]=[];
 async function download(name:string){const pending=page.waitForEvent('download');await page.getByRole('link',{name:'Download search presentation',exact:true}).click();const file=info.outputPath(name+'.html');await(await pending).saveAs(file);files.push(file);}
 await download('original-synthetic-presentation');await openSaved(legacy);
 await expect(provenance).toContainText('Dataset context not recorded');await expect(provenance).not.toContainText('Historical input');await expect(provenance).not.toContainText('Synthetic input');
 await page.screenshot({path:info.outputPath('genuine-original-legacy-context-not-inferred.png'),fullPage:true});await download('original-legacy-presentation');
 const app=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await app.close();await context.setOffline(true);const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});const decks:any[]=[];
 for(const file of files){
  await page.goto(pathToFileURL(file).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  if(file.includes('legacy'))expect(deck.pages.some((p:any)=>p.title==='Dataset context not recorded')).toBe(true);
  for(let n=0;n<deck.pages.length;n++){
   if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
   const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect();return [...document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .chart,#slide .notes p')].filter(e=>{const b=e.getBoundingClientRect();return b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5;}).length;});expect(issues).toBe(0);
  }
  decks.push({pages:deck.pages.length,facts:Object.keys(deck.facts).length});
 }
 expect(forbidden).toEqual([]);expect(network).toEqual([]);expect(errors).toEqual([]);
 await writeFile(info.outputPath('saved-provenance-observations.json'),JSON.stringify({synthetic,legacy,decks,repairs,forbidden,network,errors,scope:'Existing saved aggregates read in place; no financial job, market-data download or price-cache copy. Only explicit derived result-view construction is allowed.'},null,2));
});
