import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

async function openForm(page:any){
  await page.goto('/');await page.waitForLoadState('networkidle');
  await page.getByRole('navigation',{name:'Research sections'}).getByRole('button',{name:/^(03 )?Experiments$/}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(process.env.PA_SPREAD_DATASET!);
  await page.getByLabel('Start date',{exact:true}).fill('2026-10-19');
  await page.getByLabel('End date',{exact:true}).fill('2026-10-30');
  return page.getByRole('region',{name:'Balanced spread workflow',exact:true});
}
test('real primary qualification, frozen account continuation, reopening and complete offline exports',async({page},info)=>{
  test.setTimeout(300000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  let form=await openForm(page);
  await expect(form.getByRole('link',{name:'AI Pathways source video',exact:true})).toHaveAttribute('href','https://www.youtube.com/watch?v=z97PnFIPoFg');
  await expect(form.getByRole('checkbox',{name:/^Spread setup /})).toHaveCount(10);
  await expect(form.getByRole('checkbox',{name:/^Spread chart /})).toHaveCount(6);
  await form.getByRole('button',{name:'Preview spread work',exact:true}).click();
  await expect(form.getByLabel('Spread work preview')).toContainText('40,000 selected versions requested');
  await expect(form.getByLabel('Spread work preview')).toContainText('32,000,000 proposed variations');
  await form.getByRole('button',{name:'Use small functional run',exact:true}).click();
  await expect(form.getByRole('button',{name:'Freeze and qualify spread',exact:true})).toBeDisabled();
  await form.getByLabel('Spread primary instrument',{exact:true}).selectOption('SPY');
  await page.getByLabel('Experiment name',{exact:true}).fill('Synthetic spread '+info.project.name);
  await form.getByRole('button',{name:'Preview spread work',exact:true}).click();
  await expect(form.getByLabel('Spread work preview')).toContainText('1 selected versions requested');
  const created=page.waitForResponse((r:any)=>r.url().endsWith('/api/spreads')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Freeze and qualify spread',exact:true}).click();
  const response=await created;expect(response.status()).toBe(202);const parent=await response.json();
  await expect.poll(async()=>{const s=await(await page.request.get('/api/spreads/'+parent.id)).json();return s.job.status+':'+s.spread.stage;},{timeout:120000,intervals:[1000]}).toBe('completed:qualified');
  await expect(form.getByRole('button',{name:'Simulate frozen cohort',exact:true})).toBeVisible({timeout:15000});
  const selected=await(await page.request.get('/api/spreads/'+parent.id+'/selections')).json();
  expect(selected.selected_count).toBe(1);expect(selected.versions[0].signal_count).toBeGreaterThanOrEqual(40);
  await expect(form.getByLabel('Saved selected rules')).toContainText(String(selected.versions[0].signal_count));
  // Change the current form; continuation must inherit the original parent instead.
  await form.getByLabel('Spread primary instrument',{exact:true}).selectOption('QQQ');
  await form.getByLabel('Spread minimum executed trades',{exact:true}).fill('999');
  const continuation=page.waitForResponse((r:any)=>r.url().endsWith('/spreads/'+parent.id+'/accounts')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Simulate frozen cohort',exact:true}).click();
  const continued=await continuation;expect(continued.status()).toBe(202);expect(continued.request().postDataJSON()).toEqual({});const child=await continued.json();
  await expect.poll(async()=>{const s=await(await page.request.get('/api/jobs/'+child.id)).json();return s.status;},{timeout:120000,intervals:[1000]}).toBe('completed');
  const originalResponse=await page.request.get('/api/jobs/'+parent.id+'/inputs');const original=await originalResponse.json();
  const inputsResponse=await page.request.get('/api/jobs/'+child.id+'/inputs');const inputs=await inputsResponse.json();
  expect(inputs.payload.evaluation_symbols).toEqual(['SPY']);expect(inputs.payload.minimum_trades).toBe(original.payload.minimum_trades);expect(inputs.payload.minimum_trades).not.toBe(999);
  expect(inputs.payload.costs).toEqual(original.payload.costs);expect(inputs.payload.portfolio).toEqual(original.payload.portfolio);
  const summaryResponse=await page.request.get('/api/jobs/'+child.id+'/result');const summary=await summaryResponse.json();
  expect(summary.search_screen.accounts).toHaveLength(1);expect(summary.search_screen.accounts[0].net_profit).toBeLessThan(0);
  // Preserve original JSON number representations for independent hash audits.
  await writeFile(info.outputPath('parent-original-inputs.json'),await originalResponse.body());
  await writeFile(info.outputPath('child-original-inputs.json'),await inputsResponse.body());
  await writeFile(info.outputPath('complete-account-result.json'),await summaryResponse.body());
  await writeFile(info.outputPath('original-selected-page.json'),JSON.stringify(selected,null,2));
  await form.getByRole('button',{name:'Open saved account results',exact:true}).click();
  await expect(page.getByRole('region',{name:'Search-bias sensitivity',exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('spread-account-results.png'),fullPage:true});
  for(const name of ['search-statistics','search-screen'])for(const format of ['json','csv']){
    const r=await page.request.get('/api/jobs/'+child.id+'/'+name+'/export/'+format);expect(r.status()).toBe(200);
    await writeFile(info.outputPath(name+'.'+format),await r.body());
  }
  const report=await page.request.get('/api/jobs/'+child.id+'/report?part=0');expect(report.status()).toBe(200);
  const account=await report.json();expect(account.trades.length).toBeGreaterThan(0);expect(account.trades.every((t:any)=>t.symbol==='SPY')).toBe(true);
  await writeFile(info.outputPath('complete-part-account.json'),await report.body());
  const csv=await page.request.get('/api/jobs/'+child.id+'/export/csv?part=0');expect(csv.status()).toBe(200);await writeFile(info.outputPath('complete-trades.csv'),await csv.body());
  const html=await page.request.get('/api/jobs/'+child.id+'/export/html');expect(html.status()).toBe(200);const htmlPath=info.outputPath('spread-search-presentation.html');await writeFile(htmlPath,await html.body());
  // Reload app; bounded parent metadata must link the same original child.
  form=await openForm(page);await form.getByLabel('Reopen recent spread',{exact:true}).selectOption(parent.id);
  await expect(form.getByLabel('Original spread account job')).toContainText(child.id);
  await expect(form.getByRole('button',{name:'Simulate frozen cohort',exact:true})).toHaveCount(0);
  await form.getByRole('button',{name:'Refresh selected rules',exact:true}).click();
  await expect(form.getByLabel('Saved selected rules')).toContainText('1 selected in this saved snapshot');
  // UI fault injection only: original backend metadata remains intact. Actual
  // missing-cache reconstruction is tested separately against SQLite originals.
  await page.route('**/api/spreads/'+parent.id,route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Owned saved-status read failure.'})}));
  await form.getByRole('button',{name:'Retry saved spread status',exact:true}).click();
  await expect(form.getByRole('alert')).toContainText('Owned saved-status read failure.');
  await expect(form.getByRole('button',{name:'Simulate frozen cohort',exact:true})).toHaveCount(0);
  await page.unroute('**/api/spreads/'+parent.id);
  const verified=page.waitForResponse(r=>r.url().endsWith('/spreads/'+parent.id+'/repair-account-link')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Verify original account link',exact:true}).click();
  const verifiedResponse=await verified;expect(verifiedResponse.status()).toBe(200);expect(verifiedResponse.request().postDataJSON()).toEqual({});
  expect((await verifiedResponse.json()).account_job.id).toBe(child.id);
  await expect(form.getByLabel('Original spread account job')).toContainText(child.id);await expect(form.getByRole('alert')).toHaveCount(0);
  await form.screenshot({path:info.outputPath('spread-reopened-original-child.png')});
  const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));expect(overflow.scroll).toBeLessThanOrEqual(overflow.width+1);
  const requests:string[]=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(pathToFileURL(htmlPath).href);await expect(page.locator('#presentation-manifest')).toHaveCount(1);expect(requests).toEqual([]);
  expect(errors).toEqual([]);
});

test('validation and a flat primary exhausted cohort never authorize accounts',async({page},info)=>{
  test.setTimeout(180000);const form=await openForm(page);let posts=0;
  page.on('request',r=>{if(r.url().endsWith('/api/spreads')&&r.method()==='POST')posts++;});
  await form.getByRole('button',{name:'Use small functional run',exact:true}).click();
  await form.getByLabel('Spread proposals per batch',{exact:true}).fill('401');
  await form.getByRole('button',{name:'Preview spread work',exact:true}).click();
  await expect(form.getByRole('alert')).toContainText('whole number from 1 to 400');expect(posts).toBe(0);
  await form.getByLabel('Spread proposals per batch',{exact:true}).fill('40');
  // One genuine flat-primary probe is sufficient for this exhaustion contract.
  // The earlier retained run already exercised all 80 frozen proposals per viewport.
  await form.getByLabel('Spread proposals per batch',{exact:true}).fill('1');
  await form.getByLabel('Spread maximum batches per family',{exact:true}).fill('1');
  await form.getByLabel('Spread primary instrument',{exact:true}).selectOption('QQQ');
  await form.getByRole('button',{name:'Preview spread work',exact:true}).click();
  await expect(form.getByRole('button',{name:'Freeze and qualify spread',exact:true})).toBeEnabled();
  const creation=page.waitForResponse(r=>r.url().endsWith('/api/spreads')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Freeze and qualify spread',exact:true}).click();const parent=await(await creation).json();
  await expect.poll(async()=>{const s=await(await page.request.get('/api/spreads/'+parent.id)).json();return s.spread.stage;},{timeout:120000}).toBe('exhausted');
  await expect(form).toContainText('The frozen budget was exhausted.');await expect(form.getByRole('button',{name:'Simulate frozen cohort',exact:true})).toHaveCount(0);
  const selected=await(await page.request.get('/api/spreads/'+parent.id+'/selections')).json();expect(selected.selected_count).toBe(0);expect(selected.versions).toEqual([]);
  await writeFile(info.outputPath('exhausted-original-parent.json'),JSON.stringify(await(await page.request.get('/api/spreads/'+parent.id)).json(),null,2));
  await form.screenshot({path:info.outputPath('spread-exhausted-no-account.png')});expect(posts).toBe(1);
});
