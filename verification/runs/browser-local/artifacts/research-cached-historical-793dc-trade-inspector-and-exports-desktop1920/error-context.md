# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: research.spec.ts >> cached historical experiment through real UI, worker, trade inspector and exports
- Location: tests\research.spec.ts:4:1

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765/
Call log:
  - navigating to "http://127.0.0.1:8765/", waiting until "load"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e6]:
    - heading "This site can’t be reached" [level=1] [ref=e7]
    - paragraph [ref=e8]:
      - strong [ref=e9]: 127.0.0.1
      - text: refused to connect.
    - generic [ref=e10]:
      - paragraph [ref=e11]: "Try:"
      - list [ref=e12]:
        - listitem [ref=e13]: Checking the connection
        - listitem [ref=e14]:
          - link "Checking the proxy and the firewall" [ref=e15] [cursor=pointer]:
            - /url: "#buttons"
    - generic [ref=e16]: ERR_CONNECTION_REFUSED
  - generic [ref=e17]:
    - button "Reload" [ref=e19] [cursor=pointer]
    - button "Details" [ref=e20] [cursor=pointer]
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test';
  2  | import {writeFile} from 'node:fs/promises';
  3  | 
  4  | test('cached historical experiment through real UI, worker, trade inspector and exports',async({page},info)=>{
  5  |   const consoleErrors:string[]=[];page.on('pageerror',e=>consoleErrors.push(e.message));
> 6  |   await page.goto('/');
     |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765/
  7  |   await expect(page.getByRole('heading',{name:'Data',exact:true})).toBeVisible();
  8  |   await expect(page.getByText('90f347229b2fb03ec112ee71',{exact:true})).toBeVisible();
  9  |   await page.screenshot({path:info.outputPath('data.png'),fullPage:true});
  10 |   await page.getByRole('button',{name:'02 Strategies',exact:true}).click();
  11 |   await expect(page.locator('.family-card')).toHaveCount(10);
  12 |   await page.getByLabel('Rule set name',{exact:true}).fill('Browser smoke '+info.project.name);
  13 |   await page.getByRole('button',{name:'Save rule set',exact:true}).click();
  14 |   await expect(page.getByRole('status')).toContainText('Saved as an immutable');
  15 |   await page.screenshot({path:info.outputPath('strategies.png'),fullPage:true});
  16 |   await page.getByRole('button',{name:'Use in experiment',exact:true}).click();
  17 |   await page.getByLabel('Dataset',{exact:true}).selectOption('90f347229b2fb03ec112ee71');
  18 |   await page.getByLabel('Experiment name',{exact:true}).fill('Browser smoke '+info.project.name);
  19 |   const response=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  20 |   await page.getByRole('button',{name:'Run single configuration',exact:true}).click();
  21 |   const created=await(await response).json();expect(['queued','running']).toContain(created.status);
  22 |   const row=page.locator('tbody tr').filter({has:page.getByText(created.id.slice(0,10),{exact:true})});
  23 |   await expect(row.getByText('Completed',{exact:true})).toBeVisible({timeout:60000});
  24 |   await page.screenshot({path:info.outputPath('experiment.png'),fullPage:true});
  25 |   await row.getByRole('button',{name:'Open results',exact:true}).click();
  26 |   await expect(page.locator('.metrics')).toBeVisible();
  27 |   const report=await(await page.request.get('/api/jobs/'+created.id+'/report')).json();
  28 |   expect(report.trades).toHaveLength(10);
  29 |   expect(new Set(report.trades.map((t:any)=>t.side))).toEqual(new Set([1,-1]));
  30 |   expect(Math.abs(report.trades.reduce((sum:number,t:any)=>sum+t.net_pnl,0)-report.metrics.net_profit)).toBeLessThan(1e-7);
  31 |   await expect(page.locator('.metrics>div').first()).toContainText(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(report.metrics.net_profit));
  32 |   await expect(page.locator('.recharts-surface')).toBeVisible();
  33 |   await page.screenshot({path:info.outputPath('results.png'),fullPage:true});
  34 |   await page.getByRole('button',{name:'05 Trade inspector',exact:true}).click();
  35 |   await expect(page.locator('.trades-table tbody tr')).toHaveCount(10);
  36 |   await expect(page.locator('.candles canvas').first()).toBeVisible();
  37 |   await page.getByRole('button',{name:'Inspect trade',exact:true}).last().click();
  38 |   await expect(page.getByRole('heading',{name:'Trade cash ledger',exact:true})).toBeVisible();
  39 |   await page.screenshot({path:info.outputPath('trade-inspector.png'),fullPage:true});
  40 |   await page.getByRole('button',{name:'06 Validation',exact:true}).click();
  41 |   await expect(page.getByRole('heading',{name:'Freeze a time-ordered study',exact:true})).toBeVisible();
  42 |   await page.screenshot({path:info.outputPath('validation.png'),fullPage:true});
  43 |   await page.getByRole('button',{name:'07 Reports',exact:true}).click();
  44 |   const downloadPromise=page.waitForEvent('download');
  45 |   await page.getByRole('link',{name:'Download full JSON evidence',exact:true}).click();
  46 |   const download=await downloadPromise;const path=info.outputPath('downloaded-report.json');await download.saveAs(path);
  47 |   const exported=await(await page.request.get('/api/jobs/'+created.id+'/export/json')).json();
  48 |   expect(exported).toEqual(report);
  49 |   await page.screenshot({path:info.outputPath('reports.png'),fullPage:true});
  50 |   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  51 |   expect(consoleErrors).toEqual([]);
  52 |   await writeFile(info.outputPath('observations.json'),JSON.stringify({job_id:created.id,browser:await page.context().browser()?.version(),
  53 |     viewport:page.viewportSize(),bundle:await page.locator('script[type=module]').getAttribute('src'),
  54 |     dataset_id:report.dataset_id,net_profit:report.metrics.net_profit,trades:report.trades.length,
  55 |     equity_points:report.equity.length,ledger_events:report.ledger.length,consoleErrors,
  56 |     scope:'One real cached historical flow, not the entire acceptance catalog.'},null,2));
  57 | });
  58 | 
```