"""Terminate this owned test subprocess at one real durable boundary."""
from pathlib import Path
import os
import sys
from backend.lab.service import Lab
from backend.lab.worker import Worker
from backend.lab import research_funnel_jobs as flow
from backend.lab import trade_twin_jobs

root,jid,point=sys.argv[1:];lab=Lab(Path(root));publish=flow._publish;wait=flow._wait;event=lab.store.event;create=trade_twin_jobs.create
codes=dict(preliminary_inside_transaction=241,preliminary_committed=242,control_reserved=243,
           waiting_committed=244,root_inside_transaction=245,root_committed=246)


def publish_at_boundary(*args,**kwargs):
    value=publish(*args,**kwargs)
    if (point=='preliminary_committed' and args[2]=='preliminary') or (point=='root_committed' and args[2]=='report'):
        os._exit(codes[point])
    return value


def event_at_boundary(kind,entity,details,db=None):
    value=event(kind,entity,details,db)
    if (point=='preliminary_inside_transaction' and kind=='funnel_preliminary_saved') or (point=='root_inside_transaction' and kind=='funnel_candidates_frozen'):
        os._exit(codes[point])
    return value


def create_at_boundary(*args,**kwargs):
    value=create(*args,**kwargs)
    if point=='control_reserved':os._exit(codes[point])
    return value


def wait_at_boundary(*args,**kwargs):
    value=wait(*args,**kwargs)
    if point=='waiting_committed' and value:os._exit(codes[point])
    return value


flow._publish=publish_at_boundary;flow._wait=wait_at_boundary;lab.store.event=event_at_boundary;trade_twin_jobs.create=create_at_boundary
assert Worker(lab).run_once()
raise AssertionError('The actual requested durable boundary was not reached: '+point)
