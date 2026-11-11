import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {captureTradeChart} from './chartCapture';

test('paired historical accounts and complete trial history survive exports and late responses',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await expect.poll(async()=>{try{const h=await(await page.request.get('/api/health')).json();return h.worker_ready&&h.source_current;}catch{return false;}},{timeout:60000}).toBe(true);
  await page.goto('/');await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption('90f347229b2fb03ec112ee71');
  const panel=page.getByRole('region',{name:'Paired rule comparisons',exact:true}),ledger=page.getByRole('region',{name:'Research trial ledger',exact:true});
  await expect(panel.getByRole('checkbox',{name:'Compare target 2R',exact:true})).toBeChecked();
  await expect(panel.getByRole('checkbox',{name:'Compare target 3R',exact:true})).toBeChecked();
  async function queue(){const response=page.waitForResponse(r=>r.url().endsWith('/api/ablations')&&r.request().method()==='POST');await panel.getByRole('button',{name:'Run paired rule comparison',exact:true}).click();const r=await response;expect(r.status(),await r.text()).toBe(202);return r.json();}
  async function complete(id:string){await expect.poll(async()=>['completed','failed','canceled'].includes((await(await page.request.get('/api/jobs/'+id)).json()).status),{timeout:180000}).toBe(true);const j=await(await page.request.get('/api/jobs/'+id)).json();expect(j.status,j.error).toBe('completed');return j;}
  const job=await queue();const final=await complete(job.id);
  await expect(panel.getByTestId('ablation-output')).toHaveAttribute('data-job-id',job.id);
  const report=await(await page.request.get('/api/jobs/'+job.id+'/report')).json();expect(report.arms).toHaveLength(3);expect(report.comparisons).toHaveLength(2);
  for(const arm of report.arms){await panel.getByRole('button',{name:arm.part===0?'Inspect baseline':'Inspect alternative '+arm.part,exact:true}).click();await expect(panel.getByTestId('ablation-account')).toHaveAttribute('data-part',String(arm.part));}
  const part=report.arms[1].part;await panel.getByRole('button',{name:'Inspect alternative '+part,exact:true}).click();
  const book=await(await page.request.get('/api/jobs/'+job.id+'/report?part='+part)).json();expect(book.trades.length).toBeGreaterThan(0);
  const chartGeometry=await captureTradeChart(page,info,'ablation-trade-chart');
  async function download(name:string,filename:string){const event=page.waitForEvent('download');await panel.getByRole('link',{name,exact:true}).click();await(await event).saveAs(info.outputPath(filename));}
  await download('Download comparison JSON','ablation-study.json');expect(JSON.parse(await readFile(info.outputPath('ablation-study.json'),'utf8'))).toEqual(report);
  await download('Download comparison CSV','ablation-comparisons.csv');expect(await readFile(info.outputPath('ablation-comparisons.csv'),'utf8')).toBe(await(await page.request.get('/api/jobs/'+job.id+'/export/csv')).text());
  await download('Download selected rule-account JSON','ablation-account.json');expect(JSON.parse(await readFile(info.outputPath('ablation-account.json'),'utf8'))).toEqual(book);
  await download('Download selected rule-account CSV','ablation-account-trades.csv');
  await panel.screenshot({path:info.outputPath('ablation-panel.png')});
  await page.getByRole('button',{name:'02 Strategies',exact:true}).click();await page.getByRole('combobox',{name:'Entry',exact:true}).selectOption('limit');
  await page.getByRole('button',{name:'06 Validation',exact:true}).click();await panel.getByRole('combobox',{name:'Rule to vary',exact:true}).selectOption('limit_expiry');
  await panel.getByRole('textbox',{name:'Alternative numeric values',exact:true}).fill('1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13');
  const numeric=await queue();await complete(numeric.id);await expect(panel.getByTestId('ablation-output')).toHaveAttribute('data-job-id',numeric.id);
  const numericReport=await(await page.request.get('/api/jobs/'+numeric.id+'/report')).json();expect(numericReport.arms).toHaveLength(13);
  await writeFile(info.outputPath('numeric-ablation-study.json'),JSON.stringify(numericReport,null,2));
  await panel.getByRole('button',{name:"Show this study's trial records",exact:true}).click();
  await expect(ledger.getByTestId('trial-ledger-output')).toHaveAttribute('data-job-id',numeric.id);
  await ledger.getByRole('combobox',{name:'Trial ledger page size',exact:true}).selectOption('10');
  await expect(ledger.getByTestId('trial-occurrences').locator('tbody tr')).toHaveCount(10);
  await ledger.getByRole('button',{name:'Next trial page',exact:true}).click();await expect(ledger.getByTestId('trial-occurrences').locator('tbody tr')).toHaveCount(3);
  const ledgerResponse=await(await page.request.get('/api/trial-registry?job_id='+numeric.id+'&limit=200')).json();expect(ledgerResponse.totals.computation_attempts).toBe(13);
  expect(ledgerResponse.rows.every((r:any)=>r.state==='completed'&&r.attempts===1&&r.provenance==='prespecified'&&r.artifact_sha256)).toBe(true);
  for(const [name,filename] of [['Download complete job trial JSON','trial-ledger.json'],['Download complete job trial CSV','trial-ledger.csv']]){
    const event=page.waitForEvent('download');await ledger.getByRole('link',{name,exact:true}).click();await(await event).saveAs(info.outputPath(filename));
  }
  const full=JSON.parse(await readFile(info.outputPath('trial-ledger.json'),'utf8'));expect(full.rows).toHaveLength(13);expect(full.occurrences).toBe(13);
  await ledger.screenshot({path:info.outputPath('trial-ledger-panel.png')});
  // Deliver genuine old account data after choosing a different saved study.
  await panel.getByRole('combobox',{name:'Saved rule-comparison job',exact:true}).selectOption(job.id);
  await expect(panel.getByTestId('ablation-output')).toHaveAttribute('data-job-id',job.id);
  let release:()=>void=()=>{},arrived:()=>void=()=>{};const gate=new Promise<void>(r=>release=r),waiting=new Promise<void>(r=>arrived=r);
  const pattern='**/api/jobs/'+job.id+'/report?part=0';await page.route(pattern,async route=>{const response=await route.fetch();arrived();await gate;await route.fulfill({response});});
  await panel.getByRole('button',{name:'Inspect baseline',exact:true}).click();await waiting;
  await panel.getByRole('combobox',{name:'Saved rule-comparison job',exact:true}).selectOption(numeric.id);
  const delivered=page.waitForResponse(r=>r.url().endsWith('/jobs/'+job.id+'/report?part=0'));release();await delivered;
  await expect(panel.getByTestId('ablation-output')).toHaveAttribute('data-job-id',numeric.id);await expect(panel.getByTestId('ablation-account')).toHaveCount(0);await page.unroute(pattern);
  await page.reload();await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  await panel.getByRole('combobox',{name:'Saved rule-comparison job',exact:true}).selectOption(job.id);await expect(panel.getByTestId('ablation-output')).toHaveAttribute('data-job-id',job.id);
  await panel.getByRole('button',{name:"Show this study's trial records",exact:true}).click();await expect(ledger.getByTestId('trial-ledger-output')).toHaveAttribute('data-job-id',job.id);
  // A genuine old filtered ledger response must not repopulate all-history.
  let releaseLedger:()=>void=()=>{},ledgerArrived:()=>void=()=>{};
  const ledgerGate=new Promise<void>(r=>releaseLedger=r),ledgerWaiting=new Promise<void>(r=>ledgerArrived=r);
  const ledgerPattern='**/api/trial-registry?*job_id='+job.id;
  await page.route(ledgerPattern,async route=>{const response=await route.fetch();ledgerArrived();await ledgerGate;await route.fulfill({response});});
  await ledger.getByRole('combobox',{name:'Trial ledger page size',exact:true}).selectOption('10');await ledgerWaiting;
  await ledger.getByRole('button',{name:'Show all trial history',exact:true}).click();releaseLedger();
  await expect(ledger.getByTestId('trial-ledger-output')).toHaveAttribute('data-job-id','');await page.unroute(ledgerPattern);
  await ledger.getByRole('combobox',{name:'Trial ledger page size',exact:true}).selectOption('20');
  await ledger.getByRole('button',{name:'Show all trial history',exact:true}).click();await expect(ledger.getByTestId('trial-ledger-output')).toHaveAttribute('data-job-id','');
  await expect(ledger.getByRole('button',{name:'Next trial page',exact:true})).toBeEnabled();await ledger.getByRole('button',{name:'Next trial page',exact:true}).click();
  await expect(ledger.getByTestId('trial-occurrences').locator('tbody tr')).toHaveCount(20);
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:job.id,numeric_job_id:numeric.id,selected_part:part,browser:await page.context().browser()?.version(),viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),core_hash:report.core_hash,dataset_id:report.dataset_id,chart_geometry:chartGeometry,console_errors:errors,job_elapsed_seconds:final.updated-final.created,captures:['ablation-panel.png','trial-ledger-panel.png','ablation-trade-chart.png'],scope:'Actual historical3-arm target study,13-arm limit-expiry study, every-arm inspection, full beyond-page ledger exports, delayed account response, reload and all-history pagination. Not final acceptance or trading-edge certification.'},null,2));
});
