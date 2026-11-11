"""Versioned scheduled-news inputs. Never market-price or credential IO."""
from datetime import date,datetime,timezone
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Annotated,Literal
from zoneinfo import ZoneInfo
import calendar
import csv
import hashlib
import json
import math
import os
import re
import tempfile
import time
import uuid
from urllib.parse import urlsplit
import httpx
from pydantic import AfterValidator,BeforeValidator,Field,model_validator,field_validator
from .config import Contract,identity,canonical
from .data import DataError,atomic_json

Kind=Literal['cpi','jobs','fed','custom']
NY=ZoneInfo('America/New_York')
MAX_SOURCE=2*1024*1024
MAX_TOTAL=16*1024*1024
FED_URL='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'


def _calendar_date(value):
    if type(value) is date:return value
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('News dates require explicit YYYY-MM-DD calendar dates.')
    return value


def _known_input(value):
    if value is None or isinstance(value,datetime):return value
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:[Zz]|[+-]\d{2}:\d{2})',value):
        raise ValueError('News knowledge time requires explicit ISO date/time and timezone, at most microsecond precision.')
    return value


def _clean_name(value):
    if not value.strip() or any(ord(c)<32 for c in value):raise ValueError('News calendar name must contain text without control characters.')
    return value.strip()


CalendarDate=Annotated[date,BeforeValidator(_calendar_date)]
NewsName=Annotated[str,AfterValidator(_clean_name)]


