#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT27: repair the live pick-ladder procedure doc + its status filter + local snapshot."""
import io
import os
import subprocess

ROOT = "D:/workbuddy_space/strata_ws"
BRANCH_README = os.path.join(ROOT, "albus/audit27/README_branch.txt")
NEW_README = os.path.join(ROOT, "albus/audit27/README_branch_new.txt")
LOCAL_README = os.path.join(ROOT, "albus/w1031/lcpp_picks_README.md")
LOCAL_TSV = os.path.join(ROOT, "albus/w1031/lcpp_picks_PICKS.tsv")
LOCAL_SH = os.path.join(ROOT, "albus/w1031/lcpp_picks_apply.sh")
BRANCH_TSV = os.path.join(ROOT, "albus/audit27/PICKS_branch.txt")
BRANCH_SH = os.path.join(ROOT, "albus/audit27/apply_branch.sh")
NEW_SH = os.path.join(ROOT, "albus/audit27/apply_new.sh")


def sub(src, old, new, label):
    assert src.count(old) == 1, "%s: expected 1 occurrence, got %d" % (label, src.count(old))
    return src.replace(old, new, 1)


def main():
    r = io.open(BRANCH_README, encoding="utf-8", errors="replace").read()

    r = sub(r,
            "5. 数值门：48-token 贪心指纹三例（`/tmp/greedy_fingerprint.py`）。**能改数值的条目必须过**；逐字节相同才算\"无变化\"；",
            "5. **数值门（AUDIT27 更正 · 原判据已废止）**：不得再用「48-token 贪心指纹逐字节相同」当判据 —— "
            "`P388` 实测同一引擎同一提示连跑两次，`en2k` 234 vs 242、`zh2k` 82 vs 79（MTP/推测解码），"
            "长提示文本本就不可重复；且 `/tmp/greedy_fingerprint.py` 在 166 断电后已不存在。"
            "现行判据 = **prefill-only 的 LOGPOS 探针**（生产配置 + 单条 ~1000 token，只取提示侧 target logp 与 top-64 候选，"
            "不做 short-read 解码窗口；见 `P392`），或 `tools/quant_quality.py` 的 teacher-forced top-1 / KL 相对门"
            "（`KL ≤ 0.0139`、`top-1 ≥ 99%`，需独占 GPU）。**能改数值的条目必须过，未过不得 ADOPTED**；"
            "旧的逐字节指纹只能作为提示侧参考，不能单独判定。",
            "step5")

    r = sub(r,
            "实测吻合：ladder-5 臂（pin + 该条）在生产上回答退化（只有 reasoning、无答案）并触发客户端断连 ⇒ 判 REJECTED（臂不可信）。",
            "**【AUDIT27 撤回 · 以 W1031 续四为准】** 上面这句「ladder-5 回答退化 ⇒ #29953 REJECTED」**已撤回**："
            "`P389` 查明 ladder-5 的崩溃是我搭的**混合树**（pin 的 `common.cuh` + 新 `mmq.cuh`），不是该补丁；"
            "同样的 #29953 放进一致的 0.9.0 树（**K10** = mmq 头 @`4c1004c`，2026-10-19，含 #29953/#30168/#30553）"
            "跑出 prefill **534.83/716.72 = 基线**，2K/8K 各 3 发 + 6 发 decode 全部正常（`P390`）；"
            "再跨一步 **#29948** 的 **K13** 才是 **508.52/684.10（−4.9%/−4.6%，8–19×CV）**（`P391`）。"
            "⇒ `PICKS.tsv` 里 #29953 = **ADOPTABLE**（零代价、稳定），#29948 = **REJECTED**。"
            "**上游硬件未验的告诫仍有效**（GCN 只做了建模），所以下面的 CPU 规则检查与 `P392` 数值门不许跳过。",
            "sec6")

    r = sub(r,
            "**禁止**像 ladder-5 那样直接装机 —— 那正是把 166 搞死的那一臂。",
            "**禁止**搭混合树、也禁止在 ssh 未托管的情况下装机（`P386`/`P387`：装前断言只有一个引擎持卡、"
            "实验脚本与调用者 ssh 解耦、166 **禁止 `systemctl reboot`**，只许关电源冷启动）。",
            "sec6b")

    r = sub(r,
            "| ladder-5（#29953） | `llama_p5` | `-008` / `28a09fdc` | 回答退化 ⇒ REJECTED |",
            "| ladder-5（#29953） | `llama_p5`（**混合树**） | `-008` / `28a09fdc` | **已撤回**：崩溃源于混合树，非补丁（`P389`） |\n"
            "| **K10**（10-19 栈，含 #29953） | 一致 0.9.0 树 + mmq 头 @`4c1004c` | `-010` / `6de7b937` | **534.83/716.72 = 基线，零代价**（`P390`） |\n"
            "| **K13**（K10 + #29948） | mmq 头 @`c49edf0` | `-011` | **508.52/684.10，−4.9%/−4.6%**（`P391`；PR 只覆盖 NVIDIA Turing+） |",
            "assets")

    r = r.rstrip("\n") + "\n\n" + (
        "> **AUDIT27（2026-11-07）**：本件 §3 第 5 步与 §6 的旧结论曾同时承载「已废止判据」与「已撤回结论」，"
        "而 `PICKS.tsv` 已更新 —— 同一种「两份副本、只改一份」的病。今后改 ladder 结论必须同时改 "
        "`PICKS.tsv` / `README.md` / `apply.sh` 状态枚举，并跑 `python tools/audit_scope.py`。\n")
    io.open(NEW_README, "w", encoding="utf-8", newline="\n").write(r)
    io.open(LOCAL_README, "w", encoding="utf-8", newline="\n").write(r)

    # apply.sh: ADOPTABLE must be reachable, unknown statuses must be rejected.
    sh = io.open(BRANCH_SH, encoding="utf-8", errors="replace").read()
    sh = sub(sh, "#   apply.sh <llama.cpp 目录> --all      # 打 TESTING + ADOPTED（复现某个实验臂）",
             "#   apply.sh <llama.cpp 目录> --all      # 打 TESTING + ADOPTABLE + ADOPTED（复现实验臂）",
             "usage")
    sh = sub(sh, "    --all)   case \"$status\" in TESTING|ADOPTED) ;; *) continue;; esac ;;",
             "    --all)   case \"$status\" in TESTING|ADOPTABLE|ADOPTED) ;; *) continue;; esac ;;",
             "filter")
    sh = sub(sh, "  case \"$step\" in step|'#'*|c*) continue;; esac\n",
             "  case \"$step\" in step|'#'*|c*) continue;; esac\n"
             "  # AUDIT27: status drift used to be silent (ADOPTABLE was invisible to both modes)\n"
             "  case \"$status\" in TESTING|ADOPTABLE|ADOPTED|INERT|NEW|REJECTED|NA) ;;\n"
             "    *) echo \"unknown status '$status' at step $step\" >&2; exit 5;; esac\n",
             "enum")
    io.open(NEW_SH, "w", encoding="utf-8", newline="\n").write(sh)
    io.open(LOCAL_SH, "w", encoding="utf-8", newline="\n").write(sh)

    # local PICKS snapshot = branch file, byte for byte
    t = io.open(BRANCH_TSV, encoding="utf-8", errors="replace").read()
    io.open(LOCAL_TSV, "w", encoding="utf-8", newline="\n").write(t)
    print("README/TSV/APPLY written; local snapshot synced (%d bytes)" % len(t))


if __name__ == "__main__":
    main()
