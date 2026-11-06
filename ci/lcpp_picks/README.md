# ci/lcpp_picks — 上游 llama.cpp 的单条拣选台账（分支 `gfx906/lcpp-picks`）

存在的理由：R99 试过「整树升到最新」，R100 试过「整树升到 v0.9.0」，两次都因为**把不该要的东西一起要了**而收场
（R99 死于我们手写 kernel 算错，R100 死于上游 MMQ kernel 在 gfx906 上慢 3.8%）。这里换一种做法：
**一条 commit 一个补丁、一个臂、一次 A/B，只把过得去的收进来。**

## 1. 面（先读这个，否则会重做）

我们只编译 llama.cpp 的：

| 目标 | 文件 |
|---|---|
| `strata_mmq`（26 TU） | `ggml/src/ggml-cuda/template-instances/mmq-instance-*.cu`、`ggml/src/ggml-cuda/quantize.cu`、以及被它们 include 的头（`mmq.cuh`、`mmq-load-tiles.cuh`、`mmq-vec-dot.cuh`、`vecdotq.cuh`、`common.cuh`、`mmq-config-*.cuh`、`vendors/*.h`、`ggml{,-common,-cuda,-impl}.h`） |
| `ggml-base`（9 TU） | `ggml/src/{ggml.c,ggml-quants.c,ggml-alloc.c,ggml-backend*.cpp,gguf.cpp,ggml.cpp,ggml-threading.cpp,ggml-opt.cpp}` |
| `ggml-cpu`（16 TU） | `ggml/src/ggml-cpu/**` |

**不编译**：`ggml/src/ggml-cuda/*.cu` 里除 `quantize.cu` 与 mmq 实例以外的一切（fattn、mmvq、cpy、mmf…）、
`llama.cpp` 自身、全部其它后端与工具。证据见 `build-r28/build.ninja` 的 `libstrata_mmq.a` 成员表。

⇒ 补丁里**动 host 文件（`mmq.cu`、`moe_mmq.cu`）的段可以 `--exclude` 掉**：我们有自己的 host 粘合层
（`src/prefill/ggml_cuda_host.cu`、`moe_mmq.cu`），它按 `mmq_args` 的**槽位**喂参数（`J_best` 与旧的 `ncols_opt`
同槽），所以两代 header 都能跑。

## 2. 梯子（为什么是累加，不是单条）

`git apply --check` 实测：16 条里只有 5 条能单条落在 pin 上，且它们全部在本机上可证惰性
（`#29478` 二进制逐字节相同、`#29857`/`#29927` 只对 NVFP4/Q1_0、`#30553` GCN `stream_k=false`、`#24364` 只是 plumbing）。
真正可能改变我们执行路径的 `#29953`（J_best 重构 + MMQ 越界读修复）、`#30168`（src1 精度）、`#29948`（gate/up+GLU 融合）
都**依赖中间提交**，单条冲突。

⇒ 按历史顺序**累加**，每一步都编、都测：冲突消失，而且顺带得到"哪一步开始变慢"的二分。

## 3. 每个臂的协议

1. 建树：`cp -a <pin 树>` → 按梯子顺序 `git apply --exclude=mmq.cu --exclude=moe_mmq.cu`；
2. 编译：`cmake -S /src -B /out -G Ninja && ninja -j12 strata`（ccache 命中约 1–3 min）；
3. 部署：`ci/deploy.sh --src <build> --exe strata-0.1.57-0NN --apply --allow-untagged`，健康后测；
4. 速度门：`ci/cfg_apply.py --record-only --n 6 --lengths 2000,8000`（prefill 2K/8K + decode + ttft），
   判据 **|Δ| ≥ 2×CV（当次 run）**；
5. 数值门：48-token 贪心指纹三例（`/tmp/greedy_fingerprint.py`）。**能改数值的条目必须过**；逐字节相同才算"无变化"；
6. **控制臂**：每几个臂插一次在产 001 的同协议测量——R100 就是靠它识破"时间漂移"的；
7. 收工必须 `ci/rollback.sh --exe strata-0.1.57-001 --apply`，`restarts=0`、config md5 回原值。

