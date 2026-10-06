import io
p = r"tmp\TASK-C01-R1-staging\repair_c01_from_artifacts.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert old in s, "NOT FOUND: " + old[:120]
    s = s.replace(old, new, cnt)

rep('''    A(f"- \\u8f93\\u5165\\u4e0e\\u539f manifest \\u4e0d\\u4e00\\u81f4\\u7684\\u6570\\u91cf\\uff1a**{ctx['input_manifest_mismatches']}**\\u3002")''',
'''    A(f"- \\u9664 `output_manifest.json` \\u672c\\u8eab\\u5916\\uff0c\\u8f93\\u5165\\u4e0e\\u539f manifest \\u9010\\u9879\\u4e0d\\u4e00\\u81f4\\u7684\\u6570\\u91cf\\uff1a**{ctx['input_manifest_other_mismatches']}**\\u3002"
      f"`output_manifest.json` \\u65e0\\u6cd5\\u5728\\u81ea\\u8eab\\u5185\\u90e8\\u5217\\u51fa\\u81ea\\u5df1\\u7684 hash\\uff0c\\u5df2\\u5728 `repaired_checks.json` \\u7684 `R1-IN-MANIFEST` "
      "\\u4e2d\\u4f5c\\u4e3a `self_referential_inputs` \\u5355\\u72ec\\u58f0\\u660e\\uff0c\\u4e0d\\u8ba1\\u4e3a hash \\u4e0d\\u4e00\\u81f4\\u3002")''')

rep('''    "C8-05": ("REPAIRED_AND_VERIFIED", ["R1-C8-GROUP-KEY-MISSING"],
               "the missing-group count is cross-checked against the zero-result rows"),''',
    '''    "C8-05": ("REPAIRED_AND_VERIFIED_AND_CORRECTED", ["R1-C8-GROUP-KEY-MISSING"],
               "the missing-group count is cross-checked against the zero-result rows; the cross-check "
               "showed the two are NOT equal (19 missing keys vs 25 zero-result rows), so the repaired "
               "check reconciles them as a superset relation and records the extra 6 rows as present "
               "keys without a usable metric, instead of repeating the original single-signal claim"),''')

rep('''        "n_inputs": len(inputs_manifest), "input_manifest_mismatches": n_bad_inputs,''',
    '''        "n_inputs": len(inputs_manifest), "input_manifest_mismatches": n_bad_inputs,
        "input_manifest_other_mismatches": sum(1 for i in inputs_manifest
                                               if i["input"] != "output_manifest.json"
                                               and not i["matches_frozen_manifest"]),''')

io.open(p, "w", encoding="utf-8").write(s)
print("handoff wording + C8-05 explanation patched")
