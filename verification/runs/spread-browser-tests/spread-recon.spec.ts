import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
test('inspect the actual synthetic spread screen before workflow assertions',async({page},info)=>{
  await page.goto('/');await page.waitForLoadState('networkidle');
  await expect.poll(async()=>{const h=await(await page.request.get('/api/health')).json();return h.source_current&&h.worker_ready;},{timeout:60000}).toBe(true);
  await page.getByRole('navigation',{name:'Research sections'}).getByRole('button',{name:/^(03 )?Experiments$/}).click();
  await page.getByRole('combobox',{name:'Dataset',exact:true}).selectOption(process.env.PA_SPREAD_DATASET!);
  await expect(page.getByRole('region',{name:'Balanced spread workflow',exact:true})).toBeVisible();
  await writeFile(info.outputPath('spread-actual-dom.txt'),await page.locator('body').innerText());
  await page.getByRole('region',{name:'Balanced spread workflow',exact:true}).screenshot({path:info.outputPath('spread-form.png')});
  await page.screenshot({path:info.outputPath('spread-full-page.png'),fullPage:true});
});
