import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';

const money=(v:number)=>v.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
test('latest saved account owns report and export after reversed success, stale failure and current failure',async({page},info)=>{
  test.setTimeout(240000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');const origin=new URL(page.url()).origin;
  const session=await(await page.request.get('/api/session')).json();
  const schema=await(await page.request.get('/api/schema')).json();
  const defaults=(spec:any)=>Object.fromEntries(Object.entries(spec.properties).filter(([,v]:any)=>'default'in v).map(([k,v]:any)=>[k,v.default]));
  const jobs=[];
  for(const rate of [.03,.3]){
    const response=await page.request.post('/api/experiments',{headers:{Origin:origin,'X-Lab-Token':session.token},data:{name:'Response ownership '+info.project.name+' '+rate,dataset_id:'90f347229b2fb03ec112ee71',strategy:defaults(schema.strategy),costs:{...defaults(schema.costs),borrow_annual:rate},portfolio:defaults(schema.portfolio),start:'2022-01-03',end:'2022-01-31',seed:42}});
    expect(response.status()).toBe(202);const job=await response.json();
    await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+job.id)).json()).status,{timeout:120000}).toBe('completed');jobs.push(job);
  }
  const [a,b]=jobs;const ar=await(await page.request.get('/api/jobs/'+a.id+'/report')).json();const br=await(await page.request.get('/api/jobs/'+b.id+'/report')).json();
  expect(money(ar.metrics.net_profit)).not.toBe(money(br.metrics.net_profit));
  await page.getByRole('button',{name:'04 Results',exact:true}).click();const selector=()=>page.getByRole('combobox',{name:'Completed job',exact:true});
  const profit=()=>page.locator('.metrics b').first();const observations=[];
  for(const fault of ['stale_success','stale_failure','current_failure']){
    await selector().selectOption(a.id);await expect(profit()).toHaveText(money(ar.metrics.net_profit));
    let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});let held=false;
    const pattern='**/api/jobs/'+b.id+'/report';
    await page.route(pattern,async route=>{held=true;await gate;if(fault==='stale_success')await route.continue();else await route.abort('failed');});
    try{
      await selector().selectOption(b.id);await expect.poll(()=>held).toBe(true);
      await expect(page.locator('.metrics')).toHaveCount(0);
      if(fault!=='current_failure'){
        await selector().selectOption(a.id);await expect(profit()).toHaveText(money(ar.metrics.net_profit));
      }
      release();await page.waitForTimeout(1000);
      if(fault==='current_failure'){
        await expect(page.locator('.metrics')).toHaveCount(0);await expect(page.getByRole('alert')).toBeVisible();
        await page.getByRole('button',{name:'07 Reports',exact:true}).click();await expect(page.getByRole('link',{name:'Download full JSON evidence',exact:true})).toHaveCount(0);
        observations.push({fault,reportCleared:true,exportUnavailable:true});
      }else{
        await expect(selector()).toHaveValue(a.id);await expect(profit()).toHaveText(money(ar.metrics.net_profit));await expect(page.getByRole('alert')).toHaveCount(0);
        await page.getByRole('button',{name:'07 Reports',exact:true}).click();
        const link=page.getByRole('link',{name:'Download full JSON evidence',exact:true});await expect(link).toHaveAttribute('href','/api/jobs/'+a.id+'/export/json');
        const saved=await(await page.request.get((await link.getAttribute('href'))!)).json();expect(saved).toEqual(ar);
        observations.push({fault,selectedJob:a.id,profit:money(ar.metrics.net_profit),exportJob:a.id});
      }
      await page.screenshot({path:info.outputPath('result-ownership-'+fault+'.png'),fullPage:true});
      await page.getByRole('button',{name:'04 Results',exact:true}).click();
    }finally{release();await page.unroute(pattern);}
  }
  expect(errors).toEqual([]);await writeFile(info.outputPath('result-ownership-observations.json'),JSON.stringify({jobs:jobs.map(j=>j.id),observations,consoleErrors:errors,scope:'Two actual complete historical accounts; deliberately delayed success and aborted network responses test ownership without fabricating account values.'},null,2));
});
