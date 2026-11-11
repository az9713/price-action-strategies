import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
test('obsolete parent errors and selected-page success or failure cannot replace the newly selected original',async({page},info)=>{
  test.setTimeout(180000);await page.goto('/');await page.waitForLoadState('networkidle');
  await page.getByRole('navigation',{name:'Research sections'}).getByRole('button',{name:/^(03 )?Experiments$/}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(process.env.PA_SPREAD_DATASET!);
  await page.getByLabel('Start date',{exact:true}).fill('2026-10-19');await page.getByLabel('End date',{exact:true}).fill('2026-10-30');
  const form=page.getByRole('region',{name:'Balanced spread workflow',exact:true});
  const parents:any[]=[];
  for(const symbol of ['SPY','QQQ']){
    await form.getByRole('button',{name:'Use small functional run',exact:true}).click();await form.getByLabel('Spread primary instrument',{exact:true}).selectOption(symbol);
    if(symbol==='QQQ'){await form.getByLabel('Spread proposals per batch',{exact:true}).fill('1');await form.getByLabel('Spread maximum batches per family',{exact:true}).fill('1');}
    await form.getByRole('button',{name:'Preview spread work',exact:true}).click();
    const creation=page.waitForResponse(r=>r.url().endsWith('/api/spreads')&&r.request().method()==='POST');
    await form.getByRole('button',{name:'Freeze and qualify spread',exact:true}).click();const parent=await(await creation).json();parents.push(parent);
    await expect.poll(async()=>{const r=await(await page.request.get('/api/spreads/'+parent.id)).json();return r.job.status;},{timeout:120000}).toBe('completed');
    await expect(form.getByLabel('Saved spread progress')).toContainText(parent.id);
  }
  const [a,b]=parents;
  let release!:()=>void,settle!:()=>void,captured=false;
  const barrier=new Promise<void>(r=>release=r),settled=new Promise<void>(r=>settle=r);
  await page.route('**/api/spreads/'+a.id,async route=>{captured=true;await barrier;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Obsolete parent failure must stay hidden.'})});settle();});
  await form.getByLabel('Reopen recent spread',{exact:true}).selectOption(a.id);await expect.poll(()=>captured).toBe(true);
  await form.getByLabel('Reopen recent spread',{exact:true}).selectOption(b.id);await expect(form.getByLabel('Saved spread progress')).toContainText(b.id);release();await settled;
  await page.unroute('**/api/spreads/'+a.id);await expect(form.getByRole('alert')).toHaveCount(0);await expect(form.getByLabel('Saved spread progress')).toContainText(b.id);
  for(const fail of [false,true]){
    let releasePage!:()=>void,settlePage!:()=>void,held=false;
    const pageBarrier=new Promise<void>(r=>releasePage=r),pageSettled=new Promise<void>(r=>settlePage=r);
    await page.route('**/api/spreads/'+a.id+'/selections?*',async route=>{
      const response=await route.fetch();expect(response.status()).toBe(200);held=true;await pageBarrier;
      if(fail)await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Obsolete selected-page failure must stay hidden.'})});
      else await route.fulfill({response});settlePage();
    });
    await form.getByLabel('Reopen recent spread',{exact:true}).selectOption(a.id);await expect.poll(()=>held).toBe(true);
    await form.getByLabel('Reopen recent spread',{exact:true}).selectOption(b.id);await expect(form.getByLabel('Saved spread progress')).toContainText(b.id);
    await expect(form.getByLabel('Saved selected rules')).toContainText('0 selected in this saved snapshot');releasePage();await pageSettled;
    await page.unroute('**/api/spreads/'+a.id+'/selections?*');
    await expect(form.getByLabel('Saved selected rules').locator('tbody tr')).toHaveCount(0);await expect(form.getByRole('alert')).toHaveCount(0);
  }
  await form.screenshot({path:info.outputPath('spread-new-owner-preserved.png')});
  await writeFile(info.outputPath('spread-response-ownership-subject.json'),JSON.stringify({original_qualified_parent:a.id,new_exhausted_parent:b.id,scope:'Real frozen parents and original page; deliberate obsolete HTTP response ordering.'},null,2));
});
