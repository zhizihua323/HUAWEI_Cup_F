import pathlib
p = pathlib.Path('evidence/scaling_evidence.md')
s = p.read_text(encoding='utf-8')
reps = [
 ('`scaling_params.json.not_included`、本卡 §3 ③',
  '`scaling_params.json.not_included`、本卡 §4'),
 ('残差与该表损失仅 4 位小数（半单位 5e-5）同阶。',
  '残差量级（RMSE 1.46e-4）仅是该表损失舍入半单位（5e-5）的约 2.93 倍。'),
]
for old, new in reps:
    assert old in s, old
    s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('patched scaling card')
