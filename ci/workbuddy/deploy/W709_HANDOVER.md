# W709 交接件 ---- Strata 参数最优（明天从这里继续）

> 写于 2026-10-08 02:5x CST。上游：`Niko1221/Strata`。本机工作区 `D:/workbuddy/_z_rk81/`，部署件 `D:/strata166/`。

---

## 0 一页速览

本波回答机主的问题「现在是不是最优参数配置」。**做法：先把"最优"写成可证伪的判据，再用实测填。**
结论：**解码侧与多轮复用两项已调到实测最优**，另有两项实测否决、五项仍未测（配方见 §3）。

| 项 | 结果 |
|---|---|
| `--pcie-frac` | auto **0.36 -> 0.20**（采纳） |
| `--spec-min-p` | **0.5 -> 0.70**（采纳） |
| **`--prompt-cache-every`** | 默认 **16384 -> 8192**（采纳，**温 TTFT -74.6%**） |
| `--pool-workers` | 实测默认 21 最优 -> **不改** |
| adapt(every/swaps/decay) | 实测 default 最优 -> **不改** |
| `--prefill auto:16384` | **-0.22%** -> 否决 |
| `--prompt-cache-tail` | 无效果 -> 否决 |
| `--prompt-cache-every 4096` | 无效果（不对齐）-> 否决 |

### 终态指纹（明天开工前先核这几条，对得上再动手）

| 项 | 值 |
|---|---|
| 容器 | `strata166-402` running；`http=200` |
| LIVE config | `/home/albus/strata166/data/strata-ud-iq4_xs.json` = **`d2b10f0c4e8293ba010614c7acc70bea`** |
| 启动行 | 末次 `engine started` 含 `--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192` |
| register | `D:/strata166/params/PARAM_REGISTER.tsv` = **35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7**（md5 `a91b677ea13905cb36ef56fa6224c36d`） |
| 复验 | `verify_config.py` = **PASS=15 / FAIL=0 / SKIP=1** |
| 交付件 | `D:/strata166/W709_PARAM_OPTIMUM.md` = **13,705 B / `550be73648e89d03990a36944dff9343` / CR=0** |
| 现场 | 无临时容器、无残留进程；磁盘 73%；VRAM 33.96 GB |
| 环境 | **Z0=off（省电档）** ---- 引用任何性能读数必须带这条，否则与历史读数不可比 |

---

## 1 固化机制（明天改参数的**唯一合法通道**）

```
改 PARAM_REGISTER.tsv 的 status/value
   -> python D:/strata166/params/gen_config.py --write      # 产出生产 config（禁止手改 config）
   -> 推到 166 的 params/generated/ 再 cp 覆盖 data/ 的 LIVE（用 sudo -n 若属主是 root）
   -> docker restart -t 30 strata166-402
   -> python D:/strata166/params/verify_config.py            # 四数据面复验，必须 FAIL=0
```

- **`verify_config.py` 会读 register 的 ADOPTED 行**，所以改了 register 就得重新生成，否则复验会红。
- **取值型参数不能排在 args 末位**（核验器用「下一个 token」判值，末位会判成 `(flag)`）。新增 CLI 行请插在 `P20` 之前。
- register 两机同步：本机 `D:/strata166/params/` ↔ 166 `/home/albus/strata166/params/`。

---

## 2 本波三个关键机制发现（明天会继续用到）

1. **可复用的前缀必须与 prefill chunk 对齐**：chunk = 8192（`--prefill auto`）。
   **[2026-10-08 审计 P1 更正]** 这是**实测规律、非源码确证**：引擎 help 与源码未见显式「对齐」断言（"existing chunk boundary" 只出现在 `--prompt-cache-tail` 的 help），且 `every=4096`+`chunk=8192` 得 `reused=0` 无法用源码直读解释。引用时请按「实测规律」对待，见 `W713_AUDIT.md` §1 P1-5 与 `W713_AUDIT2.md`。
   - 18,083-token prompt + 默认 16384 -> `reused=16384`（**这一档本来就工作**，40.2 s -> 5.8 s）；
   - `--prompt-cache-every 4096` -> `reused=0`（**不对齐，无效**）；
   - `--prompt-cache-every 8192` -> `reused=8192`（**有效**）。
   - => 判据：改 `--prompt-cache-every` 只能用 **8192 的整数倍**去试。
2. **`--prompt-cache-tail` 与 `--prompt-cache-every` 重复**：前者要"an existing chunk boundary"，
   而后者默认已在同一位置放 checkpoint => 无增量。
3. **盲区位置**：默认 16384 让 **8192~16384 token 这一段**完全没有多轮复用 ---- 这正是 8192 补的洞。

---

## 3 明天可继续的五项（含**测量配方**，不必重新摸）