## 4. 采纳与拒绝

- `ADOPTED`：补丁进 `patches/`，`apply.sh` 会带上它；登记表加一行 `P###`，并在
  `deploy/W832_OPT_PLAN_V2.md` 对应 R 条目（多半是 R51）里记"从哪一条来、值多少"。
- `REJECTED`：写清死因（速度、数值、或不可复现），补丁留在 `patches/` 但不进 `apply.sh`。
- `INERT`：编得进但可证不执行（给出源码/二进制证据），不进梯子。

## 5. 铁律

1. **禁止整头同步**：H2 实测「0.9.0 的全部 MMQ 头」= **−3.8% prefill**（532.59→512.28，2×CV 判据下是 7×CV）。
   要动就单点，`#29948`/`#30168`/`#29953` 各自一个臂。
2. **融合路径要先证在跑**：`mmq_args` 末尾 `ggml_cuda_mm_fusion_args_device fusion = {}`（`mmq.cuh:1442`），
   粘合层只填到 `J_best` ⇒ `fusion.gate == nullptr` ⇒ 任何"融合带来的收益/损失"必须先证明 `gate` 非空。
3. **解码不要拿来验收 prefill 的改动**（decode CV 1.7–6.7%，且与 prefill 无因果）。
4. 版本文件名不复用；一个臂一个 `strata-0.1.57-0NN`。

## 6. `#29953` 的特别说明（W1031 实测 + 上游原文）

`#29953`（MMQ 越界读修复）是本轮唯一「对我们有真实价值」的候选：它修的是 J 选得比宿主 padding 大 ⇒ kernel 读越过 src1 末尾。
但它的 PR 讨论里明确写着：验证覆盖 RTX PRO 6000 / 2080 Ti / RDNA3.5 / CPU 十种架构，
**"Still untested: MUSA, and AMD CDNA3/RDNA4/GCN hardware, which we only modelled."** —— **GCN 就是我们（gfx906）**。

实测吻合：ladder-5 臂（pin + 该条）在生产上回答退化（只有 reasoning、无答案）并触发客户端断连 ⇒ 判 REJECTED（臂不可信）。

要拿它，顺序必须是：

1. **CPU 规则检查**（不需要 GPU）：把 `mmq-config-gcn.cuh` 的 CASE 表读出来，按上游 `ggml_cuda_mul_mat_q` 的选 J 规则
   （tile 数最少、shared memory 装得下）复算我们每个生产形状（rows/expert、cols=2560 / 640 …）的 J，
   再对照 `src/prefill/moe_mmq.cu` 的 `pad512()` 与 dst 分配，判「kernel 的读/写范围是否被覆盖」；
2. 覆盖不足 ⇒ 先在粘合层补 padding（host 侧，不进 kernel），再用 `mmq_expert_bench` 离线计时 + 数值对齐；
3. 离线两项都过，才允许上生产做一次 A/B。

**禁止**像 ladder-5 那样直接装机 —— 那正是把 166 搞死的那一臂。

## 7. 现有臂的资产（W1031）

| 臂 | 树 | 二进制 | 结论 |
|---|---|---|---|
| pin（在产） | `ref/llama_3cf0325` | `strata-0.1.57-001` / `5e63174d` | 基线 |
| v0.9.0 | `ref/llama_b12110` + `src-v090` | `-004` / `e0edacb7` | prefill −3.8%，DONE_NEG |
| H1（回退 #31247） | `llama_v090_h1` | `-005` / `1f3d7d30` | 未恢复 ⇒ #31247 非元凶 |
| H2（pin 的 ggml-cuda） | `llama_h2` + `src-h2` | `-006` / `8bed7a20` | 回到基线 ⇒ 账在 MMQ 头 |
| #29478 单条 | `llama_pin_vsub4` | `build-vsub4` | 与 001 二进制逐字节相同 ⇒ 零 |
| ladder-5（#29953） | `llama_p5` | `-008` / `28a09fdc` | 回答退化 ⇒ REJECTED |
