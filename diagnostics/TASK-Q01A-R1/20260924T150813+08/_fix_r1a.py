from pathlib import Path
import sys
p = Path(__file__).resolve().parent / 'repair_from_artifacts.py'
t = p.read_text(encoding='utf-8-sig')
new_id = p.parent.name
old_id_line = "RUN_ID = '20260924T150623+08'"
assert t.count(old_id_line) == 1
t = t.replace(old_id_line, f"RUN_ID = '{new_id}'", 1)
old_filter = "READ_ONLY_INPUTS = [R_DIR / name for name in sorted(os.listdir(R_DIR))]"
new_filter = ("READ_ONLY_INPUTS = [R_DIR / name for name in sorted(os.listdir(R_DIR))\n"
              "                   if (R_DIR / name).is_file()]\n"
              "R_DIR_SUBDIRECTORIES = [name for name in sorted(os.listdir(R_DIR)) if (R_DIR / name).is_dir()]")
assert t.count(old_filter) == 1
t = t.replace(old_filter, new_filter, 1)
t = t.replace("""    input_manifest['notes'].append('pandas default NA parsing is not used for invalid_values.csv.gz (csv module) '
                                   'so that the literal "nan" in reason/value_kind is preserved')""",
"""    input_manifest['notes'].append('pandas default NA parsing is not used for invalid_values.csv.gz (csv module) '
                                   'so that the literal "nan" in reason/value_kind is preserved')
    input_manifest['read_only_input_directories_not_required'] = R_DIR_SUBDIRECTORIES""", 1)
p.write_text(t, encoding='utf-8-sig')
print('patched RUN_ID ->', new_id)
