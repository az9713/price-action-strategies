"""Instrumented profiling diagnostic, not an uninstrumented throughput measurement."""
from pathlib import Path
import cProfile,pstats,runpy,sys
root=Path.cwd();sys.argv=[str(root/'verification/runs/measure-capacity-real-sample.py'),'100']
profile=cProfile.Profile();profile.enable()
try:runpy.run_path(sys.argv[0],run_name='__main__')
finally:
 profile.disable();print('INSTRUMENTED PROFILE; wall times include profiling and are not the baseline capacity measurements.')
 pstats.Stats(profile).strip_dirs().sort_stats('cumulative').print_stats(45)
