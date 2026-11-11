import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';

test('historical strategy compares with cash and passive holdings through saved evidence',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready&&h.source_current;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByLabel('Experiment name',{exact:true}).fill('Benchmark journey '+info.project.name);
  const created=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run single configuration',exact:true}).click();
  const strategyJob=await(await created).json();
  async function complete(id:string){
    await expect.poll(async()=>['completed','failed','canceled'].includes((await(await page.request.get('/api/jobs/'+id)).json()).status),{timeout:180000}).toBe(true);
    const final=await(await page.request.get('/api/jobs/'+id)).json();expect(final.status,final.error).toBe('completed');return final;
  }
  await complete(strategyJob.id);
  await page.locator('tbody tr').filter({has:page.getByText(strategyJob.id.slice(0,10),{exact:true})}).getByRole('button',{name:'Open results',exact:true}).click();
  const strategy=await(await page.request.get('/api/jobs/'+strategyJob.id+'/report')).json();
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  const panel=page.getByRole('region',{name:'Cash and buy-and-hold benchmarks',exact:true});
  await panel.getByRole('button',{name:"Use open strategy's inputs",exact:true}).click();
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/benchmarks')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Run cash and buy-and-hold',exact:true}).click();
  const job=await(await queued).json();const final=await complete(job.id);
  await expect(panel.getByTestId('benchmark-output')).toBeVisible();
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();
  expect(report.report_type).toBe('passive_benchmarks');
  const passive=report.benchmarks.buy_hold,cash=report.benchmarks.cash;
  expect(passive.trades).toHaveLength(5);expect(passive.equity).toHaveLength(20);
  expect(cash.metrics.net_profit).toBe(0);
  expect(cash.equity.map((d:any)=>d.date)).toEqual(strategy.equity.map((d:any)=>d.date));
  expect(report.portfolio).toEqual(strategy.portfolio);expect(report.costs).toEqual(strategy.costs);
  expect(Math.abs(passive.trades.reduce((s:number,t:any)=>s+t.net_pnl,0)-passive.metrics.net_profit)).toBeLessThan(1e-7);
  const delta=strategy.metrics.net_profit-passive.metrics.net_profit;
  const formatted=delta.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
  await expect(panel.getByTestId('benchmark-delta')).toContainText(formatted);
  await panel.scrollIntoViewIfNeeded();await page.mouse.move(0,0);
  await page.screenshot({path:info.outputPath('benchmark-validation.png'),fullPage:true});
  await panel.screenshot({path:info.outputPath('benchmark-panel.png')});
  const download=page.waitForEvent('download');
  await panel.getByRole('link',{name:'Download benchmark JSON',exact:true}).click();
  await(await download).saveAs(info.outputPath('benchmark-report.json'));
  expect(JSON.parse(await readFile(info.outputPath('benchmark-report.json'),'utf8'))).toEqual(report);
  const csv=page.waitForEvent('download');
  await panel.getByRole('link',{name:'Download passive trade CSV',exact:true}).click();
  await(await csv).saveAs(info.outputPath('benchmark-trades.csv'));
  expect(await readFile(info.outputPath('benchmark-trades.csv'),'utf8')).toBe(await(await page.request.get('/api/jobs/'+job.id+'/export/csv')).text());
  // An actual different-capital benchmark must not acquire a strategy delta.
  await page.getByRole('button',{name:'03 Experiments',exact:true}).click();
  await page.getByText('Capital and sizing assumptions',{exact:true}).click();
  await page.getByRole('spinbutton',{name:'Capital',exact:true}).fill('50000');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  const mismatched=page.waitForResponse(r=>r.url().endsWith('/api/benchmarks')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Run cash and buy-and-hold',exact:true}).click();
  const other=await(await mismatched).json();await complete(other.id);
  await expect(panel.getByTestId('benchmark-output')).toBeVisible();
  await expect(panel.getByTestId('benchmark-delta')).toHaveCount(0);
  const incompatible=await(await page.request.get('/api/jobs/'+other.id+'/report')).json();
  expect(incompatible.portfolio.capital).toBe(50000);expect(strategy.portfolio.capital).toBe(100000);
  await writeFile(info.outputPath('incompatible-report.json'),JSON.stringify(incompatible,null,2));
  // Saved benchmark remains available after an actual document reload.
  await page.reload();await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await page.getByRole('combobox',{name:'Saved benchmark job',exact:true}).selectOption(job.id);
  await expect(panel.getByTestId('benchmark-output')).toBeVisible();
  await expect(panel.getByTestId('benchmark-delta')).toHaveCount(0);
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:job.id,strategy_job_id:strategyJob.id,
    incompatible_job_id:other.id,browser:await page.context().browser()?.version(),viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),
    core_hash:report.core_hash,dataset_id:report.dataset_id,net_profit:passive.metrics.net_profit,delta,
    trades:passive.trades.length,equity_points:passive.equity.length,ledger_events:passive.ledger.length,
    console_errors:errors,job_elapsed_seconds:final.updated-final.created,
    captures:['benchmark-validation.png','benchmark-panel.png'],
    scope:'Actual historical single-strategy and passive comparison flows; not full acceptance certification.'},null,2));
});
