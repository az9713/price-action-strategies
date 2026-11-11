"""Deterministic, bounded presenter assembled exclusively from saved output JSON."""
from decimal import Decimal,ROUND_HALF_EVEN,localcontext
import base64
import hashlib
import html
import json
import math
import re
from .presentation_audit import audit_deck,PresentationAuditError
from .presenter_assets import CSS,RUNTIME
from .dataset_context import validate_context
from .data import DataError

MAX_BYTES=32*1024*1024
MAX_SOURCES=16
MAX_PAGES=2048
MAX_FACTS=100000
MAX_POINTS=10000
ROWS_PER_PAGE=6


class PresentationError(ValueError):pass


def format_value(value,style):
    if style=='symbol_list':
        if not isinstance(value,list) or not value or not all(isinstance(s,str) and re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',s) for s in value) or value!=sorted(set(value)):
            raise PresentationError('Invalid instrument list.')
        if len(value)>20:return f'{len(value):,} instruments; see indexed pages'
        return ', '.join(value)
    if style=='text':
        if not isinstance(value,str) or len(value)>1000:raise PresentationError('Invalid presentation label.')
        return value
    if style=='boolean':
        if type(value) is not bool:raise PresentationError('Invalid boolean label.')
        return 'Enabled' if value else 'Disabled'
    if style not in {'currency','percent','number','integer','exact_number'}:raise PresentationError('Unknown presentation format.')
    if value is None:return 'Undefined'
    if type(value) not in (float,int):raise PresentationError('A display number must be finite.')
    number=Decimal(str(value))
    if not number.is_finite() or abs(number)>Decimal('1e100'):raise PresentationError('A display number is outside the supported range.')
    with localcontext() as ctx:
        ctx.prec=120
        if style=='exact_number':
            raw=format(number,'f')
            return (raw.rstrip('0').rstrip('.') if '.' in raw else raw) if number else '0'
        if style=='integer':
            if number!=int(number):raise PresentationError('A count must be integral.')
            return f'{int(number):,}'
        if style=='percent':number*=100
        if style not in {'currency','percent','number'}:raise PresentationError('Unknown presentation format.')
        number=number.quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN)
        if number==0:number=abs(number)
        if style=='currency':return ('-' if number<0 else '')+'$'+f'{abs(number):,.2f}'
        return f'{number:,.2f}'+('%' if style=='percent' else '')


def _pairs(items):
    value={}
    for key,item in items:
        if key in value:raise PresentationError('Duplicate saved-output field.')
        value[key]=item
    return value


def _lookup(document,path):
    try:
        for key in path:
            if isinstance(document,list) and (type(key) is not int or key<0):raise KeyError(key)
            document=document[key]
        return document
    except (KeyError,IndexError,TypeError) as exc:raise PresentationError('Required saved-output value is missing.') from exc


def _safe_name(name):
    return isinstance(name,str) and bool(re.fullmatch(r'[A-Za-z0-9_./-]+',name)) and not name.startswith('/') and all(
        x not in {'.','..'} and not x.startswith('.env') for x in name.split('/'))


