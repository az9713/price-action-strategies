"""Non-secret local environment receipt input; no user process enumeration."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes
import json
import os
import platform
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
        ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]

def main():
    value={'at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.platform(),'python':platform.python_version(),'logical_cpus':os.cpu_count()}
    if os.name=='nt':
        memory=Memory();memory.length=ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            value['memory']={'load_percent':memory.load,'total_bytes':memory.total,'available_bytes':memory.available}
    file=ROOT/'verification/runs/readiness-junit.xml'
    if file.exists():
        value['last_process_test_properties']=[p.attrib for p in ET.parse(file).iter('property')]
    destination=ROOT/'verification/runs/environment.json'
    destination.write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
if __name__=='__main__': main()
