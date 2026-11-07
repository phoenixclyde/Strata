import json, os, copy

SRC = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
OUT = '/home/albus/strata166/data/w824arm'
os.makedirs(OUT, exist_ok=True)
base = json.load(open(SRC))

NEW = '/data/bin/strata-0.1.53'
OLD = '/src/build-906/strata'


def mk(name, exe, log_suffix=None, env=None, arg_pairs=None):
    d = copy.deepcopy(base)
    d['exe'] = exe
    d['log'] = '/data/w824_%s.log' % (log_suffix or name)
    d['env']['STRATA_PREFILL_TIMING'] = '1'      # 相位表：所有臂一致，否则拿不到 ple/attn 分解
    if env:
        d['env'].update(env)
    a = d['args']
    if arg_pairs:
        for k, v in arg_pairs.items():
            if k in a:
                a[a.index(k) + 1] = v
            else:
                a += [k, v]
    p = os.path.join(OUT, name + '.json')
    json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
    print('%-6s exe=%-26s args=%d env=%d log=%s' % (name, d['exe'], len(a), len(d['env']), d['log']))
    return d


# 0.1.53 的三臂调优（全部同一 exe，只差一个开关）
mk('N0', NEW)                                                   # 基线
mk('T1', NEW, env={'STRATA_EXPERT_V2K': '1'})                   # Q4_K 的 V2K 解码内核（bitwise）
mk('T2', NEW, arg_pairs={'--spec-min-p': 0.50})                 # 窗口是否再延长（上游 setup 值）
mk('T3', NEW, arg_pairs={'--pcie-frac': 0.30})                  # 覆盖率降到 30.7% 后 miss 更多
# 回滚/对照用：旧引擎
mk('A49', OLD)

print()
n0 = json.load(open(os.path.join(OUT, 'N0.json')))
for n in ('T1', 'T2', 'T3'):
    b = json.load(open(os.path.join(OUT, n + '.json')))
    da = [(i, x, y) for i, (x, y) in enumerate(zip(n0['args'], b['args'])) if x != y]
    de = {k: (n0['env'].get(k), b['env'].get(k)) for k in set(n0['env']) | set(b['env']) if n0['env'].get(k) != b['env'].get(k)}
    print('N0 vs %-3s args差=%s env差=%s' % (n, da or '无', de or '无'))
