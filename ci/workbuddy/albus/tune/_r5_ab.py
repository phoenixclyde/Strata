# -*- coding: utf-8 -*-
"""R5-A 的 A/B：同一个镜像，只切 STRATA_GR_TILEV（2560 默认 / 1280 小 tile），取 hc 阶段 ms。

用法：python _r5_ab.py 2560     或      python _r5_ab.py 1280
依赖：生产容器已是 strata-gfx906:0.2.4r5。
"""
import base64, io, shutil, subprocess, sys, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py"
PUSH = r"D:/workbuddy_space/strata_ws/albus/tune/_c1_push.py"
PY = sys.executable
HOST = "albus@192.168.50.166"
PIDS = ("P96", "P97", "P98")   # P96: STRATA_GR_TILEV, P97: STRATA_VERIFY_PROFILE（诊断）

def run(script, timeout=600):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                       input=base64.b64encode(script.encode()),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")

def set_env(rows):
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    lines = [ln for ln in lines if ln.split("\t")[0] not in PIDS]
    for pid, name, val, ev in rows:
        lines.append("\t".join([pid, "ENV", name, val, "decode", "ADOPTED", "-", "-", "-", ev, "R5-A 实验用"]))
    shutil.copy2(REG, REG + ".bak_r5ab_" + time.strftime("%Y%m%d_%H%M%S"))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    subprocess.run([PY, GEN, "--write"], cwd=GEN.rsplit("/", 1)[0], check=True)
    r = subprocess.run([PY, PUSH], capture_output=True, text=True)
    print(r.stdout[-900:])

if __name__ == "__main__":
    tilev = sys.argv[1] if len(sys.argv) > 1 else "2560"
    rows = [("P97", "STRATA_VERIFY_PROFILE", "1", "窗口级阶段计时（诊断，测完摘）"),
            ("P98", "STRATA_DECODE_TIMING", "1", "decode 墙钟与窗口数（诊断，测完摘）")]
    if tilev == "1280":
        rows.insert(0, ("P96", "STRATA_GR_TILEV", "1280", "小 tile：shared 17KB => 3 blocks/SM"))
    else:
        rows.insert(0, ("P96", "STRATA_GR_TILEV", "2560", "大 tile（=0.2.4 默认，显式写便于对照）"))
    print("=== set env, tilev=%s ===" % tilev)
    set_env(rows)
    print("=== bench M (2 runs) ===")
    print(run("cd /home/albus/strata166/tmp && python3 w776_bench.py M 3 2>&1 | tail -4", 1200)[-900:])
    print("=== hc stages ===")
    print(run(r'''grep -a -E "strata decode timing" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -3''')[-1400:])
