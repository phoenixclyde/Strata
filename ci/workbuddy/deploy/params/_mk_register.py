# -*- coding: utf-8 -*-
"""重写 PARAM_REGISTER.tsv：ADOPTED 行按**现行 config 的真实次序**排列，去掉 BOM。"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, 'PARAM_REGISTER.tsv')

HDR = "id\tscope\tname\tvalue\tfamily\tstatus\trequires\tconflicts_with\tsynergizes_with\tevidence\tverdict"

ADOPTED = [
    ("P00", "CLI", "--pack", "/data/packs/ud-iq4_xs", "load", "-", "-", "-", "现役配置", "基线"),
    ("P01", "CLI", "--native", "/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf", "load", "-", "-", "-", "现役配置", "基线"),
    ("P09", "CLI", "--resident-budget-gib", "76", "ram", "-", "-", "--resident-cpu-experts", "resident RAM mode 33.45 GiB page-locked；9758+14818=24576", "基线"),
    ("P08", "CLI", "--expert-profile", "/src/data/expert-profile.bin", "vram", "-", "--expert-profile-save", "-", "24576 ranked pairs；8.2s 填满 9758/9758", "基线"),
    ("P07", "CLI", "--expert-cache", "auto", "vram", "--expert-profile", "--prefill auto", "--kv-grow", "实取 9758 槽 / 21.98 GiB；策略 PROFILE, no eviction", "基线"),
    ("P05", "CLI", "--spec", "4", "mtp", "--mtp", "-", "--spec-min-p", "现役；日志 verify window up to 6", "基线"),
    ("P06", "CLI", "--spec-min-p", "0.5", "mtp", "--spec", "-", "--spec 4 / --suffix-draft", "setup 写的默认值；**calibrate 可实测**", "待 calibrate 复核"),
    ("P02", "CLI", "--mtp", "/data/mtp/rt", "mtp", "--spec", "-", "-", "现役；draft layer 1098 MiB VRAM", "基线"),
    ("P03", "CLI", "--max-context", "262144", "kv", "-", "--kv-resident", "-", "模型原生上限", "基线"),
    ("P04", "CLI", "--kv", "k8v4", "kv", "-", "-", "--kv-resident / --kv-grow", "816 B/cell vs int8 1056；K 保 int8 精度", "基线"),
    ("P10", "CLI", "--prefill", "auto", "prefill", "--native", "--expert-cache", "STRATA_PREFILL_AUTO_MAX", "实取 chunk 8192 / 96-slot ring", "基线"),
    ("P11", "ENV", "HSA_OVERRIDE_GFX_VERSION", "9.0.6", "env", "-", "-", "-", "gfx906 运行期必需（现由 docker -e 提供；写进 config 使其自包含）", "基线"),
]

CAND = [
    ("P24", "TOOL", "tools/calibrate.py", "(measure)", "tool", "-", "-", "P06 P25 P26 P27", "calibrate.py L1-22：**只调解码**；4 个旋钮；>MIN_GAIN 才保留；用法 python tools/calibrate.py <cfg>.json", "**优先执行**"),
    ("P25", "CLI", "--pcie-frac", "CALIBRATED", "decode", "-", "-", "P06", "当前引擎自动给 0.36（PCIe 13.2 GB/s 实测）", "待 calibrate"),
    ("P26", "CLI", "--pool-workers", "CALIBRATED", "decode", "-", "--no-pool", "P23", "现自动 21（=物理核-1）", "待 calibrate"),
    ("P27", "CLI", "--adapt-every/--adapt-swaps/--adapt-decay", "CALIBRATED", "vram", "--expert-cache", "--expert-profile-save", "-", "DDR3 机器换更多 +7.9%；我们 128G/22 核", "待 calibrate"),
    ("P20", "CLI", "--expert-profile-save", "/data/profiles/ud-iq4_xs-learned.bin", "vram", "-", "--expert-profile", "--adapt-every", "help L261-264：保存自适应层学到的（QUIT + 每 10 min）；行为中性，纯资产积累", "待测"),
    ("P21", "CLI", "--prompt-cache-tail", "(flag)", "session", "--prompt-cache 与 --prompt-cache-every>0", "-", "P33", "help L207；默认 off；我们 prompt-cache=6 / every=16384 满足前置", "待测"),
    ("P22", "CLI", "--prefill", "auto:32768", "prefill", "--native", "--expert-cache", "P23", "#282；generate.cpp L510-512；chunk 加大 = 每 token 流的专家字节更少", "待测"),
    ("P23", "ENV", "STRATA_PREFILL_CPU_SHARE", "auto", "prefill", "-", "--no-pool", "P22 P26", "note：prompt<1024 快 19~35%，2K 以上不变", "待测"),
    ("P28", "ENV", "STRATA_GR_SPLIT", "1", "decode", "STRATA_GR_FAST=1(默认)", "-", "P06", "AMD_HIP.md:461 ~3%/verify window；fused_gr.cu:1722 默认关（破坏位一致）", "待测（需多轮）"),
    ("P29", "ENV", "STRATA_SPEC_GUMBEL", "1", "decode", "采样(temperature>0) + coupled-draft", "-", "P06", "note：AMD +5.7~9%；**贪心时是空操作**", "待测（须采样口径）"),
    ("P31", "CLI", "--conversation-cache-mib", "(默认 0=off)", "session", "-", "-", "P21 P33", "help L188", "待测"),
    ("P32", "CLI", "--kv-grow", "(flag)", "kv", "--expert-profile", "--expert-cache", "P07", "help L131-134；k8v4 下 KV 仅 ~214 MiB ⇒ 收益小", "低优先"),
    ("P33", "REQ", "pin=N", "(请求级)", "session", "-", "-", "P21 P31", "note：长文档连问 48~149s -> 0.35~0.55s", "按用法"),
    ("P30", "ENV", "STRATA_MMVQ_IL", "(默认 on)", "decode", "-", "-", "-", "note 只说 RTX30+ 默认；源码 g_mmvq_il() 默认 true、受 native_mmvq_il_supported() 约束", "本机是否命中未验"),
]

REJ = [
    ("P90", "CLI", "--expert-cache-per-layer", "(不采用)", "vram", "-", "-", "-", "help L288：默认到达顺序仅 2.97%，per-layer 21.4%@8；但**我们已是 PROFILE 且命中 94.6~96.4%**", "不采用"),
    ("P91", "ENV", "STRATA_PLE_IO=ram", "(不采用)", "prefill", "-", "-", "-", "技能 §7.7 实测 -45%", "不采用"),
    ("P92", "CLI", "--no-pool", "(不采用)", "cpu", "-", "P23", "-", "会砍掉 21 个 CPU 专家 worker；本机是 CPU 参与计算形态", "不采用"),
    ("P93", "ENV", "EXP_MODE=2/MMVQ_WAVE=0/ROUTE_PER_TOKEN=1/GR_FAST=0", "(不采用)", "decode", "-", "-", "-", "这些是**恢复 CUDA 布局**的反向开关，在 gfx906 上是退化", "不采用"),
    ("P94", "CLI", "layer-split/peer-device/expert-cache-device1-3/remote-expert-opt", "(不适用)", "multi-gpu", "-", "-", "-", "单卡", "不适用"),
    ("P95", "CLI", "--vram-elastic", "(不适用)", "vram", "-", "-", "-", "help L193 明写 NVIDIA", "不适用"),
    ("P96", "ENV", "STRATA_HIP_WMMA / STRATA_HIPBLASLT_TUNING", "(不适用)", "prefill", "-", "-", "-", "gfx906 无 WMMA / hipBLASLt", "不适用"),
    ("P97", "CLI", "--batch / --slots / --batch-mtp", "(不采用)", "serving", "-", "-", "-", "单用户不需要，每槽吃 VRAM", "不采用"),
]

lines = [HDR]
for grp, tag in ((ADOPTED, 'ADOPTED'), (CAND, 'CANDIDATE'), (REJ, 'REJECTED')):
    for t in grp:
        t = list(t)
        if tag in ('ADOPTED',):
            lines.append('\t'.join([t[0], t[1], t[2], t[3], t[4], 'ADOPTED', t[5], t[6], t[7], t[8], t[9]]))
        elif tag == 'CANDIDATE':
            lines.append('\t'.join([t[0], t[1], t[2], t[3], t[4], ('BLOCKED' if '未验' in t[8] else 'CANDIDATE'), t[5], t[6], t[7], t[8], t[9]]))
        else:
            lines.append('\t'.join([t[0], t[1], t[2], t[3], t[4], 'REJECTED', t[5], t[6], t[7], t[8], t[9]]))

body = '\n'.join(lines) + '\n'
open(REG, 'wb').write(body.encode('utf-8'))          # 无 BOM、LF
b = open(REG, 'rb').read()
print('written %d B  BOM=%s  CR=%d  rows=%d' % (len(b), b.startswith(b'\xef\xbb\xbf'), b.count(b'\r'), len(lines) - 1))
