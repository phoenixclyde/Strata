# -*- coding: utf-8 -*-
"""固化验证：证明 register 里 status=ADOPTED 的每一项**真的**在 166 上生效。

四个数据面（互相独立）：
  (1) 166 的 config JSON（`/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json`）
  (2) 容器 `Config.Cmd` ---- 证明服务读的就是这份 config（**实测判定**：Cmd 里必须出现 LIVE 路径）
  (3) 容器 `Config.Env` ---- ENV 类参数的实况
  (4) 引擎**当前这次**启动块里的 `engine started:` 原始行 ---- 证明引擎真的收到了这些参数
      （锚点 = 日志里最后一次 `engine started`，避开跨启动块的历史行）
  (5) [W727] **CFG 面 + 上游 SETUP_KEYS 覆盖** ---- 判定 config JSON 里的键：
      a. register 里 scope=CFG 且给出了值的行（B00/V00-V02）必须与 LIVE config **逐字一致**；
      b. register 里 scope=CFG 且 value="(不设)" 的行（B01-B07）必须在 LIVE config 里**确实不存在**；
      c. 上游 `setup.py` 的 `SETUP_KEYS` 全集，减去 (LIVE config 实际键 ∪ register 已声明的 CFG 名)
         必须为**空** ---- 否则就是又一个"静默漏掉的必备键"。
      存在理由：`"backend": "hip"` 漏了整整 6 个波次，逃过了本脚本的 PASS=19、逃过了两轮独立审计、
      也逃过了多次 config 对比，**因为它不体现在 args/env 里**（W726）。本面即该类缺陷的判据。
  (6) [W728] **serve 层本地覆写（register 里 scope=PATCH）** ---- 容器内被覆写的文件 md5 是否等于
      持久留档的 `.patched` md5（在位），且 `/metrics` 里该覆写的效果键非 null（生效）。
      理由：覆写写在容器的**可写层**，**容器一重建就静默丢失**，页面只会"又有卡片空了"，
      没有任何判据会响。本面即那个判据（在位 + 生效，两侧 md5 与效果值全部现算）。

[!] 本脚本判「生效」的**面的边界**（W764 审计指出，2026-10-10）：判定面只有
    config JSON / 容器 `Config.Cmd` / 容器 `Config.Env` / serve 打印的 `engine started` 行 /
    SETUP_KEYS / PATCH md5 ---- **不读引擎进程的 `/proc/*/cmdline` 与 `/proc/*/environ`**。
    因此结论强度分档：CLI 类 = 「config 里有 + serve 构造的启动行」；ENV/CFG 类 = 「配置里有」。
    **「引擎运行期确实读到了」须另取 `/proc`** ---- 本轮已在 `deploy/W764_PARAM_LANDING_AUDIT.md`
    用 `/proc/<engine pid>/cmdline` 与 `/proc/<pid>/environ` 兜住（引擎是 serve 的子进程，pid 不等于 1）。

[!] 容器名**不再硬编码**：自动取 166 上正在运行的那个 strata 容器。
    原因（2026-10-08 审计 P1 实证）：本脚本曾写死 `strata166-402`，容器切到 -404 后
    它仍在 inspect 那个已 `Exited` 的旧容器 ---- 四个数据面里的 Env 面因此读的是死容器，
    本次两代容器 env 恰好相同才"侥幸 PASS"。硬编码会让"复验通过"这件事本身失去意义。
    可用环境变量 STRATA_CONTAINER 覆盖（默认自动探测）。

用法：python verify_config.py    # 全 PASS 退 0，任一 FAIL 退 1
"""
import io, os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'PARAM_REGISTER.tsv')
LIVE = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
LOG = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log'
C_PINNED = os.environ.get('STRATA_CONTAINER', '')   # 空 = 自动探测运行中的容器


def rows():
    t = io.open(REG, encoding='utf-8-sig').read().splitlines()
    hdr = t[0].split('\t')
    return [dict(zip(hdr, ln.split('\t'))) for ln in t[1:] if ln.strip()]


