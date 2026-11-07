# -*- coding: utf-8 -*-
"""从 PARAM_REGISTER.tsv 生成生产配置 ---- **生产 config 永远由本脚本产出，不许手改**。

用法：
    python gen_config.py                 # 打印将要生成的 config
    python gen_config.py --live          # 与 166 上现行 config 做 diff
    python gen_config.py --write         # 落盘到 generated/（自动备份旧的）

只吃 status == ADOPTED 的行。value == "CALIBRATED" 的行会被跳过并在末尾列出（还没测出值）。
value == "(flag)" 视为无值开关。
"""
import io, os, re, sys, json, difflib, time, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'PARAM_REGISTER.tsv')
GEN = os.path.join(HERE, 'generated')
OUT = os.path.join(GEN, 'strata-huihui-ud-iq4_xs.json')

META = {
    "exe": "/src/build-906/strata",
    "cwd": "/src",
    "tokenizer": "/data/packs/ud-q4_k_xl/tokenizer",
    "model_name": "qwen3.8-flash-next-ud-q4_k_xl-abliterated",
    "log": "/data/strata-huihui-ud-iq4_xs.log",
    "host": "0.0.0.0",
    "port": 8090,
}


ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CLI_NAME = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate(rs):
    """W1050 R106: bad rows must FAIL, never silently generate garbage keys.

    The W1040 drift included an ENV name containing '=' plus Chinese commentary and a
    whole-sentence Chinese name -- both would emit broken env keys.  Fail closed."""
    bad = []
    for r in rs:
        if r["status"] != "ADOPTED":
            continue
        sc, name, val = r["scope"], r["name"], r["value"]
        if sc == "ENV":
            if not ENV_NAME.match(name):
                bad.append("%s ENV name invalid: %r" % (r["id"], name))
            if any(c in val for c in ("(", "（", " ", "=")):
                bad.append("%s ENV value has comment/eq/space: %r" % (r["id"], val))
        elif sc == "CLI":
            if not CLI_NAME.match(name):
                bad.append("%s CLI name invalid: %r" % (r["id"], name))
            if val not in ("(flag)",) and any(c in val for c in ("(", "（", " ")):
                bad.append("%s CLI value has comment/eq/space: %r" % (r["id"], val))
    if bad:
        raise SystemExit("REGISTER VALIDATE FAIL\n  " + "\n  ".join(bad))


def rows():
    t = io.open(REG, encoding='utf-8-sig').read().splitlines()
    hdr = t[0].split('\t')
    out = []
    for ln in t[1:]:
        if not ln.strip():
            continue
        f = ln.split('\t')
        if len(f) != len(hdr):
            raise SystemExit('列数不符: %r' % ln[:80])
        out.append(dict(zip(hdr, f)))
    return out


def build():
    validate(rows())
    args, env, sect_cfg, top_cfg, pending, adopted = [], {}, {}, {}, [], []
    for r in rows():
        if r['status'] != 'ADOPTED':
            continue
        adopted.append(r['id'])
        if r['value'] == 'CALIBRATED':
            pending.append(r)
            continue
        if r['scope'] == 'CLI':
            if r['value'] == '(flag)':
                args.append(r['name'])
            else:
                args += [r['name'], r['value']]
        elif r['scope'] == 'ENV':
            env[r['name']] = r['value']
        elif r['scope'] == 'CFG':
            # 形如 "vision.exe" -> cfg["vision"]["exe"]（W715：vision 段）
            # W726：name 无 '.' 时写顶层字段（如 backend -> cfg["backend"]）
            # W727：占位值（"(不设)" 等）一律不写 ---- 它们是「声明不设」的账目行，不是配置项
            if r['value'].startswith('('):
                continue
            if '.' in r['name']:
                sect, key = r['name'].split('.', 1)
                sect_cfg.setdefault(sect, {})[key] = r['value']
            else:
                top_cfg[r['name']] = r['value']
    cfg = {'exe': META['exe'], 'args': args}
    for k in ('cwd', 'tokenizer', 'model_name', 'log', 'host', 'port'):
        cfg[k] = META[k]
    for k, v in top_cfg.items():      # W726：CFG 顶层字段（backend 等）；置于 env 前，保持既有键序
        cfg[k] = v
    if env:
        cfg['env'] = env
    for sect, kv in sect_cfg.items():
        cfg[sect] = kv
    return cfg, pending, adopted


