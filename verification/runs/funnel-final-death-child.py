"""Exit only this test subprocess at an actual protected-final boundary."""
import os
from pathlib import Path
import sys
from backend.lab.service import Lab
from backend.lab.worker import Worker
from backend.lab import service,research_funnel_final as flow

root,jid,point=sys.argv[1:];lab=Lab(Path(root));event=lab.store.event;consume=flow._consume;checkpoint=flow.publish_checkpoint;publish=flow._publish;receipt=flow.atomic_json
CODES=dict(inside_consumption=200,after_consumption=201,first_account_committed=202,second_instrument_committed=203,
           inside_root=204,root_committed=205,inside_view=206,first_account_file_uncommitted=207)
service.generate_signals=lambda *args,**kwargs:[]


def consume_at_boundary(*args,**kwargs):
    value=consume(*args,**kwargs)
    if point=='after_consumption':os._exit(CODES[point])
    return value


def event_at_boundary(kind,entity,details,db=None):
    value=event(kind,entity,details,db)
    if (point=='inside_consumption' and kind=='final_unlock_consumed'
            or point=='inside_root' and kind=='result_saved' and entity==jid
            or point=='inside_view' and kind=='result_view_saved' and entity==jid):os._exit(CODES[point])
    return value


def checkpoint_at_boundary(*args,**kwargs):
    value=checkpoint(*args,**kwargs)
    if args[2]==0 and (point=='first_account_committed' and args[6]==['primary_final']
                       or point=='second_instrument_committed' and args[6]==['replication_final']):os._exit(CODES[point])
    return value


def publish_at_boundary(*args,**kwargs):
    value=publish(*args,**kwargs)
    if point=='root_committed':os._exit(CODES[point])
    return value


def receipt_at_boundary(*args,**kwargs):
    value=receipt(*args,**kwargs)
    if point=='first_account_file_uncommitted':os._exit(CODES[point])
    return value


flow._consume=consume_at_boundary;lab.store.event=event_at_boundary;flow.publish_checkpoint=checkpoint_at_boundary
flow._publish=publish_at_boundary;flow.atomic_json=receipt_at_boundary
assert Worker(lab).run_once()
raise AssertionError('The real final boundary was not reached: '+point)
