from pathlib import Path
p = Path(__file__).resolve().parent / 'diagnose_missingness.py'
t = p.read_text(encoding='utf-8-sig')

# 1) add restricted constant evaluator before verify_source_spec
anchor = "def verify_source_spec():"
helper = '''def eval_const_expr(node, env):
    """Structural evaluator for module-level constant expressions of the audited
    source (names, list/dict literals, list() call, + concatenation, dict
    comprehension over PRRC). No module import and no attribute access."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise PreconditionError(f'unknown name in constant expression: {node.id}')
        return env[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [eval_const_expr(item, env) for item in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for key, value in zip(node.keys, node.values):
            if key is None:
                out.update(eval_const_expr(value, env))
            else:
                out[eval_const_expr(key, env)] = eval_const_expr(value, env)
        return out
    if isinstance(node, ast.DictComp):
        gens = node.generators
        if len(gens) != 1 or gens[0].ifs or gens[0].is_async:
            raise PreconditionError('unsupported dict comprehension in source constants')
        target = gens[0].target
        if not isinstance(target, ast.Name):
            raise PreconditionError('unsupported comprehension target')
        out = {}
        for item in eval_const_expr(gens[0].iter, env):
            local = dict(env)
            local[target.id] = item
            out[eval_const_expr(node.key, local)] = eval_const_expr(node.value, local)
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return eval_const_expr(node.left, env) + eval_const_expr(node.right, env)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'list'
            and len(node.args) == 1 and not node.keywords):
        return list(eval_const_expr(node.args[0], env))
    raise PreconditionError(f'unsupported constant expression node: {type(node).__name__}')


def verify_source_spec():'''
assert t.count(anchor) == 1
t = t.replace(anchor, helper, 1)

old_loop = """    for name, expected in expected_literals.items():
        if name not in nodes:
            raise PreconditionError(f'source constant {name} not found by AST')
        actual = ast.literal_eval(nodes[name])"""
new_loop = """    env = {}
    for name, expected in expected_literals.items():
        if name not in nodes:
            raise PreconditionError(f'source constant {name} not found by AST')
        actual = eval_const_expr(nodes[name], env)
        env[name] = actual"""
assert t.count(old_loop) == 1
t = t.replace(old_loop, new_loop, 1)

old_list = '''    node = nodes.get('LIST_LENGTHS')
    if not isinstance(node, ast.Dict):
        raise PreconditionError('LIST_LENGTHS is not a dict literal in source')
    explicit = {}
    unpack_ok = False
    for key, value in zip(node.keys, node.values):
        if key is None:
            unpack_ok = (isinstance(value, ast.DictComp)
                         and isinstance(value.key, ast.Constant) and value.key.value == 6
                         and isinstance(value.target, ast.Name) and value.target.id == 'p'
                         and isinstance(value.iter, ast.Name) and value.iter.id == 'PRRC')
        else:
            explicit[ast.literal_eval(key)] = ast.literal_eval(value)
    expected_explicit = {'fineweb_edu': 1, 'ad_en': 2, 'fluency_en': 2, 'qurater': 4}
    if explicit != expected_explicit or not unpack_ok:
        raise PreconditionError(f'LIST_LENGTHS structure differs: {explicit} unpack_ok={unpack_ok}')
    report['checks']['LIST_LENGTHS'] = True'''
new_list = '''    node = nodes.get('LIST_LENGTHS')
    if not isinstance(node, ast.Dict):
        raise PreconditionError('LIST_LENGTHS is not a dict literal in source')
    explicit = {}
    unpack_ok = False
    for key, value in zip(node.keys, node.values):
        if key is None:
            gen = value.generators[0] if isinstance(value, ast.DictComp) and value.generators else None
            unpack_ok = (isinstance(value, ast.DictComp)
                         and isinstance(value.value, ast.Constant) and value.value.value == 6
                         and isinstance(value.key, ast.Name) and value.key.id == 'p'
                         and gen is not None and isinstance(gen.target, ast.Name)
                         and gen.target.id == 'p' and isinstance(gen.iter, ast.Name)
                         and gen.iter.id == 'PRRC' and not gen.ifs and not gen.is_async)
        else:
            explicit[ast.literal_eval(key)] = ast.literal_eval(value)
    expected_explicit = {'fineweb_edu': 1, 'ad_en': 2, 'fluency_en': 2, 'qurater': 4}
    if explicit != expected_explicit or not unpack_ok:
        raise PreconditionError(f'LIST_LENGTHS structure differs: {explicit} unpack_ok={unpack_ok}')
    evaluated = eval_const_expr(node, env)
    if evaluated != LIST_LENGTHS:
        raise PreconditionError(f'LIST_LENGTHS value differs from pinned spec: {evaluated}')
    report['checks']['LIST_LENGTHS'] = True'''
assert t.count(old_list) == 1
t = t.replace(old_list, new_list, 1)
p.write_text(t, encoding='utf-8-sig')
print('source-spec evaluator patched')
