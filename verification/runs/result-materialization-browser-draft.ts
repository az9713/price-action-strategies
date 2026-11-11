import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';

test('actual fifty-one-account result pages, diagnostic pages and original export retain exact identity',async({page},info)=>{
 test.setTimeout(240000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');const origin=new URL(page.url()).origin,session=await(await page.request.get('/api/session')).json(),schema=await(await page.request.get('/api/schema')).json();
 const defaults=(spec:any)=>Object.fromEntries(Object.entries(spec.properties).filter(([,v]:any)=>'default'in v).map(([k,v]:any)=>[k,v.default]));
 const response=await page.request.post('/api/searches',{headers:{Origin:origin,'X-Lab-Token':session.token},data:{name:'Paged saved results '+info.project.name,dataset_id:'90f347229b2fb03ec112ee71',strategy:defaults(schema.strategy),costs:defaults(schema.costs),portfolio:defaults(schema.portfolio),start:'2022-01-03',end:'2022-01-03',seed:43,count:51,families:['break_of_structure'],timeframes:['1m'],sampling_policy:{mode:'common_random'},statistics:{effective_trials:[1]}}});
 expect(response.status()).toBe(202);const job=await response.json(),jid=job.id;
 await expect.poll(async()=>(await(await page.request.get('/api/jobs/'+jid)).json()).status,{timeout:120000}).toBe('completed');
 const original=await(await page.request.get('/api/jobs/'+jid+'/result')).json();expect(original.rows).toHaveLength(51);
 const summary=await page.request.get('/api/jobs/'+jid+'/result-summary');expect((await summary.body()).length).toBeLessThanOrEqual(65536);expect((await summary.json()).row_count).toBe(51);
 await page.getByRole('button',{name:'04 Results',exact:true}).click();await page.getByRole('button',{name:'Refresh workspace',exact:true}).click();await page.getByRole('combobox',{name:'Completed job',exact:true}).selectOption(jid);
 const outcomes=page.getByRole('navigation',{name:'Saved outcome pages',exact:true});await expect(outcomes).toContainText('Outcomes 1 to 50 of 51');
 const statistics=page.getByRole('region',{name:'Search-bias sensitivity',exact:true}),screen=page.getByRole('region',{name:'Initial discovery funnel',exact:true});
 await expect(statistics.locator('tbody tr')).toHaveCount(20);
 await statistics.getByRole('button',{name:'Next statistic accounts',exact:true}).click();await expect(statistics).toContainText('Page 2 of 3');await expect(statistics.locator('tbody tr')).toHaveCount(20);await expect(statistics.locator('tbody tr').first()).toContainText(original.search_statistics.accounts[20].config_id.slice(0,12));
 await screen.getByRole('button',{name:'Next discovery accounts',exact:true}).click();await expect(screen).toContainText('Page 2 of 3');await expect(screen.locator('tbody').last().locator('tr')).toHaveCount(20);
 await page.screenshot({path:info.outputPath('actual-paged-diagnostics.png'),fullPage:true});
 await outcomes.getByRole('button',{name:'Next outcomes',exact:true}).click();await expect(outcomes).toContainText('Outcomes 51 to 51 of 51');
 const saved=page.locator('section.panel').filter({has:page.getByRole('heading',{name:'Saved outcomes',exact:true})});await expect(saved.locator('tbody tr')).toHaveCount(1);
 await saved.getByRole('button',{name:'Inspect',exact:true}).click();await expect(page.locator('.report-banner')).toBeVisible();
 await expect(saved.locator('tbody tr')).toHaveCount(1);await expect(outcomes).toContainText('Outcomes 51 to 51 of 51');
 await saved.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('last-outcome-selected-report.png')});
 await page.getByRole('button',{name:'07 Reports',exact:true}).click();const link=page.getByRole('link',{name:'Download full JSON evidence',exact:true});await expect(link).toHaveAttribute('href','/api/jobs/'+jid+'/export/json?part=50&window=report');
 const report=await(await page.request.get((await link.getAttribute('href'))!)).json(),part=await(await page.request.get('/api/jobs/'+jid+'/report?part=50')).json();expect(report).toEqual(part);expect(report.config_id).toBe(original.rows[50].config_id);
 await writeFile(info.outputPath('original-complete-result.json'),JSON.stringify(original));await writeFile(info.outputPath('selected-complete-report.json'),JSON.stringify(report));
 await writeFile(info.outputPath('result-materialization-observations.json'),JSON.stringify({job_id:jid,accounts:51,selected_part:50,viewport:page.viewportSize(),errors,scope:'Actual short already-viewed January 2022 search; paging/export identity, not held-out edge or large numerical throughput.'},null,2));expect(errors).toEqual([]);
});

