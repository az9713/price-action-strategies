"""Isolated old/new decoding of one real authored account; not financial capacity."""
from contextlib import closing
from pathlib import Path
import ctypes,gzip,hashlib,importlib.util,json,os,sqlite3,subprocess,sys,time
root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))


def memory():
    from ctypes import wintypes
    size=ctypes.c_size_t
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',size),('WorkingSetSize',size),('QuotaPeakPagedPoolUsage',size),('QuotaPagedPoolUsage',size),('QuotaPeakNonPagedPoolUsage',size),('QuotaNonPagedPoolUsage',size),('PagefileUsage',size),('PeakPagefileUsage',size)]
    get=ctypes.windll.kernel32.GetCurrentProcess;get.restype=wintypes.HANDLE
    read=ctypes.windll.psapi.GetProcessMemoryInfo;read.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];read.restype=wintypes.BOOL
    result=Counters();result.cb=ctypes.sizeof(result)
    if not read(get(),ctypes.byref(result),result.cb):raise ctypes.WinError()
    return dict(peak_rss_bytes=result.PeakWorkingSetSize,rss_bytes=result.WorkingSetSize)


def child(mode,path,digest):
    if mode=='old':
        spec=importlib.util.spec_from_file_location('backend.lab._before_bounded_io',root/'verification/runs/research-family-reader-before-bounded-reads.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    else:
        from backend.lab import research_family_source as module
    from backend.lab.config import identity
    before=memory();started=time.perf_counter();values=[]
    for _ in range(3):values.append(identity(module._load(Path(path),digest)))
    elapsed=time.perf_counter()-started;after=memory();assert len(set(values))==1
    print(json.dumps(dict(mode=mode,iterations=3,elapsed_seconds=elapsed,decoded_sha256=values[0],before=before,after=after,unchanged_max_artifact_bytes=module.MAX_ARTIFACT_BYTES)))


def main():
    out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);folders=sorted((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns,reverse=True)
    folder=folders[0];assert folder.resolve().is_relative_to((root/'data/dev027/funnel-browser').resolve())
    with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone();assert row is not None
        digest=db.execute("SELECT artifact_sha256 FROM trial_plans WHERE job_id=? AND part=0 AND window='primary_final'",(row[0],)).fetchone()[0]
    path=folder/'data/jobs'/row[0]/'final/primary_final/000000.json.gz';assert path.is_file()
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
    expected=hashlib.sha256(json.dumps(json.loads(gzip.decompress(raw)),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    subject=json.loads((root/'verification/runs/20261110T111621237751Z-funnel-complete-saved-original-csv-zip-offline-and-authority-export-contracts/research-stage-subject.json').read_text(encoding='utf-8'))
    old=root/'verification/runs/research-family-reader-before-bounded-reads.py';old_sha=hashlib.sha256(old.read_bytes()).hexdigest()
    assert old_sha==subject['source_files']['backend/lab/research_family_source.py']
    outputs=[]
    for mode in ['old','new']:
        result=subprocess.run([sys.executable,'-X','utf8',__file__,'--child',mode,str(path),digest],cwd=root,capture_output=True,text=True,encoding='utf-8')
        assert result.returncode==0,result.stderr;value=json.loads(result.stdout);assert value['decoded_sha256']==expected and value['unchanged_max_artifact_bytes']==512*1024*1024;outputs.append(value)
    saved=outputs[0]['after']['peak_rss_bytes']-outputs[1]['after']['peak_rss_bytes']
    assert saved>256*1024*1024,(outputs,saved)
    value=dict(scope=__doc__,input_artifact=path.relative_to(root).as_posix(),original_trial_bound_artifact_sha256=digest,compressed_bytes=len(raw),expanded_bytes=len(gzip.decompress(raw)),exact_decoded_content_sha256=expected,
        original_control_source_sha256=old_sha,current_source_sha256=hashlib.sha256((stage/'backend/lab/research_family_source.py').read_bytes()).hexdigest(),measurements=outputs,measured_peak_rss_reduction_bytes=saved,
        actual_financial_accounts_executed=0,market_or_global_capacity_certified=False)
    (out/'isolated-original-reader-before-after.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))


if __name__=='__main__':
    if '--child' in sys.argv:child(*sys.argv[2:])
    else:main()
