# -*- coding: utf-8 -*-
"""追加 [W-Strata-29]：A+B 十臂扫描结果 + 结构性发现 + IQ2_XS 预测。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-29] A+B 十臂扫描：**官方 MI50 配方与全部预填旋钮均无可用增益**

**方法**：改用**一次性 `generate` 模式**做扫描（每臂 ~72 s，且直出 PLE/host 分解），同一 16383-token 文件、同一配置基线。
脚本 `D:\\strata166\\scripts\\_ab_ab166.py`、解析 `_parse_ab_ab.py`，日志 `_ab_ab.txt`。

| Arm | tok/s | 相对 base | PLE ms | slots | resident GiB |
|---|---|---|---|---|---|
| A1 base | 458.1 | — | 1931.1 | 10797 | 31.09 |
| A2 `--kv-resident 32768` | 447.3 | −2.4% | **31.8** | 11304 | 29.93 |
| A3 A2 + `--vram-reserve-mib 600` | 466.3 | +1.8% | 1361.6 | **11348** | 29.83 |
| A4 A3 + `STRATA_ARENA_MMAP=1` + `--pcie-frac 0` | 468.3 | +2.2% | 1906.2 | 11348 | 29.83 |
| **B1 `--no-prefill-borrow`** | **346.7** | **−24.3%** | 293.8 | 10144 | 32.57 |
| B2 `--no-split-rows` | 468.5 | +2.3% | 1942.1 | 10797 | 31.09 |
| B3 `--shared-late` | 462.1 | +0.9% | 2416.4 | 10797 | 31.09 |
| B4 `--pool-workers 22` | 467.4 | +2.0% | 1952.0 | 10797 | 31.09 |
| B5 `STRATA_PREFILL_RING=256` | 468.3 | +2.2% | 2136.5 | 10797 | 31.09 |
| B6 `--no-pool` | 跑不起来 | — | — | 10797 | 31.09 |

**结论**：
1. **A 组（官方 MI50 显存腾挪配方）对预填 ≤+2%，全部落在 462~468.5 的噪声带内**。它的真实作用是**槽数 10797 → 11348（+551/+5%）**，只对解码可能有小幅帮助。官方那套本是为 **32 GB RAM** 的小内存机腾 RAM（作者原话"23.4 GiB 交还 OS"），我们 128 GB 用不上。
2. **B1 `--no-prefill-borrow` −24.3%** ⇒ **「预填借缓存槽」是预填的关键机制**，且早已默认开启 —— 这是本次唯一"有量级"的读数，方向是**证实既有默认值必须保留**，不是新增益。
3. B2/B3/B4/B5 全在噪声带内 ⇒ 无效。B5 的注释本就写明 `STRATA_PREFILL_RING` 是"**the pre-fix rule and the A/B arm**"（复现旧行为的臂）。
4. **`--no-pool` 在本机根本无法运行**：预填要借缓存槽，而专家缓存吃满显存 ⇒ `device buffers for a chunk of 1024 tokens do not fit (84 of 32752 MiB free … wanted 318 MiB)`。⇒ **GPU-only 地板不可测**，也说明**显存已被专家缓存饱和**。
5. **PLE 的 `PLE ms` 在 31.8~2416 ms 之间乱跳而总时间稳定在 35.0~36.6 s** ⇒ 进一步证明 **PLE 暴露时间在噪声里、不在关键路径**（第 3 次印证）。

## [W-Strata-30] 结构性发现：专家确实全在内存，但 VRAM 只装得下 44% ⇒ 解码被 CPU 池拖住

`FileExpertSource: RAM budget 76.00 GiB: 13779 of the 31.09 GiB of experts the GPU cache does not hold, by profile rank`
⇒ **非 GPU 的 13779 个专家全部常驻 RAM（31.09 GiB，页锁定），无专家读盘**；**10797 + 13779 = 24576 = 全部专家**。
⇒ 所以解码里 **27 ms/token 的 CPU 专家池**，算的就是这 13779 个不驻 VRAM 的专家。**这是解码最大的单项成本**（官方 MI50 报告"全在 VRAM、CPU 池算 0 个"时 decode 45.7~50.1，我们 42.9）。

**量化预测（换小槽权重的收益）**：

| 权重 | 单槽 | 24.34 GiB 装得下 | 留给 CPU 池 | 依据 |
|---|---|---|---|---|
| UD-IQ4_XS（现） | 2.366 MB | 10797 | 13779 | 实测 |
| **GSQ-RCO IQ2_XS** | **1.318 MiB** | **≈18900** | **≈5676（−59%）** | 9070XT 上 `strata-device.exe` 实测槽大小 |
| Coder IQ1_M | ~2.45 MB，但**专家只 12288** | 全部 | **0** | 官方 MI50 报告实测 |

⇒ **IQ2_XS 有望把解码的 CPU 池工作量压掉约 59%**；IQ2_XS 本机已有（`D:\\idm\\Strata-GGUF`，68.03 GB），**只需 13 分钟内网传输 + pack**，无需下载。

**配置面清账**：至此已测 19 个旋钮/组合（含 MMQ、KQ256、PLE 全套、pcie-frac、adapt-every、chunk 三种、kv-resident、vram-reserve、arena-mmap、no-borrow、no-split-rows、shared-late、pool-workers、prefill-ring、no-pool），**唯一有效的是既有的默认值**。剩余唯一有量级空间的方向是**换更小槽的权重**。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
