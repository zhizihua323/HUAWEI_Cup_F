import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')
s = s.replace("n=int(EV(tag,'n'))", "n=int(float(EV(tag,'n')))")
p.write_text(s, encoding='utf-8')
print('patched')
