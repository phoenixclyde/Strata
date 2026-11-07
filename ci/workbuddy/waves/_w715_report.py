# 写 W715 交付报告（四面：主模型 / MTP / vision / n-gram）
import io, os

OUT = r"D:/workbuddy_space/strata_ws/deploy/W715_HUIHUI_SWITCH.md"

MD = """# W715 ---- 现役切换到 huihui abliterated 权重（交付报告）

- 日期：2026-10-09 01:40-02:20（本机时间）
- 范围内核：**切换完成，复验 PASS=17 / FAIL=0**；主模型 / MTP / vision / n-gram 四面均已就位且有实测。
- 运行位：容器 `strata166-407`（huihui abliterated），端口 8090；`strata166-406`（官方 base）Exited(0) 保留为回滚位。

---

## 0 一句话结论

现役主体已从**官方 unsloth base**（`577a38a2`/`d4634e6d`）换成**huihui-ai abliterated**（`c67b468b`/`130560b6`）。
换权重必须重生成 `--pack`，这一步做完了；顺带把此前一直没启用的 **vision** 面补齐（编译 `strata-vision` + config 加 `vision` 段），
并复核了 **n-gram（PLE + suffix draft）** 与 **MTP** 在 abliterated 主模型上的实际表现。

---

## 1 主模型

### 1.1 pack 重生成（换权重的前置，不可省）

`--pack` 是从 native GGUF 提取的 301 个投影矩阵 + 索引表，与 native 强耦合，不能沿用 base 的那份。

    python3 /src/tools/iq_pack.py \\
      --gguf /models/huihui-ai/.../unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf \\
      --out  /data/packs/huihui-ud-iq4_xs \\
      --compat-bf16        （与上游 setup.py:5314 对 Qwen3.8-Flash-Next 的调用一致；不带 --base）

产物 `/data/packs/huihui-ud-iq4_xs/`：`dense.bin` 1.49 GB、`index.txt`、`native_experts.txt`、`conversions.json`、
`compat-bf16.json`、`tokenizer/`。
引擎侧日志：`index.txt: 1079 tensors, 303 served natively, 0 in extra.bin, arena 1.38 GiB`；
`conversions.json: 460 tensors converted (264 exact, 196 rounded; max |err| 0.0144)`；
`compat-bf16: 195 tensors, 1.20 GiB; expert and PLE table bytes unchanged`。

### 1.2 与 base pack 的逐字节对撞（本次最有价值的机理结论）

| 文件 | base pack | huihui pack | 判定 |
|---|---|---|---|
| `dense.bin` | 1 485 688 320 B | 1 485 688 320 B | **sha256 完全相同**（`f5317405...`） |
| `index.txt` | 93 559 B | 93 559 B | **完全相同**（`e61c8352...`） |
| `native_experts.txt` | 5 803 B | 5 803 B | **完全相同**（`f9a8bdec...`） |
| `conversions.json` | 167 312 B | 167 312 B | **完全相同**（diff 0 行） |
| `compat-bf16.json` | 21 037 B | 21 107 B | 差 4 行（源分片哈希/舍入记录） |

**结论**：abliteration 的差异**只落在 experts（IQ4_XS 量化权重，引擎经 `--native` 直读 GGUF 生效）**；
**float 张量（norm / router 等，即 `dense.bin`）一个字节都没动**。这也解释了为什么新 pack 与 base pack
在四件产物上逐字节相同 ---- 差异全部藏在 GGUF 分片里，而不是 pack 里。

### 1.3 config 与运行证据

- `--pack /data/packs/huihui-ud-iq4_xs`、`--native /models/huihui-ai/.../00001-of-00003.gguf`、`tokenizer` 同源换新。
- `model_name` = `qwen3.8-flash-next-ud-iq4_xs-abliterated`（`/v1/models` 实测返回，`n_ctx 262144`）。
- 引擎启动行（新日志原文）：

      engine started: /src/build-906/strata --serve --pack /data/packs/huihui-ud-iq4_xs \\
        --native /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf \\
        ... --expert-profile-save /data/profiles/huihui-ud-iq4_xs-learned.bin --vision

- **分片解析已验证**：引擎按名字在同目录找到 huihui 的 00002/00003（见 4.1 的 PLE 行原文）。

---

## 2 MTP

- **来源**：huihui 仓**不提供** MTP。MTP 只能复用现成的 `/data/mtp/rt`，其源是官方
  `Qwen/Qwen3.8-Flash-Next` BF16 checkpoint 里 31 个 `mtp.*` 张量（`mtp-inventory.json` 自述）。
- 加载证据：`strata mtp: draft layer loaded, 1098 MiB of VRAM (experts 675, dense 111), files read in 0.51 s`。
- **接受率实测（本次 5 个请求）**：`33/40`、`29/33`、`162/233`、`66/104`、`80/91` = **370/501 = 73.9%**。
- **对照 base 历史同口径 5 次**：`11/13`、`29/41`、`30/34`、`30/39`、`281/440` = 381/567 = 67.2%。
- **判定**：**同一量级，无退化迹象**（73.9% vs 67.2%，且长生成 69.5% 对 base 63.9%）。
  上游 ORCA_Q4_K_S.md 原话也提示"微调版的 draft 接受率必须实测" ---- 本次实测就是这个动作。
  注意两次的 prompt 长度/内容并非严格同条件，只能作量级对照，不能当严格 A/B。

---

## 3 vision（本次新启用）

此前镜像里**没有** `strata-vision` 这个二进制（`/src/build-906/` 只有 `strata`），`--vision` 无从谈起。

### 3.1 编译

    cmake -S tools/vision -B /data/vision-build -G Ninja -DCMAKE_BUILD_TYPE=Release \\
          -DLLAMA_DIR=third_party/llama.cpp
    cmake --build /data/vision-build --target strata-vision -j8
    cp /data/vision-build/bin/strata-vision /data/vision/

- 取 `STRATA_PORTABLE=ON`（AVX2 基线）而非 native：本机 CPU 是 **Intel Xeon E5-2696 v4（Broadwell，无 AVX-512）**，
  AVX2 档同时也是文档里编码最快的一档。
- 产物 **7 754 632 B 静态单文件**（`BUILD_SHARED_LIBS OFF`），放 `/data/vision/strata-vision`。
- **为什么放 /data 而不是 /src**：`/src` 属于容器可写层，新建容器不继承；`/data` 是 bind mount，持久。

### 3.2 config 装配

`args` 增加 `--vision`；新增 `vision` 段（三个键由 `serve/server.py` 的 `Vision.__init__` 读）：

    "vision": {
      "exe":    "/data/vision/strata-vision",
      "mmproj": "/models/huihui-ai/.../mmproj-Qwen3.8-Flash-Next-BF16.gguf",
      "model":  "/models/huihui-ai/.../unsloth-UD-IQ4_XS/...-00001-of-00003.gguf"
    }

（`--model` 取文本模型**第一分片**，见 `tools/vision/strata_vision.cpp:7` 的用法行。）
mmproj 用的是 **huihui 仓那份**（sha256 `b1a82259`），与主模型同源配套。

### 3.3 实测

- 启动：`strata-vision: model files loaded in 1.0 s` / `READY 2560` / `on the CPU, 22 threads`。
- 单测（独立跑，证明它本身可用）：

      /data/vision/strata-vision --mmproj <mmproj> --model <shard1>   =>  READY 2560, exit=0

- **端到端**：造了一张 448x448 测试图（黑边框 + 红圆 + 左下蓝矩形），发 `image_url` 请求 =>
  262 prompt tokens（约 200 是图像 token），模型回答**准确**：
  "外围有一个黑色边框（正方形框）。内部有两个主要元素：一个红色的圆形 …… 一个蓝色的矩形，位于左下角，且矩形与圆形有部分重叠"。
- `/v1/models` 报 `input_modalities: ["text","image"]`。
- 说明：本机是 AMD，无 CUDA，故 `--gpu` 不可用，走 **CPU 编码档**（文档实测约 3 s / 300 image token，8 核）。

---

## 4 n-gram

### 4.1 PLE 表（n-gram 表）---- 本来就开着，且切到 huihui 后依旧

- 表是 `per_layer_token_embd.weight`（320 001 536 行），落在**分片 2**。
- **3 分片模型不需要 `--ple-gguf`**：上游 `setup.py:5351` 的逻辑是
  `*(["--ple-gguf", str(ple)] if len(shards) <= 2 else [])`，分片多于 2 时引擎自己按名字找。
- 切换后原文证据：

      PLE on, table 320001536 rows of /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf

  => 既证明 PLE 在跑，也证明**引擎确实读了 huihui 的分片 2**（不是 base 的）。

### 4.2 参数面

| 参数 | 现取值 | 说明 |
|---|---|---|
| `--ple-gguf` | 不设 | 3 分片自动找；不设时若找不到会**静默跳过 LAYER 1 的 PLE**，故本项要以日志行确认 |
| `--ple-io` | 默认 `direct` | register **P91 已测 `=ram` 为 REJECTED（-45%）**，保持默认 |
| `--suffix-draft` | 默认 3 | prompt lookup：从上下文里早先出现过的片段起草 |
| `--lookup-chain` / `--mtp-max-t` | 未启用 | 可选增强，本次未开 |

### 4.3 suffix draft 实测

| 请求 | 触发窗口 | 接受 |
|---|---|---|
| 冒烟 | 2 windows | 5 / 8 |
| 冒烟（复跑） | 1 window | 3 / 3 |
| 长生成 | 3 windows | 7 / 11 |
| **重复段 prompt** | **7 windows** | **20 / 20** |

最后一行是特意构造的（同一段英文重复 12 次）：n-gram lookup 命中 7 个窗口且 **20/20 全接受**，
正是这个机制该有的样子。

---

## 5 切换动作与核验

1. `iq_pack` 生成新 pack（见 1.1）。
2. 改 `deploy/params/PARAM_REGISTER.tsv`（唯一真值）：`P00`/`P01`/`P20` 指向 huihui；
   新增 `P99`（`--vision`）+ `V00`/`V01`/`V02`（`vision.exe`/`vision.mmproj`/`vision.model`，scope=CFG）。
   本机 md5 `88f3529d6ed9a2208c0bed307543815e`。
3. `gen_config.py --write` => `deploy/params/generated/strata-huihui-ud-iq4_xs.json`（md5 `ce7aa95e936a9199928487c2a8606951`）。
   （`gen_config.py` 新增对 scope=CFG 的支持：`vision.exe` 写入 `cfg["vision"]["exe"]`。）
4. 推 166：`/home/albus/strata166/params/PARAM_REGISTER.tsv` + `/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json`，
   两侧 md5 逐一对齐（旧件自动备份 `*.bak_w715_*`）。
5. 建 `strata166-407`（挂 `/data` + `/models:ro`，端口 8090）=> 停 `strata166-406` => 启 `-407`。
6. 复验：`verify_config.py` => **PASS=17 / FAIL=0**（含数据面 2：容器 Cmd 的 `--config` 经 bind 映射到 LIVE 这一真判定）。
   其中 `V00`-`V02` 因 scope=CFG 属 SKIP（核验器只判 CLI/ENV），已在报告中标明，不当作已校验。

**首次请求前要注意**：日志出现 `session is up` 只代表**引擎**就绪；serve 能服务还要等 33.45 GiB page-locked 建完
（日志 `copied cache complement through layer 48/48`）。此间发请求会 `Connection refused` ---- 实测踩到过，改用轮询 `/v1/models` 判定。

---

## 6 回滚

    docker stop strata166-407 && docker start strata166-406

- `-406` 用的仍是旧 config `/data/strata-ud-iq4_xs.json`（未被改动），`-406` 容器也原样保留。
- `PARAM_REGISTER.tsv` 与 config 均有 `.bak_w715_*` 备份（本机 + 166 两侧）。
- `/models` 侧的 huihui 与 base 是**各自独立的实体**，回滚不需要动文件。

---

## 7 遗留（未做 / 待查）

1. **expert cache 槽位从 10 289 降到 9 757（-1.21 GiB）**，与启动时 free VRAM 从 24.09 降到 22.88 GiB 同步。
   是否与 `--vision` 预留 VRAM 有关，**未证**。注意我们走的是 CPU 编码器，理论上不该占 VRAM，故存疑待查。
2. **长生成解码 14.3 tok/s 偏低**（342 tokens，首次冷 cache）；要判定是否退化需按老规矩跑完整基准（一车一变量）。
3. **`V00`-`V02` 无独立核验**：`verify_config.py` 对 scope=CFG 只 SKIP。若要闭合，应给核验器加一条
   "读 config 的 vision 段并与 register 对撞"的判定。
4. **答案差异未做受控 A/B**：本次提交的"换了模型"证据是**结构性**的（native/PLE 路径 + pack 来源 + compat-bf16 差异），
   不是同 prompt 的输出对比。若要做，需串行切换（显存放不下两个引擎）。
5. 旧待办仍在：0.1.41 解码分母重测、P31/P33 多轮缓存、P23/P28/P29/P30、C3 清理旧镜像容器、向上游提 feature request。
"""

io.open(OUT, "w", encoding="utf-8", newline="\n").write(MD)
back = io.open(OUT, encoding="utf-8").read()
assert back == MD, "读回不一致"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
bad = [hex(ord(c)) for c in back if ord(c) in BAN]
print("写入 %s" % OUT)
print("  %d B / %d 行 / CR=%d / 禁用码位=%d" % (os.path.getsize(OUT), len(back.splitlines()), back.count("\r"), len(bad)))
for k in ["PASS=17 / FAIL=0", "370/501", "READY 2560", "20 / 20", "f5317405", "回滚"]:
    print("  自证 %-22s %s" % (k, "OK" if k in back else "**缺失**"))
