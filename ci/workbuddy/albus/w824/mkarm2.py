import json, os, copy

SRC = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
OUT = '/home/albus/strata166/data/w824arm'
os.makedirs(OUT, exist_ok=True)
base = json.load(open(SRC))

def mk(name, exe=None, log=None, env=None, arg_pairs=None):
    d = copy.deepcopy(base)
    if exe:
        d['exe'] = exe
    d['log'] = '/data/w824_%s.log' % name
    # 相位表：本机唯一能判 2-3% 的标尺。所有臂一致（单变量），否则拿不到 ple/attn 分解。
    d['env']['STRATA_PREFILL_TIMING'] = '1'
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
    # 摘要：A/B 之间只应差 exe 与那一两个 env
    print('%-6s exe=%-34s args=%d env=%d log=%s' % (name, d['exe'], len(a), len(d['env']), d['log']))
    return d

prod_exe = '/src/build-906/strata'
mk('A', exe=prod_exe)
mk('A2', exe=prod_exe)
mk('B53', exe='/opt/newbin/strata-0.1.53', env={'STRATA_PLE_AUTO_RAM': '0'})
# 调优臂（先在 0.1.49.2 上备好，等 A/B 结论决定是否跑、跑在哪个引擎上）
mk('T1', exe=prod_exe, env={'STRATA_EXPERT_V2K': '1'})   # Q4_K 的 V2K 解码内核（bitwise），gfx906 默认关
mk('T2', exe=prod_exe, arg_pairs={'--spec-min-p': 0.50})  # 上游 setup 值；决定窗口是否再延长一次
mk('T3', exe=prod_exe, arg_pairs={'--pcie-frac': 0.30})   # 覆盖率降后 miss 更多

print()
print('=== 三臂 A/B 的差异面 ===')
a = json.load(open(os.path.join(OUT, 'A.json')))
for n in ('A2', 'B53'):
    b = json.load(open(os.path.join(OUT, n + '.json')))
    dif = [k for k in set(a) | set(b) if k not in ('args', 'env') and a.get(k) != b.get(k)]
    print(' A vs %-4s 非args差异: %s' % (n, dif))
    print('   args 相同: %s ; env 差: %s' % (a['args'] == b['args'],
          {k: (a['env'].get(k), b['env'].get(k)) for k in set(a['env']) | set(b['env']) if a['env'].get(k) != b['env'].get(k)}))
print()
print('args 里 --pcie-frac / --spec-min-p:', a['args'][a['args'].index('--pcie-frac')+1],
      a['args'][a['args'].index('--spec-min-p')+1])
