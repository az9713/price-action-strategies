let token='';
export async function api(path:string,options:RequestInit={},retried=false):Promise<any> {
  if(!token){const session=await fetch('/api/session');if(!session.ok)throw Error('Cannot connect to the local research service.');token=(await session.json()).token;}
  const headers=new Headers(options.headers);headers.set('X-Lab-Token',token);
  if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json');
  const response=await fetch('/api'+path,{...options,headers});
  if(!response.ok){let text;try{const v=await response.json();text=Array.isArray(v.detail)?v.detail.map((e:any)=>e.loc.join('.')+': '+e.msg).join('\n'):v.detail;}catch{text='Local request failed ('+response.status+').';}
    if(response.status===403&&text==='Local session token required.'&&!retried){token='';return api(path,options,true);}
    throw Error(text);}
  return response.status===204?null:response.json();
}
export const post=(path:string,value:unknown={})=>api(path,{method:'POST',body:JSON.stringify(value)});
