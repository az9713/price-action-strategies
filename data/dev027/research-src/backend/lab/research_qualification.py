"""Complete research qualification from accounts already proved by their caller.

This reducer grants no original-store authority and is never a supplied-outcome
HTTP endpoint. Instrument discovery replication is distinct from later validation.
"""
from collections.abc import Mapping
from fractions import Fraction
import hashlib
from .config import Strategy,APPLICABILITY,canonical,identity
from .research_funnel import family_average,_amount,_encoded,_cancel
from .sampling import count_discovery_signals
from .trade_twins import EXECUTION_POLICIES,TOTAL_SETS

ARMS=('primary_discovery','era_one','era_two','instrument_replication','chronological_validation')
STABILITY_POLICY=dict(version=1,same_family_and_setup_chart=True,
    membership='Frozen versions differing in exactly one public coordinate active in both versions; effective trigger chart aliases compare equal.',
    numeric_coordinate='Any other sampled value of that coordinate, not an invented proximity radius.',
    no_new_versions_generated=True,all_frozen_neighbors_retained=True,descriptive_only=True,candidate_gate=False)
CONTROL_SCHEDULING_POLICY=dict(version=1,run_after_all_non_control_account_gates=True,
    terminal_original_ineligibility_rejects_candidate_without_retry=True,
    source_adaptation='Expensive controls follow all inexpensive account gates; eligibility thresholds are unchanged.',
    attrition='Complete-cohort gate observations and a confirmed-passing prefix; unassessed controls are not measured failures.')
GATE_ORDER=('discovery_signals','discovery_trades','discovery_profit','discovery_sharpe','matched_entries',
            'era_one_profit','era_two_profit','replication_profit','replication_sharpe',
            'chronological_trades','chronological_profit','chronological_sharpe')


class _Members(Mapping):
    def __init__(self,source,ids):self.source=source;self.ids=ids;self.keys=frozenset(ids)
    def __len__(self):return len(self.ids)
    def __iter__(self):return iter(self.ids)
    def __getitem__(self,key):
        if key not in self.keys:raise KeyError(key)
        return self.source[key]


def _universe(configurations,values):
    if (not isinstance(configurations,(list,tuple)) or not configurations or len(configurations)>100000
            or any(not isinstance(c,Strategy) for c in configurations)):
        raise ValueError('A complete nonempty frozen strategy universe is required.')
    ids=[identity(c) for c in configurations]
    if len(set(ids))!=len(ids) or not isinstance(values,Mapping) or set(ids)!=set(values):
        raise ValueError('Exactly one original outcome, including unavailable members, is required per frozen version.')
    return ids


def _active(c,key):
    if key in APPLICABILITY and c.family not in APPLICABILITY[key]:return False
    if key=='confirmation_window' and c.confirmation=='none':return False
    if key=='limit_expiry' and c.entry!='limit':return False
    if key in {'sweep_depth','reclaim_bars'} and c.family=='change_of_character' and not c.sweep_required:return False
    return True


def _vector(c):
    value=c.model_dump(mode='json');value['trigger_timeframe']=c.trigger
    return value


def _coordinate(key,value):
    return int.from_bytes(hashlib.sha256(canonical([key,value]).encode()).digest(),'big')


def _observation(value):
    if value is None:return None
    profit=_amount(value['net_profit']);sharpe=value['marked_sharpe']
    if sharpe is not None:_amount(sharpe)
    return profit,sharpe


def neighbor_ids(configurations,config_id,cancel=None):
    """Exact membership query; never generate an unregistered variant."""
    _cancel(cancel);ids=_universe(configurations,{identity(c):None for c in configurations})
    if config_id not in ids:raise ValueError('Choose a frozen configuration identity.')
    chosen=configurations[ids.index(config_id)];vector=_vector(chosen);result=[]
    for c,cid in zip(configurations,ids):
        _cancel(cancel)
        if c.family!=chosen.family or c.timeframe!=chosen.timeframe:continue
        other=_vector(c);changed=[key for key in vector if vector[key]!=other[key]]
        if len(changed)==1 and _active(chosen,changed[0]) and _active(c,changed[0]):result.append(cid)
    return result


