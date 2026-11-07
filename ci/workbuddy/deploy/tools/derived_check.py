# -*- coding: utf-8 -*-
"""derived_check.py - 从生产日志的**最新一行**现算所有派生量。

为什么要有这个：R38 和 R37 两条「新序第 1」都是被**过期派生量**害的——
文档里存的是 GB/s / 倍数 / 占比，而它们的输入（窗口 T、每槽字节、专家数）会随权重与参数漂。
规矩：任何文档要写这类数字，先跑本脚本，把输出贴进去；**不许手算、不许抄上一轮的**。

用法（在 166 上）：python3 ~/strata166/ci/derived_check.py [--container strata166-407]
输出：一段可直接贴进文档的文本。
"""
import argparse
import re
import subprocess
import sys

LOG = "/data/strata-huihui-ud-iq4_xs.log"
ROOF = 884e9          # 大块连续读的实测屋顶（W875/P250），不是 GEMV 形状屋顶
PROBE_READ = 487e9    # W862 的纯读探针，3.13 MB 粒度


def sh(cmd, container):
    return subprocess.run(["docker", "exec", container, "bash", "-lc", cmd],
                          capture_output=True, text=True, timeout=120).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", default="strata166-407")
    a = ap.parse_args()
    c = a.container

    # 1) 每槽字节：从启动横幅拿 槽数 + GiB
    banner = sh("grep -a 'expert cache' %s | grep -a 'slots' | tail -1" % LOG, c)
    m = re.search(r"(\d+) slots, ([\d.]+) GiB", banner)
    if not m:
        print("找不到 expert cache 横幅，无法算每槽字节", file=sys.stderr)
        return 1
    slots, gib = int(m.group(1)), float(m.group(2))
    per = gib * (1024 ** 3) / slots

    # 2) 最新一条 decode timing
    line = sh("grep -a 'strata decode timing' %s | tail -1" % LOG, c)
    if not line:
        print("日志里没有 decode timing 行", file=sys.stderr)
        return 1
    t_avg = float(re.search(r"avg T ([\d.]+)", line).group(1))
    tok_w = float(re.search(r"([\d.]+) tokens/window", line).group(1))
    ms_w = float(re.search(r"([\d.]+) ms/window", line).group(1))
    exp_lw = float(re.search(r"VRAM hits ([\d.]+)", line).group(1))
    layers = 48

    # 3) 可选：GPU stages 的专家读时间（需 STRATA_VERIFY_PROFILE=1）
    st = sh("grep -a 'strata decode GPU stages' %s | tail -1" % LOG, c)
    times = [float(x) for x in re.findall(r"VRAM hits ([\d.]+)", st or "")]

    print("== 派生量（现算，来源：最新一条 decode timing%s） ==" %
          ("/GPU stages" if times else ""))
    print("每槽字节        = %.4f MB   (%d 槽 / %.2f GiB)" % (per / 1e6, slots, gib))
    print("avg T           = %.2f        tokens/window = %.2f" % (t_avg, tok_w))
    print("专家/层-窗口    = %.2f" % exp_lw)
    print("专家/窗口       = %.0f        (= %.2f × %d 层)" % (exp_lw * layers, exp_lw, layers))
    print("字节/窗口       = %.2f GB" % (exp_lw * layers * per / 1e9))
    if len(times) >= 2:
        tot = sum(times)
        b = exp_lw * layers * per
        bw = b / (tot * 1e-3)
        print("专家读时间      = %.2f ms      (GDN %.2f + QSA %.2f)" % (tot, times[0], times[-1]))
        print("**带宽          = %.0f GB/s   = 屋顶 %.0f 的 %.1f%%**, 对纯读探针 %.0f 是 **%.2f×**"
              % (bw / 1e9, ROOF / 1e9, 100 * bw / ROOF, PROBE_READ / 1e9, bw / PROBE_READ))
    else:
        print("专家读时间      = 需要 STRATA_VERIFY_PROFILE=1 的进程（当前日志无 stages 行）")
    print("窗口总时        = %.2f ms/window" % ms_w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