class Builder:
    def __init__(self):self.facts={};self.pages=[];self.documents={};self.sources=[]

    def fact(self,source,path,style='number'):
        value=_lookup(self.documents[source],path)
        # Projection is allowlisted by adapters, never a recursive report dump.
        if any(re.sub('[^a-z]','',str(p).lower()) in {'token','authorization','password','apikey','secret','secretkey','cookie'} for p in path):
            raise PresentationError('Credential field cannot be presentation evidence.')
        text=format_value(value,style)
        if len(self.facts)>=MAX_FACTS:raise PresentationError('Presentation fact budget exceeded; choose fewer saved sources.')
        fid='f'+str(len(self.facts))
        self.facts[fid]=dict(source=source,path=path,row=next((x for x in reversed(path) if type(x) is int),None),
            column=path[-1],format=style,value=value,text=text)
        return {'fact':fid}

    def page(self,section,title,subtitle,conclusion,chart=None,stats=None,notes=None):
        if len(self.pages)>=MAX_PAGES:raise PresentationError('Presentation page budget exceeded; choose fewer saved sources.')
        self.pages.append(dict(section=section,title=title,subtitle=subtitle,conclusion=conclusion,
            chart=chart or {'kind':'concept'},stats=stats or [],notes=notes or []))

    def dates(self,s,root=None):
        root=root or []
        d=_lookup(self.documents[s],root)
        parts=[]
        if 'start' in d and 'end' in d:parts=[self.fact(s,root+['start'],'text'),' to ',self.fact(s,root+['end'],'text')]
        if isinstance(d.get('provenance'),dict) and 'input_kind' in d['provenance']:
            parts+=[' | ',self.fact(s,root+['provenance','input_kind'],'text')]
        return parts or ['Saved results only']

    def series(self,s,values,labels,style='currency'):
        if len(values)>MAX_POINTS or len(values)!=len(labels):raise PresentationError('Saved chart exceeds the point budget or has mismatched dates.')
        return [dict(x=self.fact(s,x,'text'),y=self.fact(s,y,style)) for y,x in zip(values,labels)]

    def account(self,s,prefix=None,title='Strategy account',section='Account'):
        p=prefix or [];d=_lookup(self.documents[s],p)
        equity=d.get('equity',[])
        if not isinstance(equity,list) or len(equity)>MAX_POINTS:raise PresentationError('Unsupported saved equity series.')
        m=p+['metrics'];metrics=d['metrics']
        dates=self.dates(s) # Subaccounts inherit root date/provenance identity.
        capital_path=p+['portfolio','capital'] if 'portfolio' in d else ['portfolio','capital']
        points=self.series(s,[p+['equity',i,'equity'] for i in range(len(equity))],
            [p+['equity',i,'date'] for i in range(len(equity))])
        net=metrics['net_profit']
        conclusion='The simulated account gained money. This is not evidence of future profitability.' if net>0 else (
            'The simulated account lost money. A favorable comparison would not make this account profitable.' if net<0 else
            'The simulated account broke even. An empty or flat outcome is not evidence of an edge.')
        self.page(section,title,dates,conclusion,dict(kind='line',points=points),
            [dict(label='Net profit',value=self.fact(s,m+['net_profit'],'currency')),
             dict(label='Maximum drawdown',value=self.fact(s,m+['max_drawdown'],'percent'))],
            [['Initial capital ',self.fact(s,capital_path,'currency')]])
        pnl=metrics['daily_pnl']
        if len(pnl)!=len(equity):raise PresentationError('Daily profit and session calendars differ.')
        self.page(section,'Daily profit',dates,'Every eligible session remains in this saved daily series, including sessions without an exit.',
            dict(kind='columns',points=self.series(s,[m+['daily_pnl',i] for i in range(len(pnl))],
                [p+['equity',i,'date'] for i in range(len(equity))])),
            [dict(label='Executed trades',value=self.fact(s,m+['trades'],'integer')),
             dict(label='Winning trades',value=self.fact(s,m+['win_rate'],'percent'))])
        stats=[dict(label='Marked Sharpe',value=self.fact(s,m+['marked_sharpe']))]
        if 'profit_without_ten_best_days' in metrics:
            stats.append(dict(label='Profit excluding best ten days',value=self.fact(s,m+['profit_without_ten_best_days'],'currency')))
        self.page(section,'Uncertainty',dates,'Undefined statistics and descriptive stress tests are retained. No selection-adjusted verdict is inferred.',
            dict(kind='line',points=points),stats,
            [['Daily marked equity and complete saved sessions are used. Removing winning days is descriptive.']])

    def dataset_context(self,s):
        d=self.documents[s]
        if 'dataset_context' not in d:
            self.page('Data provenance','Dataset context not recorded','Original saved evidence',
                'This version did not save the complete dataset context. No data classification or instruments are inferred from a current selection.')
            return
        try:c=validate_context(d['dataset_context'])
        except DataError as error:raise PresentationError(str(error)) from error
        self.page('Data provenance','Saved input classification','Frozen dataset context',
            'The declared input type and source are recorded provenance, not certification of prices or financial performance.',notes=[
                ['Declared input kind: ',self.fact(s,['dataset_context','input_kind'],'text')],
                ['Data source: ',self.fact(s,['dataset_context','source'],'text')]])
        self.page('Data provenance','Complete instrument list','Frozen dataset context',
            'The original instrument list is retained as a complete source value.',
            notes=[[self.fact(s,['dataset_context','symbols'],'symbol_list')]])
        for offset in range(0,len(c['symbols']),15):
            notes=[]
            for start in range(offset,min(offset+15,len(c['symbols'])),5):
                line=[]
                for index in range(start,min(start+5,len(c['symbols']))):
                    if line:line+=[' · ']
                    line+=[self.fact(s,['dataset_context','symbols',index],'text')]
                notes.append(line)
            self.page('Data provenance','Saved instruments','Frozen dataset context',
                'These instruments belong to this saved result.',notes=notes)
        self.page('Data provenance','Dataset fingerprints','Frozen dataset context',
            'Identity refers to the immutable input manifest used by this result.',notes=[
                ['Dataset: ',self.fact(s,['dataset_context','dataset_id'],'text')],
                ['Manifest fingerprint: ',self.fact(s,['dataset_context','dataset_manifest_hash'],'text')],
                ['Context policy: ',self.fact(s,['dataset_context','policy_version'],'integer')]])

    def assumptions(self,s,cost_path=None,context=None):
        d=self.documents[s];cp=cost_path or ['costs']
        costs=_lookup(d,cp) if cost_path is not None else d.get('costs')
        notes=[['Results depend on the saved data, execution and financing assumptions.'],
            ['Buying and short selling are simulations. Historical lending availability may be assumed.']]
        if context:notes.insert(0,context)
        if isinstance(d.get('study_context'),dict):
            notes.insert(0,['Frozen study ',self.fact(s,['study_context','study_id'],'text'),' | ',self.fact(s,['study_context','study_mode'],'text'),' | phase ',self.fact(s,['study_context','phase'],'text')])
            notes.append(['Original study input hash ',self.fact(s,['study_context','study_input_hash'],'text')])
            notes.append(['Selection unit ',self.fact(s,['study_context','selection_unit_id'],'text')])
            if d['study_context'].get('candidate_hash'):notes.append(['Frozen candidate hash ',self.fact(s,['study_context','candidate_hash'],'text')])
            if d['study_context']['phase']=='final':notes.append(['Final dates were consumed before prices. Saved inspection does not grant a new final test.'])
        if isinstance(d.get('borrow_sensitivity'),dict):
            notes.insert(0,['Applied annual rate ',self.fact(s,['borrow_sensitivity','annual_rate'],'percent'),'; initial and all event rates are overridden. Availability and recalls stay fixed.'])
            notes.append(['Original costs fingerprint ',self.fact(s,['borrow_sensitivity','original_costs_id'],'text'),'. Scenario notes remain original context.'])
        if d.get('report_type')=='borrow_sensitivity' and cost_path is None:
            notes.insert(0,['Original input costs below are retained for provenance. Each comparison account overrides initial and scheduled annual rates.'])
        if isinstance(d.get('news_calendar'),dict):
            notes.append(['News calendar ',self.fact(s,['news_calendar','spec','name'],'text'),' | ',self.fact(s,['news_calendar','spec','mode'],'text')])
            if d['news_calendar']['spec']['mode']=='retrospective':notes.append(['Historical advance knowledge of these reconstructed news dates is assumed.'])
        if isinstance(costs,dict):
            fields=[('spread_bps','Spread in basis points','number'),('slippage_bps','Slippage in basis points','number'),('borrow_annual','Annual borrowing assumption','percent')]
            if d.get('report_type')=='borrow_sensitivity' or isinstance(d.get('borrow_sensitivity'),dict):
                fields += [('commission_per_share','Commission per share in dollars','exact_number'),('minimum_commission','Minimum commission','currency'),('fixed_fee_per_order','Fixed order fee','currency'),('sell_fee_per_dollar','Sell fee per dollar','exact_number'),('borrow_available','Initial new short availability','boolean')]
            for key,label,fmt in fields:
                if key in costs:notes.append([label+' ',self.fact(s,cp+[key],fmt)])
        borrowing=costs.get('borrow_scenario') if isinstance(costs,dict) else None
        if isinstance(borrowing,dict):
            p=cp+['borrow_scenario']
            notes.extend([
                ['Borrowing scenario ',self.fact(s,p+['name'],'text'),' | ',self.fact(s,p+['mode'],'text')],
                ['Coverage ',self.fact(s,p+['start'],'text'),' to ',self.fact(s,p+['end'],'text'),' | complete ',self.fact(s,p+['complete'],'boolean')],
                ['Initial new short availability ',self.fact(s,cp+['borrow_available'],'boolean')],
                ['Lending conditions are input assumptions. A recall closes an existing short at its next observed opening.'],
            ])
            if borrowing.get('note'):notes.append(['Borrowing note ',self.fact(s,p+['note'],'text')])
        expanded=isinstance(d.get('study_context'),dict) or isinstance(d.get('news_calendar'),dict) or isinstance(borrowing,dict) or bool(context) or d.get('report_type')=='borrow_sensitivity' or isinstance(d.get('borrow_sensitivity'),dict)
        groups=[notes] if not expanded else [notes[i:i+3] for i in range(0,len(notes),3)]
        for i,group in enumerate(groups):
            self.page('Contract','Research assumptions' if i==0 else 'News and cost assumptions',self.dates(s),
                'Software correctness, historical profit and future investment performance are separate questions.',notes=group)
        if isinstance(borrowing,dict):
            rows=[['Covered borrowing instrument ',self.fact(s,cp+['borrow_scenario','symbols',i],'text')] for i in range(len(borrowing['symbols']))]
            for i in range(0,len(rows),3):
                self.page('Borrowing inputs','Declared lending coverage',self.dates(s),'Coverage is an input declaration, not historical lending evidence.',notes=rows[i:i+3])
            rows=[]
            for i in range(len(borrowing['events'])):
                p=cp+['borrow_scenario','events',i]
                rows.append(['Instrument ',self.fact(s,p+['symbol'],'text'),' | effective ',self.fact(s,p+['effective_at'],'text'),
                    ' | annual rate ',self.fact(s,p+['annual_rate'],'percent'),' | available ',self.fact(s,p+['available'],'boolean'),
                    ' | recall ',self.fact(s,p+['recall'],'boolean')])
            for i in range(0,len(rows),3):
                self.page('Borrowing inputs','Scheduled lending states',self.dates(s),'Full states replace the prior assumption at their effective time. Later states do not rewrite earlier charges.',notes=rows[i:i+3])

    def frozen_rules(self,s,path,wrapped):
        rules=_lookup(self.documents[s],path)
        for i,rule in enumerate(rules):
            p=path+[i]+(['config'] if wrapped else [])
            config=rule['config'] if wrapped else rule
            subtitle=['Frozen member ',self.fact(s,p+['family'],'text'),' | ',self.fact(s,p+['timeframe'],'text')]
            if wrapped:subtitle+=[' | ',self.fact(s,path+[i,'config_id'],'text')]
            notes=[]
            for key,value in config.items():
                fmt='boolean' if type(value) is bool else 'text' if isinstance(value,str) else 'integer' if type(value) is int else 'exact_number'
                notes.append([key.replace('_',' ').capitalize()+' ',self.fact(s,p+[key],fmt)])
            for offset in range(0,len(notes),3):
                self.page('Frozen selection','Frozen member rules',subtitle,
                    'This complete rule belongs to the saved shared selection unit. Membership was fixed before screening.',notes=notes[offset:offset+3])

    def behavior(self,s):
        tables=self.documents[s]['tables']
        if not isinstance(tables,dict) or not tables:raise PresentationError('No saved behavior tables.')
        for name,table in tables.items():
            rows=table['rows']
            if not isinstance(rows,list):raise PresentationError('Malformed behavior table.')
            if not rows:
                self.page('Price behavior',name.replace('_',' ').capitalize(),self.dates(s),
                    'No eligible saved observations. This is an insufficient-data result.');continue
            for offset in range(0,len(rows),ROWS_PER_PAGE):
                chart=[]
                for i in range(offset,min(offset+ROWS_PER_PAGE,len(rows))):
                    p=['tables',name,'rows',i];row=rows[i]
                    labels=[]
                    for field in ['scope','subset','category','metric','horizon','unit']:
                        if field in row:labels+=([ ' | ' ] if labels else [])+[self.fact(s,p+[field],'integer' if field=='horizon' else 'number' if row[field] is None else 'text')]
                    chart.append(dict(label=labels,value=self.fact(s,p+['difference']),
                        low=self.fact(s,p+['interval_low']),high=self.fact(s,p+['interval_high']),
                        real=self.fact(s,p+['real_mean']),control=self.fact(s,p+['control_mean']),
                        real_n=self.fact(s,p+['real_n'],'integer'),control_n=self.fact(s,p+['control_n'],'integer'),
                        status=self.fact(s,p+['status'],'text')))
                self.page('Price behavior',name.replace('_',' ').capitalize(),self.dates(s),
                    'Dots show real minus comparison with saved intervals. Subsets and horizons remain separate; this is descriptive evidence.',
                    dict(kind='differences',rows=chart))

    def comparisons(self,s):
        d=self.documents[s];rows=d['comparison_rows']
        for i,row in enumerate(rows):
            p=['comparison_rows',i]
            def style(v):return 'boolean' if type(v) is bool else 'text' if isinstance(v,str) else 'number'
            labels=self.dates(s)+[' | ',self.fact(s,p+['field'],'text'),' | baseline ',self.fact(s,p+['baseline_value'],style(row['baseline_value'])),
                ' | alternative ',self.fact(s,p+['alternative_value'],style(row['alternative_value']))]
            points=[dict(label=['Baseline'],value=self.fact(s,p+['baseline_net_profit'],'currency')),
                dict(label=['Alternative'],value=self.fact(s,p+['alternative_net_profit'],'currency'))]
            self.page('Paired comparisons','Rule comparison',labels,
                'Improvement and absolute profit are separate. The saved interval is descriptive and does not correct a strategy search.',
                dict(kind='bars',rows=points),[dict(label='Alternative minus baseline',value=self.fact(s,p+['net_difference'],'currency'))],
                [['Interval ',self.fact(s,p+['interval_low'],'currency'),' to ',self.fact(s,p+['interval_high'],'currency')],
                 ['Status ',self.fact(s,p+['status'],'text')]])

    def borrowing_comparison(self,s):
        d=self.documents[s]
        if len(d['arms'])!=4 or len(d['comparison_rows'])!=4 or len(d['daily_differences'])!=4:
            raise PresentationError('Borrow comparison needs every saved rate account.')
        for i,row in enumerate(d['comparison_rows']):
            p=['comparison_rows',i];arm=d['arms'][i];daily=d['daily_differences'][i]
            if row['annual_rate']!=[0,.03,.1,.3][i] or arm['part']!=i or daily['part']!=i:
                raise PresentationError('Borrow comparison rate order is invalid.')
            labels=self.dates(s)+[' | applied annual rate ',self.fact(s,p+['annual_rate'],'percent')]
            self.page('Borrowing comparison','Complete account outcome',labels,
                'Each rate executes a separate account. Absolute profit and improvement over the zero-rate account are separate.',
                dict(kind='bars',rows=[dict(label=['Absolute net profit'],value=self.fact(s,p+['net_profit'],'currency'))]),
                [dict(label='Difference from zero rate',value=self.fact(s,p+['delta_from_zero'],'currency')),
                 dict(label='Borrowing paid',value=self.fact(s,p+['borrow_paid'],'currency'))],
                [['Executed trades ',self.fact(s,p+['trades'],'integer'),' | short trades ',self.fact(s,p+['short_trades'],'integer')],
                 ['No short trades ',self.fact(s,p+['no_short_trades'],'boolean'),'. This does not establish that lending costs are immaterial elsewhere.']])
            rows=daily['rows']
            points=self.series(s,[['daily_differences',i,'rows',j,'difference'] for j in range(len(rows))],
                [['daily_differences',i,'rows',j,'date'] for j in range(len(rows))])
            self.page('Borrowing comparison','Daily account difference',labels,
                'Every saved session remains. Differences are selected account minus zero-rate account; no difference interval or significance is inferred.',
                dict(kind='columns',points=points),
                [dict(label='Other execution fees',value=self.fact(s,p+['fees_paid'],'currency')),
                 dict(label='Signals',value=self.fact(s,p+['signals'],'integer'))],
                [['Account identity ',self.fact(s,p+['account_id'],'text')]])
            self.assumptions(s,['arms',i,'costs'],['Applied account annual rate ',self.fact(s,['arms',i,'annual_rate'],'percent'),'. Initial and event rates are overridden; original names and notes remain context.'])

    def controls(self,s):
        p=['comparison'];d=self.documents[s]['comparison']
        self.page('Random controls','Matched accounts',self.dates(s),
            'A better losing account still loses money. Conditional random comparisons do not establish an executable trading edge.',
            dict(kind='bars',rows=[dict(label=['Matched real account'],value=self.fact(s,p+['real_net_profit'],'currency')),
                dict(label=['Mean random account'],value=self.fact(s,p+['mean_control_net_profit'],'currency'))]),
            [dict(label='Real minus mean random',value=self.fact(s,p+['net_difference'],'currency')),
             dict(label='Random accounts',value=self.fact(s,p+['control_accounts'],'integer'))],
            [['Fraction at least as profitable as real ',self.fact(s,p+['exceedance_fraction'],'percent')]])
        if isinstance(d.get('paired_pnl_interval'),dict):
            # Preserve interval bounds on the comparison page without inventing a verdict.
            self.pages[-1]['notes'].append(['Paired interval ',self.fact(s,p+['paired_pnl_interval','low'],'currency'),
                ' to ',self.fact(s,p+['paired_pnl_interval','high'],'currency')])

    def summaries(self,s):
        document=self.documents[s]
        if 'study_mode' in document:
            notes=[['Study ',self.fact(s,['study_id'],'text')],['Selection mode ',self.fact(s,['study_mode'],'text')]]
            if 'candidate_hash' in document:notes.append(['Frozen candidate hash ',self.fact(s,['candidate_hash'],'text')])
            self.page('Frozen study','Saved study outcomes',['Separate saved evaluation windows'],('Portfolio outcomes represent one shared account per window; independently reset member profits are not combined.' if document['study_mode']=='portfolio' else 'Each rule has a separately funded account. These outcomes are not a combined portfolio.'),notes=notes)
        rows=document['rows']
        if not isinstance(rows,list):raise PresentationError('Malformed saved search rows.')
        found=False
        for i,row in enumerate(rows):
            for key in ['metrics','report','discovery','validation','final']:
                if not isinstance(row.get(key),dict) or 'net_profit' not in row[key]:continue
                found=True;p=['rows',i,key]
                self.page('Search summaries',('Saved account' if key=='metrics' else key.capitalize())+' results',['Configuration ',self.fact(s,['rows',i,'config_id'],'text')],
                    'This saved configuration summary is not a new final test or proof of a surviving strategy.',
                    dict(kind='bars',rows=[dict(label=['Net profit'],value=self.fact(s,p+['net_profit'],'currency'))]),
                    [dict(label='Trades',value=self.fact(s,p+['trades'],'integer')),
                     dict(label='Marked Sharpe',value=self.fact(s,p+['marked_sharpe']))])
            if row.get('study_mode')=='portfolio':self.frozen_rules(s,['rows',i,'configurations'],False)
        if not found:raise PresentationError('No supported saved summary windows; choose an individual saved account.')
        funnel=self.documents[s].get('funnel')
        if isinstance(funnel,dict):
            numeric=[k for k,v in funnel.items() if type(v) is int]
            for start in range(0,len(numeric),ROWS_PER_PAGE):
                self.page('Search summaries','Search funnel',['Saved stage counts'],
                    'Stage counts retain their source definitions. They are not independent hypotheses or future performance evidence.',
                    dict(kind='bars',rows=[dict(label=[k.replace('_',' ')],value=self.fact(s,['funnel',k],'integer')) for k in numeric[start:start+ROWS_PER_PAGE]]))
        if 'search_statistics' in document:self.search_statistics(s)
        if 'search_screen' in document:self.search_screen(s)

    def search_screen(self,s):
        p=['search_screen'];d=self.documents[s]['search_screen']
        if not isinstance(d,dict) or d.get('policy_version')!=1:raise PresentationError('Unsupported saved initial discovery gates.')
        self.page('Initial discovery','Frozen sampling recipe',self.dates(s),
            'This is the published equity recipe. The private host grid and named presets are not represented as reproduced.',
            notes=[['Sampling mode ',self.fact(s,p+['settings','mode'],'text')],
                   ['News variants permitted ',self.fact(s,p+['settings','include_news'],'boolean')],
                   ['Recipe hash ',self.fact(s,['sampling','recipe_hash'],'text')]])
        self.page('Initial discovery','Saved signal scope',self.dates(s),
            'The discovery signal count excludes warm-up. All later validation requirements remain separate.',
            notes=[[self.fact(s,p+['signal_definition'],'text')],[self.fact(s,p+['scope'],'text')]])
        if isinstance(self.documents[s].get('news_calendar'),dict):
            self.page('Initial discovery','Frozen news identity',self.dates(s),
                'Calendar scope and knowledge are saved input assumptions. A permitted filter need not appear in a small random sample.',
                notes=[['Calendar ',self.fact(s,['news_calendar','id'],'text')],
                       ['Knowledge mode ',self.fact(s,['news_calendar','spec','mode'],'text')],
                       ['Complete declared coverage ',self.fact(s,['news_calendar','spec','complete'],'boolean')]])
            self.page('Initial discovery','Frozen news coverage',self.dates(s),
                'This declared calendar belongs to the original search and does not establish complete historical news knowledge.',
                notes=[['From ',self.fact(s,['news_calendar','spec','start'],'text')],
                       ['Through ',self.fact(s,['news_calendar','spec','end'],'text')],
                       ['Name ',self.fact(s,['news_calendar','spec','name'],'text')]])
        labels={'generated':'Generated configurations','signal_qualified':'Enough signals','enough_trades':'Enough executed trades','profitable':'Positive net profit','sharpe_passed':'Sharpe threshold'}
        self.page('Initial discovery','Discovery gate counts',self.dates(s),
            'Counts are cumulative initial gates. Trade twins, era checks, instrument replication and final validation remain separate.',
            dict(kind='bars',rows=[dict(label=[title],value=self.fact(s,p+['counts',key],'integer')) for key,title in labels.items()]))
        self.page('Initial discovery','Frozen discovery thresholds',self.dates(s),
            'Signals are not executed trades. Net profit must be strictly positive; undefined Sharpe does not pass.',
            notes=[['Minimum signals ',self.fact(s,p+['settings','minimum_signals'],'integer')],
                   ['Minimum executed trades ',self.fact(s,p+['settings','minimum_trades'],'integer')],
                   ['Minimum marked Sharpe ',self.fact(s,p+['settings','minimum_sharpe'],'exact_number')]])
        for i,group in enumerate(d['groups']):
            self.page('Initial discovery','Family and chart denominators',[self.fact(s,p+['groups',i,'family'],'text'),' | ',self.fact(s,p+['groups',i,'timeframe'],'text')],
                'All generated accounts remain in the saved evidence, including too few signals, no trades, losses and undefined scores.',
                dict(kind='bars',rows=[dict(label=[title],value=self.fact(s,p+['groups',i,'counts',key],'integer')) for key,title in labels.items()]))
        states=[['Later stage '+name.replace('_',' ')+' ',self.fact(s,p+['later_stages',name],'text')] for name in d['later_stages']]
        for offset in range(0,len(states),3):
            self.page('Initial discovery','Later validation status',self.dates(s),
                'An initial pass does not create a frozen candidate, consume final dates or prove a surviving strategy.',notes=states[offset:offset+3])

    def search_statistics(self,s):
        p=['search_statistics'];d=self.documents[s]['search_statistics']
        if not isinstance(d,dict) or d.get('policy_version')!=1 or not isinstance(d.get('accounts'),list) or len(d['accounts'])!=len(self.documents[s]['rows']):
            raise PresentationError('Unsupported or incomplete saved search statistics.')
        self.page('Search assumptions','Search-bias sensitivity',self.dates(s),
            'Trial assumptions are scenarios, not an independence estimate. Model scores do not establish profitability or a surviving strategy.',
            stats=[dict(label='Complete configurations',value=self.fact(s,p+['raw_configurations'],'integer')),
                     dict(label='Finite daily Sharpe accounts',value=self.fact(s,p+['finite_sharpe_accounts'],'integer'))],
            notes=[['Dispersion mode ',self.fact(s,p+['settings','dispersion_mode'],'text')],
                   ['Cross-trial daily Sharpe standard deviation ',self.fact(s,p+['trial_sharpe_std'],'exact_number')],
                   [self.fact(s,p+['return_unit'],'text')]])
        generation=[['Generation '+key+' ',self.fact(s,p+['raw_generation',key],'integer')] for key in ['attempts','unique','duplicates','rejected']]
        generation += [['Role ',self.fact(s,p+['role'],'text')],['Definition ',self.fact(s,p+['source'],'text')]]
        for start in range(0,len(generation),3):
            self.page('Search assumptions','Generation and diagnostic scope',self.dates(s),
                'Proposal and configuration counts are distinct. This derived diagnostic is not another independent hypothesis.',notes=generation[start:start+3])
        for i,account in enumerate(d['accounts']):
            a=p+['accounts',i]
            self.page('Search assumptions','Saved daily-return moments',['Configuration ',self.fact(s,a+['config_id'],'text')],
                'Account profit and the model score are separate. The approximation does not correct undisclosed prior searches or establish serial independence.',
                stats=[dict(label='Net profit',value=self.fact(s,a+['net_profit'],'currency')),
                         dict(label='Observations',value=self.fact(s,a+['observations'],'integer'))],
                notes=[['Daily Sharpe ',self.fact(s,a+['daily_sharpe'],'exact_number')],
                       ['Bias-corrected skewness ',self.fact(s,a+['skewness'],'exact_number')],
                       ['Bias-corrected raw kurtosis ',self.fact(s,a+['raw_kurtosis'],'exact_number')]])
            if len(account.get('sensitivity',[]))!=len(d['settings']['effective_trials']):raise PresentationError('Incomplete saved trial-count sensitivity.')
            notes=[['Saved account hash ',self.fact(s,a+['source_part_sha256'],'text')]]
            for j,value in enumerate(account['sensitivity']):
                b=a+['sensitivity',j]
                note=['Assumed independent trials ',self.fact(s,b+['effective_trials'],'integer'),'; DSR model score ',self.fact(s,b+['score'],'exact_number')]
                if isinstance(value.get('undefined_reason'),str):note+=['; ',self.fact(s,b+['undefined_reason'],'text')]
                notes.append(note)
            for start in range(0,len(notes),3):
                self.page('Search assumptions','Trial-count sensitivity',['Configuration ',self.fact(s,a+['config_id'],'text')],
                    'Undefined values stay explicit. These diagnostics do not change candidate or final-test gates.',notes=notes[start:start+3])

    def add(self,name,raw):
        if not _safe_name(name) or name in self.documents:raise PresentationError('Saved source needs a unique safe relative name.')
        if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:raise PresentationError('Saved source exceeds the byte budget.')
        def finite_float(text):
            value=float(text)
            if not math.isfinite(value):raise PresentationError('Nonfinite saved-output number.')
            return value
        try:d=json.loads(raw,object_pairs_hook=_pairs,parse_float=finite_float,parse_constant=lambda _:(_ for _ in ()).throw(PresentationError('Nonfinite source.')))
        except (ValueError,RecursionError,UnicodeError) as exc:raise PresentationError('Invalid saved-output JSON.') from exc
        if not isinstance(d,dict):raise PresentationError('Saved output must be an object.')
        self.documents[name]=d;meta=dict(name=name,sha256=hashlib.sha256(raw).hexdigest())
        for field in ['core_hash','dataset_manifest_hash']:
            if isinstance(d.get(field),str) and re.fullmatch('[0-9a-f]{64}',d[field]):meta[field]=d[field]
        self.sources.append(meta)
        self.dataset_context(name)
        self.assumptions(name)
        kind=d.get('report_type')
        if kind in {'single_strategy','matched_control_book'}:self.account(name)
        elif kind=='shared_capital_portfolio':
            self.account(name,title='Shared portfolio account')
            if isinstance(d.get('study_context'),dict):self.frozen_rules(name,['configurations'],True)
        elif kind=='passive_benchmarks':
            self.account(name,['benchmarks','cash'],'Cash account','Passive benchmarks')
            self.account(name,['benchmarks','buy_hold'],'Buy and hold','Passive benchmarks')
        elif kind=='price_behavior':self.behavior(name)
        elif kind=='paired_ablations':self.comparisons(name)
        elif kind=='borrow_sensitivity':self.borrowing_comparison(name)
        elif kind=='matched_random_controls':self.controls(name)
        elif kind is None and 'rows' in d:self.summaries(name)
        else:raise PresentationError('This saved output has no supported presentation adapter; choose its aggregate study or account report.')