| 项 | 为什么现在没测 | 怎么测（配方） |
|---|---|---|
| `STRATA_PREFILL_CPU_SHARE=auto` | 官方口径是"prompt<1024 快 19~35%，2K 以上不变"，需要**短 prompt** 口径 | 新写一个短 prompt 探针（~600 token，`max_tokens 16`），测 **TTFT**；A/B 各 2 轮。改法：config 的 `env` 加该键（`child_env(cfg)` 会传下去）=> 只需 restart，**不必重建容器** |
| `--conversation-cache-mib` / `pin=N` | 需要**多轮真实对话**口径 | 用 `/data/bench_prefix.py` 的 `reused` 自证：多轮同一 doc，看第 2/3 轮 `reused` 是否上升；另可看 `--conversation-cache-slots`（默认 4） |
| `STRATA_GR_SPLIT=1` | 预期 ~3%，**低于解码分辨力（9.5~15%）** | 必须**多轮重复取分布**（>=5 轮/臂），或改用引擎自带的窗口计数当**机制判据**（是否生效）而非吞吐判据 |
| `STRATA_SPEC_GUMBEL=1` | 需**采样口径**（temperature>0）；我们的 bench 全用贪心 => 它是**空操作** | 探针必须设 `temperature>0`（如 0.7）并报**接受长度**分布；用贪心口径测它一定是"无效果" |
| `--kv-grow` | k8v4 下 KV 仅 ~214 MiB，预期收益小 | 若要测，看 `KV cache size` 与并发；低优先 |

**还有一个可选项**：`--prompt-cache-every` 的**其它档位**（16384 的其它因数，如 24576 / 4096 的对照）
以及 `--prompt-cache N` 的大小对 RAM 的影响（help 记 ~118 MB/checkpoint）----本波只验证了"上限约 0.7 GB"是**推算**，未实测 RAM 曲线。

---

## 4 避坑清单（本波真实踩到，明天别重复）

1. **给"停生产 / 独占资源"的窗口做兜底时，标志物要用「窗口包装进程」，不能用它的载荷。**
   v1 看门狗用"有没有 calibrate 进程"判断，而它在窗口开始后 13 秒检查（`docker exec` 还没起来）
   => 误判"窗口没开始" => **把生产容器提前拉回，两个引擎抢 GPU**（本次未造成损害，但这是真事故）。
2. **判"某 flag 无效果"之前，先自证"测的场景落在该机制的有效域内"。**
   本波同一个坑踩了两次：6.8k prompt 测需要 chunk 边界的 `--prompt-cache-tail`；4096 因**不对齐**而"无效"。
3. **本机 shim 会把 `/data/x.py` 这类命令行参数转成 Windows 路径。**
   驱动里只传**短记号**（如 `prefix220`），真实路径在脚本内拼。
   同族：`%%{http_code}` 写在非格式化字符串里 => curl 打出字面量 => 探针永远不等于 200，看起来像"服务挂了"。
4. **查容器内文件必须走 `docker exec`**，用宿主路径会报 "No such file" 假阴性（本波出现过 3 次）。
5. **只读探针也要"落盘 + `python -u` + 每步时间戳 + 断言 rc"**，否则会误判"卡死"（本波出现过 3 次假死）。

6. **要拿「引擎这次启动用的什么参数」，读引擎日志文件，别读 `docker logs`。**
   引擎把 `engine started: ...` 写进 `/data/strata-<model>.log`（宿主 `data/` 下，如
   `/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log`）；`docker logs` 只有 serve 层 stdout，
   **不含该行**。`verify_config.py` 正是靠日志里**最后一次** `engine started` 做锚点（避开跨启动块的历史行）。
   同族：容器名会变（-401 .. -407），任何脚本引用容器名一律**自动探测**（可用 `STRATA_CONTAINER` 覆盖）。

7. **`tools/` 下的引擎级工具（如 `conversation_cache_parity.py`）必须在容器内跑，不能在 166 宿主上跑。**
   `/src`、`/src/build-906/strata`、`python3` 都是**容器内**的东西；宿主上 `cd /src` 直接失败，
   而 `set -u` + `&&` 会让它**静默退出**（日志里只留一个 `EXIT=1`，看起来像工具自己崩了）。
   正解：起一个与生产容器**同设备同挂载**的临时容器（`--device /dev/kfd --device /dev/dri`、
   `--group-add video --security-opt label=disable --ipc=host`、`-v <data>:/data -v /models:/models:ro`、
   `-e HSA_OVERRIDE_GFX_VERSION=9.0.6`、`--entrypoint bash`），在它里面跑。
   该窗口会**独占 GPU**：先停生产容器（`docker stop`），跑完 `docker start` 拉回。

---

## 5 复现 / 回滚

