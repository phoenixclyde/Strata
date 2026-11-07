"""W820: 把「上游版本升级评估」与「memlock 偏差」两条落进 PARAM_REGISTER.tsv。

规则：追加两行 P146/P147，不改动已有行；写完立刻回读校验列数与编号唯一性。
"""
import csv

P = "deploy/params/PARAM_REGISTER.tsv"

P146 = [
    "P146",
    "VERSION",
    "engine 0.1.49.2 -> 0.1.52 (tag v0.2.7)",
    "0.1.49.2",
    "version/upgrade",
    "DEFERRED",
    "本机 gfx906 自建（上游不发 gfx906 包）",
    "",
    "",
    "**2026-10-28 评估，暂不升级**。上游最新 = tag v0.2.7.1（app/Control），x86 Qwen 引擎 = **0.1.52**；"
    "main 已到 0.1.53，但 0.2.7.1 的提交全在 ARM/Spark/Mac，x86 无新增。"
    "我们的基线经逐文件 git blob sha1 核对 = **v0.2.4.2 原版**（492 个 src/include/CMake 文件中 489 个逐字节相同），"
    "本地只改 3 个文件：CMakeLists.txt（W793 rocBLAS 接线 + W776 dflash2 的 STRATA_USE_HIP）、"
    "fused_gr.cu（W788 GR_TILEV=1280，已弃用）、qsa_decode_attn.cu（W794 让 query swizzle 支持 kv_mode 3 = k8v4）。"
    "0.2.4.2→0.2.7 引擎面：105 个文件改动 + 51 个新增，其中**只在 13 个代码文件里带 gfx906 分支**"
    "（verify.hpp/moe_fused.hpp、conversation_snapshot/state、expert_cache/expert_source、mtp、verify、"
    "fused_gr、native_mmvq、qsa_prompt_attn、verify_kernels、moe_fused_iq）；抽检 qsa_prompt_attn 的改动是 "
    "sm_80+ INT8 MMA 默认值（gfx906 无该指令，分支未动）。"
    "**0.2.7 的 arch_defaults 仍只有 gfx1151 与 gfx12，gfx906 表为空**，且 `STRATA_FILE_CACHE_OLD_RULE` 让 gfx906 保持旧规则 "
    "⇒ 升级不会静默改我们的默认值。"
    "对 gfx906 真正相关的只有四项：`STRATA_PLE_AUTO_RAM`（0.2.7 默认开，启动时按 RAM 判定把 n-gram 表常驻 + 锁定）、"
    "PLE reader 挂死修复（#3602，配 `STRATA_PLE_CHECK=1`）、会话 KV 串用修复（#1503）、深度上下文 top-k（>90K cells）。"
    "**其余全是 NVIDIA/RDNA/gfx1151 专属**（12GB 卡的 route prior、两卡 layer-major prefill、批量流水、sm_89/sm_80 表、gfx12 四开关、RDNA4）。"
    "而我们 64-83% 的时延在 decode，0.2.7 的 decode 收益没有一项落在 gfx906 上。"
    "**故：迁移到生产不划算（预期端到端 0~4%，且条件是要腾出 96 GB 空闲 RAM），且要重跑 142 行登记的全部基线。**"
    "取代做法：并排构建 0.1.52（打上 W793/W794 两处补丁）当第二份二进制，用同一语料做 3 臂交错 A/B，"
    "只看 `ple`/`attn` 相位与 decode tok/s、槽位、启动、36 题，≥5% 才采纳。",
    "",
]

P147 = [
    "P147",
    "DOCKER",
    "--ulimit memlock=-1",
    "(缺失)",
    "env/lockable-memory",
    "CANDIDATE",
    "无",
    "",
    "P141（--ple-io ram 常驻）",
    "**实测偏差**：运行中的 `strata166-407`（镜像 strata-gfx906:0.2.4p4，创建于 2026-10-25）"
    "`HostConfig.Ulimits=[]`、容器内 `ulimit -l = 8192 KB`，而**我们自己的启动脚本 `_b022_run.sh` / `_b023_run*.sh` "
    "都写了 `--ulimit memlock=-1`**，上游 gfx906 配方也要求 `--ulimit memlock=-1`（AMD_HIP.md）。"
    "后果：26.8 GiB 的 PLE 表**永远无法锁定**，日志里只有 `loaded (not locked)`；这也是 0.2.7 的 "
    "`STRATA_PLE_AUTO_RAM` 在本机不会成立的前置条件之一（admission 过了也会锁不住）。"
    "**零成本**：重建容器时补上该 flag（`--ipc host`/`--device=/dev/kfd`/`--device=/dev/dri`/`--group-add video` 已齐）。"
    "注意：锁定 26.8 GiB 仍要付一次 touch 时间，且与 ComfyUI（宿主 52 GB RSS）争 RAM。",
    "",
]

rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], rows[1:]
ids = {r[0] for r in body}
for row in (P146, P147):
    assert row[0] not in ids, row[0]
    assert len(row) == len(hdr), (row[0], len(row))
    body.append(row)

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)

# 回读校验
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
bad = [r[0] for r in rows if len(r) != 11]
ids = [r[0] for r in rows[1:]]
dup = [i for i in set(ids) if ids.count(i) > 1]
print("rows", len(rows) - 1, "bad_cols", bad, "dups", dup)
print("tail", ids[-3:])
