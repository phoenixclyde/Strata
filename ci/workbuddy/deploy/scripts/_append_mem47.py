# -*- coding: utf-8 -*-
"""追加 [W-Strata-27]：UD-IQ4_XS 在 166 跑通，与 UD-Q4_K_XL 的同尺对比。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-27] UD-IQ4_XS 在 166 跑通；与 UD-Q4_K_XL 同尺对比：**预填无变化、解码 +30%**

**部署**（脚本 `_deploy2_iq4xs166.py`，日志 `_deploy2_pack.txt` / `_deploy2_run.txt`）：
镜像 `strata-gfx906:0.1.40.1`、容器 `strata166-401`、端口 8090、cfg `/data/strata-ud-iq4_xs.json`（除 pack/native/model_name 外与 UD-Q4 **逐字相同**）、ctx 131072、KV int8。
- **传输**：93.68 GB / 16.4 min / **90.7 MB/s**（3 片并行裸流），传后 size 全对。
- **pack**：`iq_pack --compat-bf16` → 1079 张量 / 303 原生 / arena 1.38 GiB、460 项转换（max |err| 0.0144）、**专家与 PLE 表字节未动**；`compat-bf16: 195 tensors, 1.20 GiB`。
- 加载：专家缓存 **10289 slots / 23.19 GiB**（8.1 s 预填，3090 MB/s）；`resident RAM mode: 32.24 GiB（page-locked）`；MTP draft head 212.9 MiB；**一切载完后 VRAM 余 576 MiB**。

**对比（同一脚本 `/data/bench_ver.py`、同一会话时段、ctx 131072、预热 1 次 + 3 次预填 + 3 次解码）**：

| 指标 | UD-Q4_K_XL（K-quant） | **UD-IQ4_XS（i-quant）** | 差 |
|---|---|---|---|
| prefill 中位 | **444.9** | **438.8** | −1.4%（噪声内） |
| prefill 三次 | 439.1 / 444.9 / 445.5 | 438.8 / 458.1 / 381.7 | spread 17.4% |
| **decode 中位** | **33.1** | **42.9** | **+29.6%** |
| decode 三次 | 31.85 / 33.81 / 33.07 | 39.22 / 42.85 / **47.93** | spread 20.3% |
| GPU 专家槽 | 7875 / 22.99 GiB | **10289 / 23.19 GiB** | +2414 槽 |
| RAM 常驻专家 | 48.74 GiB | **32.24 GiB** | **−16.5 GiB** |
| 解码缓存命中率 | 81.5~93.5% | **94.9~97.3%** | 明显更高 |
| 走 PCIe 的专家 | 1.5~2.2% | **0.4~1.0%** | 明显更低 |
| MTP 接受（512 token） | 62~69% | 61~66% | 相当 |
| 预填 ms/token | ~2.25 | ~2.28 | 相同 |

**三条结论**：
1. **预填：无差异（−1.4%）⇒ 我先前"换 i-quant 能拿 1.3~1.7× 预填"的预测落空，如实更正。** 这与"预填被每 token 的常数项主导（PLE 取行等），不由专家取数决定"是自洽的。
2. **解码 +30%，机制清楚**：IQ4_XS 专家槽更小 ⇒ GPU 能装 **10289** 槽（Q4 只有 7875）⇒ 解码命中率 81.5~93.5% → **94.9~97.3%**、PCIe 专家 1.5~2.2% → **0.4~1.0%**。**不是 MTP 的功劳**（接受率相当 62~69%）。
3. **RAM 省 16.5 GiB**（48.74 → 32.24），系统余量更宽裕。

**[!] 必须标注的 confound（尚未查清，不下结论）**：
IQ4_XS 本次会话从 GGUF 读入 **~70 GB**（`files 4782 blobs 70271.4 MB read (the GGUF in place)`），而 UD-Q4 当日记的是 **`files 0 blobs`**。两者"是否零读盘"不同源。
- 但它**不能解释**解码更快（它读了更多盘还更快），所以 +30% 的方向可信；
- 真正原因待查：可能是 `--resident-budget-gib 76` 对 IQ4_XS 的专家总量**没有覆盖完**（UD-Q4 是 GPU 7875 + RAM 48.74 GiB 恰好等于全部 24576 专家；IQ4_XS 是 10289 + 32.24 GiB，是否也等于全部需按槽尺寸核）。
⇒ **下一步可达的增益**：调 `--resident-budget-gib` / `--expert-cache` 把 IQ4_XS 也做到零读盘（如果它确实没覆盖完）。

**部署脚本踩的两个坑（已固化）**：
1. `docker start` 返回 0 **不等于** `docker exec` 可用 —— 必须 poll `docker inspect -f '{{.State.Running}}'` 并在容器内试跑 `python3 -c print(1)`；否则前两条 exec 撞在启动窗口里静默失败（配置没写成 → serve 因缺配置 traceback）。
2. **`curl -w '%{http_code}'` 绝不能经过 `%` 字符串格式化**（`%%s` 会变成 `%s`，curl 原样打印），一律用字符串拼接构造远程命令。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