def live_cfg():
    sys.path.insert(0, HERE)   # 本地自包含（W717 C4：原为 routeK 旧区 D:/workbuddy/_z_rk80）
    import _sshutil
    rc, out, err = _sshutil.run_remote(
        'cat /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json', timeout=120, host='192.168.50.166')
    return json.loads(out) if out.strip().startswith('{') else None


def main():
    a = sys.argv[1:]
    if '--self-test' in a:
        raise SystemExit(self_test())
    cfg, pending, adopted = build()
    body = json.dumps(cfg, indent=1, ensure_ascii=False)
    print('=== ADOPTED 行 %d 个（其中待校准 %d 个已跳过）===' % (len(adopted), len(pending)))
    print(body)
    if pending:
        print()
        print('=== 尚未有值（需先跑 calibrate）===')
        for r in pending:
            print('   %-5s %-20s %s' % (r['id'], r['name'], r['note'] if 'note' in r else r['verdict']))

    if '--live' in a:
        lv = live_cfg()
        if lv is None:
            print('\n[--live] 取现行 config 失败')
        else:
            # W1050 R106: compare canonically -- key order is cosmetic and the exe
            # pointer is a deploy-time swap owned by deploy_gate D5, not gen_config.
            def canon(cfg):
                c = {k: v for k, v in cfg.items() if k != 'exe'}
                if isinstance(c.get('args'), list):
                    # W1050 R106: argv order is inert for these single-occurrence flags;
                    # compare as a multiset so only real drift (missing/extra/dup) shows.
                    c['args'] = sorted(c['args'])
                return json.dumps(c, indent=1, ensure_ascii=False, sort_keys=True).splitlines()
            d = list(difflib.unified_diff(
                canon(lv), canon(json.loads(body)), 'LIVE(166)', 'GENERATED', lineterm=''))
            print()
            print('=== 与 166 现行 config 的差异 ===')
            print('\n'.join(d) if d else '   (无差异)')

    if '--write' in a:
        os.makedirs(GEN, exist_ok=True)
        if os.path.isfile(OUT):
            shutil.copy2(OUT, OUT + '.bak_' + time.strftime('%Y%m%d_%H%M%S'))
        io.open(OUT, 'w', encoding='utf-8', newline='\n').write(body + '\n')
        print()
        print('已写入 %s (%d B)' % (OUT, os.path.getsize(OUT)))


def self_test():
    ok = 0
    cases = [
        ("ENV name with = and Chinese", dict(id="T1", scope="ENV", name="STRATA_X=1（注释）",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV whole-sentence name", dict(id="T2", scope="ENV", name="ROCm userland 10.1.0 + rocBLAS",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV value with comment", dict(id="T3", scope="ENV", name="STRATA_OK",
         value="1(在 k8v4 下不可达)", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("ENV good row", dict(id="T4", scope="ENV", name="STRATA_OK2",
         value="1", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), True),
        ("non-ADOPTED bad name ignored", dict(id="T5", scope="ENV", name="bad=name（x）",
         value="1", family="", status="REJECTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), True),
        ("CLI descriptive name (W1040 P259 shape)", dict(id="T6", scope="CLI", name="--prefill auto:N（chunk 上限）",
         value="auto:16384（采纳）", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("CLI value with default comment (P138 shape)", dict(id="T7", scope="CLI", name="--ple-io",
         value="direct(缺省)", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), False),
        ("CLI good flag", dict(id="T8", scope="CLI", name="--kv-grow",
         value="(flag)", family="", status="ADOPTED", requires="", conflicts_with="", synergizes_with="", evidence="", verdict=""), True),
    ]
    for label, row, want_ok in cases:
        try:
            validate([row])
            got = True
        except SystemExit:
            got = False
        good = got == want_ok
        ok += good
        print("  %-32s %s (verdict=%s)" % (label, "PASS" if good else "FAIL", got))
    print("GEN_CONFIG_SELF_TEST: %d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


if __name__ == '__main__':
    main()
