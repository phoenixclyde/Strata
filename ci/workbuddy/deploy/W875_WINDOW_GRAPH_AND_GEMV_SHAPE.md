# W875 · decode 的窗口图有 2162 个节点；「带宽只有 13%」这个归因被自己的探针推翻了一半

**日期** 2026-11-02 00:40–01:10（本轮第 3 次重启：开 `STRATA_VERIFY_NODES=1`）
**引擎** `0.1.55t`（r27），config 加 `STRATA_VERIFY_NODES=1`，其余不变
**一句话** 窗口图 2162–2222 个节点（48 层 × 45–46）；每专家 3 MB 在这张卡上有 **7–11 μs 的实现地板**，
合并 32 个专家只值 **1.25×（M=4）/ 1.7×（M=1）**，**不是 6×**。而「带宽 13%」这个说法依赖
「3 MB 是纯带宽受限」的前提，**我的探针证明它在 M≥4 时是算力/延迟受限**——所以那个百分比不能再当靶心用。

---

## 1 硬数据：一个窗口的图有多大

`STRATA_VERIFY_NODES=1`（capture 时打印，重启后第一次请求触发）：

```
strata verify: the 1-token window graph has 2162 nodes: 2149 x type0; 13 x memcpy;
strata verify: the 2-token window graph has 2174 nodes: 2172 x type0;  2 x memcpy;
strata verify: the 3-token window graph has 2186 nodes: 2183 x type0;  3 x memcpy;
strata verify: the 4-token window graph has 2198 nodes: 2194 x type0;  4 x memcpy;
strata verify: the 6-token window graph has 2222 nodes: 2216 x type0;  6 x memcpy;
```

- **48 层 ⇒ 每层 45.0–46.2 个节点**（`48 layers` 在日志里出现 9 次，确认无疑）；
  > **【W887 限定，2026-11-02 02:4x】** 这 48 层是**全部层**（含 **36 层 GDN 线性注意力** + MoE）；GGUF 实测 `full_attention_interval=4` ⇒ **只有 12 层跑 QSA**。「每层 45–46 节点」作为平均值仍成立，但**不能**读成「attention 每层 45 个节点」。
- 每层 decode 命中 **31.4 个专家**（`VRAM hits 31.42`，98.9% 命中率）⇒ **专家 kernel 占每层节点的多数，但不是全部**（其余是 attention / GDN / dense / reduce）；
- 节点数随 T 只 +12/ token（48 层 × 0.25）⇒ **窗口变长主要不是增加节点，而是每个节点算更多行**。

> 一个限制：`hipKernelNameRefByPtr` 在本机拿不到符号，所有 kernel 都打成 `type0`，
> 所以**看不到每个节点的名字**，也就无法从这张表直接分出「专家 kernel」与「attention kernel」。
> `STRATA_VERIFY_NODES=2` 会列 400 个节点名，但用的还是同一个 name，**同样是 `type0`，别再试**。

## 2 自己写的探针：3 MB 的 GEMV 有多快（含它自己的缺陷）

`ci/probe/gemv_shape_probe.cpp`（fp16，K=4096，每 block 一行，block=256，reps=50–100）：

| 每字节做几次 MAC（M） | 3 MB（1 个专家） | 96 MB（32 个合并） |
|---|---:|---:|
| M=1 | **445.8 GB/s**（7.06 μs） | **763.4 GB/s**（4.12 μs/专家） |
| M=2 | 354.4 | 602.6 |
| M=4 | 279.8 | 349.5 |
| M=8 | 182.0 | 180.6 |

**三个读数：**

1. **同一个 3 MB，M 从 1 涨到 8，时间从 7.06 → 17.29 μs（+145%）**，而 token 数 +700%
   ⇒ 每 token 的成本是下降的（7.06 → 2.16 μs/token），但**每窗口的绝对时间涨得很凶**。
2. **合并 32 个专家进一个 kernel 只值 1.25×（M=4）到 1.7×（M=1）**——不是「6 倍」。
   因为 96 MB 时也才 350 GB/s（M=4）/ 763 GB/s（M=1），离 884 的天花板仍有距离。
3. **生产是 22 μs/专家 = 136 GB/s**，探针 fp16 同尺寸是 11.2 μs（280 GB/s）。
   但**这个对比不公平**：生产 4-bit 每专家 **6 M 个权重**，探针 fp16 只有 **1.5 M**（同样的 3 MB）。
   按「每权重一次 MAC」算，4-bit 的算术量是 fp16 的 4 倍 ⇒ 慢 2× 其实不算差。

