# -*- coding: utf-8 -*-
"""从 PARAM_REGISTER.tsv 生成生产配置 ---- **生产 config 永远由本脚本产出，不许手改**。

用法：
    python gen_config.py                 # 打印将要生成的 config
    python gen_config.py --live          # 与 166 上现行 config 做 diff
    python gen_config.py --write         # 落盘到 generated/（自动备份旧的）

只吃 status == ADOPTED 的行。value == "CALIBRATED" 的行会被跳过并在末尾列出（还没测出值）。
value == "(flag)" 视为无值开关。
"""
import io, os, sys, json, difflib, time, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'PARAM_REGISTER.tsv')
GEN = os.path.join(HERE, 'generated')
OUT = os.path.join(GEN, 'strata-huihui-ud-iq4_xs.json')

META = {
    "exe": "/src/build-906/strata",
    "cwd": "/src",
    "tokenizer": "/data/packs/huihui-ud-iq4_xs/tokenizer",
    "model_name": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
    "log": "/data/strata-huihui-ud-iq4_xs.log",
    "host": "0.0.0.0",
    "port": 8090,
}


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
            d = list(difflib.unified_diff(
                json.dumps(lv, indent=1, ensure_ascii=False).splitlines(),
                body.splitlines(), 'LIVE(166)', 'GENERATED', lineterm=''))
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


if __name__ == '__main__':
    main()
