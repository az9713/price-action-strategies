"""Use the observed native PowerShell binary; preserve the original verifier and failed receipt."""
from pathlib import Path
source=Path('verification/runs/check-search-statistics-runtime.py').read_text(encoding='utf-8')
before="['powershell.exe','-NoProfile','-Command',script]"
after="[str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'),'-NoProfile','-Command',script]"
assert source.count(before)==1
exec(compile(source.replace(before,after),'check-search-statistics-runtime-v2-resolved.py','exec'))
