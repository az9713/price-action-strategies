"""Read-only Alpaca data client with bounded retries and durable page checkpoints."""
from pathlib import Path
from datetime import datetime,timedelta,timezone,date
import json
import time
import httpx
import pandas as pd
from .data import Action,DataError,atomic_json
from .config import identity

class ProviderError(DataError):
    pass

def credentials(path:Path):
    fields={}
    if path.exists():
        for raw in path.read_text(encoding='utf-8-sig').splitlines():
            line=raw.strip()
            if line.startswith('export '): line=line[7:].strip()
            if not line or line.startswith('#') or '=' not in line: continue
            key,value=line.split('=',1);value=value.strip()
            if value[:1] in {'"',"'"} and value[-1:]==value[:1]: value=value[1:-1]
            else: value=value.split(' #',1)[0].strip()
            fields[key.strip()]=value
    key=fields.get('ALPACA_API_KEY') or fields.get('APCA_API_KEY_ID')
    secret=next((fields[x] for x in ['ALPACA_SECRET_KEY','ALPACA_API_SECRET','ALPACA_API_SECRET_KEY','APCA_API_SECRET_KEY'] if fields.get(x)),None)
    if not key or not secret: raise ProviderError('Add the Alpaca key and secret to the local .env file.')
    return key,secret

