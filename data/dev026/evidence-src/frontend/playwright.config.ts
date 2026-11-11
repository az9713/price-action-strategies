import {defineConfig} from '@playwright/test';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
// Direct CLI use also retains raw evidence privately. The Python verification
// wrapper derives the sanitized review tree before a receipt records it.
const output=process.env.PA_BROWSER_OUTPUT||'../data/private-evidence/captures/manual-'+Date.now();
// Chrome can move from a per-user install to a machine-wide install. Resolve
// an existing executable explicitly rather than trusting a stale channel path.
const browserPath=process.env.PA_BROWSER_EXECUTABLE||[
  join(process.env.LOCALAPPDATA||'', 'Google/Chrome/Application/chrome.exe'),
  join(process.env.ProgramFiles||'C:/Program Files', 'Google/Chrome/Application/chrome.exe'),
].find(path=>existsSync(path));
export default defineConfig({testDir:'./tests',workers:1,timeout:240000,expect:{timeout:10000},
  outputDir:output+'/artifacts',
  reporter:[['list'],['json',{outputFile:output+'/results.json'}],['junit',{outputFile:output+'/junit.xml'}]],
  use:{baseURL:process.env.PA_BROWSER_BASE_URL||'http://127.0.0.1:8765',channel:browserPath?undefined:'chrome',
    launchOptions:browserPath?{executablePath:browserPath}:{},headless:true,locale:'en-US',timezoneId:'UTC',
    colorScheme:'dark',reducedMotion:'reduce',actionTimeout:15000,trace:'on',screenshot:'on'},
  projects:[{name:'desktop1920',use:{viewport:{width:1920,height:1080}}},{name:'desktop1280',use:{viewport:{width:1280,height:720}}}]});
