"""Original preparation contract, compression and assembly corruption boundaries."""
from copy import deepcopy
from pathlib import Path
import gzip,json,hashlib
import pytest
from backend.lab.spread import SpreadError
from backend.lab.config import canonical,identity
from backend.lab import spread_preparation as module
from test_spread_preparation import settings,run

@pytest.mark.parametrize('binding',[None,True,'z'*64,'a'*63])
def test_preparation_requires_an_external_original_payload_identity(binding):
 with pytest.raises(SpreadError):module.preparation_contract(settings(),binding)

@pytest.mark.parametrize('fault',['same_directory','different_parent','malformed_header','missing_header','foreign_directory','out_of_budget','malformed_row','changed_configuration','changed_configuration_hash','changed_row_family','incomplete_seal','unanchored_manifest'])
def test_preparation_does_not_reconstruct_authority_from_corrupt_artifacts(tmp_path,monkeypatch,fault):
 folder=tmp_path/'owned';records=[];first=run(module,folder,records)
 if fault=='same_directory':
  with pytest.raises(SpreadError):module.prepare_plan(folder/'batches',folder/'batches',settings(),binding='a'*64,committed=[],commit=records.append)
  return
 if fault=='different_parent':
  with pytest.raises(SpreadError):module.prepare_plan(folder/'proposals',tmp_path/'other/batches',settings(),binding='a'*64,committed=[],commit=records.append)
  return
 if fault=='malformed_header':(folder/'batches/contract.json').write_text('{')
 elif fault=='missing_header':(folder/'batches/contract.json').unlink()
 elif fault=='foreign_directory':(folder/'batches/foreign').mkdir()
 elif fault=='out_of_budget':(folder/'batches'/settings().families[0]/'999999.json.gz').write_bytes(b'x')
 elif fault in {'malformed_row','changed_configuration','changed_configuration_hash','changed_row_family'}:
  record=records[0];p=folder/'batches'/record['relative_path'];row=json.loads(gzip.decompress(p.read_bytes()))
  if fault=='malformed_row':raw=b'not a json document'
  else:
   if fault=='changed_configuration':row['configurations'][0]['timeframe']='1d';record['configurations_hash']=identity(row['configurations'])
   elif fault=='changed_row_family':row['family']='foreign'
   else:row['configurations'][0]['direction']='short' if row['configurations'][0]['direction']!='short' else 'long'
   raw=canonical(row).encode()
  zipped=gzip.compress(raw,mtime=0);p.write_bytes(zipped);record.update(bytes=len(zipped),sha256=hashlib.sha256(zipped).hexdigest())
 elif fault=='incomplete_seal':records.pop()
 else:
  p=folder/'proposals/manifest.json';value=json.loads(p.read_text());value['planned_proposals']+=1;p.write_text(canonical(value))
 def forbidden(*a):raise AssertionError('Corrupt original preparation triggered new proposals')
 monkeypatch.setattr('backend.lab.spread.draw',forbidden)
 with pytest.raises(SpreadError):run(module,folder,records,expected_plan_id=first['plan'].plan_id if fault=='incomplete_seal' else None)

@pytest.mark.parametrize('fault',['batch_symlink','manifest_symlink','directory_symlink'])
def test_preparation_rejects_redirected_owned_paths(tmp_path,fault):
 folder=tmp_path/'owned';records=[];run(module,folder,records);outside=tmp_path/'outside';outside.mkdir();target=outside/'target';target.write_text('original external bytes')
 if fault=='directory_symlink':
  redirected=tmp_path/'redirected';redirected.mkdir()
  try:(redirected/'batches').symlink_to(outside,target_is_directory=True)
  except OSError:pytest.skip('Native symlink privilege unavailable; junction coverage remains a separate obligation.')
  folder=redirected;records=[]
 else:
  p=folder/('proposals/manifest.json' if fault=='manifest_symlink' else 'batches/'+records[0]['relative_path']);p.unlink()
  try:p.symlink_to(target)
  except OSError:pytest.skip('Native symlink privilege unavailable; junction coverage remains a separate obligation.')
 with pytest.raises(SpreadError):run(module,folder,records)
 assert target.read_text()=='original external bytes'

def test_repeated_uncommitted_identical_bytes_reuse_the_preserved_orphan(tmp_path):
 folder=tmp_path/'owned';events=[]
 def crash(record):raise InterruptedError('Before external commit')
 for _ in range(3):
  with pytest.raises(InterruptedError):module.prepare_plan(folder/'proposals',folder/'batches',settings(),binding='a'*64,committed=[],commit=crash)
 result=run(module,folder,events)
 assert result['plan'].manifest['planned_proposals']==30 and len(list((folder/'preparation-orphans').glob('*.gz')))==1

def test_rebuilt_unanchored_family_preserves_changed_original_bytes(tmp_path):
 folder=tmp_path/'owned';events=[];first=run(module,folder,events);p=folder/'proposals'/(settings().families[0]+'.jsonl.gz');p.write_bytes(b'altered unanchored family')
 result=run(module,folder,events)
 assert result['plan'].plan_id==first['plan'].plan_id and any(p.read_bytes()==b'altered unanchored family' for p in (folder/'preparation-orphans').glob('*.gz'))

def test_foreign_assembly_directory_is_never_absorbed_into_a_plan(tmp_path):
 folder=tmp_path/'owned';events=[];run(module,folder,events);(folder/'proposals/foreign').mkdir()
 with pytest.raises(SpreadError):run(module,folder,events)