class Alpaca:
    ALLOWED={'/v2/stocks/bars','/v1/corporate-actions'}
    def __init__(self,env:Path,cache:Path,transport=None):
        self.key,self.secret=credentials(env)
        self.cache=cache
        self.client=httpx.Client(base_url='https://data.alpaca.markets',
            headers={'APCA-API-KEY-ID':self.key,'APCA-API-SECRET-KEY':self.secret},
            follow_redirects=False,timeout=8,transport=transport)
        self.last_request=0.
        self.last_query_receipt={}
    def close(self): self.client.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    def _request(self,path,params,cancel=None):
        if path not in self.ALLOWED: raise ProviderError('Only approved read-only data endpoints are permitted.')
        for attempt in range(5):
            if cancel and cancel(): raise InterruptedError('Download canceled.')
            wait=max(0,.31-(time.monotonic()-self.last_request))
            if wait: time.sleep(wait)
            self.last_request=time.monotonic()
            try:
                response=self.client.get(path,params=params)
            except httpx.TransportError:
                if attempt==4: raise ProviderError('Data provider connection timed out or failed. Retry the saved download.') from None
            else:
                if response.status_code==200:
                    try: return response.json()
                    except ValueError: raise ProviderError('Data provider returned invalid JSON.') from None
                if response.status_code not in {429,500,502,503,504}:
                    # Do not echo response body, headers, request objects or credentials.
                    raise ProviderError(f'Data provider rejected the request (HTTP {response.status_code}). Check credentials, feed entitlement and parameters. No alternate feed was substituted.')
                if attempt==4: raise ProviderError(f'Data provider temporarily unavailable (HTTP {response.status_code}). Saved pages can be resumed.')
            # Small cancel-aware waits keep the worker responsive during rate limiting.
            for _ in range(min(2**attempt,8)*4):
                if cancel and cancel(): raise InterruptedError('Download canceled.')
                time.sleep(.25)
        raise ProviderError('Provider request did not complete.')

    def pages(self,path,params,cancel=None,progress=None):
        query_id=identity({'path':path,'parameters':params})
        folder=self.cache/query_id
        folder.mkdir(parents=True,exist_ok=True)
        token=None;seen=set();index=0
        receipts=[]
        self.last_query_receipt={'query_id':query_id,'complete':False,'pages':receipts}
        while True:
            if cancel and cancel(): raise InterruptedError('Download canceled.')
            target=folder/f'page-{index:06}.json'
            actual={**params,**({'page_token':token} if token else {})}
            if target.exists():
                checkpoint=json.loads(target.read_text(encoding='utf-8'))
                if checkpoint['request_hash']!=identity({'path':path,'parameters':actual}): raise ProviderError('Cached page chain does not match the query; restart with a new data version.')
                body=checkpoint['body']
                if identity(body)!=checkpoint['body_hash']: raise ProviderError('Cached provider response is corrupt.')
                cached=True
            else:
                body=self._request(path,actual,cancel)
                atomic_json(target,dict(request_hash=identity({'path':path,'parameters':actual}),body_hash=identity(body),body=body,
                                        retrieved_at_utc=datetime.now(timezone.utc).isoformat()))
                cached=False
            checkpoint=json.loads(target.read_text(encoding='utf-8'))
            receipts.append({'page':index,'cached':cached,'retrieved_at_utc':checkpoint['retrieved_at_utc'],'body_hash':checkpoint['body_hash']})
            yield body
            index+=1
            if progress: progress({'pages':index,'cached':cached,'query_id':query_id})
            token=body.get('next_page_token')
            if not token:
                self.last_query_receipt['complete']=True
                break
            if token in seen: raise ProviderError('Provider repeated a pagination cursor; refusing a truncated/duplicated result.')
            seen.add(token)

    @staticmethod
    def window(start,end):
        first=date.fromisoformat(start);last=date.fromisoformat(end)
        if first>last: raise ProviderError('Download dates are reversed.')
        begin=datetime.combine(first,datetime.min.time(),tzinfo=timezone.utc)
        # Include the entire ET session, including after UTC midnight where applicable.
        finish=datetime.combine(last+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc)
        finish=min(finish,datetime.now(timezone.utc)-timedelta(minutes=20))
        if begin>=finish: raise ProviderError('Only historical data ending at least 20 minutes ago is requested.')
        return begin.isoformat(),finish.isoformat()

    def bars(self,symbols,start,end,cancel=None,progress=None):
        begin,finish=self.window(start,end)
        params=dict(symbols=','.join(sorted(set(symbols))),timeframe='1Min',start=begin,end=finish,
                    adjustment='raw',feed='sip',sort='asc',limit=10000)
        records=[]
        for body in self.pages('/v2/stocks/bars',params,cancel,progress):
            for symbol,rows in (body.get('bars') or {}).items():
                for row in rows:
                    records.append(dict(symbol=symbol,timestamp=row['t'],open=row['o'],high=row['h'],low=row['l'],close=row['c'],volume=row['v']))
        if not records: raise ProviderError('No historical minute bars returned for these symbols/dates.')
        found={r['symbol'] for r in records}
        absent=set(symbols)-found
        if absent: raise ProviderError('No bars returned for: '+', '.join(sorted(absent)))
        return pd.DataFrame(records),{'provider':'Alpaca','feed':'sip','adjustment':'raw','query':params,
                                     'page_receipt':self.last_query_receipt,
                                     'accessed_at_utc':datetime.now(timezone.utc).isoformat()}

    def corporate_actions(self,symbols,start,end,cancel=None):
        # Endpoint filters by process_date, not ex_date. Widen to include later payments.
        lower=(date.fromisoformat(start)-timedelta(days=30)).isoformat()
        upper=(date.fromisoformat(end)+timedelta(days=120)).isoformat()
        params=dict(symbols=','.join(sorted(set(symbols))),start=lower,end=upper,limit=1000,sort='asc',data_quality='all')
        collected={};pages=0
        for body in self.pages('/v1/corporate-actions',params,cancel):
            pages+=1
            for kind,rows in (body.get('corporate_actions') or {}).items():
                collected.setdefault(kind,[]).extend(rows)
        return collected,{'provider':'Alpaca corporate actions','query':params,'pages':pages,'page_receipt':self.last_query_receipt}

def parse_actions(collected,start,end):
    actions=[];issues=[];seen=set()
    for kind,rows in collected.items():
        for row in rows:
            ex=row.get('ex_date') or row.get('effective_date')
            if not ex:
                issues.append('Corporate action has no effective/ex date: '+kind);continue
            if not start<=ex<=end: continue
            action_id=row.get('id') or identity(row)
            if action_id in seen: continue
            seen.add(action_id)
            try:
                if kind in {'forward_splits','reverse_splits'}:
                    actions.append(Action(row['symbol'],ex,'split',float(row['new_rate'])/float(row['old_rate'])))
                elif kind in {'cash_dividends','capital_gains_distributions'}:
                    if row.get('foreign') or row.get('currency','USD')!='USD':
                        issues.append('Non-USD/foreign distribution needs explicit treatment.');continue
                    actions.append(Action(row['symbol'],ex,'dividend',float(row['rate']),row.get('payable_date')))
                else:
                    issues.append('Unsupported corporate event in the evaluation range: '+kind)
            except (ValueError,KeyError,TypeError,ZeroDivisionError):
                issues.append('Incomplete/invalid corporate action: '+kind)
    return sorted(actions,key=lambda a:(a.ex_date,a.symbol,a.kind)),issues