def ssh(sc, t=200):
    sys.path.insert(0, HERE)   # 本地自包含（W717 C4：原为 routeK 旧区 D:/workbuddy/_z_rk80）
    import _sshutil
    return _sshutil.run_remote(sc, timeout=t, host='192.168.50.166')


def pick_container():
    """166 上正在运行的 strata 容器；取不到就报错退出（不允许静默回退到某个写死的名字）。"""
    if C_PINNED:
        return C_PINNED
    rc, out, err = ssh("docker ps --filter name=strata --format '{{.Names}}' | head -5", 120)
    names = [x.strip() for x in out.splitlines() if x.strip()]
    if len(names) != 1:
        raise SystemExit('无法唯一确定运行中的 strata 容器（docker ps 得到 %r）；'
                         '请显式设 STRATA_CONTAINER' % (names,))
    return names[0]


def pull(C):
    sc = (
        'echo "###CONFIG###"\ncat %s\necho ""\n'
        'echo "###CMD###"\ndocker inspect %s --format "{{json .Config.Cmd}}"\n'
        'echo "###ENV###"\ndocker inspect %s --format "{{json .Config.Env}}"\n'
        'echo "###BINDS###"\ndocker inspect %s --format "{{json .HostConfig.Binds}}"\n'
        'echo "###STARTED###"\nN=$(grep -n "engine started" %s | tail -1 | cut -d: -f1)\n'
        'sed -n "${N}p" %s\n'
        'echo "###SETUPKEYS###"\n'
        'docker exec %s sh -c \'sed -n "/^SETUP_KEYS = frozenset(/,/})/p" /src/setup.py\'\n'
    ) % (LIVE, C, C, C, LOG, LOG, C)
    rc, out, _ = ssh(sc)
    blk, cur = {}, None
    for ln in out.splitlines():
        m = re.search(r'###(\w+)###', ln)
        if m:
            cur = m.group(1)
            blk[cur] = []
            rest = ln[m.end():]
            if rest.strip():
                blk[cur].append(rest)
        elif cur is not None:
            blk[cur].append(ln)
    cfg = json.loads('\n'.join(blk.get('CONFIG', [])))
    try:
        env_list = json.loads(''.join(blk.get('ENV', [])).strip() or '[]')
    except Exception:
        env_list = []
    env = {}
    for kv in env_list:
        if '=' in kv:
            k, v = kv.split('=', 1)
            env[k] = v
    started = '\n'.join(blk.get('STARTED', [])).strip()
    cmd = '\n'.join(blk.get('CMD', [])).strip()
    try:
        binds = json.loads(''.join(blk.get('BINDS', [])).strip() or '[]')
    except Exception:
        binds = []
    setup_keys = parse_setup_keys('\n'.join(blk.get('SETUPKEYS', [])))
    return cfg, env, started, cmd, binds, setup_keys


def parse_setup_keys(text):
    """从 setup.py 的 `SETUP_KEYS = frozenset({...})` 里取出键名全集（跨行）。

    [!] W727：**从容器实时取**，不写死在本脚本里 ---- 上游加键时本判定自动跟上，
        这正是「必备键清单」要防的那类静默漏项。取不到则返回空集（该面自动降级为 SKIP）。
    """
    if not text or 'SETUP_KEYS' not in text:
        return set()
    body = text.split('SETUP_KEYS', 1)[1]
    return set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', body))


def cfg_lookup(cfg, name):
    """按 register 的写法取值：'vision.exe' -> cfg['vision']['exe']；'backend' -> cfg['backend']。"""
    if '.' in name:
        sect, key = name.split('.', 1)
        d = cfg.get(sect)
        return d.get(key) if isinstance(d, dict) else None
    return cfg.get(name)


