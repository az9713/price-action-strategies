import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {captureTradeChart} from './chartCapture';

test('historical behavior diagnostics retain actual samples, uncertainty and saved records',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready&&h.source_current;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  const panel=page.getByRole('region',{name:'Price behavior experiments',exact:true});
  for(const frame of ['5m','15m','1h','4h','1d'])await expect(panel.getByRole('checkbox',{name:'Behavior '+frame,exact:true})).toBeChecked();
  await expect(panel.getByRole('checkbox',{name:'Behavior 1m',exact:true})).not.toBeChecked();
  await expect(panel.getByRole('spinbutton',{name:'Shifted stand-ins per feature',exact:true})).toHaveValue('20');
  for(const frame of ['5m','4h','1d'])await panel.getByRole('checkbox',{name:'Behavior '+frame,exact:true}).uncheck();
  await panel.getByRole('spinbutton',{name:'Shifted stand-ins per feature',exact:true}).fill('2');
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/behavior')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Run price behavior study',exact:true}).click();
  const created=await queued;expect(created.status()).toBe(202);const job=await created.json();
  await expect.poll(async()=>['completed','failed','canceled'].includes((await(await page.request.get('/api/jobs/'+job.id)).json()).status),{timeout:180000}).toBe(true);
  const final=await(await page.request.get('/api/jobs/'+job.id)).json();expect(final.status,final.error).toBe('completed');
  await expect(panel.getByTestId('behavior-output')).toHaveAttribute('data-job-id',job.id);
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();
  expect(report.report_type).toBe('price_behavior');expect(report.settings.timeframes).toEqual(['15m','1h']);expect(report.counts.real_touches).toBeGreaterThan(0);
  const keys=Object.keys(report.tables);expect(keys).toHaveLength(17);
  const csvFiles:string[]=[];
  for(const key of keys){
    await panel.getByRole('combobox',{name:'Behavior diagnostic',exact:true}).selectOption(key);
    for(const scope of ['pooled','timeframe','instrument','era']){
      await panel.getByRole('combobox',{name:'Behavior grouping',exact:true}).selectOption(scope);
      const expected=report.tables[key].rows.filter((r:any)=>r.scope===scope);
      await expect(panel.getByTestId('behavior-table').locator('tbody tr')).toHaveCount(expected.length);
      for(let i=0;i<expected.length;i++)await expect(panel.getByTestId('behavior-table').locator('tbody tr').nth(i)).toContainText(expected[i].status);
    }
    const download=page.waitForEvent('download');await panel.getByRole('link',{name:'Download diagnostic CSV',exact:true}).click();
    const filename='behavior-'+key+'.csv';await(await download).saveAs(info.outputPath(filename));csvFiles.push(filename);
    expect(await readFile(info.outputPath(filename),'utf8')).toBe(await(await page.request.get('/api/jobs/'+job.id+'/export/csv?table='+key)).text());
  }
  await panel.getByRole('combobox',{name:'Behavior diagnostic',exact:true}).selectOption('levels_vs_shifted');
  await panel.getByRole('combobox',{name:'Behavior grouping',exact:true}).selectOption('pooled');
  const root=page.waitForEvent('download');await panel.getByRole('link',{name:'Download behavior-study JSON',exact:true}).click();await(await root).saveAs(info.outputPath('behavior-study.json'));
  expect(JSON.parse(await readFile(info.outputPath('behavior-study.json'),'utf8'))).toEqual(report);
  await panel.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('behavior-validation.png'),fullPage:true});
  await panel.screenshot({path:info.outputPath('behavior-panel.png')});
  await panel.getByRole('button',{name:'Inspect 15m behavior chart',exact:true}).click();
  await expect(panel.getByTestId('behavior-chart')).toHaveAttribute('data-timeframe','15m');
  const chart=await(await page.request.get('/api/jobs/'+job.id+'/report?part=0')).json();
  await panel.getByRole('combobox',{name:'Behavior chart instrument',exact:true}).selectOption('SPY');
  const touches=chart.touches.filter((t:any)=>t.symbol==='SPY');expect(touches.length).toBeGreaterThan(0);
  await expect(panel.getByRole('combobox',{name:'Recorded behavior touch',exact:true}).locator('option')).toHaveCount(touches.length);
  await panel.getByRole('combobox',{name:'Recorded behavior touch',exact:true}).selectOption(String(touches.length-1));
  expect(JSON.parse(await panel.getByTestId('behavior-touch').innerText())).toEqual(touches.at(-1));
  await expect(page.locator('.candles')).toHaveAttribute('data-bar-count',String(chart.bars.SPY.length));
  const geometry=await captureTradeChart(page,info,'behavior-price-chart');
  const part=page.waitForEvent('download');await panel.getByRole('link',{name:'Download behavior-chart JSON',exact:true}).click();await(await part).saveAs(info.outputPath('behavior-chart.json'));
  expect(JSON.parse(await readFile(info.outputPath('behavior-chart.json'),'utf8'))).toEqual(chart);
  // Delay a genuine response, then deselect the study. The old chart must not
  // populate after selection changes, even though its response is successful.
  let release:()=>void=()=>{},arrived:()=>void=()=>{};
  const gate=new Promise<void>(r=>release=r),waiting=new Promise<void>(r=>arrived=r);
  const pattern='**/api/jobs/'+job.id+'/report?part=1';
  await page.route(pattern,async route=>{const response=await route.fetch();arrived();await gate;await route.fulfill({response});});
  await panel.getByRole('button',{name:'Inspect 1h behavior chart',exact:true}).click();await waiting;
  await panel.getByRole('combobox',{name:'Saved behavior job',exact:true}).selectOption('');
  const delivered=page.waitForResponse(r=>r.url().endsWith('/jobs/'+job.id+'/report?part=1'));release();await delivered;
  await expect(panel.getByTestId('behavior-output')).toHaveCount(0);await expect(panel.getByTestId('behavior-chart')).toHaveCount(0);
  await page.unroute(pattern);await page.reload();await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await panel.getByRole('combobox',{name:'Saved behavior job',exact:true}).selectOption(job.id);
  await expect(panel.getByTestId('behavior-output')).toHaveAttribute('data-job-id',job.id);
  await panel.getByRole('button',{name:'Inspect 1h behavior chart',exact:true}).click();await expect(panel.getByTestId('behavior-chart')).toHaveAttribute('data-timeframe','1h');
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:job.id,browser:await page.context().browser()?.version(),viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),core_hash:report.core_hash,dataset_id:report.dataset_id,counts:report.counts,tables:keys,csv_files:csvFiles,chart_geometry:geometry,console_errors:errors,job_elapsed_seconds:final.updated-final.created,captures:['behavior-validation.png','behavior-panel.png','behavior-price-chart.png'],scope:'Actual five-instrument historical two-chart/two-shift UI flow; default20/five-chart run is separate. Not final acceptance certification.'},null,2));
});
