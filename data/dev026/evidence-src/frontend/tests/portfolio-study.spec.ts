import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

const days=['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12'];
test('freeze a whole shared portfolio, screen real synthetic accounts, cancel/resume the reserved final and inspect offline evidence',async({page,context},info)=>{
  test.setTimeout(480000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;},{timeout:60000}).toBe(true);
  const baseline=JSON.parse(await readFile('../verification/fixtures/strategy-baselines.json','utf8'));
  const prefix=(process.env.PA_STUDY_FIXTURE_TAG||'PA')+(info.project.name==='desktop1920'?'A':'B');
  const symbols=Array.from({length:20},(_,i)=>prefix+String(i+1).padStart(2,'0'));
  let csv='symbol,timestamp,open,high,low,close,volume\n';
  for(const day of days)for(const symbol of symbols)for(let minute=0;minute<390;minute++){
    const at=new Date(day+'T13:30:00Z');at.setUTCMinutes(at.getUTCMinutes()+minute);
    const close=minute>=21?200:baseline.common_closes[minute];
    csv += [symbol,at.toISOString(),(close-.02).toFixed(2),(close+.1).toFixed(2),(close-.1).toFixed(2),close.toFixed(2),10000].join(',')+'\n';
  }
  await page.goto('/');await page.getByLabel('Price file',{exact:true}).setInputFiles({name:'synthetic-portfolio-'+prefix+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
  await page.getByLabel('Start',{exact:true}).fill(days[0]);await page.getByLabel('End',{exact:true}).fill(days[5]);await page.getByRole('combobox',{name:'Input type',exact:true}).selectOption('synthetic');
  const imported=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Import & audit',exact:true}).click();
  const importedResponse=await imported;expect(importedResponse.status()).toBe(201);const manifest=await importedResponse.json();expect(manifest.quality.eligible).toBe(true);expect(manifest.quality.rows).toBe(46800);
  await page.getByRole('button',{name:'02 Strategies',exact:true}).click();const saved=[];
  for(const [index,timeframe,target] of [[0,'1m','4R'],[1,'1h','5R']] as const){
    await page.locator('.family-card').filter({has:page.getByText('Break of structure',{exact:true})}).click();
    if(!await page.getByRole('combobox',{name:'Max hold',exact:true}).isVisible())await page.getByText('Additional rules and context filters',{exact:true}).click();
    for(const [field,value] of [['Timeframe',timeframe],['Direction','long'],['Swing strength','2'],['Stop reference','level'],['Stop buffer','0'],['Max hold','0'],['Target',target]])await page.getByRole('combobox',{name:field,exact:true}).selectOption(value);
    const name='Frozen member '+index+' '+info.project.name+' <img src=x onerror=globalThis.studyProbe=1>';
    await page.getByLabel('Rule set name',{exact:true}).fill(name);const created=page.waitForResponse(r=>r.url().endsWith('/api/strategies')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Save rule set',exact:true}).click();saved.push(await(await created).json());
  }
  await page.getByRole('button',{name:'Use in experiment',exact:true}).click();await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(manifest.id);
  await page.getByLabel('Experiment name',{exact:true}).fill('Whole portfolio '+info.project.name);
  await page.getByText('Capital and sizing assumptions',{exact:true}).click();
  for(const [field,value] of [['Capital','10000'],['Risk fraction','0.1'],['Symbol exposure','1'],['Total exposure','1'],['Participation','1']])await page.getByLabel(field,{exact:true}).fill(value);
  await page.getByText('Execution costs and short borrowing',{exact:true}).click();
  for(const field of ['Commission per share','Spread bps','Slippage bps','Borrow annual'])await page.getByLabel(field,{exact:true}).fill('0');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await page.getByRole('combobox',{name:'Study selection unit',exact:true}).selectOption('portfolio');
  await expect(page.getByRole('button',{name:'Register & protect final dates',exact:true})).toBeDisabled();
  for(const rule of saved)await page.getByRole('checkbox',{name:'Freeze portfolio member '+rule.name+' '+rule.id.slice(0,8),exact:true}).check();
  for(const [field,value] of [['Discovery end',days[1]],['Validation start',days[2]],['Validation end',days[3]],['Final test start',days[4]],['Minimum trades per screening window','1'],['Minimum marked Sharpe per screening window','0']])await page.getByLabel(field,{exact:true}).fill(value);
  const registered=page.waitForResponse(r=>r.url().endsWith('/api/studies')&&r.request().method()==='POST');await page.getByRole('button',{name:'Register & protect final dates',exact:true}).click();
  const registeredResponse=await registered;expect(registeredResponse.status()).toBe(201);const projected=await registeredResponse.json(),sid=projected.id;expect(projected.spec.configuration_count).toBe(2);const inputResponse=await page.request.get('/api/studies/'+sid+'/inputs');expect(inputResponse.status()).toBe(200);const study=(await inputResponse.json()).study;
  expect(study.spec.study_mode).toBe('portfolio');expect(study.spec.configurations).toHaveLength(2);
  const row=()=>page.locator('tbody tr').filter({has:page.getByText(sid.slice(0,12),{exact:true})});
  await expect(row()).toContainText('Shared portfolio · 2 frozen rules');
  expect((await page.request.get('/api/datasets/'+manifest.id+'/preview?'+new URLSearchParams({symbol:symbols[0],start:days[4],end:days[5]}))).status()).toBe(409);
  await page.screenshot({path:info.outputPath('portfolio-study-frozen.png'),fullPage:true});
  const screening=page.waitForResponse(r=>r.url().endsWith('/api/studies/'+sid+'/screen')&&r.request().method()==='POST');await row().getByRole('button',{name:'Screen candidates',exact:true}).click();const screen=await(await screening).json();
  await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+screen.id)).json()).status,{timeout:240000}).toBe('completed');
  await expect(row()).toContainText('Screened');
  const selection=await(await page.request.get('/api/jobs/'+screen.id+'/result')).json();expect(selection.count).toBe(1);expect(selection.candidates).toHaveLength(1);expect(selection.candidates[0]).toEqual(study.spec.configurations);
  const accounts=[];
  for(const window of ['discovery','validation']){
    const report=await(await page.request.get('/api/jobs/'+screen.id+'/report?part=0&window='+window)).json();expect(report.metrics.net_profit).toBeGreaterThan(0);expect(report.metrics.trades).toBeGreaterThan(0);accounts.push({job:screen.id,window,report});
  }
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.locator('tbody tr').filter({has:page.getByText(screen.id.slice(0,10),{exact:true})}).getByRole('button',{name:'Open results',exact:true}).click();
  await expect(page.getByText('Shared portfolio · 2 frozen rules',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Inspect',exact:true}).click();await expect(page.getByRole('region',{name:'Frozen study account',exact:true})).toContainText('validation screening window');
  await page.getByRole('button',{name:'Discovery',exact:true}).click();await expect(page.getByRole('region',{name:'Frozen study account',exact:true})).toContainText('discovery screening window');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  // Registering a final job reserves its identity. Stop and resume that real job;
  // the backend fixture includes enough symbols to expose an actual running state.
  const finalQueued=page.waitForResponse(r=>r.url().endsWith('/api/studies/'+sid+'/final')&&r.request().method()==='POST');await row().getByRole('button',{name:'Consume final test',exact:true}).click();const final=await(await finalQueued).json();
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();const jobRow=()=>page.locator('tbody tr').filter({has:page.getByText(final.id.slice(0,10),{exact:true})});
  await jobRow().getByRole('button',{name:'Cancel',exact:true}).click();await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+final.id)).json()).status,{timeout:60000}).toBe('canceled');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();await expect(row().getByRole('button',{name:'Consume final test',exact:true})).toHaveCount(0);await expect(row()).toContainText('Final job reserved');
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();await jobRow().getByRole('button',{name:'Resume',exact:true}).click();
  await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+final.id)).json()).status,{timeout:240000}).toBe('completed');
  const finalReport=await(await page.request.get('/api/jobs/'+final.id+'/report?part=0')).json();accounts.push({job:final.id,window:'report',report:finalReport});
  expect(finalReport.study_context.phase).toBe('final');expect(finalReport.report_type).toBe('shared_capital_portfolio');expect(finalReport.configurations).toHaveLength(2);expect(Object.keys(finalReport.chart_sets)).toHaveLength(2);
  const events=await(await page.request.get('/api/studies/'+sid+'/events')).json();expect(events.filter((e:any)=>e.kind==='final_unlock_consumed')).toHaveLength(1);expect(events.filter((e:any)=>e.kind==='portfolio_final_reserved')).toHaveLength(1);
  await jobRow().getByRole('button',{name:'Open results',exact:true}).click();await expect(page.getByText('Shared portfolio · 2 frozen rules',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Inspect',exact:true}).click();await expect(page.getByRole('region',{name:'Frozen study account',exact:true})).toContainText('Final dates consumed');
  await page.getByRole('button',{name:'05 Trade inspector',exact:true}).click();const trade=finalReport.trades[0];expect(trade).toBeTruthy();
  await page.locator('.trades-table tbody tr').first().getByRole('button',{name:'Inspect trade',exact:true}).click();await expect(page.locator('.candles')).toHaveAttribute('data-trade-id',trade.id);await expect(page.locator('.candles')).toHaveAttribute('data-bar-count',String(finalReport.chart_sets[trade.strategy_id][trade.symbol].length));
  await page.screenshot({path:info.outputPath('portfolio-study-final-trade.png'),fullPage:true});
  await page.getByRole('button',{name:'07 Reports',exact:true}).click();await expect(page.getByRole('region',{name:'Frozen study account',exact:true})).toContainText(sid);
  for(const account of accounts){
    const query='?part=0&window='+account.window;
    const json=await page.request.get('/api/jobs/'+account.job+'/export/json'+query);expect(json.status()).toBe(200);expect(await json.json()).toEqual(account.report);await writeFile(info.outputPath(account.window+'-account.json'),await json.body());
    const csv=await page.request.get('/api/jobs/'+account.job+'/export/csv'+query);expect(csv.status()).toBe(200);await writeFile(info.outputPath(account.window+'-trades.csv'),await csv.body());
  }
  const registry=await(await page.request.get('/api/trial-registry?job_id='+final.id)).json();expect(registry.totals.roles.portfolio).toEqual({occurrences:1,distinct_configurations:1});
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'Download current presentation',exact:true}).click();const htmlPath=info.outputPath('portfolio-study-presentation.html');await(await download).saveAs(htmlPath);
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();await expect(row()).toContainText('Final complete');await row().getByRole('button',{name:'View audit trail',exact:true}).click();await expect(page.getByRole('heading',{name:'Study audit trail',exact:true})).toBeVisible();await page.screenshot({path:info.outputPath('portfolio-study-audit.png'),fullPage:true});
  expect(await page.evaluate(()=>(globalThis as any).studyProbe)).toBeUndefined();expect(await page.locator('img[onerror]').count()).toBe(0);
  const workspace=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await workspace.close();await context.setOffline(true);
  const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});await page.goto(pathToFileURL(htmlPath).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  const paths=new Set(Object.values(deck.facts).map((f:any)=>f.path.join('.')));expect(paths.has('study_context.phase')).toBe(true);
  for(let i=0;i<2;i++)for(const key of Object.keys(finalReport.configurations[i].config))expect(paths.has('configurations.'+i+'.config.'+key)).toBe(true);
  const layouts=[];
  for(let n=0;n<deck.pages.length;n++){
    if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
    const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,issues:string[]=[];
      for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)issues.push('camera overlap');}
      const c=document.querySelector<HTMLElement>('.concept');if(c&&c.getBoundingClientRect().bottom>r.y+820*s+.5)issues.push('concept overlaps conclusion');if(document.documentElement.scrollWidth>innerWidth)issues.push('horizontal scroll');return issues;});
    expect.soft(issues,'Portfolio final page '+(n+1)).toEqual([]);layouts.push(issues);await page.screenshot({path:info.outputPath('portfolio-study-page-'+(n+1)+'.png')});
  }
  expect(network).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('portfolio-study-observations.json'),JSON.stringify({study_id:sid,screen_job:screen.id,final_job:final.id,dataset_id:manifest.id,symbols,viewport:page.viewportSize(),browser:context.browser()?.version(),events,registry,pages:deck.pages.length,facts:Object.keys(deck.facts).length,layouts,networkRequests:network,consoleErrors:errors,scope:'Explicitly synthetic positive-control prices and20 synthetic symbols. Actual UI/import/worker/screening/final/cancel/resume/saved accounts, not an untouched market result or strategy-edge certificate.'},null,2));
});