def build_deck(sources):
    if not 1<=len(sources)<=MAX_SOURCES:raise PresentationError('Choose one to sixteen saved sources.')
    if sum(len(x[1]) for x in sources)>MAX_BYTES:raise PresentationError('Combined source byte budget exceeded.')
    b=Builder()
    try:
        for name,raw in sources:b.add(name,raw)
        deck=dict(version=1,sources=b.sources,facts=b.facts,pages=b.pages,
            limitations=['Saved-output presentation; underlying research and final software acceptance require their own evidence.',
                'Sources retain separate accounts and denominators; a combined deck does not establish comparability.'])
        deck['audit']=audit_deck(dict(sources),deck)
        return deck
    except PresentationError:raise
    except (PresentationAuditError,KeyError,TypeError,IndexError,OverflowError,RecursionError) as exc:
        raise PresentationError('Saved output failed the independent presentation contract: '+str(exc)) from exc


def render_html(deck):
    data=json.dumps(deck,ensure_ascii=True,allow_nan=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    script_hash=base64.b64encode(hashlib.sha256(RUNTIME.encode()).digest()).decode()
    csp="default-src 'none'; script-src 'sha256-"+script_hash+"'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
    result='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="'+html.escape(csp,quote=True)+'"><title>Saved research presentation</title><style>'+CSS+'</style></head><body><main id="stage" aria-label="Saved research presentation"><div id="slide"></div><div id="camera-guide" hidden aria-label="Reserved camera area">Reserved camera area</div><svg id="annotations" viewBox="0 0 1920 1080" aria-hidden="true"></svg><div id="pointer" aria-hidden="true"></div><nav id="controls" aria-label="Presentation controls"><button id="previous" aria-label="Previous page">Previous</button><button id="next" aria-label="Next page">Next</button><button id="menu-toggle">Sections</button><button id="replay">Replay</button><button id="camera-toggle">Camera guide</button><button id="manifest-download">Save provenance</button></nav><dialog id="menu" aria-label="Presentation sections"><h2>Sections</h2><button id="close-menu">Close</button><div id="sections"></div></dialog><p id="live" class="sr-only" aria-live="polite"></p></main><script id="presentation-manifest" type="application/json">'+data+'</script><script>'+RUNTIME+'</script></body></html>'
    if len(result.encode())>MAX_BYTES:raise PresentationError('HTML byte budget exceeded; choose fewer saved sources.')
    return result
