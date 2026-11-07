# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：gfx906 单卡跑通 + 真实读数"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-08] **166 单卡 gfx906 跑通（官方无先例）** —— 真机读数 + MTP 清单反斜杠坑

### 一、结论：UD-Q4_K_XL（111 GB / 4-bit）在 1×MI50 32GB + AVX2 Xeon 上**完整跑起来**
引擎全载成功，末尾 `strata serve: 570 MiB of VRAM free with everything loaded`，`/v1/models` http=200。
- 模型 id **`qwen3.8-flash-next-ud-q4_k_xl`**，端点 `http://127.0.0.1:8090/v1`（容器内）／`http://172.17.0.6:8090/v1`（同网）
- 专家分两层的**实测**：GPU 缓存 **8495 slots / 24.79 GiB**，RAM 常驻 **16081 个 / 46.94 GiB（页锁定）**
  ⇒ **8495 + 16081 = 24576 = 模型全部专家 ⇒ 稳态零文件读**（`resident RAM mode`）
- `--resident-budget-gib 76` 会**被引擎自己 clamp**：真正只用 46.94 GiB（= 显存装不下的那部分），不是"给多少用多少"
- 首启 **240 s**（含 46.94 GiB 页锁定补全的逐层拷贝 `copied cache complement through layer 48/48`）；温度 50/53/52 ℃
- VRAM 用到 **34.09 / 34.34 GB = 99.25%**

### 二、读数（ctx 8192，`--spec 4 --spec-min-p 0.5`，KV int8）
| 轮次 | prompt tok | 解码 t/s | 预填 t/s | MTP 接受 | 解码专家缓存命中 |
|---|---|---|---|---|---|
| R1 短 | 290 | 27.7 | 80.5（冷） | 81/114 = **71%** | 83.4% |
| R2 长 | 2226 | 33.1 | 317.1（冷） | 89/123 = **72%** | 91.2% |
| R3 同前缀复跑 | 2226 | 40.7 | 2226 中 **2221 复用**，TTFT 0.12s | 88/124 = **71%** | 94.8% |
| R4 512-token | 290 | **42.2（稳态）** | 95.2 | 101/133 = **76%** | 94.3% |
| R5 长 | 4373 | 36.9 | **414.0（冷）** | 41/54 = 76% | 94.1% |

**与 9070XT（IQ2_XS 2-bit）对拍**：
| 机 | 量化 | 解码 | 预填 |
|---|---|---|---|
| 166 MI50 32G + Xeon 22C | **UD-Q4_K_XL（4-bit，更高质）** | **42.2 t/s** | 414 t/s（4.4k 冷） |
| 本机 9070XT 16G + 12700K | IQ2_XS（2-bit） | 34.1~36.5 t/s | 622 t/s |
⇒ **166 用「更高位宽」反而解码更快**（128 GB 内存让 71 GiB 专家全常驻，不挤 PCIe）；
**预填反而慢约 1.5×**，与源码判据吻合（K-quant 的 prompt kernel 是 CUDA-only → AMD 走退化路径）。
- `--suffix-draft` 几乎不命中（2/5、0/3），主要收益全在 MTP

### 三、**[!] 新坑：MTP 张量清单里的 Windows 反斜杠**
- 症状：`mtp_pack.py` 报 `FileNotFoundError: /data/mtp/tensors\\mtp.fc_embedding.weight.bin`
- 根因：`mtp-manifest.json` 的 `"file"` 字段是 `tensors\\mtp....bin`（我本机 `_mtp_dl2.py` 生成时用了 Windows 分隔符），
  Linux 上 `Path('/data/mtp')/ 'tensors\\x'` 就成了**带反斜杠的字面文件名**，文件其实在旁边好好的
- 修法：`json` 读出 → `file.replace('\\\\','/')` → 写回（31/31 条）；备份 `.bak`
- 顺带确认官方口径：MTP draft **固定 `--experts q2_0`**（`setup.py` 里无条件这么调），产物 `experts.bin 707.8MB / dense.bin 116MB / dense.txt 29 行 / draft_vocab.bin`
- **`--mtp` 是 serve 模式硬要求**：缺了引擎会载完模型后只报
  `strata serve: needs --spec T, --mtp DIR and --prefill CHUNK` 然后退出
- 通用教训：**跨平台搬运文件清单，路径分隔符要显式归一**；别信 JSON 里"看着像路径"的字符串

### 四、可调旋钮（`strata --help` 实读，供下一波调优）
- `--kv int8|q4_0|k8v4`：int8 = 1056 B/cell，k8v4 = 816 B/cell（**不可与 `--kv-resident` 同用**）
- `--kv-resident N`：每层 QSA 保 N cell 在显存（**min 20480**），其余流式
- `--max-context N`（默认 4096）；`--prefill CHUNK`（auto = 专家缓存能借出的最大 ≤8192 块）
- `--pool-workers N`（166 实测默认 21 workers = 22 核 − 1）
- `--prompt-cache N`（默认 6 个会话检查点，各约 118 MB RAM）；`--suffix-draft N`（默认 3）
- `--mtp-max-t M`（0 = 跟随 `--spec`）
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old + TXT)
print('appended, size now', os.path.getsize(p), 'B')