def validate_source(source,official=False):
    try:
        if not isinstance(source,dict) or set(source)!={'sha256','bytes','url','acquired_at'}:raise ValueError()
        if not isinstance(source['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',source['sha256']):raise ValueError()
        if type(source['bytes']) is not int or not 0<=source['bytes']<=MAX_SOURCE:raise ValueError()
        url=source['url'];at=source['acquired_at']
        if url is not None:
            if not isinstance(url,str) or any(c.isspace() or ord(c)<32 for c in url):raise ValueError()
            u=urlsplit(url)
            if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError()
            u.port  # Validate a supplied port without fetching the citation.
        if at is not None:
            if not isinstance(at,str):raise ValueError()
            _known_input(at);when=datetime.fromisoformat(at.upper().replace('Z','+00:00'))
            if when.utcoffset() is None:raise ValueError()
        if official and (url is None or at is None):raise ValueError()
    except (ValueError,TypeError,KeyError):raise DataError('News source metadata is invalid.') from None
    return source


class NewsEvent(Contract):
    date:CalendarDate
    kind:Kind
    label:str=Field(min_length=1,max_length=160)
    known_at:datetime|None=None
    @field_validator('known_at',mode='before')
    @classmethod
    def explicit_known(cls,value):return _known_input(value)
    @field_validator('known_at')
    @classmethod
    def aware(cls,value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:raise ValueError('News knowledge time requires an explicit timezone.')
            return value.astimezone(timezone.utc)
        return value
    @field_validator('label')
    @classmethod
    def clean_label(cls,value):
        if any(ord(c)<32 for c in value):raise ValueError('News labels cannot contain control characters.')
        if not value.strip():raise ValueError('News label is empty.')
        return value.strip()


class NewsCalendar(Contract):
    name:NewsName=Field(min_length=1,max_length=100)
    start:CalendarDate
    end:CalendarDate
    mode:Literal['retrospective','asof','synthetic']='retrospective'
    kinds:list[Kind]=Field(default_factory=lambda:['cpi','jobs','fed'],min_length=1,max_length=4)
    complete:bool=False
    events:list[NewsEvent]=Field(default_factory=list,max_length=10000)
    note:str=Field('',max_length=1000)
    @model_validator(mode='after')
    def valid(self):
        if self.start>self.end or (self.end-self.start).days>3660:raise ValueError('Calendar coverage must be ordered and at most ten years.')
        if len(set(self.kinds))!=len(self.kinds):raise ValueError('News kinds must be distinct.')
        seen=set()
        for event in self.events:
            key=(event.date,event.kind,event.label if event.kind=='custom' else '')
            if key in seen:raise ValueError('Duplicate or conflicting news event.')
            seen.add(key)
            if not self.start<=event.date<=self.end or event.kind not in self.kinds:raise ValueError('Event falls outside declared coverage or selected kinds.')
            if self.mode=='asof' and event.known_at is None:raise ValueError('As-of events require recorded knowledge times.')
            if self.mode=='retrospective' and event.known_at is not None:raise ValueError('Retrospective dates cannot masquerade as recorded knowledge times.')
        object.__setattr__(self,'kinds',sorted(self.kinds))
        object.__setattr__(self,'events',sorted(self.events,key=lambda e:(e.date,e.kind,e.label)))
        return self


class NewsDownload(Contract):
    name:NewsName=Field('Official scheduled news',min_length=1,max_length=100)
    start:CalendarDate
    end:CalendarDate
    kinds:list[Literal['cpi','jobs','fed']]=Field(default_factory=lambda:['cpi','jobs','fed'],min_length=1,max_length=3)
    @model_validator(mode='after')
    def valid(self):
        if self.start>self.end or self.start.year<2021 or (self.end-self.start).days>3660:
            raise ValueError('Choose ordered official calendar dates from2021, spanning at most ten years.')
        if len(set(self.kinds))!=len(self.kinds):raise ValueError('News kinds must be distinct.')
        object.__setattr__(self,'kinds',sorted(self.kinds));return self


class NewsClock:
    def __init__(self,spec:NewsCalendar):
        self.spec=spec;self.days={}
        for e in spec.events:
            day=e.date.isoformat()
            if day not in self.days:self.days[day]=e.known_at
            elif e.known_at is None or (self.days[day] is not None and e.known_at<self.days[day]):self.days[day]=e.known_at
    def is_news(self,when):
        if when.tzinfo is None:raise DataError('News decisions require an explicit timezone.')
        day=when.astimezone(NY).date().isoformat()
        return day in self.days and (self.days[day] is None or when>=self.days[day])


def news_active(value,when):
    if isinstance(value,NewsClock):return value.is_news(when)
    return when.astimezone(NY).date().isoformat() in (value or set())


def news_weight(mode,value,when):
    if mode=='trade':return 1.
    if value is None:raise DataError('This news filter needs a versioned news calendar.')
    return (0. if mode=='skip' else .5) if news_active(value,when) else 1.


def event_dates(value):return sorted(value.days) if isinstance(value,NewsClock) else None if value is None else sorted(str(x) for x in value)


def news_assumptions(snapshot):
    if snapshot is None:return []
    mode=snapshot['spec']['mode']
    text={'retrospective':'Historical advance knowledge of reconstructed scheduled-news dates is assumed; this is not point-in-time publication evidence.',
          'asof':'News eligibility uses the supplied recorded knowledge timestamp at each confirmation; those timestamps are an input assumption.',
          'synthetic':'News events are a synthetic testing scenario.'}[mode]
    return [text,'News skip/half affects new signal eligibility/planned risk; it does not force existing positions to close.']


def strict_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise DataError('Duplicate JSON news field.')
            out[k]=v
        return out
    def finite(text):
        value=float(text)
        if not math.isfinite(value):raise DataError('Nonfinite news JSON.')
        return value
    try:return json.loads(raw,object_pairs_hook=pairs,parse_float=finite,parse_constant=lambda _:(_ for _ in ()).throw(DataError('Nonfinite news JSON.')))
    except (ValueError,UnicodeError,RecursionError) as exc:raise DataError('Malformed news JSON.') from exc


class NewsStore:
    def __init__(self,root):
        self.workspace=Path(root).resolve();self.root=(self.workspace/'data/news').resolve()
        if not self.root.is_relative_to(self.workspace):raise DataError('Calendar storage escapes the workspace.')
        (self.root/'calendars').mkdir(parents=True,exist_ok=True);(self.root/'sources').mkdir(exist_ok=True)
    def inside(self,path):
        p=path.resolve()
        if not p.is_relative_to(self.root):raise DataError('Calendar path escapes its storage root.')
        return p
    def calendar_path(self,cid):
        if not isinstance(cid,str) or not re.fullmatch('[a-f0-9]{64}',cid):raise DataError('Invalid news calendar identifier.')
        return self.inside(self.root/'calendars'/(cid+'.json'))
    def source_path(self,digest):
        if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):raise DataError('Invalid news source hash.')
        return self.inside(self.root/'sources'/(digest+'.bin'))
    def publish(self,path,raw):
        path=self.inside(path)
        fd,name=tempfile.mkstemp(prefix='.news-',suffix='.tmp',dir=path.parent);temp=Path(name)
        try:
            with os.fdopen(fd,'wb') as f:f.write(raw)
            try:os.link(temp,path)
            except FileExistsError:
                if path.read_bytes()!=raw:raise DataError('Immutable news content was modified.')
        finally:temp.unlink(missing_ok=True)
    def source(self,raw,url=None,acquired_at=None):
        if not isinstance(raw,bytes) or len(raw)>MAX_SOURCE:raise DataError('News source exceeds two MiB.')
        digest=hashlib.sha256(raw).hexdigest();path=self.source_path(digest)
        source=validate_source(dict(sha256=digest,bytes=len(raw),url=url,acquired_at=acquired_at))
        self.publish(path,raw)
        return source
    def save(self,spec:NewsCalendar,sources=None,origin='user_json'):
        spec=NewsCalendar(**spec.model_dump())
        if origin not in {'user_json','user_csv','official'}:raise DataError('Unsupported news source origin.')
        if sources is None:sources=[self.source(canonical(spec.model_dump(mode='json')).encode())]
        if not isinstance(sources,list) or not 1<=len(sources)<=128:raise DataError('News source inventory is invalid.')
        for s in sources:
            validate_source(s,origin=='official')
            raw=self.source_path(s['sha256']).read_bytes()
            if len(raw)!=s['bytes'] or hashlib.sha256(raw).hexdigest()!=s['sha256']:raise DataError('News source integrity check failed before publication.')
        document=dict(version=1,spec=spec.model_dump(mode='json'),origin=origin,sources=sources)
        cid=identity(document);path=self.calendar_path(cid);value=dict(id=cid,**document)
        self.publish(path,canonical(value).encode())
        return self.load(cid)
    def load(self,cid,verify_sources=True):
        try:
            value=strict_json(self.calendar_path(cid).read_bytes())
            if set(value)!={'id','version','spec','origin','sources'} or value['version']!=1 or value['id']!=cid or identity({k:v for k,v in value.items() if k!='id'})!=cid:
                raise DataError('News calendar integrity check failed.')
            NewsCalendar(**value['spec'])
            if value['origin'] not in {'user_json','user_csv','official'} or not isinstance(value['sources'],list) or not 1<=len(value['sources'])<=128:raise DataError('News source inventory is invalid.')
            for s in value['sources']:
                validate_source(s,value['origin']=='official')
                path=self.source_path(s['sha256'])
                if verify_sources:
                    raw=path.read_bytes()
                    if len(raw)!=s['bytes'] or hashlib.sha256(raw).hexdigest()!=s['sha256']:raise DataError('News source integrity check failed.')
            return value
        except DataError:raise
        except (OSError,ValueError,TypeError,KeyError) as exc:raise DataError('News calendar or source is missing or invalid.') from exc
    def list(self):
        out=[]
        for p in sorted((self.root/'calendars').glob('*.json')):
            try:
                v=self.load(p.stem,False);s=v['spec']
                out.append(dict(id=p.stem,**{k:s[k] for k in ['name','start','end','mode','kinds','complete']},events=len(s['events']),origin=v['origin'],sources=len(v['sources'])))
            except DataError:out.append(dict(id=p.stem,error='Stored calendar is invalid; cannot be used.'))
        return out
    def clock(self,cid,start,end,snapshot=None):
        value=self.load(cid)
        if snapshot is not None and value!=snapshot:raise DataError('Frozen news calendar snapshot changed.')
        spec=NewsCalendar(**value['spec'])
        if not spec.complete or str(spec.start)>str(start) or str(spec.end)<str(end):raise DataError('A complete news calendar must cover the entire evaluation window.')
        return NewsClock(spec)


def parse_csv(raw,metadata):
    if len(raw)>MAX_SOURCE:raise DataError('News CSV exceeds two MiB.')
    try:
        reader=csv.DictReader(StringIO(raw.decode('utf-8-sig')))
        fields=reader.fieldnames
        if not fields or len(fields)!=len(set(fields)) or not {'date','kind','label'}<=set(fields) or set(fields)-{'date','kind','label','known_at'}:
            raise DataError('News CSV needs unique date,kind,label and optional known_at columns.')
        rows=[]
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise DataError('News CSV row has the wrong column count.')
            rows.append({k:v for k,v in row.items() if k!='known_at' or v.strip()})
            if len(rows)>10000:raise DataError('News CSV exceeds ten thousand events.')
        return NewsCalendar(**(metadata|dict(events=rows)))
    except (UnicodeError,csv.Error) as exc:raise DataError('Malformed UTF-8 news CSV.') from exc


class _BLS(HTMLParser):
    def __init__(self):super().__init__();self.cells=[];self.cell=None;self.paragraph=None;self.headers=[];self.header=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in {'h1','title'}:self.header=[]
        if tag=='td' and re.fullmatch(r'd\d{4}',a.get('id','')):self.cell=dict(id=a['id'],paragraphs=[])
        if tag=='p' and self.cell is not None:self.paragraph=[]
        if tag=='br' and self.paragraph is not None:self.paragraph.append(' ')
    def handle_data(self,data):
        if self.header is not None:self.header.append(data)
        if self.paragraph is not None:self.paragraph.append(data)
    def handle_endtag(self,tag):
        if tag in {'h1','title'} and self.header is not None:self.headers.append(' '.join(''.join(self.header).split()));self.header=None
        if tag=='p' and self.paragraph is not None:
            self.cell['paragraphs'].append(' '.join(''.join(self.paragraph).split()));self.paragraph=None
        if tag=='td' and self.cell is not None:self.cells.append(self.cell);self.cell=None;self.paragraph=None


def parse_bls(raw,year,month,kinds):
    try:
        parser=_BLS();parser.feed(raw.decode('utf-8'));expected=calendar.month_name[month]+' '+str(year)
        if not any(expected in h for h in parser.headers) or not parser.cells:raise DataError('BLS calendar title or date grid changed.')
        events=[];names={'cpi':'Consumer Price Index','jobs':'Employment Situation'}
        for cell in parser.cells:
            if int(cell['id'][1:3])!=month:continue
            day=date(year,month,int(cell['id'][3:])).isoformat()
            for text in cell['paragraphs']:
                for kind,name in names.items():
                    if kind in kinds and re.match(re.escape(name)+r'(?:\s|$)',text):
                        if not re.search(r'\b\d{1,2}:\d{2}\s+[AP]M\b',text):raise DataError('BLS event time is missing.')
                        events.append(dict(date=day,kind=kind,label=name))
        if any(not any(e['kind']==k for e in events) for k in kinds if k in names):raise DataError('Selected BLS events are absent; inspect source or import a reviewed calendar.')
        return events
    except (UnicodeError,ValueError) as exc:raise DataError('BLS calendar format is invalid.') from exc


class _Fed(HTMLParser):
    def __init__(self):super().__init__();self.depth=0;self.year=None;self.heading=None;self.row=None;self.part=None;self.rows=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h4':self.heading=[]
        if tag=='div':
            self.depth+=1;classes=a.get('class','').split()
            if 'fomc-meeting' in classes:self.row=dict(year=self.year,depth=self.depth,month='',days='')
            if self.row is not None:
                if 'fomc-meeting__month' in classes:self.part=('month',self.depth)
                elif 'fomc-meeting__date' in classes:self.part=('days',self.depth)
    def handle_data(self,data):
        if self.heading is not None:self.heading.append(data)
        if self.row is not None and self.part:self.row[self.part[0]]+=data
    def handle_endtag(self,tag):
        if tag=='h4' and self.heading is not None:
            m=re.search(r'(\d{4}) FOMC Meetings',''.join(self.heading));self.year=int(m[1]) if m else None;self.heading=None
        if tag=='div':
            if self.part and self.part[1]==self.depth:self.part=None
            if self.row is not None and self.row['depth']==self.depth:self.rows.append(self.row);self.row=None
            self.depth-=1


def parse_fed(raw,year):
    try:
        p=_Fed();p.feed(raw.decode('utf-8'));months={name.lower():i for i in range(1,13) for name in [calendar.month_name[i],calendar.month_abbr[i]]}
        events=[]
        for row in p.rows:
            days=''.join(row['days'].split())
            if row['year']!=year or not re.fullmatch(r'\d{1,2}(?:-\d{1,2})?\*?',days):continue
            tokens=[months[t.lower()] for t in re.findall('[A-Za-z]+',row['month']) if t.lower() in months]
            if not tokens:raise DataError('Fed meeting month is unrecognized.')
            day=int(days.rstrip('*').split('-')[-1]);when=date(year,tokens[-1],day).isoformat()
            events.append(dict(date=when,kind='fed',label='Scheduled Fed decision'))
        if len(events)!=8 or len({e['date'] for e in events})!=8:raise DataError('Expected eight scheduled Fed decisions; inspect changed or unavailable source.')
        return sorted(events,key=lambda e:e['date'])
    except (ValueError,UnicodeError) as exc:raise DataError('Fed calendar format is invalid.') from exc


def _check_cancel(cancel):
    if cancel and cancel():raise InterruptedError('News acquisition canceled; no complete calendar published.')


def fetch_document(url,cancel=None):
    allowed=url==FED_URL or re.fullmatch(r'https://www\.bls\.gov/schedule/\d{4}/(?:0[1-9]|1[0-2])_sched\.htm',url)
    if not allowed:raise DataError('News downloads use allowlisted official calendar URLs only.')
    for attempt in range(3):
        _check_cancel(cancel)
        try:
            with httpx.Client(timeout=3,follow_redirects=False,trust_env=False,headers={'User-Agent':'PriceActionResearchLab/0.1 calendar research'}) as client:
                with client.stream('GET',url) as response:
                    status=response.status_code
                    if status==200:
                        if 'text/html' not in response.headers.get('content-type',''):raise DataError('Official calendar returned an unexpected content type.')
                        chunks=[];size=0
                        for chunk in response.iter_bytes():
                            _check_cancel(cancel);size+=len(chunk)
                            if size>MAX_SOURCE:raise DataError('Official calendar exceeds two MiB.')
                            chunks.append(chunk)
                        return b''.join(chunks)
                    retry=status==429 or 500<=status<=599
                    if not retry:raise DataError('Official calendar request failed with HTTP '+str(status)+'.')
        except httpx.HTTPError:
            if attempt==2:raise DataError('Official calendar request timed out or failed; no complete calendar published.') from None
        if attempt<2:
            until=time.monotonic()+.5*(2**attempt)
            while time.monotonic()<until:_check_cancel(cancel);time.sleep(.05)
    raise DataError('Official calendar retry budget exhausted; no complete calendar published.')


def acquire_calendar(root,request:NewsDownload,cancel=None,progress=None,checkpoint_dir=None,committed=None,commit=None):
    request_hash=identity(request.model_dump(mode='json'))
    store=NewsStore(root);base=Path(checkpoint_dir) if checkpoint_dir else store.root/'acquisitions'/uuid.uuid4().hex
    base=base.resolve()
    if not base.is_relative_to(Path(root).resolve()/'data'):raise DataError('News checkpoint escapes local data storage.')
    base.mkdir(parents=True,exist_ok=True);cp=base/'news-documents.json';context=request_hash
    cache=strict_json(cp.read_bytes()) if cp.exists() else dict(request_hash=context,documents={})
    if cache.get('request_hash')!=context or not isinstance(cache.get('documents'),dict):raise DataError('News acquisition checkpoint belongs to different inputs.')
    urls=[];months=[];year,month=request.start.year,request.start.month
    while (year,month)<=(request.end.year,request.end.month):
        months.append((year,month));month+=1
        if month==13:year+=1;month=1
    bls_kinds=[k for k in request.kinds if k in {'cpi','jobs'}]
    if bls_kinds:urls.extend(('https://www.bls.gov/schedule/'+str(y)+'/'+str(m).zfill(2)+'_sched.htm',('bls',y,m)) for y,m in months)
    if 'fed' in request.kinds:urls.append((FED_URL,('fed',)))
    documents=[];events=[];total=0
    for index,(url,task) in enumerate(urls):
        _check_cancel(cancel);saved=cache['documents'].get(url)
        if committed is not None:
            recorded=committed.get(url)
            if saved and recorded and saved!=recorded:raise DataError('News checkpoint differs from its committed document receipt.')
            saved=recorded
        if saved:
            if saved.get('url')!=url:raise DataError('News checkpoint source URL changed.')
            raw=store.source_path(saved['sha256']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=saved['sha256'] or len(raw)!=saved['bytes']:raise DataError('News acquisition source checkpoint was modified.')
        else:
            raw=fetch_document(url,cancel);saved=store.source(raw,url,datetime.now(timezone.utc).isoformat())
            _check_cancel(cancel)
            if commit:commit(url,saved)
        cache['documents'][url]=saved;atomic_json(cp,cache)
        total+=len(raw)
        if total>MAX_TOTAL:raise DataError('Combined calendar sources exceed sixteen MiB; choose a shorter range.')
        documents.append(saved)
        if task[0]=='bls':events.extend(parse_bls(raw,task[1],task[2],bls_kinds))
        else:
            for y in range(request.start.year,request.end.year+1):events.extend(parse_fed(raw,y))
        if progress:progress((index+1)/len(urls),'Verified '+str(index+1)+'/'+str(len(urls))+' official calendar documents.')
    _check_cancel(cancel)
    events=[e for e in events if str(request.start)<=e['date']<=str(request.end)]
    spec=NewsCalendar(name=request.name,start=request.start,end=request.end,mode='retrospective',kinds=request.kinds,complete=True,events=events,
        note="Reconstructed from official pages retrieved now. Historical advance knowledge and coverage of these selected scheduled releases are assumptions; unscheduled news and other releases are excluded.")
    return store.save(spec,documents,'official')