**探针的缺陷（必须写下来，防止下次拿它当结论）**：每 block 只读 **8 KB**（一行 4096 个 half），
384 个 block，每线程只迭代 2 次。**8 KB 在 884 GB/s 下是 9 ns，而 block 的启动/排空是 μs 级**
⇒ 这个探针测的是「小 block 的地板」，不是纯带宽。M 越大越慢，一部分是算术，一部分是每 block 只读一次的延迟没被隐藏。
**要拿它定带宽，得改成每 block 处理多行 / split-K；现在的数字只能做「同探针内部横向比较」。**

## 3 这两个数放一起，能说什么、不能说什么

**能说：**

- decode 的一个窗口图上 **2162–2222 个节点**，48 层摊下来每层 45–46 个；
- 3 MB 的 GEMV 在这种实现下 **7–17 μs**，而理论的 3.4 μs 只是「884 GB/s 按字节算」的产物；
- 「把 31 个专家合并成一个大 kernel」的收益上限是 **1.25–1.7×**，不是数量级。

**不能说（撤回 W874 §5 的措辞）：**

- ❌「每 token 1.45 GB ÷ 884 GB/s = 1.64 ms，实测 13.21 ⇒ 效率 12.4%」——
  这个除法假设「只要字节够多就能跑满带宽」，而 §2 的 M=4 只有 280–350 GB/s
  ⇒ **884 不是 GEMV 形状的有效屋顶**，12.4% 这个数没有意义。
- ❌「每专家 GPU 22 μs vs 理论 3.5 μs ⇒ 差 6.3×」——同样的问题，3.5 μs 用的是不适用本例的屋顶。

**修正后的口径**：有效屋顶要按形状取。M≈3–4 的 GEMV，本机实测 **280–350 GB/s（fp16）**，
4-bit 生产的 136 GB/s 与它同量级（元素数 4 倍）⇒ **decode 不是「浪费了 87% 带宽」，而是「GEMV 这个形状本来就跑不满带宽」。**

## 4 那 decode 还剩什么可动

按本轮的数据重排：

| 项 | 数 | 可动性 |
|---|---:|---|
| 每 token 专家流 | 10.1 专家/层 × 3.135 MB（**W891 更正：2.99 是算错的，`21.79 GiB ÷ 7463 = 3.135 MB`**） × 48 = **1.45 GB** | 路由决定，不可动 |
| 每窗口固定开销 | 8.3 ms（W874 拟合） | draft 3.4 + host 2.1 + 图发射 |
| 每专家 GEMV | 22 μs（生产） | kernel 工程，W858/R30–R35 的地盘 |
| 合并专家 kernel | 预期 **1.25–1.7×** | 需改 kernel，风险中高 |
| 窗口长度 T | 3.11（min-p 封死） | 已判否 |

⇒ **唯一还没被证伪的杠杆是「合并专家 kernel」**，上限 1.25–1.7×，而且它要动引擎最热的那条路径。

## 5 下一轮（两件事，一件便宜一件贵）

1. **便宜**：把探针改成正规 GEMV（每 block 多行 + split-K），拿到「形状 → 带宽」的真曲线。
   判据：3 MB/M=4 若真能上 600 GB/s，则「生产 136 只是 4-bit 元素数的代价」成立，合并方向无利可图；
   若仍卡在 300，则合并值得做。**这一步决定要不要动 kernel。**
2. **贵**：`rocprofv3` 在本机可用（`/opt/rocm/bin/rocprofv3`、`rocprof-attach`），
   但 **attach 到生产进程有崩溃风险**（ptrace + 注入 .so，且引擎跑的是 HIP graph）。
   要拿到每 kernel 的真实耗时，建议**另起一个容器**跑同一引擎 + `rocprofv3`（启动约 4 分钟，但生产不受影响）。

---

## 复算命令

```bash
# 图节点数
docker exec strata166-407 grep -a "window graph has" /data/strata-huihui-ud-iq4_xs.log
# 形状探针
cd ~/strata166/ci/probe && docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v $PWD:/p -w /p strata-gfx906:0.2.9-101 ./gemv_shape_probe --mb 3 --m 4 --groups 1,32 --reps 50
```
