import io
p = r"tmp\TASK-C01-R1-staging\verify_c01_repairs.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert old in s, "NOT FOUND: " + old[:140]
    s = s.replace(old, new, cnt)

rep('''    frozen_hashes = {a["file"]: a["sha256"] for a in frozen_manifest["artifacts"]}
    hash_bad = [i["input"] for i in inp
                if frozen_hashes.get(i["input"]) != sha256_file(os.path.join(source_dir, i["input"]))]
    results.append(result("V-IN-01", "every declared input is inside the frozen C01 directory and matches its frozen hash",
                          not raw_paths and not outside and not hash_bad,
                          {"inputs": len(inp), "raw_paths": raw_paths, "outside_source_dir": outside,
                           "hash_mismatches": hash_bad},
                          {"raw_paths": [], "outside_source_dir": [], "hash_mismatches": []},
                          "input_manifest.json vs output_manifest.json + live hashes",
                          "re-hash each declared input and compare with the archived manifest"))''',
'''    frozen_hashes = {a["file"]: a["sha256"] for a in frozen_manifest["artifacts"]}
    not_in_frozen = [i["input"] for i in inp if i["input"] not in frozen_hashes]
    hash_bad = [i["input"] for i in inp if i["input"] != "output_manifest.json"
                and frozen_hashes.get(i["input"]) != sha256_file(os.path.join(source_dir, i["input"]))]
    results.append(result("V-IN-01",
                          "every declared input is inside the frozen C01 directory; every input except "
                          "the manifest itself matches the hash archived in that manifest",
                          not raw_paths and not outside and not hash_bad
                          and not_in_frozen == ["output_manifest.json"],
                          {"inputs": len(inp), "raw_paths": raw_paths, "outside_source_dir": outside,
                           "hash_mismatches": hash_bad, "inputs_without_a_frozen_manifest_entry": not_in_frozen},
                          {"raw_paths": [], "outside_source_dir": [], "hash_mismatches": [],
                           "inputs_without_a_frozen_manifest_entry": ["output_manifest.json"]},
                          "input_manifest.json vs output_manifest.json + live hashes",
                          "re-hash every declared input and compare with the archived manifest; the "
                          "manifest cannot contain a hash of itself, so that single input is handled "
                          "explicitly instead of being counted as a mismatch"))
    key_items_pre = [c for c in repaired["checks"] if c.get("key_c8_item")]
    results.append(result("V-IND-06", "the key C8 item set is non-empty and covers the file, corruption, "
                                      "coverage and completeness families",
                          len(key_items_pre) >= 40
                          and any(c["check_id"].endswith("FILE-IDENTITY") for c in key_items_pre)
                          and any(c["check_id"].endswith("PROPAGATION") for c in key_items_pre)
                          and any(c["check_id"].endswith("WIDE-PARTIAL-NAN") for c in key_items_pre),
                          {"key_items": len(key_items_pre),
                           "ids": [c["check_id"] for c in key_items_pre]},
                          {"key_items": ">= 40 covering identity, propagation and partial-mean"},
                          "repaired_checks.json", "inventory of the key C8 items"))''')

io.open(p, "w", encoding="utf-8").write(s)
print("verifier patched")
