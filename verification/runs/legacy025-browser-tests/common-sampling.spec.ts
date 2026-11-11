import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('complete published common grid and exact random quotas retain real worker accounts and offline gates',async({page,context},info)=>{
  test.setTimeout(900000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture=JSON.parse(await readFile('../verification/fixtures/common-sampling-browser-contract-v2.json','utf8'));
  await expect.poll(async()=>{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;},{timeout:60000}).toBe(true);
  const symbol=fixture.symbols[info.project.name];let csv='symbol,timestamp,open,high,low,close,volume\n';
  for(const [index,day] of fixture.sessions.entries())for(let minute=0;minute<390;minute++){
    const at=new Date(day+'T13:30:00Z');at.setUTCMinutes(at.getUTCMinutes()+minute);const close=1000+10*index-.1*minute+8*Math.sin(2*Math.PI*minute/64);
    csv+=[symbol,at.toISOString(),(close+.02).toFixed(12),(close+.2).toFixed(12),(close-.1).toFixed(12),close.toFixed(12),10000].join(',')+'\n';
  }
  await page.goto('/');const beforeHealth=await(await page.request.get('/api/health')).json();
  await page.getByLabel('Price file',{exact:true}).setInputFiles({name:'synthetic-common-'+symbol+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
  await page.getByLabel('Start',{exact:true}).fill(fixture.sessions[0]);await page.getByLabel('End',{exact:true}).fill(fixture.sessions.at(-1));
  await page.getByRole('combobox',{name:'Input type',exact:true}).selectOption('synthetic');
  const imported=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Import & audit',exact:true}).click();
  const response=await imported;expect(response.status()).toBe(201);const dataset=await response.json();expect(dataset.quality.eligible).toBe(true);
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(dataset.id);
  await page.getByLabel('Random seed',{exact:true}).fill('42');await page.getByLabel('Experiment name',{exact:true}).fill('Explicit synthetic common modes '+info.project.name);
  const search=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Reproducible parameter search',exact:true})});
  await search.getByLabel('Change of character',{exact:true}).uncheck();await search.getByLabel('Break of structure',{exact:true}).check();
  await search.getByLabel('1h',{exact:true}).uncheck();await search.getByLabel('1m',{exact:true}).check();
  await search.getByLabel('Sampling method',{exact:true}).selectOption('common_grid');await expect(search.getByRole('button',{name:'Queue parameter search',exact:true})).toBeDisabled();
  const preview=page.waitForResponse(r=>r.url().endsWith('/api/searches/preview')&&r.request().method()==='POST');await search.getByRole('button',{name:'Preview published recipe',exact:true}).click();
  const recipe=await(await preview).json();expect(recipe.grid_count).toBe(48);
  await expect(search.getByRole('spinbutton',{name:/^Unique configurations\b/})).toHaveValue('48');await expect(search.getByRole('spinbutton',{name:/^Unique configurations\b/})).toBeDisabled();
  await search.getByText('Search-bias assumptions',{exact:true}).click();await search.getByLabel('Assumed independent trial counts',{exact:true}).fill('1');
  const books:any[]=[];const jobs:any[]=[];
  for(const [mode,count,prefix] of [['common_grid',48,'grid'],['common_random',6,'random'],['common_random',6,'news']] as const){
    if(mode==='common_random'){
      await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await search.getByLabel('Sampling method',{exact:true}).selectOption(mode);
      await search.getByRole('spinbutton',{name:/^Unique configurations\b/}).fill(String(count));
      if(prefix==='news'){
        const token=(await(await page.request.get('/api/session')).json()).token;
        const imported=await page.request.post('/api/news-calendars',{headers:{Origin:new URL(page.url()).origin,'X-Lab-Token':token},data:{name:'Synthetic common news '+info.project.name,start:fixture.sessions[0],end:fixture.sessions.at(-1),mode:'synthetic',complete:true,kinds:['fed'],events:fixture.additional_news_case.events.map((date:string)=>({date,kind:'fed',label:'Authored testing event'}))}});
        expect(imported.status()).toBe(201);const calendar=await imported.json();
        await expect.poll(async()=>page.getByRole('combobox',{name:'News calendar',exact:true}).locator('option[value="'+calendar.id+'"]').count()).toBe(1);
        await page.getByRole('combobox',{name:'News calendar',exact:true}).selectOption(calendar.id);
        await search.getByRole('checkbox',{name:'Include news filter variants',exact:true}).check();
      }
    }
    const pending=page.waitForResponse(r=>r.url().endsWith('/api/searches')&&r.request().method()==='POST');await search.getByRole('button',{name:'Queue parameter search',exact:true}).click();
    const createdResponse=await pending;expect(createdResponse.status()).toBe(202);const created=await createdResponse.json(),jid=created.id;
    expect(created.payload.sampling_policy.mode).toBe(mode);expect(created.payload.configuration_count).toBe(count);expect(created.payload.sampling_policy.include_news).toBe(prefix==='news');
    await expect.poll(async()=>{const j=await(await page.request.get('/api/jobs/'+jid)).json();return ['completed','failed','canceled'].includes(j.status);},{timeout:360000}).toBe(true);
    const job=await(await page.request.get('/api/jobs/'+jid)).json();expect(job.status,job.error||'Actual complete common-mode worker job').toBe('completed');
    const saved=await(await page.request.get('/api/jobs/'+jid+'/result')).json();expect(saved.rows).toHaveLength(count);expect(saved.search_screen.accounts).toHaveLength(count);
    if(mode==='common_grid'){
      expect(saved.rows.reduce((n:number,r:any)=>n+r.metrics.trades,0)).toBeGreaterThan(0);expect(saved.search_screen.counts.signal_qualified).toBeGreaterThan(0);
    }else{
      const counts=[0,0,0];for(const r of saved.rows){const c=r.config,n=Number(c.trend_filter!=='none')+Number(c.session_filter!=='core')+Number(c.news!=='trade')+Number(c.skip_run_days!==0)+Number(c.skip_choppy)+Number(c.fresh_breakout)+Number(c.gap_confluence);counts[n]++;}expect(counts).toEqual([3,2,1]);
    }
    const row=page.locator('tbody tr').filter({has:page.getByText(jid.slice(0,10),{exact:true})});await row.getByRole('button',{name:'Open results',exact:true}).click();
    const region=page.getByRole('region',{name:'Initial discovery funnel',exact:true});await expect(region).toBeVisible();if(prefix==='news'){await expect(region).toContainText('Synthetic common news '+info.project.name);expect(saved.news_calendar_id).toBeTruthy();expect(saved.news_calendar.id).toBe(saved.news_calendar_id);}
    for(const [i,key] of ['generated','signal_qualified','enough_trades','profitable','sharpe_passed'].entries())await expect(region.locator('.metrics b').nth(i)).toHaveText(String(saved.search_screen.counts[key]));
    await expect(region).toContainText('have not run');await expect(region.locator('tbody').last().locator('tr')).toHaveCount(Math.min(count,20));
    if(count>20){await region.getByRole('button',{name:'Next discovery accounts',exact:true}).click();await expect(region).toContainText('Page 2 of 3');await region.getByRole('button',{name:'Next discovery accounts',exact:true}).click();await expect(region.locator('tbody').last().locator('tr')).toHaveCount(8);await region.getByRole('button',{name:'Previous discovery accounts',exact:true}).click();}
    await page.screenshot({path:info.outputPath(prefix+'-outcomes.png'),fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    for(const [label,file] of [['Download initial discovery JSON',prefix+'-screen.json'],['Download all initial discovery CSV',prefix+'-screen.csv']]){const d=page.waitForEvent('download');await region.getByRole('link',{name:label,exact:true}).click();await(await d).saveAs(info.outputPath(file));}
    const statistics=page.getByRole('region',{name:'Search-bias sensitivity',exact:true});
    for(const [label,file] of [['Download saved search summary JSON',prefix+'-summary.json'],['Download search presentation',prefix+'-presentation.html']]){const d=page.waitForEvent('download');await statistics.getByRole('link',{name:label,exact:true}).click();await(await d).saveAs(info.outputPath(file));}
    expect(JSON.parse(await readFile(info.outputPath(prefix+'-summary.json'),'utf8'))).toEqual(saved);
    expect(JSON.parse(await readFile(info.outputPath(prefix+'-screen.json'),'utf8'))).toEqual(saved.search_screen);
    for(let part=0;part<count;part++){
      const report=await page.request.get('/api/jobs/'+jid+'/report?part='+part);expect(report.status()).toBe(200);await writeFile(info.outputPath(prefix+'-account-'+part+'.json'),await report.body());
      const csv=await page.request.get('/api/jobs/'+jid+'/export/csv?part='+part);expect(csv.status()).toBe(200);await writeFile(info.outputPath(prefix+'-account-'+part+'.csv'),await csv.body());
    }
    const registry=await(await page.request.get('/api/trial-registry?job_id='+jid)).json();expect(registry.totals.planned_occurrences).toBe(count);await writeFile(info.outputPath(prefix+'-registry.json'),JSON.stringify(registry,null,2));
    jobs.push({id:jid,prefix,count});books.push(saved);
  }
  const afterHealth=await(await page.request.get('/api/health')).json();expect(afterHealth.core_hash).toBe(beforeHealth.core_hash);
  const workspace=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await workspace.close();await context.setOffline(true);
  const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});const layouts:any[]=[];
  for(const job of jobs){
    await page.goto(pathToFileURL(info.outputPath(job.prefix+'-presentation.html')).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
    for(let n=0;n<deck.pages.length;n++){
      if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
      const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,issues:string[]=[];
        for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)issues.push('camera overlap');}
        if(document.documentElement.scrollWidth>innerWidth)issues.push('horizontal scroll');return issues;});
      expect.soft(issues,job.prefix+' page '+(n+1)).toEqual([]);layouts.push({prefix:job.prefix,page:n+1,issues});await page.screenshot({path:info.outputPath(job.prefix+'-page-'+(n+1)+'.png')});
    }
    job.pages=deck.pages.length;job.facts=Object.keys(deck.facts).length;
  }
  expect(network).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('common-observations.json'),JSON.stringify({jobs,dataset_id:dataset.id,symbol,viewport:page.viewportSize(),browser:context.browser()?.version(),core_hash:afterHealth.core_hash,recipe_hash:recipe.recipe_hash,layouts,networkRequests:network,consoleErrors:errors,scope:'Explicit synthetic12-session/one-symbol common48-grid and six-random controls. Initial discovery software evidence; not a market replication, profitable strategy or final validation.'},null,2));
});
