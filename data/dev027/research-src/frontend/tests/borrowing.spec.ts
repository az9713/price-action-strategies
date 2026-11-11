import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

test('changing borrowing editor freezes a real account and latched weekend recall into saved exports',async({page,context},info)=>{
  test.setTimeout(300000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByText('Execution costs and short borrowing',{exact:true}).click();
  const editor=page.getByRole('region',{name:'Changing short borrowing',exact:true});await expect(editor).toBeVisible();
  const before=(await(await page.request.get('/api/jobs')).json()).length;
  // Duplicate-key JSON is separately exercised by the actual API test. Its raw trace
  // is intentionally unsupported by the fail-closed privacy parser and remains private.
  const invalid=JSON.stringify({name:'Invalid clock',start:'2022-01-03',end:'2022-01-31',symbols:['AAPL','IWM','MSFT','QQQ','SPY'],complete:true,mode:'synthetic',events:[{symbol:'MSFT',effective_at:'2022-01-21T14:31:00',annual_rate:.1,available:true,recall:false}]});
  await page.getByLabel('Import borrowing scenario JSON',{exact:true}).setInputFiles({name:'invalid-time.json',mimeType:'application/json',buffer:Buffer.from(invalid)});
  await expect(editor.getByRole('alert')).toContainText('timezone');
  expect((await(await page.request.get('/api/jobs')).json()).length).toBe(before);
  await page.screenshot({path:info.outputPath('borrow-invalid-import.png'),fullPage:true});
  await editor.getByRole('button',{name:'Add changing borrowing scenario',exact:true}).click();
  const name='Borrow scenario '+info.project.name+' <img src=x onerror=globalThis.borrowProbe=1>';
  await page.getByLabel('Borrow scenario name',{exact:true}).fill(name);
  await page.getByRole('combobox',{name:'Borrowing assumption type',exact:true}).selectOption('synthetic');
  await page.getByLabel('I reviewed borrowing coverage for every declared instrument and date',{exact:true}).check();
  await page.getByLabel('Borrowing note',{exact:true}).fill('Authored weekend recall and rate scenario. These lending conditions are not historical observations.');
  const events=[['2022-01-21T14:31','10',false],['2022-01-22T14:30','30',true],['2022-01-23T14:30','10',false]] as const;
  for(let i=0;i<events.length;i++){
    await editor.getByRole('button',{name:'Add borrow event',exact:true}).click();
    await page.getByLabel('Borrow event instrument '+(i+1),{exact:true}).fill('MSFT');
    await page.getByLabel('Borrow event UTC time '+(i+1),{exact:true}).fill(events[i][0]);
    await page.getByLabel('Borrow event annual percent '+(i+1),{exact:true}).fill(events[i][1]);
    if(events[i][2])await page.getByLabel('Borrow event recall '+(i+1),{exact:true}).check();
  }
  await page.getByLabel('Borrow event annual percent 1',{exact:true}).fill('');
  const blankRejected=page.waitForResponse(r=>r.url().endsWith('/api/borrow-scenarios/validate')&&r.request().method()==='POST');
  await editor.getByRole('button',{name:'Apply borrowing scenario',exact:true}).click();expect((await blankRejected).status()).toBe(422);
  await expect(editor.getByRole('alert')).toContainText('number');
  await expect(editor.getByRole('link',{name:'Download borrowing scenario JSON',exact:true})).toHaveCount(0);
  await page.getByLabel('Borrow event annual percent 1',{exact:true}).fill('10');
  const validated=page.waitForResponse(r=>r.url().endsWith('/api/borrow-scenarios/validate')&&r.request().method()==='POST');
  await editor.getByRole('button',{name:'Apply borrowing scenario',exact:true}).click();const validatedResponse=await validated;expect(validatedResponse.status()).toBe(200);
  const frozen=(await validatedResponse.json()).scenario;expect(frozen.events[1].recall).toBe(true);expect(frozen.events[1].available).toBe(false);expect(frozen.events[2].available).toBe(true);
  await expect(editor.getByRole('status')).toContainText('Applied borrowing scenario');
  const scenarioDownload=page.waitForEvent('download');await editor.getByRole('link',{name:'Download borrowing scenario JSON',exact:true}).click();
  const scenarioPath=info.outputPath('downloaded-borrow-scenario.json');await(await scenarioDownload).saveAs(scenarioPath);expect(JSON.parse(await readFile(scenarioPath,'utf8'))).toEqual(frozen);
  await page.getByLabel('Import borrowing scenario JSON',{exact:true}).setInputFiles(scenarioPath);
  await expect(editor.getByRole('status')).toContainText('Applied borrowing scenario');
  await page.screenshot({path:info.outputPath('borrow-applied-editor.png'),fullPage:true});
  await page.getByLabel('Experiment name',{exact:true}).fill('Borrow scenario '+info.project.name);
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run single configuration',exact:true}).click();const job=await(await queued).json();expect(job.id).toMatch(/^[a-f0-9]{32}$/);
  await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+job.id)).json()).status,{timeout:180000}).toBe('completed');
  const stored=await(await page.request.get('/api/jobs/'+job.id)).json();expect(stored.payload.costs.borrow_scenario).toEqual(frozen);
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();expect(report.costs.borrow_scenario).toEqual(frozen);expect(report.trades.length).toBeGreaterThan(0);
  const recalls=report.trades.filter((t:any)=>t.exit_reason==='borrow_recall');expect(recalls.length).toBeGreaterThan(0);
  expect(recalls.every((t:any)=>t.side===-1&&t.symbol==='MSFT'&&t.exit_at==='2022-01-24T14:30:00+00:00'&&t.borrow>0)).toBe(true);
  const row=page.locator('tbody tr').filter({has:page.getByText(job.id.slice(0,10),{exact:true})});await row.getByRole('button',{name:'Open results',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Results',exact:true,level:1})).toBeVisible();
  await expect(page.getByRole('region',{name:'Saved short borrowing scenario',exact:true})).toContainText(name);
  await page.getByRole('button',{name:'05 Trade inspector',exact:true}).click();
  const saved=page.getByRole('region',{name:'Saved short borrowing scenario',exact:true});await expect(saved).toContainText('Synthetic lending scenario');await expect(saved).toContainText(name);
  await page.locator('.trades-table tbody tr').filter({hasText:'Borrow recall'}).getByRole('button',{name:'Inspect trade',exact:true}).first().click();
  await expect(page.getByRole('heading',{name:'Trade cash ledger',exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('borrow-recall-trade-and-ledger.png'),fullPage:true});
  await page.getByRole('button',{name:'07 Reports',exact:true}).click();await expect(page.getByRole('region',{name:'Saved short borrowing scenario',exact:true})).toContainText(name);
  expect(await page.evaluate(()=>(globalThis as any).borrowProbe)).toBeUndefined();expect(await page.locator('img[onerror]').count()).toBe(0);
  const jsonDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download full JSON evidence',exact:true}).click();
  const jsonPath=info.outputPath('downloaded-borrow-account.json');await(await jsonDownload).saveAs(jsonPath);expect(JSON.parse(await readFile(jsonPath,'utf8'))).toEqual(report);
  const htmlDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download current presentation',exact:true}).click();
  const htmlPath=info.outputPath('borrow-presentation.html');await(await htmlDownload).saveAs(htmlPath);
  // Close the polling workspace before measuring the standalone file's network activity.
  const workspacePage=page;page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await workspacePage.close();
  await context.setOffline(true);const network:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await page.goto(pathToFileURL(htmlPath).href);const deck=JSON.parse((await page.locator('#presentation-manifest').textContent())!);
  for(let i=0;i<frozen.events.length;i++)for(const field of ['symbol','effective_at','annual_rate','available','recall'])
    expect(Object.values(deck.facts).some((f:any)=>f.path.join('.')==='costs.borrow_scenario.events.'+i+'.'+field)).toBe(true);
  const layouts=[];
  for(let n=0;n<deck.pages.length;n++){
    if(n)await page.keyboard.press('ArrowRight');await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
    const issues=await page.evaluate(()=>{const r=document.getElementById('stage')!.getBoundingClientRect(),s=r.width/1920,issues:string[]=[];
      for(const e of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){const b=e.getBoundingClientRect();if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('outside stage');if(b.right>r.x+1400*s+.5&&b.bottom>r.y+712*s+.5)issues.push('camera overlap');}
      const c=document.querySelector<HTMLElement>('.concept');if(c&&c.getBoundingClientRect().bottom>r.y+820*s+.5)issues.push('concept overlaps conclusion');
      if(document.documentElement.scrollWidth>innerWidth)issues.push('horizontal scroll');return issues;});
    expect.soft(issues,'Borrow presenter page '+(n+1)).toEqual([]);layouts.push(issues);await page.screenshot({path:info.outputPath('borrow-presentation-'+(n+1)+'.png')});
  }
  expect(await page.evaluate(()=>(globalThis as any).borrowProbe)).toBeUndefined();expect(network).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('borrow-observations.json'),JSON.stringify({job_id:job.id,scenario:frozen,viewport:page.viewportSize(),browser:context.browser()?.version(),recalls:recalls.map((t:any)=>({id:t.id,entry_at:t.entry_at,exit_at:t.exit_at,borrow:t.borrow})),
    trades:report.trades.length,net_profit:report.metrics.net_profit,pages:deck.pages.length,facts:Object.keys(deck.facts).length,layouts,networkRequests:network,consoleErrors:errors,
    scope:'Real cached historical equity run with authored synthetic lending assumptions; no assertion that historical borrow availability or recall was observed.'},null,2));
});
