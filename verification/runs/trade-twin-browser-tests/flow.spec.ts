import {test,expect} from '../../../frontend/node_modules/@playwright/test';
import {writeFile} from 'node:fs/promises';

test('original saved account queues cancels resumes and reopens its actual ineligible comparison',async({page},info)=>{
  const parent=JSON.parse(process.env.PA_TWIN_PARENTS||'{}')[info.project.name];expect(parent).toBeTruthy();
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');await page.getByRole('button',{name:/^(04 )?Results$/}).click();
  const history=page.getByRole('region',{name:'Saved job history',exact:true});
  await history.getByRole('row').filter({hasText:parent}).getByRole('button',{name:'Open historical results',exact:true}).click();
  const launch=page.getByRole('region',{name:'Compare original account with random entries',exact:true});
  await expect(launch.getByRole('button',{name:'Compare saved account with random entries',exact:true})).toBeEnabled();
  const queued=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+parent+'/trade-twins')&&r.request().method()==='POST');
  await launch.getByRole('button',{name:'Compare saved account with random entries',exact:true}).click();
  const child=await(await queued).json();expect(child.id).toBeTruthy();
  const panel=page.getByRole('region',{name:'Saved trade-twin comparisons',exact:true});
  await expect(panel.getByTestId('trade-twin-job')).toHaveAttribute('data-job-id',child.id);
  await expect(panel.getByTestId('trade-twin-job')).toContainText('queued');
  await panel.getByRole('button',{name:'Cancel trade-twin comparison',exact:true}).click();
  await expect(panel.getByRole('button',{name:'Resume original trade-twin comparison',exact:true})).toBeVisible();
  await panel.getByRole('button',{name:'Resume original trade-twin comparison',exact:true}).click();
  await expect(panel.getByTestId('trade-twin-output')).toBeVisible({timeout:60000});
  const report=await(await page.request.get('/api/jobs/'+child.id+'/report')).json();
  expect(report.report_type).toBe('trade_twins');expect(report.comparison_eligible).toBe(false);
  expect(report.financial_occurrences).toBe(0);expect(report.unique_committed_books).toBe(0);
  for(const value of Object.values(report.summaries) as any[]){expect(value.state).toBe('ineligible');expect(value.complete_sets).toBe(0);expect(value.adapted_pass).toBe(null);}
  await expect(panel.getByTestId('trade-twin-output')).toContainText('Unavailable');
  const download=page.waitForEvent('download');await panel.getByRole('link',{name:'Download comparison summary',exact:true}).click();
  await(await download).saveAs(info.outputPath('comparison-summary.json'));
  await page.screenshot({path:info.outputPath('comparison-workflow.png'),fullPage:true});
  await page.reload();await page.getByRole('button',{name:/^(06 )?Validation$/}).click();
  await panel.getByRole('combobox',{name:'Saved trade-twin job',exact:true}).selectOption(child.id);
  await expect(panel.getByTestId('trade-twin-output')).toHaveAttribute('data-job-id',child.id);
  const completed=process.env.PA_TWIN_COMPLETED;expect(completed).toBeTruthy();
  await panel.getByRole('combobox',{name:'Saved trade-twin job',exact:true}).selectOption(completed!);
  await expect(panel.getByTestId('trade-twin-output')).toHaveAttribute('data-job-id',completed!);
  await expect(panel.getByTestId('trade-twin-output')).toContainText('20000');
  await expect(panel.getByRole('cell',{name:'10000 / 10000',exact:true})).toHaveCount(2);
  await expect(panel.getByRole('cell',{name:'Fail',exact:true})).toHaveCount(2);
  await panel.screenshot({path:info.outputPath('completed-comparison-panel.png')});
  const comparison=panel.getByRole('region',{name:'Trade-twin interpretation comparison',exact:true});
  if(info.project.name==='mobile390'){
    await comparison.focus();
    for(let i=0;i<8;i++)await page.keyboard.press('ArrowRight');
    await expect.poll(()=>comparison.evaluate(element=>element.scrollLeft)).toBeGreaterThan(0);
    await comparison.screenshot({path:info.outputPath('comparison-keyboard-scroll.png')});
  }
  expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await writeFile(info.outputPath('observations.json'),JSON.stringify({parent,child:child.id,browser:await page.context().browser()?.version(),viewport:page.viewportSize(),
    bundle:await page.locator('script[type=module]').getAttribute('src'),source_count:report.source.source_count,financial_occurrences:0,console_errors:errors,
    reopened_completed_workload:completed,
    scope:'Actual API/worker on empty original cohort; zero new financial sets. Also reopens the independently audited completed synthetic 10000-set summaries from an earlier source snapshot. Controlled scheduling holds queued children until their original resume event. Full saved-set inspection and final acceptance remain separate.'},null,2));
});
