import {test,expect} from '@playwright/test';
import {writeFile,readFile} from 'node:fs/promises';
import {captureTradeChart} from './chartCapture';

test('two saved rules compete in one real historical portfolio account',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready&&h.source_current;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');
  await page.getByRole('button',{name:'02 Strategies',exact:true}).click();
  const saved:any[]=[];
  for(const [family,timeframe] of [['Change of character','1h'],['Break of structure','15m']]){
    await page.locator('.family-card').filter({has:page.getByText(family,{exact:true})}).click();
    const chart=page.getByRole('combobox',{name:'Timeframe',exact:true});
    await expect(chart).toBeVisible();
    await chart.selectOption(timeframe);
    const name='Portfolio '+family+' '+info.project.name;
    await page.getByLabel('Rule set name',{exact:true}).fill(name);
    const response=page.waitForResponse(r=>r.url().endsWith('/api/strategies')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Save rule set',exact:true}).click();
    saved.push(await(await response).json());
    await expect(page.getByRole('status')).toContainText('Saved as an immutable');
  }
  await page.getByRole('button',{name:'Use in experiment',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  await page.getByLabel('Experiment name',{exact:true}).fill('Shared-account browser '+info.project.name);
  for(const rule of saved)await page.getByRole('checkbox',{name:'Include '+rule.name+' '+rule.id.slice(0,8),exact:true}).check();
  const captures=['portfolio-inputs','portfolio-results','portfolio-reports'];
  const chartCaptures:string[]=[];
  const chartGeometry:Record<string,any>={};
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:info.outputPath('portfolio-inputs.png'),fullPage:true});
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/portfolios')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Run shared-capital portfolio',exact:true}).click();
  const job=await(await queued).json();expect(['queued','running']).toContain(job.status);
  await expect.poll(async()=>['completed','failed','canceled'].includes((await(await page.request.get('/api/jobs/'+job.id)).json()).status),{timeout:180000}).toBe(true);
  const finished=await(await page.request.get('/api/jobs/'+job.id)).json();expect(finished.status,finished.error).toBe('completed');
  const row=page.locator('tbody tr').filter({has:page.getByText(job.id.slice(0,10),{exact:true})});
  await row.getByRole('button',{name:'Open results',exact:true}).click();
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();
  expect(report.report_type).toBe('shared_capital_portfolio');expect(report.config).toBeNull();expect(report.configurations).toHaveLength(2);
  expect(new Set(report.configurations.map((c:any)=>c.config.timeframe))).toEqual(new Set(['1h','15m']));
  expect(report.attribution.every((a:any)=>a.signals>0&&a.trades>0)).toBe(true);
  expect(report.trades.length).toBeGreaterThan(1);
  expect(Math.abs(report.trades.reduce((n:number,t:any)=>n+t.net_pnl,0)-report.metrics.net_profit)).toBeLessThan(1e-7);
  expect(report.attribution.reduce((n:number,a:any)=>n+a.trades,0)).toBe(report.trades.length);
  await expect(page.getByText('Shared-capital portfolio · 2 rules · 2022-01-03 – 2022-01-31',{exact:true})).toBeVisible();
  await expect(page.locator('.portfolio-attribution tbody tr')).toHaveCount(2);
  await page.screenshot({path:info.outputPath('portfolio-results.png'),fullPage:true});
  await page.getByRole('button',{name:'05 Trade inspector',exact:true}).click();
  for(const rule of report.configurations){
    const trade=report.trades.filter((t:any)=>t.strategy_id===rule.config_id).at(-1);
    const index=report.trades.findIndex((t:any)=>t.id===trade.id);
    await page.locator('.trades-table tbody tr').nth(index).getByRole('button',{name:'Inspect trade',exact:true}).click();
    const bars=report.chart_sets[trade.strategy_id][trade.symbol];
    await expect(page.locator('.candles')).toHaveAttribute('data-trade-id',trade.id);
    await expect(page.locator('.candles')).toHaveAttribute('data-bar-count',String(bars.length));
    await expect(page.locator('.candles')).toHaveAttribute('data-first-bar-time',String(Math.floor(Date.parse(bars[0].timestamp)/1000)));
    const exitBar=bars.filter((b:any)=>Date.parse(b.timestamp)<=Date.parse(trade.exit_at)).at(-1);
    await expect.poll(async()=>Number(await page.locator('.candles').getAttribute('data-exit-price'))).toBeCloseTo(trade.exit_price*exitBar.factor,8);
    await expect(page.getByRole('checkbox',{name:'Fit all trade levels',exact:true})).toBeChecked();
    for(const coordinate of ['stop','target'])await expect.poll(async()=>{
      const y=Number.parseFloat(await page.locator('.candles').getAttribute('data-'+coordinate+'-y')||'');return y>=0&&y<=350;
    }).toBe(true);
    await page.evaluate(()=>window.scrollTo(0,0));
    const capture='portfolio-trade-'+rule.config_id.slice(0,10);captures.push(capture);
    await page.screenshot({path:info.outputPath(capture+'.png'),fullPage:true});
    const chart='chart-'+rule.config_id.slice(0,10);chartCaptures.push(chart);
    chartGeometry[chart]=await captureTradeChart(page,info,chart);
  }
  await page.getByRole('button',{name:'07 Reports',exact:true}).click();
  const downloading=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download full JSON evidence',exact:true}).click();
  await(await downloading).saveAs(info.outputPath('downloaded-report.json'));
  const csvDownload=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download trade CSV',exact:true}).click();
  const csvPath=info.outputPath('downloaded-trades.csv');await(await csvDownload).saveAs(csvPath);
  expect(await readFile(csvPath,'utf8')).toBe(await(await page.request.get('/api/jobs/'+job.id+'/export/csv')).text());
  await page.screenshot({path:info.outputPath('portfolio-reports.png'),fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:job.id,browser:await page.context().browser()?.version(),
    viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),dataset_id:report.dataset_id,
    report_type:report.report_type,net_profit:report.metrics.net_profit,trades:report.trades.length,equity_points:report.equity.length,
    ledger_events:report.ledger.length,consoleErrors:errors,job_elapsed_seconds:finished.updated-finished.created,
    captures,chart_captures:chartCaptures,chart_geometry:chartGeometry,csv_file:'downloaded-trades.csv',performance_status:'Functional observation only; scale/resource acceptance remains open.',
    scope:'Two selected rules and two chart clocks in a real shared-capital historical run, not full acceptance certification.'},null,2));
});
