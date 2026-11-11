# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: research.spec.ts >> cached historical experiment through real UI, worker, trade inspector and exports
- Location: tests\research.spec.ts:4:1

# Error details

```
Test timeout of 90000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 90000ms exceeded.
Call log:
  - waiting for getByLabel('Dataset', { exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - link [ref=e5] [cursor=pointer]:
      - /url: "#data"
      - generic [aria-hidden] [ref=e6]: PA
      - generic [ref=e7]:
        - text: PRICE ACTION
        - strong [ref=e8]: Research lab
    - paragraph [ref=e9]: LOCAL WORKSPACE
    - navigation "Research sections" [ref=e10]:
      - button "01 Data" [ref=e11] [cursor=pointer]:
        - generic [ref=e12]: "01"
        - text: Data
      - button "02 Strategies" [ref=e13] [cursor=pointer]:
        - generic [ref=e14]: "02"
        - text: Strategies
      - button "03 Experiments" [ref=e15] [cursor=pointer]:
        - generic [ref=e16]: "03"
        - text: Experiments
      - button "04 Results" [ref=e17] [cursor=pointer]:
        - generic [ref=e18]: "04"
        - text: Results
      - button "05 Trade inspector" [ref=e19] [cursor=pointer]:
        - generic [ref=e20]: "05"
        - text: Trade inspector
      - button "06 Validation" [ref=e21] [cursor=pointer]:
        - generic [ref=e22]: "06"
        - text: Validation
      - button "07 Reports" [ref=e23] [cursor=pointer]:
        - generic [ref=e24]: "07"
        - text: Reports
    - generic [ref=e25]:
      - generic [ref=e26]: Localhost only
      - paragraph [ref=e27]: US stocks & ETFsRegular exchange sessions
      - link "Source video · AI Pathways" [ref=e28] [cursor=pointer]:
        - /url: https://www.youtube.com/watch?v=z97PnFIPoFg
      - generic [ref=e29]: Functional recreation. Exact host code and futures results are unavailable.
  - main [ref=e30]:
    - generic [ref=e31]:
      - generic [ref=e32]: RESEARCH / EXPERIMENTS
      - generic [ref=e33]:
        - text: Local engine connected
        - generic [ref=e35]: Development build
    - generic [ref=e36]:
      - generic [ref=e37]:
        - generic [ref=e38]:
          - paragraph [ref=e39]: FROM A PRICE PATTERN TO TESTABLE EVIDENCE
          - heading "Experiments" [level=1] [ref=e40]
          - paragraph [ref=e41]: Run the rules against history, with every assumption saved.
        - button "Refresh workspace" [ref=e42] [cursor=pointer]
      - generic "Research workflow" [ref=e43]:
        - generic [ref=e44]: 1 eligible datasets
        - generic [ref=e45]: 1 saved rule sets
        - generic [ref=e46]: 1 completed jobs
        - generic [ref=e47]: 0 consumed final tests
      - generic [ref=e48]: Implementation in progress. Final plan conformance is not verified. Historical results do not establish future profitability.
      - status [ref=e49]: Saved as an immutable strategy version.
      - generic [ref=e50]:
        - heading "Experiment inputs" [level=2] [ref=e52]
        - generic [ref=e53]:
          - generic [ref=e54]:
            - generic [ref=e55]: Dataset
            - combobox "Dataset" [ref=e56]:
              - option "Choose saved data" [selected]
              - option "AAPL, DIA, IWM, MSFT, QQQ, SPY · 2022-01-03 – 2022-01-31 · Audit issues"
              - option "AAPL, IWM, MSFT, QQQ, SPY · 2022-01-03 – 2022-01-31"
          - generic [ref=e57]:
            - generic [ref=e58]: Start date
            - textbox "Start date" [ref=e59]: 2022-01-03
          - generic [ref=e60]:
            - generic [ref=e61]: End date
            - textbox "End date" [ref=e62]: 2022-01-31
        - generic [ref=e63]:
          - generic [ref=e64]:
            - generic [ref=e65]: Experiment name
            - textbox "Experiment name" [ref=e66]: Browser smoke desktop1280
          - generic [ref=e67]:
            - generic [ref=e68]: Random seed
            - spinbutton "Random seed" [ref=e69]: "42"
        - generic [ref=e70]:
          - generic [ref=e71]: Change of character
          - generic [ref=e72]: 1h · both · next_open · 1R
          - button "Edit rules" [ref=e73] [cursor=pointer]
        - group [ref=e74]:
          - generic "Capital and sizing assumptions" [ref=e75] [cursor=pointer]
        - group [ref=e76]:
          - generic "Execution costs and short borrowing" [ref=e77] [cursor=pointer]
        - button "Run single configuration" [disabled] [ref=e78]
      - generic [ref=e79]:
        - heading "Reproducible parameter search" [level=2] [ref=e81]
        - paragraph [ref=e82]: Sample unique configurations with a fixed seed. Results are discovery evidence. The host's undisclosed sampling grid is not reproduced.
        - generic [ref=e83]:
          - generic [ref=e84]:
            - checkbox "Level bounce" [ref=e85]
            - text: Level bounce
          - generic [ref=e86]:
            - checkbox "Breakout" [ref=e87]
            - text: Breakout
          - generic [ref=e88]:
            - checkbox "Flip zone" [ref=e89]
            - text: Flip zone
          - generic [ref=e90]:
            - checkbox "Trend pullback" [ref=e91]
            - text: Trend pullback
          - generic [ref=e92]:
            - checkbox "Trend line" [ref=e93]
            - text: Trend line
          - generic [ref=e94]:
            - checkbox "Break of structure" [ref=e95]
            - text: Break of structure
          - generic [ref=e96]:
            - checkbox "Change of character" [checked] [ref=e97]
            - text: Change of character
          - generic [ref=e98]:
            - checkbox "Sweep and reclaim" [ref=e99]
            - text: Sweep and reclaim
          - generic [ref=e100]:
            - checkbox "Supply and demand" [ref=e101]
            - text: Supply and demand
          - generic [ref=e102]:
            - checkbox "Fair value gap" [ref=e103]
            - text: Fair value gap
        - generic [ref=e104]:
          - generic [ref=e105]:
            - checkbox "1m" [ref=e106]
            - text: 1m
          - generic [ref=e107]:
            - checkbox "5m" [ref=e108]
            - text: 5m
          - generic [ref=e109]:
            - checkbox "15m" [ref=e110]
            - text: 15m
          - generic [ref=e111]:
            - checkbox "1h" [checked] [ref=e112]
            - text: 1h
          - generic [ref=e113]:
            - checkbox "4h" [ref=e114]
            - text: 4h
          - generic [ref=e115]:
            - checkbox "1d" [ref=e116]
            - text: 1d
        - generic [ref=e117]:
          - generic [ref=e118]:
            - generic [ref=e119]: Unique configurations
            - spinbutton "Unique configurations Begin small. Large-search performance is not yet measured." [ref=e120]: "10"
            - generic [ref=e121]: Begin small. Large-search performance is not yet measured.
          - button "Queue parameter search" [disabled] [ref=e122]
      - generic [ref=e123]:
        - heading "Job queue" [level=2] [ref=e125]
        - table [ref=e127]:
          - rowgroup [ref=e128]:
            - row [ref=e129]:
              - columnheader "Job / created" [ref=e130]
              - columnheader "Type" [ref=e131]
              - columnheader "State" [ref=e132]
              - columnheader "Progress" [ref=e133]
              - columnheader "Action" [ref=e134]
          - rowgroup [ref=e135]:
            - row [ref=e136]:
              - cell "d950c9c543 11/8/2026, 4:15:51 AM" [ref=e137]:
                - code [ref=e138]: d950c9c543
                - generic [ref=e139]: 11/8/2026, 4:15:51 AM
              - cell "Experiment" [ref=e140]
              - cell "Completed" [ref=e141]
              - cell "1 Results saved and content-bound." [ref=e143]:
                - progressbar "Job progress" [ref=e144]
                - generic [ref=e145]: Results saved and content-bound.
              - cell [ref=e146]:
                - button "Open results" [ref=e147] [cursor=pointer]
      - generic [ref=e148]:
        - generic [ref=e149]: Price Action Research Lab · Private research · No live orders
        - generic [ref=e150]: Source rules, adaptations, and evidence remain distinct.
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test';
  2  | import {writeFile} from 'node:fs/promises';
  3  | 
  4  | test('cached historical experiment through real UI, worker, trade inspector and exports',async({page},info)=>{
  5  |   const consoleErrors:string[]=[];page.on('pageerror',e=>consoleErrors.push(e.message));
  6  |   await page.goto('/');
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
> 17 |   await page.getByLabel('Dataset',{exact:true}).selectOption('90f347229b2fb03ec112ee71');
     |                                                 ^ Error: locator.selectOption: Test timeout of 90000ms exceeded.
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