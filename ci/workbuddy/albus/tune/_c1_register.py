# -*- coding: utf-8 -*-
"""C1: 把 P26(--pool-workers 21) / P62(--vram-reserve-mib 768) 登记为 ADOPTED。
TSV 原地改写，先备份；断言 11 列、无 tab 污染。"""
import io, os, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
BAK = REG + ".bak_w776c1_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(REG, BAK)
print("backup:", BAK)

txt = io.open(REG, encoding="utf-8-sig").read()
hdr, *lines = txt.splitlines()
assert len(hdr.split("\t")) == 11, hdr
out, done = [], []
for ln in lines:
    if not ln.strip():
        out.append(ln); continue
    f = ln.split("\t")
    assert len(f) == 11, (len(f), ln[:60])
    if f[0] == "P26":
        f[3] = "21"
        f[5] = "ADOPTED"
        f[9] = ("【W776-C1 2026-10-22 改判】0.1.42 臂日志 `21 pool workers on logical processors 1..21, host on 0`；"
                "0.1.47 臂日志 `20 pool workers on logical processors 1..20, the host thread on 0`，且 "
                "`aux cpus: ... go to CPUs 22,21,43 (off at start)` => core 21 在 aux 默认 off 时完全空转。"
                "原 calibrate（21=36.0 / 14=34.8 / 10=34.2 / 5=29.1）证明 21 优于更少核 => 本条不是调参，"
                "是**修 0.1.47 的默认漂移**（21 -> 20）。判据：/metrics.pool_workers==21 且预填中位数回到 0.1.42 臂水平。"
                "help 原文 'Moves threads only, never a result'")
        f[10] = "0.1.47 默认漂移修复：显式写回 21（原判『默认最优』正是 21，默认变了则显式钉住）"
        done.append("P26")
    elif f[0] == "P62":
        f[3] = "768"
        f[5] = "ADOPTED"
        f[9] = ("【W776-C1 2026-10-22 重开】0.1.47 运行期新增警告（本机实测日志 19727 行原文）："
                "`WARNING: only 495 MiB of VRAM free at the start of this request (below 512 MiB): when the card is "
                "this full the driver can page GPU memory to system RAM, decode falls to a few tok/s and a window may "
                "never finish (#2065). Add --vram-reserve-mib 768 to the config's args, or lower --max-context / --batch`。"
                "旧判据（AMD_HIP.md:199『给桌面留显存』）已被版本推翻：此处是给 driver 留白防 paging，属 #2065 新 issue。"
                "代价 68 MiB 约 -30 槽（-0.3%）。判据：vram_free>=700 且连续 5 次长请求无 below 512 警告。")
        f[10] = "重开并采纳 768：新版本运行期警告 + #2065 decode 崩塌风险，证据等级高于旧文档口径"
        done.append("P62")
    out.append("\t".join(f))
assert set(done) == {"P26", "P62"}, done
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join([hdr] + out) + "\n")
print("rewritten; changed:", done)
