# -*- coding: utf-8 -*-
import hashlib
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
TXT = """

## W708d ---- 加装「参数固化机制」+ 组合/冲突矩阵 + 批次 A 落地（机主令：可以按你的方案走，但要有固化机制，有效果的要收进来，还要看冲突/协同组合）

### 一、固化机制（机主要求的第 1 条）—— 已建成并自证
`D:/strata166/params/` 三件 + 一个闭环：
- **`PARAM_REGISTER.tsv` = 唯一真值**：35 行 = 12 ADOPTED / 14 CANDIDATE(+1 BLOCKED) / 8 REJECTED；
  每行带 `requires / conflicts_with / synergizes_with / evidence / verdict`，`id`（P00..P97）稳定可跨波引用。
- **`gen_config.py`**：只吃 `status=ADOPTED` **生成**生产 config（生产 config 从此不许手改）；
  `--live` 与 166 现行 config 做 diff；`--write` 落盘并备份；`CALIBRATED` 值会跳过并列出。
- **`verify_config.py`**：用**四个独立数据面**证明生效 —— config JSON / 容器 `Config.Cmd` / `Config.Env` /
  引擎**当前这次**启动块的 `engine started:` 行（锚到最后一次，避开跨启动块历史行）。
- 闭环：`测 -> 判 -> 改 register -> gen_config --write -> 推 166 -> 重启 -> verify_config`，**任一步 fail 不进下一步**。

### 二、批次 A 落地（含一次被复验拦下的失败 —— 机制当场证明了自己有用）
- 收养两项**行为中性**的：`P20 --expert-profile-save /data/profiles/ud-iq4_xs-learned.bin`；`P11` 把
  `HSA_OVERRIDE_GFX_VERSION` 从 docker -e 落进 config（使其自包含）。
- **第 1 次部署失败**：config 是 `root:root` 而 SSH 用户是 `albus` ⇒ `cp` 被拒；我又没断言 rc，静默跳过。
  **是 `verify_config.py` 报 FAIL 拦住的**（P20 `config=False started=False`）。
- 修正：`sudo -n cp -a` + 每步断言（本地/远端 md5 一致、`grep -c` 新 flag = 1）。第 2 次：md5 双端一致
  `547d280c…`，重启 40 s 就绪，**复验 PASS=13 FAIL=0**，锚定启动行 `16:49:58`。
- **附带实证**：`/data/profiles/ud-iq4_xs-learned.bin` **196,632 B 已生成**（= 24576 pairs 的定长格式，
  与随镜像发的 `expert-profile.bin` 同尺寸）⇒ 自适应学习**从此不再随重启丢弃**。
- 教训入机制：远端写盘一律 `sudo -n` + **每步断言**；复验不是形式。

### 三、冲突/协同矩阵（机主要求的第 2 条）—— 源码级
- **资源争夺**：`--prefill auto:N` 与专家缓存（`--prefill auto` 的定义就是"能借到缓冲的最大 chunk"，
  现在借 1554 槽/3.49 GiB；有 `--no-prefill-borrow` 反证"借"是默认）=> **必须成对评**；
  `--kv-resident`/`--kv-grow` 与专家槽（help 明写 freed VRAM 归专家槽）；`pin=N` 与 prompt-cache；
  `STRATA_PREFILL_CPU_SHARE` 与 21 个 pool worker。
- **硬前置**：`GR_SPLIT` 需 `GR_FAST=1`（默认）；**`SPEC_GUMBEL` 需采样（贪心时是空操作）**；
  `--prompt-cache-tail` 需 `--prompt-cache` 且 `--prompt-cache-every>0`。
- **必须同口径测**：verify window 组（`--spec`/`--spec-min-p`/`--suffix-draft`/`--lookup-chain`）；
  VRAM 分配组；采样口径组。
- **互斥**：`--no-pool` 与 `PREFILL_CPU_SHARE`；`--peer-device` 与 `--layer-split`；`--vram-elastic` 与 AMD；
  **`--expert-cache-per-layer` 不要在 PROFILE 策略下开**（我们命中 94.6~96.4%，已优于其文档数字）。
- **建议打包**：K 校准包 / L 长文复用包 / S 短 prompt 包 / D 解码包 / V 容量包。

### 四、校准（P24）被硬约束挡住 —— 需机主给窗口
`tools/calibrate.py` 直接可跑、只调解码、只保留 >MIN_GAIN 的改动。**但它自带引擎要独占显存**：
实测第一次就挂 `cudaMalloc(1485606400) for the weight arena failed (out of memory): 568 MiB of 32752 MiB VRAM free`
（生产容器占着 33.95 GB）。wrapper 的"结束时无条件 `docker restart`"已生效（`POST_RESTART_DONE`）。
=> 绕法已写好：停 `strata166-402` -> **同镜像临时容器**跑 calibrate（挂 /weights:ro + /data + kfd/dri）-> 无条件起回。
**窗口约 10~15 分钟，期间 /v1/models 不可用**（WorkBuddy 正接这个模型）⇒ 要机主点头。

### 五、产物
- `D:/strata166/W708d_PARAM_SOLIDIFY.md`（9,921 B / `0bb2ebac…` / CR=0 / BAN 空）
- `D:/strata166/params/`：`PARAM_REGISTER.tsv` · `gen_config.py` · `verify_config.py` · `_mk_register.py`
  · `generated/strata-ud-iq4_xs.json` · `_verify_baseline.txt`(12/12) · `_batchA2.out.txt`(13/13)
- 166：`/data/profiles/ud-iq4_xs-learned.bin` · `logs/_calib_402.log` · config 备份 x2
- 终态核验：服务 `Up`、`http=200`、真实推理 OK（MTP draft 12 / accepted 10）
"""
b = TXT.encode('utf-8')
open(P, 'ab').write(b)
bb = open(P, 'rb').read()
print('appended %d B -> total %d B  CR=%d  md5=%s' % (len(b), len(bb), bb.count(b'\r'), hashlib.md5(bb).hexdigest()))