def patch_state(C):
    """数据面 (6)：register 里 scope=PATCH 的**本地覆写**是否在位且生效（W728；W734 起**逐文件**判两个）。

    存在理由：serve 层覆写写在容器**可写层**，容器一重建就**静默丢失**（回滚到上游原文，
    而页面只是"又有几张卡空了"---- 没有任何判据会响）。本面就是那个判据，对每个覆写文件判：
      a. 容器内被覆写的文件 md5 == 持久留档的 `.patched` md5（在位）
      b. `/metrics` 里该覆写的效果键非 null（生效）
    两侧 md5 与效果值**全部现算**，不在脚本或 register 里写死指纹。
    返回 (verdict, detail)。"""
    # (留档名, 容器内路径)；W734 起 app.js 也是覆写（sparkline 轴下限 + PCIe 副行带窗口峰值）
    FILES = (('serve-telemetry.py', '/src/serve/telemetry.py'),
             ('serve-web-app.js', '/src/serve/web/app.js'))
    P = '/home/albus/strata166/patches'
    sc = ''
    for i, (nm, cpath) in enumerate(FILES):
        sc += 'echo "have%d=$(docker exec {C} md5sum %s 2>/dev/null | cut -d\' \' -f1)"\n' % (i, cpath)
        sc += 'echo "want%d=$(md5sum %s/%s.patched 2>/dev/null | cut -d\' \' -f1)"\n' % (i, P, nm)
        sc += 'echo "orig%d=$(test -f %s/%s.orig && echo 1 || echo 0)"\n' % (i, P, nm)
    sc += ('echo "metrics_pcie=$(curl -s -m 8 http://127.0.0.1:8090/metrics 2>/dev/null '
           '| tr "," "\\n" | grep -E "\\"gpu_pcie_gen\\"|\\"gpu_pcie_width\\"|\\"gpu_name\\"" | tr -d " " | tr "\\n" " ")"\n')
    sc = sc.format(C=C)
    rc, out, _ = ssh(sc, 150)
    d = {}
    for ln in out.splitlines():
        if '=' in ln:
            k, v = ln.split('=', 1)
            d[k.strip()] = v.strip()
    parts, missing, inplace_all = [], [], True
    for i, (nm, cpath) in enumerate(FILES):
        want = d.get('want%d' % i, '')
        have = d.get('have%d' % i, '')
        if not want:
            missing.append('%s/%s.patched' % (P, nm))
            continue
        ok = (have == want)
        inplace_all = inplace_all and ok
        parts.append('%s %s' % (nm, ('ON ' + want[:8]) if ok else ('OFF have=%s want=%s' % (have[:8] or '空', want[:8]))))
    if missing:
        return None, '取不到持久留档 %s' % ', '.join(missing)
    mp = d.get('metrics_pcie', '')
    # 效果判定：/metrics 里出现了 gpu_pcie_gen / gpu_pcie_width 且不是 null（这两键只由 telemetry 覆写产生）
    #   app.js 覆写是**纯视觉**的（sparkline 轴下限），/metrics 观察不到 => 只判"在位"，不假装有运行时判据。
    eff = ('"gpu_pcie_gen"' in mp or '"gpu_pcie_width"' in mp) and (':null' not in mp)
    if inplace_all and eff:
        return True, '%s；/metrics 效果键 %s' % (' + '.join(parts), mp or '(空)')
    if not inplace_all:
        return False, ('**覆写不在位**（容器重建会丢，或留档过期）：%s => 先比容器内 md5 与 '
                       'deploy/tmp/_tpatch/*.patched.<引擎版>；相等即"留档过期"，把该文件推到 %s/*.patched。'
                       '**禁 apply_telemetry_pcie.sh**：它会把 0.1.42 时代的整份 telemetry.py 覆盖回去，'
                       '回退 0.1.47 的改动（遥测现在烘在镜像 COPY 层里）' % ('; '.join(parts), P))
    return False, '覆写文件在位，但 /metrics 未出现效果键（服务未起或未重启）：metrics=%r' % mp


