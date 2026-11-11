"""Retain the first actual D040 aggregate-provenance failure as an open product gap."""
from pathlib import Path
import json
root=Path.cwd();p=root/'verification/defects.json';value=json.loads(p.read_text(encoding='utf-8'))
receipt=sorted((root/'verification/receipts').glob('*-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract.json'))[-1]
r=json.loads(receipt.read_text(encoding='utf-8'));assert r['command']['exit_code']==1
report=json.loads((root/next(a['path'] for a in r['artifacts'] if a['path'].endswith('/aggregate-provenance-first-contract.json'))).read_text(encoding='utf-8'));assert len(report['missing'])==18
row=dict(id='D-AGGREGATE-DATASET-PROVENANCE-001',status='open_authored_fresh_job_counterexample_before_implementation',area='Aggregate instrument and synthetic/historical provenance',observed='A fresh synthetic one-account common search completes, but its queued payload/root lack frozen dataset context; CSV and offline facts omit input kind, instruments/source and manifest context. The first contract reports18 missing locations/fields. Individual account provenance does not complete the aggregate use case.',fix='Pending D040: freeze minimal verified dataset context before queueing; preserve it in saved aggregate/CSV/offline/UI results; distinguish unknown/user imports; do not infer from the selected UI dataset or rewrite legacy jobs. Extend all aggregate types, corruption/recovery and protected metadata tests before acceptance.',initial_evidence=receipt.relative_to(root).as_posix())
old=next((d for d in value['defects'] if d['id']==row['id']),None)
if old:assert old==row
else:value['defects'].append(row)
p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(total_defect_records=len(value['defects']),open_product_gap=row['id'],first_failure_retained=True)))
