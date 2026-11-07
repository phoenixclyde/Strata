#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1048 landing: CI coverage ledger + authoritative-plan writeback + queue rows +
# artifact-ledger corrections (pa2/pa5/pa7 provenance refined by the replay proof).
import io
import os

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)


def w(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote", path, len(text))


# ---------------------------------------------------------------- CI_RUNS.tsv
CI = """# CI 覆盖账（唯一账） · W1048 立
#
# 规则：任何产生过二进制/曾装机的变更 sha，必须有一条 Downstream gate run（status=success），
# 或一条 status=exempt 的豁免行并写明补偿证据。deploy_gate D7 装机前机械核对本表。
# 回溯执行记录：W1048 对 10 个历史 ref 打 workflow_dispatch，全部 success（retro_* run）。
# 豁免不豁免事实：UNTRACKED 制品的 md5 全在 artifact_ledger，永远可验尸，只是不能再造。
#
# sha	ref	run_id	status	artifacts/note	来源
fa8e6761842179d56085b06db4b31776aa0e354b	ci/retro/fa8e6761-k10-pin	42384965137	success	strata-0.1.57-b12180;strata-0.1.57-k10p	W1048 retro
79516b21ca5d747045e6c5dc00e0a1bd6c9c0a29	ci/retro/79516b21-pa0	42384971336	success	strata-0.1.57-pa0	W1048 retro
8b44f3d1097b74c731b733dd60c0a15aeb15e494	ci/retro/8b44f3d1-pa1	42384976042	success	strata-0.1.57-pa1	W1048 retro
806a4b2f6288345a4409f9e51bee3309cd334cf5	ci/retro/806a4b2f-tqfix	42384981158	success	(no artifact; W1037 TQ fix)	W1048 retro
3b935ddfcc8d6a8c53c789fd7cfdb9d6df0c4e74	ci/retro/3b935ddf-pa2land	42384985902	success	pa2 content landing (prefill OPT wiring)	W1048 retro
8b5e547fa64fad8a67861731e6aa33f0bff5055d	ci/retro/8b5e547f-pa3	42384990467	success	strata-0.1.57-pa3	W1048 retro
62d10e25cfb094ce4c2092aaae4d5f01cc6168b4	ci/retro/62d10e25-pa5	42384995266	success	strata-0.1.57-pa5	W1048 retro
91a7c5a4e284f71b44316927131248362802d0ef	ci/retro/91a7c5a4-pa6pa7	42385018433	success	strata-0.1.57-pa7 build tree == this content (pa6->wire_f16d->pa7 replay byte-identical)	W1048 retro
064aa6c0451af73be9bc9b899bbdb4d8e3696e7d	ci/retro/064aa6c0-hc-first	42385005419	success	superseded first hc4 attempt (kept in history)	W1048 retro
e36f0889c7baad2bd539014561ab0c86afe0f4c9	ci/retro/pa4-recon	42384609225	success	strata-0.1.57-pa4 exact patch replay (pa4_patch.py on 8b5e547f)	W1048 retro recon
6501c28fecf2fb1613c3e4e2517ac1769092f18b	gfx906/mi50	42280869210	success	strata-0.1.57-001 (tag mi50-0.2.11-r33-14)	pre-existing
af797b900a0b9728a517fa503eed76758eb3543c	gfx906/lcpp-k10	42377965459	success	strata-0.1.57-kvg (W1040 install)	W1047 retro
deb41e126cb3d07c24c5d305b42c551b4922ea92	gfx906/attn-opt	42377970764	success	strata-0.1.57-attn (W1044 install)	W1047 retro
e0ce7c96ae367f19098c3458deea3a10567b60e5	gfx906/dot48	42377975182	success	strata-0.1.57-dot48	W1047 retro
179bd6b59730e6278f2d0cd44f12604aae504aec	gfx906/hc-dp4a	42377792780	success	strata-0.1.57-hc4	W1047 retro
03509d1b6895b4015f03a3aa416c962e5bf56d3d	gfx906/hc-dp4a	4238161670	success	strata-0.1.57-hc4b (W1047 install, live)	W1047 retro
eb5bfbb8e9a420e93659dd862d6ccd21d679211c	ci/w1046-gates	42377983949	success	ci tooling	W1047 retro
b2c82ff05101300881ce3165f1d3a69feb89fef6	ci/w1046-hooks	42377987566	success	ci tooling (worktree-safe hooks)	W1047 retro
9e780f58128a818fe844837be98d7ac759b3ee0d	ci/w1047-coverage	42378063380	success	ci/workbuddy provenance bundle	W1047 retro
6213fcb870275b6be444c7556ce44ced9acd476d	ci/w1047-coverage	42382825186	success	final provenance sync (post-install)	W1047 retro
# ---- exemptions (never silent; md5 preserved in artifact_ledger) ----
strata-0.1.57-pa2	(exempt)	-	exempt	exact W1037 worktree unrecoverable; content landing 3b935ddf covered by 42384985902	W1048
strata-0.1.57-010	(exempt)	-	exempt	0.9.0 tree, source sha unrecorded (P390 counterexample; recipe P433)	W1047/W1048
UNTRACKED-0.1.5x-43	(exempt)	-	exempt	43 builds 0.1.53-0.1.56 era: source sha unknown, md5 preserved, rollback-only	W1048
"""
w("deploy/CI_RUNS.tsv", CI)

# -------------------------------------------------- artifact ledger corrections
P = "albus/w1047/bundle/stage/ci/provenance/artifact_ledger.tsv"
s = io.open(P, encoding="utf-8").read()
lines = s.splitlines()
out = [lines[0] + "\tci_run"]
n = 0
for l in lines[1:]:
    f = l.split("\t")
    name = f[0] if f else ""
    run = ""
    note_i = 6
    if name == "strata-0.1.57-pa5":
        f[3] = "gfx906/port-all @ 62d10e25 (= pa5 commit, commit_pa5.sh)"
        f[6] = "W1039/W1041 candidate: warp-per-group dp4a query quantization; committed as 62d10e25; CI run 42384995266 (W1048 retro); 数值门未开,未装机,见 P451"
        run = "42384995266"
        n += 1
    elif name == "strata-0.1.57-pa7":
        f[3] = "62d10e25 + pa6 + wire_f16d + pa7 (replay == 91a7c5a4, byte-identical)"
        f[6] = "诊断位 16/32(CTLREAD/F16Q),八开关 strings 全 1,未装机(P459)。W1048 replay 证明构建树内容=91a7c5a4;CI run 42385018433"
        run = "42385018433"
        n += 1
    elif name == "strata-0.1.57-pa2":
        f[3] = "W1037 uncommitted worktree (exact tree unrecoverable)"
        f[6] = "OPT 接到预填派发后的候选,未装机;llama 仍是 b11062。W1048:精确树豁免,内容落点 3b935ddf(run 42384985902),见 P441/P534"
        run = "exempt(3b935ddf)"
        n += 1
    elif name == "strata-0.1.57-pa4":
        f[3] = "8b5e547f + pa4_patch.py replay (ci/retro/pa4-recon @ e36f0889)"
        f[6] = "OPT 派发搬进 swizzle 分支;W1039 A/B 窗口内临时装机后已还原。W1048 exact patch replay 重建并 CI(run 42384609225);见 P447/P448"
        run = "42384609225"
        n += 1
    elif name == "strata-0.1.57-attn":
        run = "42377970764"
        n += 1
    elif name == "strata-0.1.57-kvg":
        run = "42377965459"
        n += 1
    elif name == "strata-0.1.57-hc4":
        run = "42377792780"
        n += 1
    elif name == "strata-0.1.57-b12180" or name == "strata-0.1.57-k10p":
        run = "42384965137"
        n += 1
    elif name == "strata-0.1.57-pa0":
        run = "42384971336"
        n += 1
    elif name == "strata-0.1.57-pa1":
        run = "42384976042"
        n += 1
    elif name == "strata-0.1.57-pa3":
        run = "42384990467"
        n += 1
    elif name == "strata-0.1.57-001":
        run = "42280869210"
        n += 1
    elif name == "strata-0.1.57-dot48":
        run = "42377975182"
        n += 1
    out.append("\t".join(f) + "\t" + run)
w(P, "\n".join(out) + "\n")
print("artifact ledger run bindings:", n)