def stability(configurations,observations,cancel=None):
    """Coordinate slices use O(N) working buckets, never an O(N-squared) graph.

    XOR of domain-separated SHA256 coordinate values is a compact grouping key;
    each slice excludes exactly its coordinate from the complete frozen vector.
    Missing metrics remain missing. Exact serialized profit moments include losses.
    """
    _cancel(cancel);ids=_universe(configurations,observations)
    vectors=[_vector(c) for c in configurations];values=[_observation(observations[cid]) for cid in ids]
    signatures=[]
    for vector in vectors:
        signature=0
        for key,value in vector.items():signature^=_coordinate(key,value)
        signatures.append(signature)
    totals=[[0,0,0,Fraction(),Fraction(),0] for _ in ids];coordinates=[{} for _ in ids]
    for key in Strategy.model_fields:
        if key in {'family','timeframe'}:continue
        buckets={};keys={}
        for index,(c,vector,signature,value) in enumerate(zip(configurations,vectors,signatures,values)):
            _cancel(cancel)
            if not _active(c,key):continue
            bucket=(c.family,c.timeframe,signature^_coordinate(key,vector[key]))
            # Equal effective vectors (e.g. implicit/explicit trigger aliases) are
            # excluded below rather than counted as a changed setting.
            keys[index]=(bucket,canonical(vector[key]));group=buckets.setdefault(bucket,{})
            aggregate=group.setdefault(keys[index][1],[0,0,0,Fraction(),Fraction(),0])
            aggregate[0]+=1
            if value is not None:
                profit,sharpe=value;aggregate[1]+=1;aggregate[2]+=profit>0
                aggregate[3]+=profit;aggregate[4]+=profit*profit;aggregate[5]+=sharpe is None
        for bucket,group in buckets.items():
            if len(group)<2:continue
            complete=[sum((row[i] for row in group.values()),Fraction() if i in (3,4) else 0) for i in range(6)]
            buckets[bucket]=(complete,group)
        for index,(bucket,level) in keys.items():
            if not isinstance(buckets[bucket],tuple):continue
            complete,group=buckets[bucket];other=[complete[i]-group[level][i] for i in range(6)]
            coordinates[index][key]=other[0]
            for i,value in enumerate(other):totals[index][i]+=value
    rows=[]
    for cid,total,by_coordinate in zip(ids,totals,coordinates):
        _cancel(cancel);count,available,positive,profit,squares,undefined=total
        rows.append(dict(config_id=cid,neighbors=count,available=available,missing=count-available,positive=positive,
            mean_net_profit=_encoded(profit/available) if available else None,
            sample_variance_net_profit=_encoded((squares-profit*profit/available)/(available-1)) if available>1 else None,
            undefined_sharpe=undefined,coordinate_counts=by_coordinate))
    return dict(**STABILITY_POLICY,configuration_universe_hash=identity([c.model_dump(mode='json') for c in configurations]),
                version_count=len(ids),rows=rows)


def control_gate(value):
    """Read actual counts; a stored adapted_pass flag cannot certify a strategy."""
    state=value.get('state','missing') if isinstance(value,dict) else 'missing'
    if state!='completed':return dict(state=state,passed=False,reason='Both original complete 10000-set interpretations are required.')
    summaries=value.get('summaries')
    if not isinstance(summaries,dict) or set(summaries)!=set(EXECUTION_POLICIES):
        raise ValueError('Both and only the declared original interpretations are required.')
    results={}
    for policy,summary in summaries.items():
        counts=[summary.get(k) for k in ['expected_sets','observed_sets','complete_sets','failed_sets','exceedances']]
        if (summary.get('state')!='completed' or any(type(n) is not int for n in counts)
                or counts[:4]!=[TOTAL_SETS,TOTAL_SETS,TOTAL_SETS,0] or not 0<=counts[-1]<=TOTAL_SETS):
            raise ValueError('A completed control must prove every original set without failures.')
        results[policy]=dict(exceedances=counts[-1],denominator=TOTAL_SETS,passed=20*counts[-1]<TOTAL_SETS)
    return dict(state='completed',passed=all(r['passed'] for r in results.values()),interpretations=results,
                threshold='strictly fewer than 500 out of 10000; ties count as exceedances')