def cmd_points_at_live(cmd, binds):
    """数据面 (2) 的真判定：容器的 --config 与宿主 LIVE 是不是同一份文件。

    容器里看到的是内部路径（如 /data/strata-huihui-ud-iq4_xs.json），不能拿宿主路径直接比
    ---- 必须用 Binds 把它映射回宿主，再看是不是 LIVE。
    返回 (bool, 依据文本)。"""
    if not cmd.strip().startswith('['):
        return None, 'Cmd 非 JSON 形态：%s' % cmd[:80]
    try:
        cl = json.loads(cmd)
    except Exception:
        return None, 'Cmd 解析失败：%s' % cmd[:80]
    joined = ' '.join(cl)
    m = re.search(r'--config\s+(\S+)', joined)
    if not m:
        return False, 'Cmd 里没有 --config：%s' % joined[:90]
    cpath = m.group(1)
    if cpath == LIVE:
        return True, 'Cmd 直指宿主 LIVE'
    for b in binds:
        parts = b.split(':')
        if len(parts) >= 2 and parts[1] == os.path.dirname(cpath) and parts[0] == os.path.dirname(LIVE):
            return True, 'Cmd 的 %s 经 bind %s 映射到 LIVE' % (cpath, b)
    return False, 'Cmd 的 --config = %s，与 LIVE(%s) 无 bind 映射关系' % (cpath, LIVE)


