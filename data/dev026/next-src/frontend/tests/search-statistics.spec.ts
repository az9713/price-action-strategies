import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('prespecified historical search retains all DSR scenarios and saved offline evidence',async({page,context},info)=>{
  test.setTimeout(480000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;},{timeout:60000}).toBe(true);
  await page.goto('/');await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByLabel('Experiment name',{exact:true}).fill('DSR prespecified historical '+info.project.name);
  await page.getByLabel('Random seed',{exact:true}).fill('42');
  const search=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Reproducible parameter search',exact:true})});
  await search.getByLabel('Break of structure',{exact:true}).check();
  await search.getByLabel('15m',{exact:true}).check();
  await search.getByRole('spinbutton',{name:/^Unique configurations\b/}).fill('6');
  await search.getByText('Search-bias assumptions',{exact:true}).click();
  await search.getByLabel('Assumed independent trial counts',{exact:true}).fill('1, 2, 7');
  let posted=0;page.on('request',r=>{if(r.url().endsWith('/api/searches')&&r.method()==='POST')posted++;});
  await search.getByRole('button',{name:'Queue parameter search',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Trial assumptions must be distinct integers');expect(posted).toBe(0);
  await search.getByLabel('Assumed independent trial counts',{exact:true}).fill('1, 2, 4');
  await search.getByLabel('Trial Sharpe dispersion',{exact:true}).selectOption('assumed');
  await search.getByRole('button',{name:'Queue parameter search',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Enter a finite nonnegative');expect(posted).toBe(0);
  await search.getByLabel('Assumed daily Sharpe standard deviation',{exact:true}).fill('0.25');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/searches')&&r.request().method()==='POST');
  await search.getByRole('button',{name:'Queue parameter search',exact:true}).click();
  const created=await(await response).json(),jid=created.id;expect(jid).toBeTruthy();
  expect(created.payload.statistics).toEqual({effective_trials:[1,2,4],dispersion_mode:'assumed',trial_sharpe_std:.25});
  expect(created.payload.families).toEqual(['change_of_character','break_of_structure']);expect(created.payload.timeframes).toEqual(['1h','15m']);
  await expect.poll(async()=>{const j=await(await page.request.get('/api/jobs/'+jid)).json();return ['completed','failed','canceled'].includes(j.status);},{timeout:360000}).toBe(true);
  const job=await(await page.request.get('/api/jobs/'+jid)).json();expect(job.status,job.error||'Actual historical search must complete').toBe('completed');
  const saved=await(await page.request.get('/api/jobs/'+jid+'/result')).json(),stats=saved.search_statistics;
  expect(stats.accounts).toHaveLength(6);expect(stats.settings).toEqual(created.payload.statistics);
  expect(saved.rows.reduce((n:number,r:any)=>n+r.metrics.trades,0)).toBeGreaterThan(0);
  expect(stats.accounts.some((a:any)=>a.sensitivity.some((s:any)=>s.score!==null))).toBe(true);
  const row=page.locator('tbody tr').filter({has:page.getByText(jid.slice(0,10),{exact:true})});
  await row.getByRole('button',{name:'Open results',exact:true}).click();
  const region=page.getByRole('region',{name:'Search-bias sensitivity',exact:true});await expect(region).toBeVisible();
  await expect(region.locator('tbody tr')).toHaveCount(18);
  for(let i=0;i<6;i++)for(let k=0;k<3;k++){
    const a=stats.accounts[i],s=a.sensitivity[k],r=region.locator('tbody tr').nth(i*3+k);
    await expect(r).toContainText(a.config_id.slice(0,12));await expect(r.locator('td').nth(5)).toHaveText(s.score===null?'Undefined':s.score.toPrecision(6));
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('search-statistics.png'),fullPage:true});
  for(const [label,file] of [['Download search statistics JSON','statistics.json'],['Download all search statistics CSV','statistics.csv'],['Download saved search summary JSON','summary.json'],['Download search presentation','presentation.html']]){
    const pending=page.waitForEvent('download');await region.getByRole('link',{name:label,exact:true}).click();await(await pending).saveAs(info.outputPath(file));
  }
  expect(JSON.parse(await readFile(info.outputPath('statistics.json'),'utf8'))).toEqual(stats);
  expect(JSON.parse(await readFile(info.outputPath('summary.json'),'utf8'))).toEqual(saved);
  const registry=await(await page.request.get('/api/trial-registry?job_id='+jid)).json();expect(registry.totals.planned_occurrences).toBe(6);
  await writeFile(info.outputPath('trial-registry.json'),JSON.stringify(registry,null,2));
  for(let part=0;part<6;part++){
    const report=await page.request.get('/api/jobs/'+jid+'/report?part='+part);expect(report.status()).toBe(200);await writeFile(info.outputPath('account-'+part+'.json'),await report.body());
    const csv=await page.request.get('/api/jobs/'+jid+'/export/csv?part='+part);expect(csv.status()).toBe(200);await writeFile(info.outputPath('account-'+part+'.csv'),await csv.body());
  }
  const workspace=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await workspace.close();
  await context.setOffline(true);const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await page.goto(pathToFileURL(info.outputPath('presentation.html')).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  const layouts=[];
  for(let n=0;n<deck.pages.length;n++){
    if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
    const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,issues:string[]=[];
      for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)issues.push('camera overlap');}
      if(document.documentElement.scrollWidth>innerWidth)issues.push('horizontal scroll');return issues;});
    expect.soft(issues,'Search presenter page '+(n+1)).toEqual([]);layouts.push(issues);await page.screenshot({path:info.outputPath('presentation-'+(n+1)+'.png')});
  }
  expect(network).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('statistics-observations.json'),JSON.stringify({job_id:jid,viewport:page.viewportSize(),browser:context.browser()?.version(),pages:deck.pages.length,facts:Object.keys(deck.facts).length,layouts,networkRequests:network,consoleErrors:errors,scope:'Prespecified six-account search on already viewed cached January 2022 prices. Diagnostic, not holdout or strategy-edge certification.'},null,2));
});
