import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

const sources=['d7ef4d13eb3d4fb39c35799b49ac045b','563dc788030047e3b71e010c95ccb95a','527f8aa325e2458f83cf5d1ab93e1e5a',
  '64e62e70a5214e35b9f96a4a8c156472','37ce9886b50245bab64b10a815ce2450','f918e610e0854982a5aafd31c46de20d'];

test('actual saved-output combined presenter downloads and works offline on every page',async({page,context},info)=>{
  test.setTimeout(360000);
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');await page.getByRole('button',{name:'07 Reports',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Offline research presenter',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Download offline presentation',exact:true})).toBeDisabled();
  for(const job_id of sources){await page.getByRole('combobox',{name:'Saved presentation source',exact:true}).selectOption(job_id);await page.getByRole('button',{name:'Add complete saved study',exact:true}).click();}
  const response=page.waitForResponse(r=>r.url().endsWith('/api/presentations')&&r.request().method()==='POST');
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download offline presentation',exact:true}).click();
  const result=await(await response).json();expect(result.manifest.pages).toHaveLength(169);
  const path=info.outputPath('saved-research-presentation.html');await(await download).saveAs(path);
  expect(await readFile(path,'utf8')).toBe(result.html);
  await page.screenshot({path:info.outputPath('presenter-export.png'),fullPage:true});
  const requests:string[]=[];page.on('request',request=>{if(/^https?:/.test(request.url()))requests.push(request.url());});
  await context.setOffline(true);await page.goto(pathToFileURL(path).href);
  await expect(page.locator('#stage')).toHaveAttribute('data-page','1');
  const manifest=await page.locator('#presentation-manifest').textContent();expect(JSON.parse(manifest!)).toEqual(result.manifest);
  const layouts:any[]=[];
  for(let n=0;n<result.manifest.pages.length;n++){
    if(n)await page.keyboard.press('ArrowRight');
    await expect(page.locator('#stage')).toHaveAttribute('data-page',String(n+1));
    await expect(page.locator('h1')).toHaveText(result.manifest.pages[n].title);
    const layout=await page.evaluate(()=>{
      const stage=document.getElementById('stage')!,r=stage.getBoundingClientRect(),s=r.width/1920;
      const issues:string[]=[];const reserved={x:r.x+1400*s,y:r.y+712*s};
      for(const element of document.querySelectorAll('#slide h1,#slide .subtitle,#slide .conclusion,#slide .stat,#slide .concept p,#slide .chart,#slide .notes p')){
        const b=element.getBoundingClientRect();
        if(b.x<r.x-.5||b.y<r.y-.5||b.right>r.right+.5||b.bottom>r.bottom+.5)issues.push('Outside stage: '+element.className);
        if(b.right>reserved.x+.5&&b.bottom>reserved.y+.5)issues.push('Camera overlap: '+element.className);
      }
      for(const element of document.querySelectorAll<SVGTextElement>('.chart text')){const b=element.getBBox();if(b.x<-.5||b.y<-.5||b.x+b.width>1230.5||b.y+b.height>500.5)issues.push('SVG text overflow: '+element.textContent);}
      const subtitle=document.querySelector<HTMLElement>('.subtitle')!;
      if(subtitle.scrollWidth>1741)issues.push('Subtitle overflow');
      if(document.documentElement.scrollWidth>innerWidth||document.documentElement.scrollHeight>innerHeight)issues.push('Document scrolling');
      return {issues,stage:{x:r.x,y:r.y,width:r.width,height:r.height},title:document.querySelector('h1')!.textContent,
        subtitle:subtitle.textContent,conclusion:document.querySelector('.conclusion')!.textContent,
        facts:[...document.querySelectorAll<HTMLElement>('#slide [data-fact]')].map(e=>({id:e.dataset.fact,text:e.textContent}))};
    });
    layouts.push(layout);expect.soft(layout.issues,`Page ${n+1}: ${layout.title}`).toEqual([]);
    await page.screenshot({path:info.outputPath('page-'+String(n+1).padStart(3,'0')+'.png')});
  }
  await writeFile(info.outputPath('presenter-layouts.json'),JSON.stringify(layouts,null,2));
  await page.keyboard.press('Home');await expect(page.locator('#stage')).toHaveAttribute('data-page','1');
  await page.keyboard.press('Space');await expect(page.locator('#stage')).toHaveAttribute('data-page','2');
  await page.keyboard.press('PageDown');await expect(page.locator('#stage')).toHaveAttribute('data-page','3');
  await page.keyboard.press('PageUp');await expect(page.locator('#stage')).toHaveAttribute('data-page','2');
  await page.keyboard.press('ArrowUp');await expect(page.locator('#stage')).toHaveAttribute('data-page','1');
  await page.keyboard.press('End');await expect(page.locator('#stage')).toHaveAttribute('data-page','169');
  await page.evaluate(()=>{location.hash='#4';});await expect(page.locator('#stage')).toHaveAttribute('data-page','4');
  const before=await page.locator('#stage').getAttribute('data-revision');const title=await page.locator('h1').textContent();
  await page.keyboard.press('r');expect(await page.locator('#stage').getAttribute('data-revision')).not.toBe(before);await expect(page.locator('h1')).toHaveText(title!);
  await page.keyboard.press('m');await expect(page.getByRole('dialog')).toBeVisible();
  await page.screenshot({path:info.outputPath('presenter-menu.png')});
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.keyboard.press('m');await page.getByRole('dialog').getByRole('button',{name:'Price behavior : Bos forward',exact:true}).click();
  await expect(page.locator('h1')).toHaveText('Bos forward');
  await page.emulateMedia({reducedMotion:'no-preference'});await page.keyboard.press('r');
  await expect(page.locator('h1')).toHaveCSS('animation-name','reveal');
  await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('h1')).toHaveCSS('animation-name','none');
  await page.keyboard.press('f');await expect(page.locator('#camera-guide')).toBeVisible();
  const guide=await page.locator('#camera-guide').boundingBox();
  expect(await page.locator('#camera-guide').evaluate(e=>getComputedStyle(e).width)).toBe('520px');
  // Apply the same half-logical-pixel raster tolerance as the stage checks.
  expect(Math.abs(guide!.width/(info.project.use.viewport!.width/1920)-520)).toBeLessThanOrEqual(.5);
  await page.screenshot({path:info.outputPath('presenter-camera-guide.png')});await page.keyboard.press('f');await expect(page.locator('#camera-guide')).not.toBeVisible();
  const factor=info.project.use.viewport!.width/1920;
  await page.mouse.move(200*factor,400*factor);await expect(page.locator('#pointer')).toBeVisible();
  await page.mouse.down();await page.mouse.move(500*factor,450*factor,{steps:8});await page.mouse.up();
  await expect(page.locator('.mark')).toHaveCount(1);await page.screenshot({path:info.outputPath('presenter-highlight.png')});
  await expect(page.locator('.mark')).toHaveCount(0,{timeout:6000});
  const manifestDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Save provenance',exact:true}).click();
  const manifestPath=info.outputPath('downloaded-presentation-provenance.json');await(await manifestDownload).saveAs(manifestPath);
  expect(JSON.parse(await readFile(manifestPath,'utf8'))).toEqual(result.manifest);
  expect(requests).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('presenter-observations.json'),JSON.stringify({viewport:page.viewportSize(),browser:context.browser()?.version(),
    source_jobs:sources,pages:layouts.length,facts:result.manifest.audit.facts_checked,layouts,networkRequests:requests,consoleErrors:errors,
    scope:'Actual saved historical output export and every-page offline presentation; not final certification of the research engine.'},null,2));
});
