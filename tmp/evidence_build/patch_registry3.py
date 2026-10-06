import pathlib
p = pathlib.Path('tmp/evidence_build/build_registry.py')
s = p.read_text(encoding='utf-8')
s = s.replace("n=int(M('training_domain_means',lab,'n'))", "n=int(float(M('training_domain_means',lab,'n')))")
p.write_text(s, encoding='utf-8')
print('patched int() cast')
