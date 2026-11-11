"""Offline presenter assets kept in the hashed Python source inventory."""
CSS=r'''
:root{color-scheme:dark;font-family:"Segoe UI",sans-serif;background:#050811;color:#f4f7fc}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}button{font:inherit;cursor:pointer;color:#dbe6f5;background:#152237;border:1px solid #35506b;border-radius:8px;padding:10px 17px}button:hover{background:#213b52}button:focus-visible{outline:3px solid #f4bf62;outline-offset:4px}[hidden]{display:none!important}#stage{position:absolute;width:1920px;height:1080px;transform-origin:top left;background:#0b0f1a;overflow:hidden}#slide{position:absolute;inset:0}.eyebrow{position:absolute;left:90px;top:65px;font:22px Consolas,monospace;letter-spacing:4px;text-transform:uppercase;color:#e7b35d}h1{position:absolute;top:102px;left:90px;margin:0;font-size:62px;line-height:1.15;font-weight:650;max-width:1720px}.subtitle{position:absolute;left:90px;top:192px;font-size:26px;color:#acb9ce;white-space:nowrap;max-width:1740px;margin:0}.chart{position:absolute;left:90px;top:290px;width:1230px;height:500px}.stat{position:absolute;left:1440px;width:380px}.stat-label{font-size:22px;color:#a7b6ca;margin-bottom:10px}.stat-value{font:54px Consolas,monospace;color:#62dce5}.negative{color:#ff929b!important}.positive{color:#8fdbaf!important}.stat small{font-size:19px;display:block;color:#a7b6ca}.conclusion{position:absolute;left:90px;top:830px;width:1220px;font-size:26px;line-height:1.4;margin:0}.notes{position:absolute;left:90px;top:915px;width:1220px;font-size:20px;line-height:1.5;color:#9baec8}.notes p{margin:0 0 5px}.concept{position:absolute;left:90px;top:300px;width:1220px;display:grid;gap:20px}.concept p{margin:0;padding:24px 30px;background:#101a2b;border:1px solid #26354d;border-radius:18px;font-size:29px;line-height:1.35}.concept strong{display:inline-block;color:#e7b35d;font:25px Consolas,monospace;margin-right:25px}#controls{position:absolute;left:90px;bottom:22px;display:flex;gap:12px;font-size:17px;z-index:5}#camera-guide{position:absolute;right:0;bottom:0;width:520px;height:368px;border:2px dashed #677a93;border-radius:30px 0 0 0;display:flex;align-items:center;justify-content:center;color:#899ab2;font-size:22px;background:#0b0f1a;z-index:3}#pointer{position:absolute;width:34px;height:34px;margin:-17px;border:3px solid #f4bf62;border-radius:50%;pointer-events:none;z-index:10;display:none}#annotations{position:absolute;inset:0;width:1920px;height:1080px;pointer-events:none;z-index:8}.mark{stroke:#ffe26f;stroke-width:12;stroke-linecap:round;fill:none;opacity:.8}.mark.fading{transition:opacity 1s;opacity:0}dialog{position:absolute;left:100px;top:90px;margin:0;width:1160px;max-height:820px;border:1px solid #49617e;border-radius:18px;background:#101a2b;color:#f4f7fc;padding:30px;font-size:24px}dialog::backdrop{background:#050811d9}dialog h2{margin:0 0 20px}#sections{display:grid;gap:10px;margin-top:20px;max-height:650px;overflow:auto}#sections button{text-align:left}svg text{font-family:Consolas,monospace;fill:#a9b9ce}.build{animation:reveal .6s ease both}@keyframes reveal{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}@media(prefers-reduced-motion:reduce){.build{animation:none}.mark.fading{transition:none}}
'''

