import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {captureTradeChart} from './chartCapture';

test('matched historical random accounts preserve sample and expose actual trade evidence',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready&&h.source_current;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByLabel('Experiment name',{exact:true}).fill('Random controls browser '+info.project.name);
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  const panel=page.getByRole('region',{name:'Matched random controls',exact:true});
  await panel.getByRole('spinbutton',{name:'Random control accounts',exact:true}).fill('2');
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/controls')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Run matched random controls',exact:true}).click();
  const job=await(await queued).json();
  await expect.poll(async()=>['completed','failed','canceled'].includes((await(await page.request.get('/api/jobs/'+job.id)).json()).status),{timeout:180000}).toBe(true);
  const final=await(await page.request.get('/api/jobs/'+job.id)).json();expect(final.status,final.error).toBe('completed');
  await expect(panel.getByTestId('random-controls-output')).toBeVisible();
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();
  expect(report.report_type).toBe('matched_random_controls');expect(report.matching.matched_count).toBeGreaterThan(0);
  expect(report.matching.source_count).toBe(report.matching.matched_count+report.matching.unmatched.length);
  expect(report.books).toHaveLength(4);
  for(const replica of report.matching.replicas){
    expect(replica.matches.map((m:any)=>m.source_id).sort()).toEqual([...report.matching.matched_source_ids].sort());
    expect(new Set(replica.matches.map((m:any)=>m.candidate_key)).size).toBe(report.matching.matched_count);
  }
  await expect(panel.getByTestId('matching-counts')).toContainText(String(report.matching.matched_count));
  const random=report.books.find((r:any)=>r.role==='random_control'&&r.metrics.trades>0);expect(random).toBeTruthy();
  const selected=await(await page.request.get('/api/jobs/'+job.id+'/report?part='+random.part)).json();
  await panel.getByRole('button',{name:'Inspect random account '+(random.replica+1),exact:true}).click();
  await expect(panel.getByTestId('control-book')).toHaveAttribute('data-role','random_control');
  await expect(panel.locator('.candles')).toHaveAttribute('data-trade-id',selected.trades[0].id);
  const captures=['controls-validation','controls-panel'];
  await page.mouse.move(0,0);await page.screenshot({path:info.outputPath('controls-validation.png'),fullPage:true});
  await panel.screenshot({path:info.outputPath('controls-panel.png')});
  const geometry=await captureTradeChart(page,info,'control-trade-chart');
  const rootDownload=page.waitForEvent('download');await panel.getByRole('link',{name:'Download control-study JSON',exact:true}).click();
  await(await rootDownload).saveAs(info.outputPath('control-study.json'));
  expect(JSON.parse(await readFile(info.outputPath('control-study.json'),'utf8'))).toEqual(report);
  const accountDownload=page.waitForEvent('download');await panel.getByRole('link',{name:'Download selected account JSON',exact:true}).click();
  await(await accountDownload).saveAs(info.outputPath('control-account.json'));
  expect(JSON.parse(await readFile(info.outputPath('control-account.json'),'utf8'))).toEqual(selected);
  const csvDownload=page.waitForEvent('download');await panel.getByRole('link',{name:'Download selected account CSV',exact:true}).click();
  await(await csvDownload).saveAs(info.outputPath('control-trades.csv'));
  expect(await readFile(info.outputPath('control-trades.csv'),'utf8')).toBe(await(await page.request.get('/api/jobs/'+job.id+'/export/csv?part='+random.part)).text());
  // Delay a genuine account response while selecting another completed study.
  // It must not populate the newly selected study with the old account.
  const other=(await(await page.request.get('/api/jobs')).json()).find((j:any)=>j.kind==='controls'&&j.status==='completed'&&j.id!==job.id);
  expect(other,'Run the required default20-account fixture before this recovery journey.').toBeTruthy();
  let release:()=>void=()=>{},received:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{release=resolve;}),seen=new Promise<void>(resolve=>{received=resolve;});
  const accountUrl='**/api/jobs/'+job.id+'/report?part='+random.part;
  await page.route(accountUrl,async route=>{const response=await route.fetch();received();await held;await route.fulfill({response});});
  await panel.getByRole('button',{name:'Inspect random account '+(random.replica+1),exact:true}).click();await seen;
  const otherLoaded=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+other.id+'/report'));
  await panel.getByRole('combobox',{name:'Saved random-control job',exact:true}).selectOption(other.id);
  await otherLoaded;await expect(panel.getByTestId('random-controls-output')).toHaveAttribute('data-job-id',other.id);
  const lateResponse=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+job.id+'/report?part='+random.part));
  release();await lateResponse;
  await page.evaluate(()=>new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve()))));
  await expect(panel.getByTestId('control-book')).toHaveCount(0);
  await page.unroute(accountUrl);
  await page.reload();await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await panel.getByRole('combobox',{name:'Saved random-control job',exact:true}).selectOption(job.id);
  await expect(panel.getByTestId('random-controls-output')).toBeVisible();
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:job.id,browser:await page.context().browser()?.version(),
    viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),core_hash:report.core_hash,
    matched_sources:report.matching.matched_count,source_count:report.matching.source_count,selected_part:random.part,
    selected_trades:selected.trades.length,selected_ledger_events:selected.ledger.length,captures,chart_geometry:geometry,
    console_errors:errors,job_elapsed_seconds:final.updated-final.created,
    scope:'Two actual historical random accounts plus full/matched real accounts, delayed-response selection recovery. Default20-account and final acceptance gates remain separate.'},null,2));
});
