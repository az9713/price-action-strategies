import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';

test('actual saved-family queue all versions pages downloads reload errors and stale responses',async({page},info)=>{
  const parent=process.env.PA_FAMILY_PARENT!,other=process.env.PA_FAMILY_OTHER!;
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await page.getByRole('button',{name:/^(04 )?Results$/}).click();
  await page.getByRole('combobox',{name:'Completed job',exact:true}).selectOption(parent);
  const panel=page.getByRole('region',{name:'All-version family research',exact:true});
  await panel.getByRole('combobox',{name:'Family to analyze',exact:true}).selectOption('change_of_character');
  await panel.getByRole('button',{name:'Queue complete family analysis',exact:true}).click();
  const output=panel.getByTestId('family-analysis-output');
  await expect(output).toContainText('51 complete versions',{timeout:60000});
  const jid=(await output.getAttribute('data-job-id'))!;expect(jid).toBeTruthy();
  await expect(output).toContainText('Financial accounts rerun: 0');
  await expect(output).toContainText('Final dates accessed: No');
  const members=output.getByRole('region',{name:'Complete family membership',exact:true});
  await expect(members).toContainText('Records 1–50 of 51.');
  await members.getByRole('button',{name:'Next family page',exact:true}).click();
  await expect(members).toContainText('Records 51–51 of 51.');
  await expect(members.getByRole('link',{name:'Download source account',exact:true})).toHaveCount(1);
  await members.getByRole('button',{name:'Previous family page',exact:true}).focus();
  await page.keyboard.press('Enter');await expect(members).toContainText('Records 1–50 of 51.');
  await members.getByRole('button',{name:'Next family page',exact:true}).click();
  await expect(members).toContainText('Records 51–51 of 51.');
  await panel.screenshot({path:info.outputPath('complete-family-evidence.png')});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  for(const [label,ext] of [['Download complete family JSON','json'],['Download both daily conventions CSV','csv']]){
    const pending=page.waitForEvent('download');await panel.getByRole('link',{name:label,exact:true}).click();
    const download=await pending,path=join(process.env.PA_FAMILY_PRIVATE_EXPORTS!,info.project.name+'-'+jid+'.'+ext);
    await download.saveAs(path);const text=await readFile(path,'utf8');
    if(ext==='json'){const value=JSON.parse(text);expect(value.rows).toHaveLength(51);expect(value.report.members).toHaveLength(51);expect(value.report.marked.daily).toHaveLength(3);}
    else{expect(text.trim().split(/\r?\n/)).toHaveLength(7);expect(text).toContain('mean_pnl_numerator');}
  }
  await page.reload();await page.getByRole('button',{name:/^(04 )?Results$/}).click();
  await panel.getByRole('combobox',{name:'Saved family analysis',exact:true}).selectOption(jid);
  await expect(output).toHaveAttribute('data-job-id',jid);
  // The helper created a genuinely failed job by changing an original part,
  // observed the failure, then restored its exact authored original bytes.
  await panel.getByRole('combobox',{name:'Saved family analysis',exact:true}).selectOption(other);
  const status=await(await page.request.get('/api/jobs/'+other)).json();
  if(status.status==='failed')await panel.getByRole('button',{name:'Resume original family analysis',exact:true}).click();
  await expect(output).toHaveAttribute('data-job-id',other,{timeout:60000});
  await expect(output).toContainText('3 complete versions');
  let release:()=>void=()=>{},received:()=>void=()=>{};
  const held=new Promise<void>(r=>{release=r;}),seen=new Promise<void>(r=>{received=r;});
  const path='**/api/jobs/'+jid+'/family-analysis';
  await page.route(path,async route=>{const response=await route.fetch();received();await held;try{await route.fulfill({response});}catch{/* Obsolete selection was abandoned. */}});
  await panel.getByRole('combobox',{name:'Saved family analysis',exact:true}).selectOption(jid);await seen;
  await panel.getByRole('combobox',{name:'Saved family analysis',exact:true}).selectOption(other);
  await expect(output).toHaveAttribute('data-job-id',other);release();await page.unroute(path);
  await expect(output).toContainText('3 complete versions');
  // An actual failed HTTP response must remove old results and download links.
  await page.route(path,route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Authored original evidence unavailable'})}),{times:1});
  await panel.getByRole('combobox',{name:'Saved family analysis',exact:true}).selectOption(jid);
  await expect(panel.getByRole('alert')).toContainText('Authored original evidence unavailable');
  await expect(output).toHaveCount(0);await expect(panel.getByRole('link',{name:'Download complete family JSON',exact:true})).toHaveCount(0);
  await panel.getByRole('button',{name:'Reload family evidence',exact:true}).click();
  await expect(output).toHaveAttribute('data-job-id',jid);expect(errors).toEqual([]);
});