def main():
    C = pick_container()
    cfg, env, started, cmd, binds, setup_keys = pull(C)
    a = cfg.get('args', [])
    cfg_env = cfg.get('env') or {}   # W718：config 的 env 段 ---- serve 层把它注入给引擎子进程
    ok = bad = 0
    print('目标容器（自动探测运行中的 strata 容器）= %s' % C)
    print('%-5s %-34s %-36s %-6s %s' % ('id', 'name', 'value', '结果', '依据'))
    print('-' * 124)
    # ---- 数据面 (2)：容器 Cmd 的 --config 必须映射到宿主 LIVE（此前只取不用，实为一处空判定）----
    c_ok, c_why = cmd_points_at_live(cmd, binds)
    if c_ok is None:
        print('%-5s %-34s %-36s %-6s %s' % ('--', '(数据面2) 容器 Cmd -> LIVE', '-', 'SKIP', c_why))
    else:
        print('%-5s %-34s %-36s %-6s %s' % ('--', '(数据面2) 容器 Cmd -> LIVE', LIVE.split('/')[-1], 'PASS' if c_ok else 'FAIL', c_why))
        ok, bad = (ok + 1, bad) if c_ok else (ok, bad + 1)
    all_rows = rows()
    declared_cfg = set()   # 数据面 (5c)：register 里 scope=CFG 的名字（含「不设」）---- 已声明过，不算漏
    for r in all_rows:
        if r['scope'] == 'CFG':
            declared_cfg.add(r['name'])
        if r['status'] != 'ADOPTED':
            continue
        nm, val, sc = r['name'], r['value'], r['scope']
        if sc not in ('CLI', 'ENV', 'CFG'):
            extra = '（见数据面 6）' if sc == 'PATCH' else ''
            print('%-5s %-34s %-36s %-6s %s' % (r['id'], nm, val, 'SKIP',
                                                'scope=%s 非 config 项%s' % (sc, extra)))
            continue
        if val == 'CALIBRATED':
            print('%-5s %-34s %-36s %-6s %s' % (r['id'], nm, '(待校准)', 'SKIP', 'calibrate 未跑'))
            continue
        if sc == 'CLI':
            present = nm in a
            nxt = a[a.index(nm) + 1] if (present and a.index(nm) + 1 < len(a)) else None
            got = nxt if (nxt and not nxt.startswith('--')) else '(flag)'
            hit_cfg = present and (val == '(flag)' or got == val)
            hit_eng = (nm in started) and (val == '(flag)' or ('%s %s' % (nm, val)) in started)
            v = 'PASS' if (hit_cfg and hit_eng) else 'FAIL'
            why = 'config JSON + 引擎启动行' if v == 'PASS' else 'config=%s(started=%s)' % (hit_cfg, hit_eng)
            print('%-5s %-34s %-36s %-6s %s' % (r['id'], nm, val, v, why))
            got2 = got
        elif sc == 'CFG':
            # W727：CFG 面此前一律 SKIP（config 的完整性因此无人守）。现在两面都真判：
            #   给了值 -> 必须逐字一致；value="(不设)" -> 必须确实不在 config 里。
            got = cfg_lookup(cfg, nm)
            if val == '(不设)':
                hit = got is None
                v = 'PASS' if hit else 'FAIL'
                why = '声明不设，LIVE config 确无此键' if hit else '声明不设，但 LIVE config 里有：%r' % (got,)
            else:
                hit = (got is not None) and (str(got) == val)
                v = 'PASS' if hit else 'FAIL'
                why = 'config JSON 逐字一致' if hit else 'config=%r 期望=%r' % (got, val)
            print('%-5s %-34s %-36s %-6s %s' % (r['id'], nm, val[:34], v, why))
        else:
            # W718 修复：ENV 面此前**只查容器 Config.Env**，漏了 config JSON 的 env 段
            #   （serve 用 child_env(cfg) 把 config 的 env 注入引擎子进程）。两个面任一命中即 PASS，
            #   并报出命中面（HSA_OVERRIDE_GFX_VERSION 在两个面都有；STRATA_PREFILL_CPU_SHARE 只在 config env 段）。
            hit_c = env.get(nm) == val
            hit_j = cfg_env.get(nm) == val
            hit = hit_c or hit_j
            if hit_c:
                why = 'docker Config.Env'
            elif hit_j:
                why = 'config JSON env 段（serve 注入引擎子进程）'
            else:
                why = '两个面都无（container=%r, config=%r）' % (env.get(nm), cfg_env.get(nm))
            v = 'PASS' if hit else 'FAIL'
            print('%-5s %-34s %-36s %-6s %s' % (r['id'], nm, val, v, why))
        ok, bad = (ok + 1, bad) if v == 'PASS' else (ok, bad + 1)
    # ---- 数据面 (5c)：上游 SETUP_KEYS 覆盖（任何静默漏掉的必备键都在此暴露）----
    if not setup_keys:
        print('%-5s %-34s %-36s %-6s %s' % ('--', '(数据面5) SETUP_KEYS 覆盖', '-', 'SKIP',
                                            '未从容器取到 setup.py 的 SETUP_KEYS'))
    else:
        live_keys = set(cfg.keys())
        missing = sorted(k for k in setup_keys if k not in live_keys and k not in declared_cfg)
        v = 'PASS' if not missing else 'FAIL'
        why = ('上游 SETUP_KEYS %d 个全部有着落（config 实设 %d + register 声明 %d）'
               % (len(setup_keys), len(live_keys & setup_keys), len(declared_cfg & setup_keys))
               ) if not missing else '未被 config 设、也未在 register 声明的上游键：%s' % missing
        print('%-5s %-34s %-36s %-6s %s' % ('--', '(数据面5) SETUP_KEYS 覆盖', '%d 键' % len(setup_keys), v, why))
        ok, bad = (ok + 1, bad) if not missing else (ok, bad + 1)
    # ---- 数据面 (6)：serve 层本地覆写（scope=PATCH）是否在位且生效 ----
    pk = [r for r in all_rows if r['scope'] == 'PATCH']
    if pk:
        p_ok, p_why = patch_state(C)
        pv = 'SKIP' if p_ok is None else ('PASS' if p_ok else 'FAIL')
        print('%-5s %-34s %-36s %-6s %s' % (','.join(r['id'] for r in pk),
                                            '(数据面6) serve 覆写 ' + pk[0]['name'], '(本地覆写)', pv, p_why))
        if p_ok is not None:
            ok, bad = (ok + 1, bad) if p_ok else (ok, bad + 1)
    print('-' * 124)
    print('PASS=%d  FAIL=%d' % (ok, bad))
    print()
    print('锚定的启动行（最后一次 engine started）：')
    print('  ' + (started[:230] if started else '(未取到)'))
    print()
    print('容器 Cmd（实测，来自容器 %s）：' % C)
    print('  ' + (cmd if cmd else '(未取到)')[:220])
    print('  binds: ' + str(binds))
    print('  ' + str(cfg.get('model_name')) + '  <- config: ' + LIVE)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