def _gate(observed,threshold,comparison):
    passed=observed is not None and (observed>threshold if comparison=='>' else observed>=threshold)
    return dict(observed=observed,threshold=threshold,comparison=comparison,passed=bool(passed),
                state='observed' if observed is not None else 'unavailable')


def _account(spec,key,c,report):
    if report is None:return None
    arm=spec['development_arms'][key];cid=identity(c);context=report.get('research_arm_context',{})
    if (report.get('report_type')!='single_strategy' or report.get('config_id')!=cid or report.get('config')!=c.model_dump(mode='json')
            or report.get('core_hash')!=spec['core_hash'] or report.get('costs')!=spec['costs'] or report.get('portfolio')!=spec['portfolio']
            or report.get('dataset_context')!=arm['dataset_context'] or report.get('dataset_id')!=arm['dataset_context']['dataset_id']
            or report.get('dataset_manifest_hash')!=arm['dataset_context']['dataset_manifest_hash']
            or report.get('start')!=arm['start'] or report.get('end')!=arm['end']
            or context.get('arm_key')!=key or context.get('arm_hash')!=identity(arm) or context.get('role')!=arm['role']
            or context.get('configuration_universe_hash')!=spec['configuration_universe_hash']
            or set(report.get('charts',{}))!={arm['symbol']}):
        raise ValueError('Original arm role, complete rule, instrument, dates or assumptions differ.')
    metrics=report['metrics'];sharpe=metrics['marked_sharpe'];trades=metrics['trades']
    if type(metrics['net_profit']) not in (int,float) or (sharpe is not None and type(sharpe) not in (int,float)):
        raise ValueError('Original account metrics must be finite numerical scalars.')
    profit=_amount(metrics['net_profit'])
    if type(trades) is not int or trades<0 or trades!=len(report['trades']):raise ValueError('Original executed-trade denominator differs.')
    if sharpe is not None:_amount(sharpe)
    return dict(signal_count=count_discovery_signals(report['signals'],arm['start'],arm['end']),trades=trades,
                net_profit=metrics['net_profit'],marked_sharpe=sharpe,positive_profit=profit>0,report_hash=identity(report))


def qualify(spec,arm_reports,controls=None,cancel=None):
    """All rows/families survive attrition reporting; no supplied winner subset."""
    _cancel(cancel)
    if spec.get('stability_policy')!=STABILITY_POLICY or spec.get('control_scheduling_policy')!=CONTROL_SCHEDULING_POLICY:
        raise ValueError('Frozen stability or control-scheduling policy is missing or differs.')
    configurations=[Strategy(**c) for c in spec['configurations']];ids=[identity(c) for c in configurations]
    if set(arm_reports)!=set(ARMS):raise ValueError('All five distinct development axes are required.')
    if identity(spec['configurations'])!=spec['configuration_universe_hash']:raise ValueError('Frozen cohort differs.')
    controls={} if controls is None else controls
    if not isinstance(controls,Mapping) or set(controls)-set(ids):raise ValueError('Control identity is outside the original cohort.')
    observations={};families={};policy=spec['qualification_policy']
    for key in ARMS:
        _universe(configurations,arm_reports[key]);observations[key]={}
        for c,cid in zip(configurations,ids):
            _cancel(cancel);observations[key][cid]=_account(spec,key,c,arm_reports[key][cid])
    for family in sorted({c.family for c in configurations}):
        members=[c for c in configurations if c.family==family];member_ids=[identity(c) for c in members];axes={}
        for key in ARMS:
            axes[key]=family_average(members,_Members(arm_reports[key],member_ids),
                                     minimum_sharpe=policy['family']['minimum_sharpe'],cancel=cancel)
        primary=axes['primary_discovery'];marked=primary.get('marked')
        passed=bool(primary['state']=='complete' and marked['gate_pass'] and
                    all(axes[key]['state']=='complete' and int(axes[key]['marked']['net_profit']['numerator'])>0 for key in ['era_one','era_two']))
        families[family]=dict(members=member_ids,axes=axes,passed=passed,gate_basis='Primary marked mean and positive profit in both eras; realized-P&L compatibility separately retained.')
    rows=[]
    for c,cid in zip(configurations,ids):
        _cancel(cancel);accounts={key:observations[key][cid] for key in ARMS};gates={}
        def observed(key,name):return accounts[key][name] if accounts[key] is not None else None
        discovery=policy['discovery'];chrono=policy['chronological_validation'];replica=policy['replication']
        gates['discovery_signals']=_gate(observed('primary_discovery','signal_count'),discovery['minimum_signals'],'>=')
        for prefix,key,rules in [('discovery','primary_discovery',discovery),('chronological','chronological_validation',chrono)]:
            gates[prefix+'_trades']=_gate(observed(key,'trades'),rules['minimum_trades'],'>=')
            gates[prefix+'_profit']=_gate(observed(key,'net_profit'),0,'>')
            gates[prefix+'_sharpe']=_gate(observed(key,'marked_sharpe'),rules['minimum_sharpe'],'>=')
        for key in ['era_one','era_two']:gates[key+'_profit']=_gate(observed(key,'net_profit'),0,'>')
        gates['replication_profit']=_gate(observed('instrument_replication','net_profit'),0,'>')
        gates['replication_sharpe']=_gate(observed('instrument_replication','marked_sharpe'),replica['minimum_sharpe'],'>=')
        preliminary=all(value['passed'] for value in gates.values());control=control_gate(controls.get(cid))
        gates['matched_entries']=control
        rows.append(dict(config_id=cid,configuration=c.model_dump(mode='json'),accounts=accounts,gates=gates,
            prequalified=preliminary,candidate=preliminary and control['passed'],family_passed=families[c.family]['passed'],
            controls_required=preliminary,control_state=control['state']))
    result=dict(report_type='research_qualification',source_video=spec['source_video'],host_engine_parity_verified=False,
        version_count=len(ids),rows=rows,families=families,configuration_universe_hash=spec['configuration_universe_hash'],
        stability=stability(configurations,observations['primary_discovery'],cancel),
        incomplete_accounts=any(value is None for axis in observations.values() for value in axis.values()),
        qualification_does_not_consume_final=True,final_cohort_policy=spec['final_cohort_policy'],
        control_scheduling_policy=spec['control_scheduling_policy'])
    return finish_controls(result,controls,cancel)


