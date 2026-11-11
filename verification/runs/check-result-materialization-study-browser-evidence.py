"""Current result-view compatibility: complete study inputs, protection/history, joint accounts and offline source facts."""
from pathlib import Path
source=Path('verification/runs/check-study-status-browser-evidence.py').read_text(encoding='utf-8')
source=source.replace('study-status-current-two-desktop-download-repair-history-ownership-and-current-errors','result-materialization-current-fourteen-desktop-result-study-and-ownership-workflows').replace('study-status-current-two-desktop-portfolio-final-and-result-ownership','result-materialization-current-fourteen-desktop-result-study-and-ownership-workflows')
exec(compile(source,'result-materialization-study-browser-resolved.py','exec'))
