import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
import {captureTradeChart} from './chartCapture';

test('cached historical experiment through real UI, worker, trade inspector and exports',async({page},info)=>{
  const consoleErrors:string[]=[];page.on('pageerror',e=>consoleErrors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready===true&&h.source_current===true;}catch{return false;}},
    {timeout:60000,message:'Wait for the actual local service and worker to be ready before browser actions.'}).toBe(true);
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Data',exact:true})).toBeVisible();
  await expect(page.getByText('90f347229b2fb03ec112ee71',{exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('data.png'),fullPage:true});
  await page.getByRole('button',{name:'02 Strategies',exact:true}).click();
  await expect(page.locator('.family-card')).toHaveCount(10);
  await page.getByLabel('Rule set name',{exact:true}).fill('Browser smoke '+info.project.name);
  await page.getByRole('button',{name:'Save rule set',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Saved as an immutable');
  await page.screenshot({path:info.outputPath('strategies.png'),fullPage:true});
  await page.getByRole('button',{name:'Use in experiment',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByLabel('Experiment name',{exact:true}).fill('Browser smoke '+info.project.name);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run single configuration',exact:true}).click();
  const created=await(await response).json();expect(['queued','running']).toContain(created.status);
  const row=page.locator('tbody tr').filter({has:page.getByText(created.id.slice(0,10),{exact:true})});
  // Functional completion has a bounded wait; this is not a performance pass.
  // Earlier 60-second failure and its actual 96-second completion are retained.
  await expect.poll(async()=>{
    const job=await(await page.request.get('/api/jobs/'+created.id)).json();
    return ['completed','failed','canceled'].includes(job.status);
  },{timeout:180000,message:'Wait for the actual background job to reach a terminal state.'}).toBe(true);
  const finishedJob=await(await page.request.get('/api/jobs/'+created.id)).json();
  expect(finishedJob.status,finishedJob.error||'Background job must complete successfully.').toBe('completed');
  await expect(row.getByText('Completed',{exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('experiment.png'),fullPage:true});
  await row.getByRole('button',{name:'Open results',exact:true}).click();
  await expect(page.locator('.metrics')).toBeVisible();
  const report=await(await page.request.get('/api/jobs/'+created.id+'/report')).json();
  expect(report.trades).toHaveLength(10);
  expect(new Set(report.trades.map((t:any)=>t.side))).toEqual(new Set([1,-1]));
  expect(Math.abs(report.trades.reduce((sum:number,t:any)=>sum+t.net_pnl,0)-report.metrics.net_profit)).toBeLessThan(1e-7);
  await expect(page.locator('.metrics>div').first()).toContainText(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(report.metrics.net_profit));
  await expect(page.locator('.recharts-surface')).toBeVisible();
  await page.screenshot({path:info.outputPath('results.png'),fullPage:true});
  await page.getByRole('button',{name:'05 Trade inspector',exact:true}).click();
  await expect(page.locator('.trades-table tbody tr')).toHaveCount(10);
  await expect(page.locator('.candles canvas').first()).toBeVisible();
  await page.getByRole('button',{name:'Inspect trade',exact:true}).last().click();
  await expect(page.getByRole('heading',{name:'Trade cash ledger',exact:true})).toBeVisible();
  await expect(page.locator('.candles')).toHaveAttribute('data-trade-id',report.trades.at(-1).id);
  await expect.poll(async()=>page.locator('.candles').evaluate(e=>Number((e as HTMLElement).dataset.visibleTo)-Number((e as HTMLElement).dataset.visibleFrom))).toBeLessThanOrEqual(50);
  const inspected=report.trades.at(-1);
  const exitBar=report.charts[inspected.symbol].filter((b:any)=>Date.parse(b.timestamp)<=Date.parse(inspected.exit_at)).at(-1);
  await expect.poll(async()=>Number(await page.locator('.candles').getAttribute('data-exit-price'))).toBeCloseTo(inspected.exit_price*exitBar.factor,8);
  const fit=page.getByRole('checkbox',{name:'Fit all trade levels',exact:true});
  await expect(fit).toBeChecked();
  for(const coordinate of ['stop','target'])await expect.poll(async()=>{
    const y=Number.parseFloat(await page.locator('.candles').getAttribute('data-'+coordinate+'-y')||'');return y>=0&&y<=350;
  }).toBe(true);
  const countBefore=await page.locator('.candles').getAttribute('data-bar-count');
  await fit.uncheck();await expect(page.locator('.candles')).toHaveAttribute('data-fit-levels','false');
  await expect(page.locator('.candles')).toHaveAttribute('data-bar-count',countBefore!);
  await expect(page.locator('.candles')).toHaveAttribute('data-trade-id',inspected.id);
  await fit.check();await expect(page.locator('.candles')).toHaveAttribute('data-fit-levels','true');
  const heading=page.locator('.trades-table th').first();
  expect(await heading.evaluate(e=>getComputedStyle(e).position)).toBe('sticky');
  const headerBox=await heading.boundingBox(),tableBox=await page.locator('.trades-table').boundingBox();
  expect(headerBox!.y).toBeGreaterThanOrEqual(tableBox!.y-1);
  expect(headerBox!.y+headerBox!.height).toBeLessThanOrEqual(tableBox!.y+65);
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:info.outputPath('trade-inspector.png'),fullPage:true});
  const chartGeometry=await captureTradeChart(page,info,'trade-chart');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Freeze a time-ordered study',exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('validation.png'),fullPage:true});
  await page.getByRole('button',{name:'07 Reports',exact:true}).click();
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download full JSON evidence',exact:true}).click();
  const download=await downloadPromise;const path=info.outputPath('downloaded-report.json');await download.saveAs(path);
  const exported=await(await page.request.get('/api/jobs/'+created.id+'/export/json')).json();
  expect(exported).toEqual(report);
  await page.screenshot({path:info.outputPath('reports.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(consoleErrors).toEqual([]);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:created.id,browser:await page.context().browser()?.version(),
    viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),
    dataset_id:report.dataset_id,net_profit:report.metrics.net_profit,trades:report.trades.length,
    equity_points:report.equity.length,ledger_events:report.ledger.length,consoleErrors,chart_captures:['trade-chart'],chart_geometry:{'trade-chart':chartGeometry},
    job_elapsed_seconds:finishedJob.updated-finishedJob.created,
    performance_status:'Measured observation only; PERF gates remain unverified.',
    scope:'One real cached historical flow, not the entire acceptance catalog.'},null,2));
});