RUNTIME=r'''
'use strict';
const deck=JSON.parse(document.getElementById('presentation-manifest').textContent);
const stage=document.getElementById('stage'),slide=document.getElementById('slide'),menu=document.getElementById('menu');
const ns='http://www.w3.org/2000/svg';let index=0,scale=1,drawing=null,revision=0;
const el=(tag,cls)=>{const node=document.createElement(tag);if(cls)node.className=cls;return node;};
const svg=(tag,attrs={})=>{const node=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));return node;};
const fact=r=>deck.facts[r.fact];
function copy(node,parts){for(const part of (Array.isArray(parts)?parts:[parts])){if(part&&typeof part==='object'&&'fact'in part){const f=fact(part),span=el('span');span.textContent=f.text;span.dataset.fact=part.fact;span.title=f.source+' : '+JSON.stringify(f.path);node.append(span);}else node.append(document.createTextNode(String(part)));}return node;}
function text(parent,x,y,parts,size=18,attrs={}){const node=svg('text',{x,y,'font-size':size,...attrs});for(const part of (Array.isArray(parts)?parts:[parts])){const span=svg('tspan');if(part&&typeof part==='object'&&'fact'in part){span.textContent=fact(part).text;span.dataset.fact=part.fact;}else span.textContent=String(part);node.append(span);}parent.append(node);return node;}
const value=r=>fact(r).value===null?null:Number(fact(r).value);
const signClass=n=>n===null?'':n<0?'negative':n>0?'positive':'';
function chart(data){const root=svg('svg',{viewBox:'0 0 1230 500',role:'img','aria-label':'Saved research values'});root.classList.add('chart','build');
 const axis=()=>root.append(svg('path',{d:'M90 30 V440 H1200',stroke:'#30435d',fill:'none'}));
 if(data.kind==='line'||data.kind==='columns'){
  axis();const points=data.points,valid=points.filter(p=>value(p.y)!==null);if(!valid.length){text(root,170,240,['No eligible saved observations'],26);return root;}
  let minimum=Math.min(...valid.map(p=>value(p.y))),maximum=Math.max(...valid.map(p=>value(p.y)));
  if(data.kind==='columns'){minimum=Math.min(0,minimum);maximum=Math.max(0,maximum);}
  const span=maximum-minimum||Math.max(Math.abs(maximum)*.02,1),lo=minimum-span*.08,hi=maximum+span*.08;
  const y=v=>430-(v-lo)/(hi-lo)*380,x=i=>105+i/Math.max(points.length-1,1)*1080;
  if(data.kind==='line'){
   let path='',gap=true;for(let i=0;i<points.length;i++){const n=value(points[i].y);if(n===null){gap=true;continue;}path+=(gap?'M':'L')+x(i)+' '+y(n)+' ';gap=false;}
   root.append(svg('path',{d:path,stroke:'#62dce5','stroke-width':4,fill:'none'}));
  }
  for(let i=0;i<points.length;i++){const p=points[i],n=value(p.y);if(n===null)continue;let mark;
   if(data.kind==='columns'){const yy=y(n),zero=y(0);mark=svg('rect',{x:x(i)-Math.max(1,440/points.length),y:Math.min(yy,zero),width:Math.max(2,880/points.length),height:Math.max(2,Math.abs(yy-zero)),fill:n<0?'#ff929b':'#8fdbaf'});}
   else mark=svg('circle',{cx:x(i),cy:y(n),r:points.length>500?1:4,fill:'#62dce5'});
   mark.dataset.fact=p.y.fact;mark.dataset.xFact=p.x.fact;const title=svg('title');title.textContent=fact(p.x).text+' : '+fact(p.y).text;mark.append(title);root.append(mark);
  }
  const minRef=valid.reduce((a,b)=>value(a.y)<value(b.y)?a:b).y,maxRef=valid.reduce((a,b)=>value(a.y)>value(b.y)?a:b).y;
  text(root,100,20,[maxRef],20);text(root,100,475,[minRef],20);text(root,350,475,[points[0].x,' to ',points.at(-1).x],20);
 }else if(data.kind==='bars'){
  const rows=data.rows,nums=rows.map(r=>value(r.value)).filter(n=>n!==null),lo=Math.min(0,...nums),hi=Math.max(0,...nums),width=hi-lo||1;
  const x=n=>500+(n-lo)/width*580,zero=x(0);root.append(svg('path',{d:'M'+zero+' 20 V455',stroke:'#425671'}));
  rows.forEach((r,i)=>{const y=40+i*(390/Math.max(rows.length,1)),n=value(r.value);text(root,8,y+24,r.label,23);if(n!==null)root.append(svg('rect',{x:Math.min(x(n),zero),y,width:Math.max(3,Math.abs(x(n)-zero)),height:38,rx:4,fill:n<0?'#ff929b':'#62dce5'}));text(root,1090,y+26,[r.value],22);});
 }else if(data.kind==='differences'){
  const nums=data.rows.flatMap(r=>[value(r.value),value(r.low),value(r.high)]).filter(n=>n!==null),lo=Math.min(0,...nums),hi=Math.max(0,...nums),width=hi-lo||1,x=n=>825+(n-lo)/width*265;
  root.append(svg('path',{d:'M'+x(0)+' 10 V480',stroke:'#405670','stroke-dasharray':'4 5'}));
  data.rows.forEach((r,i)=>{const y=20+i*78;text(root,8,y,r.label,15);
   text(root,8,y+29,['Real ',r.real,' | Comparison ',r.control,' | Samples ',r.real_n,' / ',r.control_n],17);
   text(root,8,y+53,[r.status],15);const n=value(r.value),l=value(r.low),h=value(r.high);
   if(l!==null&&h!==null)root.append(svg('path',{d:'M'+x(l)+' '+(y+26)+' H'+x(h),stroke:'#a3b7cf','stroke-width':3}));
   if(n!==null)root.append(svg('circle',{cx:x(n),cy:y+26,r:6,fill:n<0?'#ff929b':'#62dce5','data-fact':r.value.fact}));
   text(root,1100,y+30,[r.value],20);text(root,825,y+57,[r.low,' to ',r.high],14);
  });
 }
 return root;
}
function resize(){scale=Math.min(innerWidth/1920,innerHeight/1080);stage.style.transform='scale('+scale+')';stage.style.left=((innerWidth-1920*scale)/2)+'px';stage.style.top=((innerHeight-1080*scale)/2)+'px';}
function show(next,updateHash=true){index=Math.max(0,Math.min(deck.pages.length-1,next));const p=deck.pages[index];slide.replaceChildren();document.getElementById('annotations').replaceChildren();
 const eyebrow=el('div','eyebrow');eyebrow.textContent=p.section;slide.append(eyebrow);
 const title=el('h1','build');title.textContent=p.title;slide.append(title);
 const subtitle=copy(el('p','subtitle'),p.subtitle);slide.append(subtitle);
 const conclusion=el('p','conclusion build');conclusion.textContent=p.conclusion;slide.append(conclusion);
 if(p.chart.kind==='concept'){
  const cards=el('div','concept');p.notes.forEach((parts,i)=>{const card=el('p','build'),badge=el('strong');badge.textContent=String(i+1);badge.dataset.structure='concept-order';card.append(badge);copy(card,parts);cards.append(card);});slide.append(cards);
 }else{
  slide.append(chart(p.chart));const notes=el('div','notes');p.notes.forEach(parts=>notes.append(copy(el('p'),parts)));slide.append(notes);
 }
 p.stats.forEach((s,i)=>{const stat=el('aside','stat build');stat.style.top=(300+i*195)+'px';const label=el('div','stat-label');label.textContent=s.label;stat.append(label);const large=copy(el('div','stat-value '+signClass(value(s.value))),s.value);stat.append(large);slide.append(stat);for(let size=54;large.scrollWidth>380&&size>16;size--)large.style.fontSize=(size-1)+'px';});
 if(updateHash)history.replaceState(null,'','#'+(index+1));document.getElementById('previous').disabled=index===0;document.getElementById('next').disabled=index===deck.pages.length-1;
 document.getElementById('live').textContent=p.section+': '+p.title;stage.dataset.page=String(index+1);stage.dataset.revision=String(++revision);
 // Keep the entire subtitle on one line without truncating its source text.
 for(let size=26;subtitle.scrollWidth>1740&&size>16;size--)subtitle.style.fontSize=(size-1)+'px';
}
function jumpHash(){const matched=/^#([1-9][0-9]*)$/.exec(location.hash);show(matched?Number(matched[1])-1:0,false);}
function toggleMenu(){if(menu.open){menu.close();return;}menu.showModal();document.getElementById('close-menu').focus();}
function replay(){slide.querySelectorAll('.build').forEach(n=>{n.classList.remove('build');void n.getBoundingClientRect();n.classList.add('build');});stage.dataset.revision=String(++revision);}
function camera(){const guide=document.getElementById('camera-guide');guide.hidden=!guide.hidden;document.getElementById('camera-toggle').setAttribute('aria-pressed',String(!guide.hidden));}
const sections=document.getElementById('sections');let prior='';deck.pages.forEach((p,i)=>{if(p.section!==prior){const b=el('button');b.textContent=p.section+' : '+p.title;b.addEventListener('click',()=>{menu.close();show(i);});sections.append(b);prior=p.section;}});
document.getElementById('previous').addEventListener('click',()=>show(index-1));document.getElementById('next').addEventListener('click',()=>show(index+1));document.getElementById('menu-toggle').addEventListener('click',toggleMenu);document.getElementById('close-menu').addEventListener('click',()=>menu.close());document.getElementById('replay').addEventListener('click',replay);document.getElementById('camera-toggle').addEventListener('click',camera);
document.getElementById('manifest-download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([document.getElementById('presentation-manifest').textContent],{type:'application/json'})),a=el('a');a.href=url;a.download='presentation-provenance.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
addEventListener('keydown',e=>{if(e.altKey||e.ctrlKey||e.metaKey||e.repeat)return;if(menu.open){if(e.key==='m'||e.key==='M'){e.preventDefault();menu.close();}return;}if(e.target instanceof HTMLButtonElement&&[' ','Enter'].includes(e.key))return;let handled=true;
 switch(e.key){case 'ArrowRight':case 'ArrowDown':case ' ':case 'PageDown':show(index+1);break;case 'ArrowLeft':case 'ArrowUp':case 'PageUp':show(index-1);break;case 'Home':show(0);break;case 'End':show(deck.pages.length-1);break;case 'm':case 'M':toggleMenu();break;case 'r':case 'R':replay();break;case 'f':case 'F':camera();break;default:handled=false;}if(handled)e.preventDefault();});
function position(e){const rect=stage.getBoundingClientRect();return {x:(e.clientX-rect.x)/scale,y:(e.clientY-rect.y)/scale};}
stage.addEventListener('pointermove',e=>{const p=position(e),ring=document.getElementById('pointer');ring.style.display='block';ring.style.left=p.x+'px';ring.style.top=p.y+'px';if(drawing){drawing.points.push(p.x+','+p.y);drawing.node.setAttribute('points',drawing.points.join(' '));}});
stage.addEventListener('pointerdown',e=>{if(e.button!==0||e.target.closest('button,dialog,a'))return;const p=position(e),node=svg('polyline',{points:p.x+','+p.y});node.classList.add('mark');document.getElementById('annotations').append(node);drawing={node,points:[p.x+','+p.y]};stage.setPointerCapture(e.pointerId);});
function finish(){if(!drawing)return;const node=drawing.node;drawing=null;setTimeout(()=>node.classList.add('fading'),2500);setTimeout(()=>node.remove(),3600);}
stage.addEventListener('pointerup',finish);stage.addEventListener('pointercancel',finish);stage.addEventListener('pointerleave',()=>{if(!drawing)document.getElementById('pointer').style.display='none';});
addEventListener('resize',resize);addEventListener('hashchange',jumpHash);resize();jumpHash();
'''