def finish_controls(result,controls,cancel=None):
    """Attach source-verified diagnostic evidence without rerunning family math."""
    ids=[row['config_id'] for row in result['rows']]
    if not isinstance(controls,Mapping) or set(controls)-set(ids):raise ValueError('Unknown original diagnostic identity.')
    rows=[]
    for original in result['rows']:
        _cancel(cancel);cid=original['config_id'];control=control_gate(controls.get(cid))
        rows.append(original | dict(gates=original['gates'] | dict(matched_entries=control),
            candidate=original['prequalified'] and control['passed'],control_state=control['state']))
    attrition=_attrition(rows,cancel)
    pending=[row['config_id'] for row in rows if row['prequalified'] and row['control_state'] not in {'completed','ineligible'}]
    ineligible=[row['config_id'] for row in rows if row['prequalified'] and row['control_state']=='ineligible']
    return result | dict(state='incomplete_accounts' if result['incomplete_accounts'] else 'awaiting_controls' if pending else 'complete',
        rows=rows,candidate_ids=[row['config_id'] for row in rows if row['candidate']],pending_control_ids=pending,
        ineligible_control_ids=ineligible,attrition=attrition)


def _attrition(rows,cancel):
    remaining={row['config_id'] for row in rows};output=[]
    for name in GATE_ORDER:
        cohort=dict(passing=0,failed=0,unavailable=0,not_required=0,ineligible=0);prefix=cohort.copy();following=set()
        for row in rows:
            _cancel(cancel);gate=row['gates'][name]
            if gate['passed']:category='passing'
            elif gate['state'] in {'observed','completed'}:category='failed'
            elif name=='matched_entries' and gate['state']=='ineligible':category='ineligible'
            elif name=='matched_entries' and not row['controls_required']:category='not_required'
            else:category='unavailable'
            cohort[category]+=1
            if row['config_id'] in remaining:
                prefix[category]+=1
                if category=='passing':following.add(row['config_id'])
        output.append(dict(gate=name,entering=len(remaining),passing=prefix['passing'],removed=prefix['failed'],
            unavailable=prefix['unavailable'],not_required=prefix['not_required'],ineligible=prefix['ineligible'],
            cohort=cohort,confirmed_passing_prefix=True))
        remaining=following
    return output
