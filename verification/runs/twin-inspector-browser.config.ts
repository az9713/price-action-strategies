import base from '../../frontend/playwright.config';
export default {...base,testDir:'./twin-inspector-browser-tests',projects:[
  {name:'desktop1920',use:{viewport:{width:1920,height:1080}}},
  {name:'desktop1280',use:{viewport:{width:1280,height:720}}},
  {name:'mobile390',use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}}
]};
