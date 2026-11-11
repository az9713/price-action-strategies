// Render only static documentation in isolated headless Chromium.
import {createRequire} from 'node:module';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {homedir,hostname} from 'node:os';
import {existsSync} from 'node:fs';
const root=process.cwd(), site=resolve(process.argv[2]||'docs'), out=resolve(process.argv[3]||'docs/pause/browser');
const require=createRequire(join(root,'frontend/package.json'));
const {chromium}=require('@playwright/test');
await mkdir(out,{recursive:true});
const browserPath=[join(process.env.LOCALAPPDATA||'','Google/Chrome/Application/chrome.exe'),join(process.env.ProgramFiles||'C:/Program Files','Google/Chrome/Application/chrome.exe')].find(existsSync);
const browser=await chromium.launch({headless:true,...(browserPath?{executablePath:browserPath}:{channel:'chrome'})});
const observations=[];
try{
 for(const [profile,viewport] of [['desktop',{width:1440,height:900}],['mobile',{width:390,height:844}]]){
  const context=await browser.newContext({viewport});
  const page=await context.newPage();const errors=[],network=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url());});
  for(const name of ['index.html','handoff.html','development-journey.html','verification-history.html']){
   const raw=await readFile(join(site,name));
   await page.goto(pathToFileURL(join(site,name)).href);
   if(await page.locator('h1').count()!==1)throw Error(name+': expected one primary heading');
   if(!(await page.title()).includes('Price Action Research Lab'))throw Error(name+': missing title');
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
   if(overflow)throw Error(name+': horizontal viewport overflow');
   for(const privateValue of [homedir(),hostname(),process.env.USERNAME].filter(Boolean)){
    if(raw.toString().toLowerCase().includes(privateValue.toLowerCase()))throw Error(name+': private machine value');
   }
   const snapshot=join(out,profile+'-'+name.replace('.html','.png'));
   await page.screenshot({path:snapshot});
   const item={profile,viewport,page:name,title:await page.title(),horizontal_overflow:overflow,
    html_sha256:createHash('sha256').update(raw).digest('hex'),screenshot:snapshot.replace(out+'\\','').replace(out+'/','')};
   if(name==='development-journey.html'){
    item.journal_sections=await page.locator('section[id^="journal-"]').count();
    if(item.journal_sections!==4)throw Error('Missing one of the four journals');
   }
   if(name==='verification-history.html'){
    item.all_entries=await page.locator('#runs tbody tr').count();
    await page.locator('#query').fill('20261111T033747231640Z-adopted-numerical-real-market-10000-capacity');
    item.search_entries=await page.locator('#runs tbody tr:visible').count();
    if(item.search_entries<1||item.search_entries>=item.all_entries)throw Error('Ledger search did not discriminate');
    await page.locator('#query').fill('');await page.locator('#status').selectOption('nonzero');
    item.nonzero_entries=await page.locator('#runs tbody tr:visible').count();
    if(item.nonzero_entries<1||item.nonzero_entries>=item.all_entries)throw Error('Ledger status filter did not discriminate');
    await page.locator('#query').focus();await page.keyboard.type('no-such-run-acceptance-probe');
    if(await page.locator('#runs tbody tr:visible').count()!==0)throw Error('Keyboard search did not filter to zero');
   }
   observations.push(item);
  }
  if(errors.length||network.length)throw Error('Static documents emitted page errors or network requests');
  await context.close();
 }
}finally{await browser.close();}
await writeFile(join(out,'verification.json'),JSON.stringify({scope:'Static documentation rendering only; no trading-app verification or desktop takeover.',browser:'isolated headless Chromium',passed:true,observations,external_requests:0,page_errors:0},null,2)+'\n');
console.log(JSON.stringify({passed:true,rendered_pages:observations.length,profiles:2,external_requests:0,page_errors:0,report:join(out,'verification.json').replace(root+'\\','').replace(root+'/','')}));
