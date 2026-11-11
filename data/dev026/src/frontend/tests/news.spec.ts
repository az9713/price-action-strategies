import {test,expect} from '@playwright/test';
import {writeFile,readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('official news acquisition and reviewed import freeze into actual account and offline report',async({page,context},info)=>{
  test.setTimeout(300000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');const panel=page.getByRole('region',{name:'Scheduled news calendars',exact:true});await expect(panel).toBeVisible();
  await page.getByLabel('Calendar name',{exact:true}).fill('Official news '+info.project.name);
  await page.getByLabel('News coverage start',{exact:true}).fill('2022-01-03');await page.getByLabel('News coverage end',{exact:true}).fill('2022-01-31');
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/news-downloads')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Acquire free official calendar',exact:true}).click();
  const created=await(await queued).json();expect(created.id).toMatch(/^[0-9a-f]{32}$/);
  await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+created.id)).json()).status,{timeout:90000}).toBe('completed');
  const acquired=await(await page.request.get('/api/jobs/'+created.id+'/result')).json();const official=acquired.calendar;
  expect(official.spec.mode).toBe('retrospective');expect(official.origin).toBe('official');
  expect(official.spec.events.map((e:any)=>[e.date,e.kind])).toEqual([['2022-01-07','jobs'],['2022-01-12','cpi'],['2022-01-26','fed']]);
  await expect(page.getByRole('combobox',{name:'News calendar',exact:true})).toHaveValue(official.id);
  await expect(panel.getByText('Historical advance knowledge of these reconstructed dates is assumed. This is not a point-in-time calendar.',{exact:false})).toBeVisible();
  await page.screenshot({path:info.outputPath('official-news.png'),fullPage:true});
  await panel.getByText('Import a reviewed calendar CSV',{exact:true}).click();
  await page.getByLabel('Consumer prices (CPI)',{exact:true}).uncheck();await page.getByLabel('Employment Situation (jobs)',{exact:true}).uncheck();
  await page.getByRole('combobox',{name:'Imported calendar knowledge',exact:true}).selectOption('asof');
  await page.getByLabel('I checked coverage of all selected event types for the entire declared date range',{exact:true}).check();
  const before=(await(await page.request.get('/api/news-calendars')).json()).length;
  await page.getByLabel('Calendar CSV',{exact:true}).setInputFiles({name:'invalid-known-time.csv',mimeType:'text/csv',buffer:Buffer.from('date,kind,label,known_at\n2022-01-12,fed,Invalid knowledge time,2022-01-10T12:00:00\n')});
  await page.getByRole('button',{name:'Import calendar CSV',exact:true}).click();
  await expect(panel.getByRole('alert')).toContainText('invalid');
  expect((await(await page.request.get('/api/news-calendars')).json()).length).toBe(before);
  await page.screenshot({path:info.outputPath('news-invalid-import.png'),fullPage:true});
  await page.getByRole('combobox',{name:'Imported calendar knowledge',exact:true}).selectOption('synthetic');
  await page.getByLabel('Calendar name',{exact:true}).fill('Synthetic news '+info.project.name+' <img src=x onerror=globalThis.newsNameProbe=1>');
  const label='Scenario <img src=x onerror=globalThis.newsProbe=1>';
  await page.getByLabel('Calendar CSV',{exact:true}).setInputFiles({name:'authored-synthetic-news.csv',mimeType:'text/csv',buffer:Buffer.from('date,kind,label,known_at\n2022-01-12,fed,'+label+',\n')});
  const imported=page.waitForResponse(r=>r.url().endsWith('/api/news-imports')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Import calendar CSV',exact:true}).click();const importedResponse=await imported;expect(importedResponse.status()).toBe(201);
  const version=await importedResponse.json();await expect(page.getByRole('combobox',{name:'News calendar',exact:true})).toHaveValue(version.id);
  await expect(panel.getByText(label,{exact:true})).toBeVisible();expect(await page.evaluate(()=>(globalThis as any).newsProbe)).toBeUndefined();
  expect(await page.evaluate(()=>(globalThis as any).newsNameProbe)).toBeUndefined();expect(await page.locator('img[onerror]').count()).toBe(0);
  expect(await(await page.request.get('/api/news-calendars/'+official.id)).json()).toEqual(official);
  await page.screenshot({path:info.outputPath('news-imported-scenario.png'),fullPage:true});
  const calDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download calendar JSON',exact:true}).click();
  const calPath=info.outputPath('downloaded-news-calendar.json');await(await calDownload).saveAs(calPath);expect(JSON.parse(await readFile(calPath,'utf8'))).toEqual(version);
  await page.getByRole('button',{name:'02 Strategies',exact:true}).click();
  await page.getByText('Additional rules and context filters',{exact:true}).click();
  await page.getByRole('combobox',{name:'News',exact:true}).selectOption('half');
  await page.getByRole('button',{name:'Use in experiment',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await expect(page.getByRole('combobox',{name:'News calendar',exact:true})).toHaveValue(version.id);
  await page.getByLabel('Experiment name',{exact:true}).fill('News scenario '+info.project.name);
  const running=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run single configuration',exact:true}).click();const job=await(await running).json();expect(job.id).toMatch(/^[a-f0-9]{32}$/);
  await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+job.id)).json()).status,{timeout:180000}).toBe('completed');
  const stored=await(await page.request.get('/api/jobs/'+job.id)).json();expect(stored.payload.news_calendar).toEqual(version);
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();expect(report.news_calendar).toEqual(version);expect(report.config.news).toBe('half');
  expect(report.trades.length).toBeGreaterThan(0);
  const nyDate=(at:string)=>{const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(at));return ['year','month','day'].map(k=>parts.find(p=>p.type===k)!.value).join('-');};
  const affected=report.signals.filter((s:any)=>nyDate(s.available_at)==='2022-01-12');expect(affected.length).toBeGreaterThan(0);expect(affected.every((s:any)=>s.weight===.5)).toBe(true);
  expect(report.signals.filter((s:any)=>nyDate(s.available_at)!=='2022-01-12').every((s:any)=>s.weight===1)).toBe(true);
  expect(Math.abs(report.trades.reduce((sum:number,t:any)=>sum+t.net_pnl,0)-report.metrics.net_profit)).toBeLessThan(1e-7);
  // Hold a real report response until after navigation: a late result must not steal the selected page.
  let releaseReport!:()=>void;const reportGate=new Promise<void>(resolve=>{releaseReport=resolve;});
  await page.route('**/api/jobs/'+job.id+'/report',async route=>{const response=await route.fetch();await reportGate;await route.fulfill({response});});
  const row=page.locator('tbody tr').filter({has:page.getByText(job.id.slice(0,10),{exact:true})});await row.getByRole('button',{name:'Open results',exact:true}).click();
  await page.getByRole('button',{name:'07 Reports',exact:true}).click();await expect(page.getByRole('heading',{name:'Reports',exact:true,level:1})).toBeVisible();
  releaseReport();await expect(page.getByText('Synthetic news events are a testing scenario.',{exact:false})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Reports',exact:true,level:1})).toBeVisible();
  await page.screenshot({path:info.outputPath('news-account-report.png'),fullPage:true});
  const jsonDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download full JSON evidence',exact:true}).click();
  const jsonPath=info.outputPath('downloaded-news-account.json');await(await jsonDownload).saveAs(jsonPath);expect(JSON.parse(await readFile(jsonPath,'utf8'))).toEqual(report);
  const htmlDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download current presentation',exact:true}).click();
  const htmlPath=info.outputPath('news-presentation.html');await(await htmlDownload).saveAs(htmlPath);
  // Close the polling workspace before measuring the standalone file's network activity.
  const workspacePage=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await workspacePage.close();
  await context.setOffline(true);const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await page.goto(pathToFileURL(htmlPath).href);const manifest=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  expect(Object.values(manifest.facts).some((f:any)=>f.path.join('.')==='news_calendar.spec.mode'&&f.value==='synthetic')).toBe(true);
  const layouts=[];
  for(let n=0;n<manifest.pages.length;n++){
    if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
    const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,issues:string[]=[];
      for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)issues.push('camera overlap');}
      const c=document.querySelector<HTMLElement>('.concept');if(c&&c.getBoundingClientRect().bottom>r.y+820*s+.5)issues.push('concept overlaps conclusion');
      if(document.documentElement.scrollWidth>innerWidth)issues.push('horizontal scroll');return issues;});
    expect.soft(issues,'News presenter page '+(n+1)).toEqual([]);layouts.push(issues);await page.screenshot({path:info.outputPath('news-presentation-'+(n+1)+'.png')});
  }
  expect(await page.evaluate(()=>(globalThis as any).newsNameProbe)).toBeUndefined();expect(network).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('news-observations.json'),JSON.stringify({job_id:job.id,official_job_id:created.id,official_calendar:official.id,scenario_calendar:version.id,
    viewport:page.viewportSize(),browser:context.browser()?.version(),affected_signals:affected.length,net_profit:report.metrics.net_profit,trades:report.trades.length,presentation_pages:manifest.pages.length,layouts,consoleErrors:errors,networkRequests:network,
    scope:'Actual free official acquisition plus labeled authored news scenario and saved-output offline export; not point-in-time history or final release certification.'},null,2));
});
