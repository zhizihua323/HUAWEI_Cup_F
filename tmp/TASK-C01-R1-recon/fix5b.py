import io
p = r"tmp\TASK-C01-R1-staging\repair_c01_from_artifacts.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert old in s, "NOT FOUND: " + old[:140]
    s = s.replace(old, new, cnt)

rep('''    gk = gs.loc[~gs.group_key_present.fillna(False)]
    gk_by_task = gk.groupby("task_group").size().to_dict()
    zero_task = mt.loc[mt.n_valid_results == 0].groupby("task_group").size().to_dict()
    add("R1-C8-GROUP-KEY-MISSING", "documents lacking a leaderboard group key are identified and counted",
        {"group_rows_missing_source_key": int(len(gk)),
         "missing_by_task": {str(k): int(v) for k, v in gk_by_task.items()},
         "model_task_zero_rows_by_task": {str(k): int(v) for k, v in zero_task.items()},
         "agree": {str(k): int(v) for k, v in gk_by_task.items()} == {str(k): int(v) for k, v in zero_task.items()}},
        {"agree": True},
        "c8_group_scores_all_runs.csv vs c8_model_task_aggregate.csv",
        "the per-task count of group rows whose source key is absent must equal the per-task count of "
        "model x task rows with zero valid results",
        "the original C8-05 reported the count without cross-checking it")''',
'''    gk_by_task = gs.loc[~gs.group_key_present.fillna(False)].groupby("task_group").size().to_dict()
    zero_task = mt.loc[mt.n_valid_results == 0].groupby("task_group").size().to_dict()
    tasks_union = sorted(set(gk_by_task) | set(zero_task))
    per_task_ge = {str(t): int(zero_task.get(t, 0)) >= int(gk_by_task.get(t, 0)) for t in tasks_union}
    add("R1-C8-GROUP-KEY-MISSING",
        "missing group keys and zero-result rows are reconciled: a zero-result row is either a missing "
        "group key or a present key whose metric is absent or non-numeric",
        {"group_rows_missing_source_key": int(sum(gk_by_task.values())),
         "model_task_zero_rows": int(sum(zero_task.values())),
         "missing_by_task": {str(k): int(v) for k, v in gk_by_task.items()},
         "zero_rows_by_task": {str(k): int(v) for k, v in zero_task.items()},
         "zero_rows_ge_missing_keys_per_task": per_task_ge,
         "zero_rows_minus_missing_keys": int(sum(zero_task.values()) - sum(gk_by_task.values())),
         "zero_rows_total_matches_anchor": int(sum(zero_task.values())) == ANCHOR["n_model_task_rows_zero"]},
        {"model_task_zero_rows": ANCHOR["n_model_task_rows_zero"],
         "zero_rows_ge_missing_keys_per_task": {str(t): True for t in tasks_union},
         "zero_rows_total_matches_anchor": True},
        "c8_group_scores_all_runs.csv (group_key_present) vs c8_model_task_aggregate.csv (n_valid_results)",
        "per-task comparison of the two independent zero-coverage signals; the total is compared with "
        "the work-order anchor 25 = 11160 - 11135",
        "the two signals are NOT equal: some documents carry the group key but not the specific metric, "
        "so a zero-result row can occur with the key present. The original C8-05 attributed every "
        "missing task score to a missing group key, which this cross-check shows is incomplete.")''')

rep('''    add("R1-IN-MANIFEST", "every R1 input still hashes to the value in the frozen TASK-C01 output manifest",
        {"inputs": len(inputs_manifest),
         "not_matching": [i["input"] for i in inputs_manifest if not i["matches_frozen_manifest"]],
         "not_in_frozen_manifest": [i["input"] for i in inputs_manifest if not i["frozen_manifest_present"]]},
        {"not_matching": [], "not_in_frozen_manifest": []},''',
'''    self_ref = [i["input"] for i in inputs_manifest if i["input"] == "output_manifest.json"]
    others = [i for i in inputs_manifest if i["input"] != "output_manifest.json"]
    add("R1-IN-MANIFEST", "every R1 input still hashes to its value in the frozen TASK-C01 output manifest",
        {"inputs": len(inputs_manifest),
         "not_matching": [i["input"] for i in others if not i["matches_frozen_manifest"]],
         "not_in_frozen_manifest": [i["input"] for i in others if not i["frozen_manifest_present"]],
         "self_referential_inputs": self_ref},
        {"not_matching": [], "not_in_frozen_manifest": [], "self_referential_inputs": ["output_manifest.json"]},''')

io.open(p, "w", encoding="utf-8").write(s)
print("part B patched")
