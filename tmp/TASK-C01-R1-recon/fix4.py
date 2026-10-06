import io
ws = r"tmp\TASK-C01-R1-staging"

helper = '''
def find_workspace(start):
    """Locate the project root by looking for the F\u9898 / solution markers, so that the script
    behaves identically whether it is executed from a staging directory or from the run directory."""
    cur = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "F\u9898")) or os.path.isdir(os.path.join(cur, "solution")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(start)

'''

p1 = ws + r"\repair_c01_from_artifacts.py"
s = io.open(p1, encoding="utf-8").read()
old1 = 'WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))'
assert old1 in s
s = s.replace(old1, 'WORKSPACE = find_workspace(os.path.dirname(os.path.abspath(__file__)))', 1)
anchor1 = 'TASKS = ["IFEval", "BBH", "MATH Lvl 5", "GPQA", "MUSR", "MMLU-PRO"]\n'
assert anchor1 in s
s = s.replace(anchor1, anchor1 + helper, 1)
io.open(p1, "w", encoding="utf-8").write(s)

p2 = ws + r"\verify_c01_repairs.py"
v = io.open(p2, encoding="utf-8").read()
old2 = '    workspace = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))'
assert old2 in v
v = v.replace(old2, '    workspace = find_workspace(os.path.dirname(os.path.abspath(__file__)))', 1)
anchor2 = 'LOG = []\n'
assert anchor2 in v
v = v.replace(anchor2, anchor2 + helper, 1)
io.open(p2, "w", encoding="utf-8").write(v)
print("workspace resolution made location independent for both scripts")
