#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1049 landing: register rows + plan writeback + ab evidence + cfg_new.
import io
import json
import os

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------ 1. PARAM_REGISTER rows
P = "deploy/params/PARAM_REGISTER.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["P536", "ENV", "STRATA_GFX906_ATTN_LDS_PAD", "1", "attention", "ADOPTED",
     "strata-0.1.57-hc4b (W1049 A2)",
     "", "P512",
     "【W1049 实测】A2 列式 LDS +1 pad（OPT bit4，SQ_PAD=4/SP_PAD=1）。G1 双重 bitwise：pad 单独 f≡c（KL 0.00000），组合 e≡m（DP4A+PAD vs DP4A，KL 0.00000）⇒ 纯布局不改算术。n=3 干净计时（破缓存）：8K qsa attn 组合 1103.7 vs 现产 1119.0 ms（−1.37%，2×CV 0.18%），对地板 1261.7（−12.5%）；2.5K 226 vs 230（−1.7%）；decode 49.2 vs 50.3 tok/s 持平。外证 skyne98/CK：gfx906 列式 LDS 读 ld=32→33 从 1865→3974 GB/s。",
     "采纳（W1049）。**边界**：加在现有 DP4A=1 之上（OPT=6）；一次只动这一位。"],
    ["P537", "SWITCH", "STRATA_GFX906_ROUTE_DPP", "off", "attention", "REJECTED",
     "strata-0.1.57-r103x (W1049 A1)",
     "", "P536",
     "【W1049 实测】A1 router 三处归约换 DPP xor 树（native_router 144 行，gfx906/r103x@4a78f50ce）。G1 bitwise（f≡g KL 0.00000，同操作数对同序）。性能不可检出：router+shared 相位 271 vs 271 ms（n=3），decode 47 vs 49 tok/s，全部在噪声内；历史预估 −0.3~0.6ms 低于相位分辨率。",
     "否（W1049）。证据保留：r103x + 开关在册，可复测。"],
    ["P538", "SWITCH", "STRATA_GFX906_Q8_GATHER8", "off", "attention", "REJECTED",
     "strata-0.1.57-r103x (W1049 A5)",
     "", "P536",
     "【W1049 实测】A5 Q8_1 8-wide gather 出 SM60 实验宏进 HIP_GFX906（kv_q8.cu）。G1 bitwise（f≡h KL 0.00000，自述同 scale 同舍入证实）。性能不可检出：gather 相位 24-25 ms 持平、decode 50 vs 49 tok/s。gather 在预填占比 0.3%。",
     "否（W1049）。证据保留。"],
    ["P539", "SWITCH", "STRATA_GFX906_ATTN_DPP", "off", "attention", "REJECTED",
     "strata-0.1.57-hc4b (W1049 A3)",
     "", "P536",
     "【W1049 实测】A3 softmax warp_sum/max 换 DPP（OPT bit1）。8K qsa attn 1255 vs 地板 1261.7（−0.56%，2×CV≈0.2% 显著但微小）；整条 GPU 8870 vs 8830（+0.45%）不显著，2.5K 全条不显著，decode 48 vs 50。P447 历史 −0.76% 同向。",
     "否（W1049）：局部小赢、全条不显著，不值得占一个 env。"],
    ["P540", "FLAG", "amdgpu-sched-strategy=max-ilp (per-TU)", "off", "attention", "REJECTED",
     "strata-0.1.57-r103ilp (W1049 A4)",
     "", "P536",
     "【W1049 实测】A4 逐 TU max-ilp（qsa_decode_attn/qsa_pattn/fused_gr，build.ninja 三边 FLAGS，ninja 按命令行哈希强制重编）。数值 bitwise（a≡k KL 0.00000，调度不改算术）但性能**显著有害**：8K qsa attn 1762 vs 1261.7（**+39.6%**）、2.5K 353 vs 261（+35%）、整条 GPU +6.2%。与社区「全局 flag prefill +10~20%」相反——收益大概率在 GEMM TU，不在 attn/fused_gr。",
     "否（W1049）。**警示**：全局抄作业会伤 attn；若重试只试 gemm TU。"],
    ["P541", "JUDGE", "P457 归约混淆", "resolved", "attention", "DONE",
     "strata-0.1.57-hc4b/r103x (W1049)",
     "", "P457",
     "【W1049 判】三段剥离：① REDUCE12 单独 a≡d KL 0.00000 ⇒ **归约无辜**（P457 判据的 KL=0 支）；② CTLREAD（手工 K 读+晚 scale、基线算术）f vs i KL mean 0.0948 / max 0.367 / top-1 75% ⇒ **「手工读无辜」假设推翻**，OPT 路径的 K 读/scale 应用是真实数值差异源；③ F16Q（fp16 查询往返）f vs j KL 0.0340 / top-1 100% ⇒ 查询精度次之。生产 DP4A=1 的历史 KL 归因：主体=int8 查询量化（P454 机理），不来自 REDUCE12。",
     "结案（W1049）。P457 关。"],
    ["P542", "JUDGE", "B2 落点闭案", "resolved", "attention", "DONE",
     "prod tree (W1049)",
     "", "P435",
     "【W1049 源码钉死】预填派发 ①qsa_prompt_attn_batch_gated 编译排除（!STRATA_HIP_GFX906）②qsa_prompt_attn_batch 首行 return false（STRATA_HIP_GFX906）③qsa_pattn STRATA_PATTN_BUILT=0 ④qsa_decode_attn_batch 循环=真实热路径。⇒ B2「prefill 分数 dp4a」与 B1 同模板（OPT&2，qsa_decode_attn.cu:234/306），W1044 已装。P435「预填吃 prompt_attn」对 gfx906 不成立（对 NVIDIA 成立）。收益兑现：P499 attn −10.9~−11.3%、W1049 复证 1119 vs 1261.7（−11.3%）。",
     "结案（W1049）：B2=DONE via B1，非丢失项。"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[0] == r[0] for l in lines if l.count("\t") >= 9), r[0]
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("register rows added")

