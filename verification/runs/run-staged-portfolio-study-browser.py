import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from verification.frontend_check import browser_run
raise SystemExit(browser_run(['exec','--','playwright','test','--config=../verification/runs/portfolio-study-browser.config.ts','portfolio-study.spec.ts']))
