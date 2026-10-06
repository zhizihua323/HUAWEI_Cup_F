import importlib.util
from pathlib import Path
root = Path.cwd()
modpath = root / 'diagnostics/TASK-T07/20260925T113744+08/code/t07_run.py'
spec = importlib.util.spec_from_file_location('t07_run', modpath)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
d = m.load_inputs()
support = m.make_support()
m.H3_TABLE = d['h3']
m.H3_Q0 = {'q0': support['q0']}
drawdf, summary = m.run_uncertainty(d['registry'], d['draws'], support, d['p0'], d['coeff'])
drawdf.to_parquet(m.RUN / 'parameter_draw_optima.parquet', index=False)
summary.to_csv(m.RUN / 'uncertainty_summary.csv', index=False, encoding='utf-8-sig')
print(len(drawdf), len(summary))