# ------------------------------------------------ 2. ab evidence for D3
def st(v):
    import statistics
    m = statistics.mean(v)
    cv = statistics.pstdev(v) / m * 100 if len(v) > 1 and m else 0.0
    return {"n": len(v), "mean": m, "cv_pct": cv}


ab = {
    "target": "qsa_attn_8k",
    "target_kind": "latency",
    "baseline": st([1119, 1119, 1119]),
    "candidate": st([1105, 1103, 1103]),
    "guard": [
        {"name": "qsa_attn_2k5", "n": 3, "mean_base": 230.0, "mean_cand": 226.0, "cv_pct": 0.0},
        {"name": "gpu_timeline_8k", "n": 3, "mean_base": 8704.3, "mean_cand": 8676.3, "cv_pct": 0.41},
        {"name": "decode_tps", "n": 1, "mean_base": 50.3, "mean_cand": 49.2, "cv_pct": 0.0},
    ],
    "numeric": {
        "mode": "anchor",
        "build_floor_bitident": True,
        "anchor": [{"length": "1K", "kl_cand": 0.0, "kl_anchor": 0.00037},
                   {"length": "8K", "kl_cand": 0.0, "kl_anchor": 0.00345},
                   {"length": "16K", "kl_cand": 0.0, "kl_anchor": 0.01429},
                   {"length": "20K", "kl_cand": 0.0, "kl_anchor": 0.18750}],
        "task_gate": "3/3",
        "task_gate_status": "PASS",
        "evidence": "W1049 pcompare e vs m: 4 prompts top-1 100% KL 0.00000 (bitident on top of DP4A); f vs c bitident",
    },
    "source": "albus/w1049/phase_b_full.txt + pcompare_summary.txt; combo arm r103c",
    "caveats": ["PAD is layout-only (G1 twice bitident)", "one combo gpu outlier excluded from qsa stats (qsa itself cv<0.1%)"],
}
io.open("albus/w1049/ab_ladspad.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(ab, ensure_ascii=False, indent=2))
print("ab written")

# ------------------------------------------------ 3. cfg_new
base = json.load(io.open("albus/w1047/cfg_base.json", encoding="utf-8-sig"))
cur = json.load(io.open("albus/w1047/cfg_new.json", encoding="utf-8-sig"))  # hc4b + 2 env
assert cur["exe"] == "/data/bin/strata-0.1.57-hc4b"
new = json.loads(json.dumps(cur))
new["env"]["STRATA_GFX906_ATTN_LDS_PAD"] = "1"
io.open("albus/w1049/cfg_new.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(new, ensure_ascii=False, indent=2))
print("cfg_new env", len(new["env"]), new["exe"])
