# -*- coding: utf-8 -*-
"""临时挂/摘诊断 env（STRATA_DECODE_TIMING / STRATA_VERIFY_PROFILE），走 register -> gen_config -> 推送 -> 重启。
用法：python _diag_env.py on    两小时后必须 off
      python _diag_env.py off
"""
import io, os, sys, subprocess, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
GEN = r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py"
PUSH = r"D:/workbuddy_space/strata_ws/albus/tune/_c1_push.py"
PY = sys.executable

ROWS = [
    ("P85", "ENV", "STRATA_DECODE_TIMING", "1", "decode", "ADOPTED",
     "【W784 E0 诊断】引擎自带的分阶段计时（generate.cpp:14200 dec_timing）：每请求一行 wait/pool/host/plan/actq/jobs/run + misses/entries/hits/pcie。仅打印，不改行为。用完即摘。"),
    ("P86", "ENV", "STRATA_VERIFY_PROFILE", "1", "decode", "ADOPTED",
     "【W784 E0 诊断】窗口级 GPU 阶段计时（generate.cpp:7145 指向同一组开关）。与 P85 同时开才能把 decode 窗口拆成 mix/ffn/post。仅打印。用完即摘。"),
]

mode = sys.argv[1] if len(sys.argv) > 1 else "on"

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
lines = [ln for ln in lines if not ln.startswith(("P85\t", "P86\t"))]
if mode == "on":
    for pid, scope, name, val, stage, status, ev in ROWS:
        lines.append("\t".join([pid, scope, name, val, stage, status, "-", "-", "-", ev, "E0 诊断用，测完摘掉"]))
shutil.copy2(REG, REG + ".bak_diag_" + time.strftime("%Y%m%d_%H%M%S"))
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("register", mode, "rows:", len(lines))

subprocess.run([PY, GEN, "--write"], cwd=os.path.dirname(GEN), check=True)
print("gen_config written")
r = subprocess.run([PY, PUSH], capture_output=True, text=True)
print(r.stdout[-1800:])
print(r.stderr[-400:])
