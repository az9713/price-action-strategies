import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {join} from 'node:path';

test('actual original sets members books complete export and response ownership',async({page},info)=>{
  const jid=process.env.PA_TWIN_INSPECTOR_JOB!;expect(jid).toBeTruthy();
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');await page.getByRole('button',{name:/^(06 )?Validation$/}).click();
  const panel=page.getByRole('region',{name:'Saved trade-twin comparisons',exact:true});
  await panel.getByRole('combobox',{name:'Saved trade-twin job',exact:true}).selectOption(jid);
  await expect(panel.getByTestId('trade-twin-output')).toHaveAttribute('data-job-id',jid);
  const inspector=panel.getByRole('region',{name:'Original saved trade-twin evidence',exact:true});
  await expect(inspector.getByRole('button',{name:'Inspect set 1',exact:true})).toBeVisible();
  await inspector.getByRole('button',{name:'Next financial sets',exact:true}).click();
  await expect(inspector.getByRole('button',{name:'Inspect set 26',exact:true})).toBeVisible();
  await inspector.getByRole('button',{name:'Inspect set 26',exact:true}).click();
  await expect(inspector.getByTestId('trade-twin-members')).toHaveAttribute('data-set-index','25');
  await inspector.getByRole('button',{name:'Inspect original book 1',exact:true}).click();
  await expect(inspector.getByTestId('trade-twin-book')).toHaveAttribute('data-set-index','25');
  const book=await(await page.request.get('/api/jobs/'+jid+'/trade-twins/sets/25/books/0')).json();
  await expect(inspector.getByTestId('trade-twin-book')).toContainText(book.book.net_profit);
  await inspector.getByRole('combobox',{name:'Original event history',exact:true}).selectOption('equity');
  await expect(inspector.getByRole('region',{name:'Original financial records',exact:true})).toContainText('equity');
  await inspector.getByRole('combobox',{name:'Original event history',exact:true}).selectOption('ledger');
  await expect(inspector.getByRole('region',{name:'Original financial records',exact:true})).toContainText('entry');
  await inspector.screenshot({path:info.outputPath('original-book-inspector.png')});
  // Hold a genuine old book response while selecting a different policy.
  let release:()=>void=()=>{},received:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{release=resolve;}),seen=new Promise<void>(resolve=>{received=resolve;});
  const old='**/api/jobs/'+jid+'/trade-twins/sets/25/books/0?policy=barrier_capped_elapsed_v1&kind=ledger&offset=0&limit=25';
  await page.route(old,async route=>{const response=await route.fetch();received();await held;try{await route.fulfill({response});}catch{/* Selection aborted this obsolete fetch. */}});
  await inspector.getByRole('button',{name:'Retry saved evidence pages',exact:true}).click();await seen;
  await inspector.getByRole('combobox',{name:'Saved interpretation',exact:true}).selectOption('fixed_elapsed_v1');
  await expect(inspector.getByTestId('trade-twin-book')).toHaveCount(0);
  release();await page.unroute(old);
  await expect(inspector.getByRole('button',{name:'Inspect set 1',exact:true})).toBeVisible();
  await inspector.getByRole('button',{name:'Inspect set 1',exact:true}).click();
  await inspector.getByRole('button',{name:'Inspect original book 1',exact:true}).click();
  await expect(inspector.getByTestId('trade-twin-book')).toHaveAttribute('data-set-index','0');
  const download=page.waitForEvent('download',{timeout:120000});
  await inspector.getByRole('link',{name:'Download complete saved evidence ZIP',exact:true}).click();
  const file=await download;expect(await file.failure()).toBe(null);
  expect(file.suggestedFilename()).toBe('trade-twins-'+jid+'.zip');
  const privatePath=join(process.env.PA_TWIN_PRIVATE_EXPORTS!,info.project.name+'.zip');await file.saveAs(privatePath);
  const data=await readFile(privatePath),sha=createHash('sha256').update(data).digest('hex');
  expect(data.subarray(0,2).toString()).toBe('PK');
  await page.reload();await page.getByRole('button',{name:/^(06 )?Validation$/}).click();
  await panel.getByRole('combobox',{name:'Saved trade-twin job',exact:true}).selectOption(jid);
  await expect(inspector.getByRole('button',{name:'Inspect set 1',exact:true})).toBeVisible();
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('inspector-observations.json'),JSON.stringify({job_id:jid,browser:await page.context().browser()?.version(),viewport:page.viewportSize(),
    bundle:await page.locator('script[type=module]').getAttribute('src'),download_sha256:sha,download_bytes:data.length,raw_export_retained_private:true,
    console_errors:errors,obsolete_book_response_cannot_replace_selected_interpretation:true,
    scope:'Actual saved completed20000-occurrence synthetic result, original pages/books/full ZIP. No new financial simulation.'},null,2));
});