- **校准重跑**：`bash /home/albus/strata166/w709/run_calib.sh`（先确认 `data/strata-calib.json` 在；
  它会独占 GPU 约 15 分钟并**自动恢复生产**）。看门狗用 `watchdog2.sh`（v2，判据已修正）。
- **配置回滚**：LIVE 的历代备份都在旁边（`strata-ud-iq4_xs.json.bak_w709*`）；
  register 的历代备份 `PARAM_REGISTER.tsv.bak_w709{,b,c}_*`。
- **校准证据**：`/home/albus/strata166/params/evidence/w709_calib_out.json`（`5a39b6a08bc92d25073fb960f007d08f`）
  与 `/home/albus/strata166/w709/calib_out.json`（原始 stdout）。
- **旧容器/旧镜像**（回滚用）：`strata166-401`（0.1.40.1）/ `strata166`（0.1.39）仍为 `Exited` 保留；
  镜像 `strata-gfx906:0.1.40.1`、`0.1.39` 未删。

---

## 6 产物索引

| 类别 | 路径 |
|---|---|
| 结论件 | `D:/strata166/W709_PARAM_OPTIMUM.md` |
| 本件 | `D:/strata166/W709_HANDOVER.md` |
| register / 生成器 / 核验器 | `D:/strata166/params/`（166 同路径已同步） |
| 生产 config（生成件） | `D:/strata166/params/generated/strata-ud-iq4_xs.json` |
| A/B 原始输出 | `D:/workbuddy/_z_rk81/_pr131.out.txt`（解码）· `_w726.out.txt`（预填）· `_w731.out.txt`（tail,18k）· `_w732.out.txt`（every=4096）· **`_w733.out.txt`（every=8192）** · `_w734.out.txt`(无) · `_w736.out.txt`（部署+复验） |
| 通用 A/B 驱动 | `D:/workbuddy/_z_rk81/_w726_ab.py`（`python _w726_ab.py --flag=value [prefix\|prefix150\|prefix220\|ver]`） |
| 探针 | `D:/strata166/data/bench_prefix.py`（长度可调）· `bench_ver.py` · `bench_reuse.py` |
| 记忆 | `D:/workbuddy/.workbuddy/memory/2026-10-08.md`（W707 / W709a / W709b / W709c 段） |

**测试域无效、不要当结论引用**：`D:/workbuddy/_z_rk81/_w727.out.txt`
---- 它其实是**一轮完整有效运行**的 `--prompt-cache-tail` A/B（4 臂全跑完、数据自洽），但用的 prompt 只有 **6,833 token（短于一个 chunk 8192）** => 该 flag 的机制前提不成立，**是测试域无效**。
正确结果（18,083-token prompt）在 `_w731.out.txt`。
（**更正记录**：本件初版把原因写成"驱动跑错了 bench"----那是我**误读了输出**；原文头部是 `bench=/data/bench_prefix.py`、正文是 `===== PREFIX ARM A-r1`，探针没错。）

---

## 7 本波落盘修复（收口时自查出的 4 点，已修）

| # | 问题 | 处置 |
|---|---|---|
| 1 | `PARAM_REGISTER.tsv` 含 2 个禁用码位（`3x3` 里的乘号 U+00D7、P32 行的 U+21D2） | 已清（改动 2 行），现 **BAN=CLEAN** |
| 2 | `gen_config.py`(1 行) / `verify_config.py`(3 行) 的破折号 | 已清，现 **BAN=CLEAN** |
| 3 | 记忆日志 `2026-10-08.md` 的**本波增量段**（`## W709a` 起）含 U+21D2 x1 + U+2014 x12 | 已清（改动 7 行）；**更早段落的存量命中单独报出，非本波缺陷** |
| 4 | 本机 `params/evidence/` 缺 `w709_calib_out.json`（此前只推到了 166） | 已补本机副本（`5a39b6a08bc92d25073fb960f007d08f`） |

修复自证判据（首版判据有缺陷，已换）：
首版用「反向 undo 必须逐字节等于原文」----但 `-` 的反向映射**不唯一**（U+002D 可能来自 U+2013 或 U+2212），
undo 会把所有连字符变成减号 => 断言必然失败。**是判据本身有缺陷，不是文件有问题。**
现判据三条：① 改后无禁用码位；② 行数不变且 `equal` 块逐行字节相同；
③ `replace` 块里每对 (old,new) 满足 `new == 对 old 施加同一张替换表`，且 **old 行必含至少一个禁用码位**。

> **注（易踩）**：`D:/strata166/params/_verify_w709b.txt` 是**过时的捕获件**（改 TOOL 分支**之前**的
> `PASS=14 / FAIL=1`）。**当前正确读数 `PASS=15 / FAIL=0 / SKIP=1` 在 `D:/workbuddy/_z_rk81/_w736.out.txt`。**
> 若已把 `verify_config.py` 改成带 TOOL 分支的版本，重跑一次即可复现 15/0。