test('independent older job history owns reversed responses, visible current failures and selected report metadata',async({page},info)=>{
 test.setTimeout(150000);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const actual=await(await page.request.get('/api/jobs')).json(),template=actual.find((j:any)=>j.status==='completed'&&j.kind==='experiment');expect(template).toBeTruthy();
 const first=Array.from({length:50},(_,i)=>({...template,id:'controlled-newer-job-'+i,payload:{name:'Controlled newer job '+i}})),older=[{...template,id:'controlled-older-job',payload:{name:'Controlled older job'}}];
 let release!:()=>void,gate=Promise.resolve(),hold=false,held=false,failure=false,currentFailure=false;
 await page.route('**/api/jobs?limit=50&offset=*',async route=>{const offset=Number(new URL(route.request().url()).searchParams.get('offset'));if(offset===50&&currentFailure){await route.abort('failed');return;}if(hold&&offset===50){hold=false;held=true;await gate;if(failure){await route.abort('failed');return;}}await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(offset===0?first:older)});});
 try{
  await page.goto('/');await page.getByRole('button',{name:'04 Results',exact:true}).click();const nav=page.getByRole('navigation',{name:'Saved job history pages',exact:true}),region=page.getByRole('region',{name:'Saved job history',exact:true});await expect(nav).toContainText('Records 1 to 50');
  for(const mode of ['success','failure']){held=false;failure=mode==='failure';gate=new Promise<void>(resolve=>{release=resolve;});hold=true;await nav.getByRole('button',{name:'Older job history',exact:true}).click();await expect.poll(()=>held).toBe(true);await nav.getByRole('button',{name:'Newest job history',exact:true}).click();await expect(nav).toContainText('Records 1 to 50');release();await page.waitForTimeout(500);await expect(nav).toContainText('Records 1 to 50');await expect(region.getByRole('alert')).toHaveCount(0);}
  currentFailure=true;await nav.getByRole('button',{name:'Older job history',exact:true}).click();await expect(region.getByRole('alert')).toBeVisible();await expect(region.locator('tbody tr')).toHaveCount(0);await nav.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('visible-current-history-error.png')});currentFailure=false;await nav.getByRole('button',{name:'Refresh job history',exact:true}).click();await expect(nav).toContainText('Records 51 to 51');await expect(region.getByRole('alert')).toHaveCount(0);
  // The controlled transport records are only history fixtures. Open a real
  // account from the independent latest-job selector, then browse history.
  await page.getByRole('combobox',{name:'Completed job',exact:true}).selectOption(template.id);await expect(page.locator('.report-banner')).toBeVisible();await nav.getByRole('button',{name:'Newest job history',exact:true}).click();await expect(nav).toContainText('Records 1 to 50');await expect(page.getByRole('combobox',{name:'Completed job',exact:true})).toHaveValue(template.id);
  const buttons=await nav.getByRole('button').evaluateAll(elements=>elements.map(e=>{const r=e.getBoundingClientRect();return {label:e.textContent,x:r.x,y:r.y,width:r.width,height:r.height};}));expect(buttons[0].y).toBe(buttons[1].y);await nav.scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('independent-history-horizontal-toolbar.png')});
  expect(errors).toEqual([]);await writeFile(info.outputPath('history-transport-observations.json'),JSON.stringify({viewport:page.viewportSize(),buttons,selected_real_job:template.id,errors,scope:'Controlled 50/1 metadata pages and held/aborted transport; selected account uses real saved evidence. Controlled IDs are not financial results.'},null,2));
 }finally{release?.();await page.unroute('**/api/jobs?limit=50&offset=*');}
});
