"""Fixed-rate complete-account policy and reconciled descriptive comparisons."""
from copy import deepcopy
import math
from .config import Costs,Strategy,identity
from .data import DataError
from .ablations import _validate_account

RATES=(0.,.03,.1,.3)
POLICY='flat_initial_and_event_annual_rates'


def cost_arms(original:Costs,configuration:Strategy):
    original=Costs(**original.model_dump())
    configuration=Strategy(**configuration.model_dump())
    arms=[]
    for part,rate in enumerate(RATES):
        value=deepcopy(original.model_dump());value['borrow_annual']=rate
        if value['borrow_scenario'] is not None:
            for event in value['borrow_scenario']['events']:event['annual_rate']=rate
        costs=Costs(**value).model_dump()
        arms.append(dict(part=part,annual_rate=rate,costs=costs,costs_id=identity(costs),
            account_id=identity(dict(strategy=configuration.model_dump(),costs=costs))))
    return arms


def summarize_accounts(reports,original:Costs,configuration:Strategy):
    """Never derive an arm by subtracting financing from another arm's result."""
    try:return _summarize(reports,original,configuration)
    except DataError:raise
    except (ValueError,TypeError,KeyError,IndexError,OverflowError) as exc:
        raise DataError('Borrow sensitivity account fields are missing or invalid.') from exc


def _summarize(reports,original,configuration):
    arms=cost_arms(original,configuration)
    if not isinstance(reports,list) or len(reports)!=len(arms):raise DataError('Borrow sensitivity requires all four complete accounts.')
    common=['dataset_id','dataset_manifest_hash','core_hash','start','end','seed','portfolio','config','config_id','news_dates','news_calendar','signals']
    base=reports[0];days=[];summaries=[];rows=[];daily_rows=[];baseline_daily=None;baseline_profit=None
    for part,(report,arm) in enumerate(zip(reports,arms)):
        if any(report.get(k)!=base.get(k) for k in common):raise DataError('Borrow sensitivity accounts have incompatible frozen inputs or signals.')
        if report['costs']!=arm['costs'] or report['config']!=configuration.model_dump():
            raise DataError('Borrow sensitivity account does not match its frozen rate arm.')
        _,daily,_=_validate_account(report)
        current_days=[r['date'] for r in report['equity']]
        if part==0:days=current_days;baseline_daily=daily;baseline_profit=report['metrics']['net_profit']
        if current_days!=days:raise DataError('Borrow sensitivity requires an identical complete session calendar.')
        borrow=[t['borrow'] for t in report['trades']];fees=[t['fees'] for t in report['trades']]
        ledger_borrow=[-r['cash_change'] for r in report['ledger'] if r['kind']=='borrow']
        ledger_fees=[r['fee'] for r in report['ledger'] if r['kind'] in {'entry','exit'}]
        if any(not math.isfinite(v) or v<0 for v in [*borrow,*fees,*ledger_borrow,*ledger_fees]):
            raise DataError('Borrow sensitivity financing and fees must be finite and nonnegative.')
        paid=math.fsum(borrow);fee_total=math.fsum(fees)
        if abs(paid-math.fsum(ledger_borrow))>1e-7 or abs(fee_total-math.fsum(ledger_fees))>1e-7:
            raise DataError('Borrow sensitivity trade charges do not reconcile to the cash ledger.')
        metrics=report['metrics']
        for name in ['marked_sharpe','total_return','max_drawdown']:
            if metrics[name] is not None and not math.isfinite(metrics[name]):raise DataError('Borrow sensitivity metrics must be finite or undefined.')
        difference=daily-baseline_daily;delta=float(difference.sum())
        if abs(delta-(metrics['net_profit']-baseline_profit))>1e-7:raise DataError('Borrow sensitivity daily differences do not reconcile to absolute profits.')
        short_trades=sum(t['side']==-1 for t in report['trades'])
        row=dict(part=part,annual_rate=arm['annual_rate'],costs_id=arm['costs_id'],account_id=arm['account_id'],
            signals=len(report['signals']),trades=len(report['trades']),short_trades=short_trades,no_short_trades=short_trades==0,
            net_profit=metrics['net_profit'],borrow_paid=paid,fees_paid=fee_total,delta_from_zero=delta,
            marked_sharpe=metrics['marked_sharpe'],total_return=metrics['total_return'],max_drawdown=metrics['max_drawdown'])
        rows.append(row)
        summaries.append(dict(**arm,config_id=identity(configuration),metrics=metrics,borrow_paid=paid,fees_paid=fee_total,
            signals=len(report['signals']),short_trades=short_trades))
        daily_rows.append(dict(part=part,annual_rate=arm['annual_rate'],rows=[dict(date=day,
            baseline_profit=float(left),scenario_profit=float(right),difference=float(value)) for day,left,right,value in zip(days,baseline_daily,daily,difference)]))
    return dict(arms=summaries,comparison_rows=rows,daily_differences=daily_rows,
        comparison_interpretation='Descriptive historical flat-rate counterfactuals. Differences are scenario minus the zero-rate account; no difference interval, significance or independent-trial count is inferred.',
        limitations=['Original Costs remain separately saved. Initial and scheduled annual rates are overridden; availability, recalls and every other input remain fixed.',
            'Each account regenerates signals and executes its own fills, whole-share sizing and cash ledger. A rate can change later quantities; results are not scaled P&L.',
            'No short trades is a visible outcome, not evidence that borrowing costs are immaterial to other strategies.',
            'Existing account-level uncertainty is separate. These scenarios do not establish actual past lending conditions or a future trading edge.'])
