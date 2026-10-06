import io
p = r"tmp\TASK-C01-R1-staging\repair_c01_from_artifacts.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert old in s, "NOT FOUND: " + old[:120]
    s = s.replace(old, new, cnt)

rep('CHECKS = []\n', '''CHECKS = []

# Checks that guard the C8 file / corruption / coverage / completeness semantics.
# Acceptance criterion 9 requires these to be PASS or FAIL only - never NOT_CHECKED / NOT_VERIFIABLE.
KEY_CHECK_IDS = {
    "R1-C8-FILE-TOTAL", "R1-C8-FILE-OK", "R1-C8-FILE-FAIL", "R1-C8-FILE-IDENTITY",
    "R1-C8-DIR-COUNT", "R1-C8-DIR-FILESET-EQUAL", "R1-C8-DIR-FILE-COUNT-MATCH",
    "R1-C8-DIR-ONE-FILE", "R1-C8-DIR-TWO-FILE", "R1-C8-CORRUPT-SET", "R1-C8-CORRUPT-SHA",
    "R1-C8-CORRUPT-DIRS", "R1-C8-PURE-CORRUPT", "R1-C8-PROPAGATION", "R1-C8-PURE-CORRUPT-ROW",
    "R1-C8-DIR-ID", "R1-C8-SLOTS", "R1-C8-FINITE", "R1-C8-MISSING-SLOTS", "R1-C8-DIRVALID-SUM",
    "R1-C8-CORRUPTDIR-SCORES", "R1-C8-GROUP-GRIDSET", "R1-C8-GROUP-KEY-MISSING",
    "R1-C8-MT-ROWS", "R1-C8-MT-VALID-ROWS", "R1-C8-MT-ZERO-ROWS", "R1-C8-MT-SUM",
    "R1-C8-MT-RECOMPUTE", "R1-C8-MT-COVERAGE", "R1-C8-MT-INCOMPLETE-PROP",
    "R1-C8-WIDE-ROWS", "R1-C8-WIDE-ROWS-CORRECTED", "R1-C8-WIDE-DIST", "R1-C8-WIDE-DIST-CROSS",
    "R1-C8-WIDE-COMPLETE", "R1-C8-WIDE-COMPLETE-MEAN", "R1-C8-WIDE-PARTIAL-MEAN",
    "R1-C8-WIDE-PARTIAL-NAN", "R1-C8-WIDE-PARTIAL-LIST", "R1-C8-WIDE-CONSISTENT",
    "R1-C8-WIDE-LEGACY-CONTRAST", "R1-C8-X-DIRMODEL", "R1-C8-X-MTWIDE", "R1-C8-NONNUMERIC",
}
''')
rep('''        "claim": claim, "key_c8_item": bool(key),''',
    '''        "claim": claim, "key_c8_item": bool(key or check_id in KEY_CHECK_IDS),''')

rep('"C4 row count and Publication-date completeness agree across four frozen artifacts",',
    '"C4 row count and Publication-date completeness agree across four frozen artifacts; a blank CSV '
    'field counts as MISSING and is not conflated with a parse failure",')
rep('''         "missing_equals_rows_minus_nonnull": int(c4_miss.missing_nan) == int(c4_pub.rows) - int(c4_pub.nonnull),
         "parse_fail_equals_rows_minus_parsed": int(c4_pub.parse_fail) == int(c4_field.rows) - int(c4_pub.parsed_ok),
         "nonnull_plus_missing_equals_rows": int(c4_pub.nonnull) + int(c4_pub.parse_fail) == int(c4_pub.rows)},
        {"rows_agree": True, "nonnull_agree": True, "missing_equals_rows_minus_nonnull": True,
         "parse_fail_equals_rows_minus_parsed": True, "nonnull_plus_missing_equals_rows": True},''',
'''         "missing_equals_rows_minus_nonnull": int(c4_miss.missing_nan) == int(c4_pub.rows) - int(c4_pub.nonnull),
         "parse_fail_equals_nonnull_minus_parsed": int(c4_pub.parse_fail) == int(c4_pub.nonnull) - int(c4_pub.parsed_ok),
         "nonnull_plus_missing_equals_rows": int(c4_pub.nonnull) + int(c4_miss.missing_nan) == int(c4_pub.rows)},
        {"rows_agree": True, "nonnull_agree": True, "missing_equals_rows_minus_nonnull": True,
         "parse_fail_equals_nonnull_minus_parsed": True, "nonnull_plus_missing_equals_rows": True},''')

rep('"C1 submission-date coverage agrees across three artifacts",',
    '"C1 submission-date coverage agrees across three artifacts; missing fields are separated from '
    'parse failures",')
rep('''         "missing_agree": int(c1_sub_miss) == int(c1_sub.parse_fail),
         "nonnull_plus_missing_equals_rows": int(c1_sub.nonnull) + int(c1_sub.parse_fail) == int(c1_sub.rows),
         "parse_rate_is_one": bool(np.isclose(float(c1_sub.parse_rate_of_nonnull), 1.0))},
        {"rows_agree": True, "nonnull_agree": True, "missing_agree": True,
         "nonnull_plus_missing_equals_rows": True, "parse_rate_is_one": True},''',
'''         "missing_matches_rows_minus_nonnull": int(c1_sub_miss) == int(c1_sub.rows) - int(c1_sub.nonnull),
         "parse_fail_is_zero": int(c1_sub.parse_fail) == 0,
         "nonnull_plus_missing_equals_rows": int(c1_sub.nonnull) + int(c1_sub_miss) == int(c1_sub.rows),
         "parse_rate_is_one": bool(np.isclose(float(c1_sub.parse_rate_of_nonnull), 1.0))},
        {"rows_agree": True, "nonnull_agree": True, "missing_matches_rows_minus_nonnull": True,
         "parse_fail_is_zero": True, "nonnull_plus_missing_equals_rows": True, "parse_rate_is_one": True},''')

rep('''    type_pat = re.compile(r"(^|[_\\s])type($|[_\\s])", re.I)
''', '''    def is_model_type_column(name):
        """A model-Type column, not the parse-error column `error_type`."""
        n = re.sub(r"[^a-z]", "", str(name).lower())
        return n in {"type", "modeltype", "modeltypeclass", "architecturetype"}
''')
rep('''         "parse_log_type_hits": [c for c in log_cols if type_pat.search(c)],''',
    '''         "parse_log_type_hits": [c for c in log_cols if is_model_type_column(c)],''')
rep('''         "task_inventory_type_hits": [c for c in inv_cols if type_pat.search(c)],''',
    '''         "task_inventory_type_hits": [c for c in inv_cols if is_model_type_column(c)],''')

io.open(p, "w", encoding="utf-8").write(s)
print("part A patched")
