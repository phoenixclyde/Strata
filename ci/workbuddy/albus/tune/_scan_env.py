# -*- coding: utf-8 -*-
"""批量扫描 gfx1151 默认表里**未测过**的 env 开关（gfx906 上逐个强制开）。

每项：写 register(P79 扫描槽) -> gen_config -> 推 166 -> restart -> 等 ready ->
      M 档 3 runs -> 记录。任何一项起不来就回滚该 env 并继续。
结果写 _scan_env_results.json。
"""
import io, os, sys, json, time, base64, hashlib, subprocess, re

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
HOST = "albus@192.168.50.166"
REMOTE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
OUT = r"D:/workbuddy_space/strata_ws/albus/tune/_scan_env_results.json"
PY = sys.executable

CANDIDATES = [
    ("STRATA_Q8_PACKED", "1", "packed Q8_0 decode layout (gfx1151 +2.3%)"),
    ("STRATA_Q6_PACKED", "1", "packed Q6_K heads"),
    ("STRATA_MMVF_ROWS", "1", "bf16 multi-row GEMV, 4 rows/block"),
    ("STRATA_LFUSE", "1", "fewer launches around shared expert + KV append"),
    ("STRATA_QFUSE", "1", "activation q8_1 images written by producers"),
    ("STRATA_PLE_BATCH", "1", "verify window's PLE key/value projections at once"),
    ("STRATA_TOPK_REG_MIN_BLOCKS", "4096", "register top-k from 16K cells"),
]


def sh(script, timeout=400):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


def set_slot(name, value, note):
    """P79 扫描槽：有则改，无则加。"""
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    row = None
    for i, ln in enumerate(lines):
        if ln.startswith("P79\t"):
            f = ln.split("\t")
            f[2], f[3], f[5], f[9], f[10] = name, value, "CANDIDATE", note, "W778 扫描中"
            lines[i] = "\t".join(f)
            row = i
    if row is None:
        lines.append("\t".join(["P79", "ENV", name, value, "decode", "CANDIDATE", "-", "-", "-", note, "W778 扫描中"]))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def drop_slot():
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    io.open(REG, "w", encoding="utf-8", newline="\n").write(
        "\n".join(l for l in lines if not l.startswith("P79\t")) + "\n")


def deploy_and_wait():
    p = subprocess.run([PY, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        return False, "gen_config failed"
    md5 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
    b64 = base64.b64encode(open(GEN, "rb").read()).decode("ascii")
    o = sh("echo '%s' | base64 -d > %s.tmp && mv %s.tmp %s && md5sum %s" % (b64, REMOTE, REMOTE, REMOTE, REMOTE))
    if md5 not in o:
        return False, "push md5 mismatch"
    sh("docker restart strata166-407 >/dev/null 2>&1")
    for _ in range(50):
        if '"loaded": true' in sh("curl -s --max-time 4 http://127.0.0.1:8090/health"):
            m = sh("curl -s --max-time 5 http://127.0.0.1:8090/metrics")
            try:
                e = json.loads(m)["engine"]
                return True, "slots=%s vram=%s" % (e["expert_slots"], e["vram_free_mib"])
            except Exception as ex:
                return True, "metrics parse: %r" % (ex,)
        time.sleep(3)
    return False, "NOT READY"


def bench_m(runs=3):
    o = sh("cd /home/albus/strata166/tmp && python3 w776_bench.py M %d 2>&1" % runs, timeout=900)
    m = re.search(r"prompt_tps median=([\d.]+)\s+decode_tps median=([\d.]+)", o)
    if not m:
        return None, o
    return (float(m.group(1)), float(m.group(2))), o


if __name__ == "__main__":
    only = sys.argv[1:] or None
    base_p, base_d = 486.6, 61.3   # 0.2.3 + HC_Q8 基线
    results = []
    if os.path.exists(OUT):
        results = json.load(open(OUT, encoding="utf-8"))

    for name, value, why in CANDIDATES:
        if only and name not in only:
            continue
        print("=" * 70, flush=True)
        print("[%s=%s] %s" % (name, value, why), flush=True)
        set_slot(name, value, "W778 扫描: %s" % why)
        ok, info = deploy_and_wait()
        print("  deploy:", ok, info, flush=True)
        if not ok:
            results.append(dict(name=name, value=value, status="NOT_READY", info=info))
            json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            drop_slot(); deploy_and_wait()
            continue
        r, raw = bench_m(3)
        if r is None:
            print("  bench parse fail:\n", raw[-800:], flush=True)
            results.append(dict(name=name, value=value, status="BENCH_FAIL", info=raw[-400:]))
        else:
            dp = (r[0] - base_p) / base_p * 100
            dd = (r[1] - base_d) / base_d * 100
            print("  prompt %.1f (%+.2f%%)  decode %.1f (%+.2f%%)" % (r[0], dp, r[1], dd), flush=True)
            results.append(dict(name=name, value=value, status="OK", prompt=r[0], decode=r[1], dpct=dp, dpct_d=dd))
        json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 收尾：撤掉扫描槽
    drop_slot()
    ok, info = deploy_and_wait()
    print("cleanup:", ok, info)
