"""Reusable historical acquisition path for CLI and background jobs."""
from pathlib import Path
from .provider import Alpaca,parse_actions
from .data import save_dataset,DataError

def ingest(root:Path,symbols,start,end,cancel=None,progress=None):
    with Alpaca(root/'.env',root/'data'/'downloads') as provider:
        frame,metadata=provider.bars(symbols,start,end,cancel,progress)
        raw_actions,action_source=provider.corporate_actions(symbols,start,end,cancel)
    actions,issues=parse_actions(raw_actions,start,end)
    metadata.update(corporate_action_source=action_source,corporate_actions_raw=raw_actions,
                    corporate_action_issues=issues,
                    corporate_actions_status='provider_query_completed_not_independently_certified',
                    input_kind='historical_market_data',
                    limitations=['Provider corporate-action history can be incomplete; unsupported/incomplete records block ordinary execution.',
                                 'No point-in-time universe or stock-lending history is inferred from prices.'])
    manifest=save_dataset(root/'data'/'datasets',frame,metadata,actions,start,end)
    return manifest
