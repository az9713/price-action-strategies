"""Run one foreground verification child under a temporary idle-sleep lease."""
import subprocess,sys
from verification_awake import awake
with awake():
    raise SystemExit(subprocess.run([sys.executable,*sys.argv[1:]]).returncode)
