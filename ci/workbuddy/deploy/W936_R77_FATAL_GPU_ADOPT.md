# W936 · R77：GPU 致命错误后自退（`e1b27d54` / #4350）移植并采纳

- 日期：2026-11-04 11:2x（CST）
- 上游提交：`e1b27d54`（2026-10-31，"After a fatal GPU error the engine ends itself and the server starts it again"，#4350）
- 本地：`gfx906/mi50 @ d963c791` + `5a13c34f`（PLE 提限，已采纳）+ **本补丁**
- 生产：`strata166-407`，引擎 `cf2ba243`，`server.py 7dfcc000`
- 结论：**DONE，已采纳**。注入实测 503 → 自动重启 → 后续请求 200；零性能回归。

---

## 0 它解决的是什么问题

上游原文（提交说明）：

> an illegal memory access, launch failure or hardware exception in a prompt read or a decode round used to turn into an ERR/cancel **while the engine kept running on a dead GPU context**, so **every later request failed with HTTP 400 until someone restarted it**.

也就是：GPU 上下文死了，引擎还活着，之后每个请求都返回 **400（不可重试）**，客户端以为是自己的请求有问题，实际要人工重启。

补丁把它改成：引擎打印 `ERR fatal GPU error: ...` 并 `_Exit(3)`；服务端把这条 ERR 判为**引擎死亡（503，可重试）**，下一请求自动拉起；并有「10 分钟内 3 次就停止重启」的防抖。

---

## 1 四部分，逐个判定能不能移

| 文件 | 行数 | 我们的情况 | 判定 |
|---|---|---|---|
| `src/program/generate.cpp` | +43 | **Qwen 引擎主线**，即我们跑的 | **移**（1 处上下文冲突） |
| `serve/server.py` | +46 | 运行期 Python，容器内 `/src/serve/server.py`，与仓库 `b1aa1d36` 逐字节相同 | **移**（干净） |
| `serve/test_fatal_gpu_restart.py` | +82 | 新增 | **移**（干净，7 个单测） |
| `src/dsv41/ds4_main.cpp` | +38 | DeepSeek 引擎，我们不用 | **移了但无效**（不参与我们的构建路径） |

`grep -c 'STRATA_USE_HIP|STRATA_HIP_GFX906'` = 1，但那 1 处是**既有**的 `#if defined(STRATA_USE_HIP) && defined(_WIN32)`，不是补丁新增的 ⇒ **P257 那条「HIP only 补丁在我们树上是死代码」不适用**。

`cudaPeekAtLastError` / `cudaGetErrorString` 在垫片里都有映射（`strata_hip.h:83` / `:80`），且 `generate.cpp:16052` 本来就在用。

---

## 2 `generate.cpp` 的唯一冲突：我们树里没有 `engine_main`

补丁的插入点上下文是

```
#if defined(STRATA_USE_HIP) && defined(_WIN32)
static int engine_main(int argc, char** argv) {   // main() is at the end of this file (#3431)
```

而 `engine_main` 是 **0.2.10 新增的写法**（把 `main()` 拆成 `engine_main` + Windows 壳）。我们树上：

```
2904: }                                  <- prepare_gated_window 结束
2906: int main(int argc, char** argv) {  <- 直接是 main
```

⇒ 解冲突方式：把两个函数（`exit_gpu_fatal` / `exit_if_gpu_fatal`）插在 `int main` **之前**，其余 4 处调用点按上游原样插。用脚本按唯一锚点替换，**没有**用 sed 全局替换（P257）。

四个调用点（`exit_if_gpu_fatal` 共 4 次调用）：

| 位置 | 上游意图 |
|---|---|
| `ver.run(...)` **之前** | `exit_if_gpu_fatal("")` —— 只为让测试钩子数窗口 |
| `ver.run(...)` 失败分支内，打印 ERR **之前** | 真判定：sticky error 文本命中就自退 |
| `!ver.commit(a+1, err)` 内 | 同上 |
| `!ver.wait_commit(err)`（decode 循环最后那个，前面有 `decode_ms`）内 | 同上 |

匹配词表（运行时自己的文本，CUDA/HIP/SYCL 一致）：`illegal memory access` / `illegal address` / `unspecified launch failure` / `launch failure` / `hardware exception` / `illegal instruction` / `misaligned address` / `uncorrectable` / `launch timed out` / `device-side assert`。

`cudaPeekAtLastError()` 而**不是** `cudaGetLastError()` —— Peek 不清错，避免把下面代码还要检查的错误吃掉。

---

## 3 实测：注入 → 503 → 重启 → 200

`STRATA_INJECT_FATAL=2` + `STRATA_INJECT_FATAL_ONCE=/data/w936/fired.flag`（写进 config env，重启一次）。

| 请求 | HTTP | 耗时 | 结果 |
|---|---|---|---|
| **req1** | **503** | 1.3 s | `the GPU reported a fatal error and the engine ended: injected (STRATA_INJECT_FATAL): an illegal memory access was encountered; the next request restarts it` |
| req2 | 200 | **268.8 s** | 引擎在请求内被重新拉起，正常出 8 token |
| req3 | 200 | 0.4 s | — |
| req4 | 200 | 0.4 s | 标志文件已存在，不再注入 |

**一个语义细节（必须记住）**：`STRATA_INJECT_FATAL=N` 数的是 **decode 窗口**，不是请求。`max_tokens=8` + spec 让第一个请求就要 2 个窗口，所以它命中在 **req1**，而不是上游描述的 req2。判据不变。

服务端记账（`docker logs`，不是引擎日志文件 —— server 的 `print()` 走 stdout）：

```
[strata] the GPU reported a fatal error (injected (...)); the engine ended (exit code 3) and is
         started again; the request that was running failed and can be sent again (1 of 3 allowed in 10 minutes)
[strata] the engine had stopped (exit code 3); starting it again (a minute or two) ...
```

引擎侧（引擎日志文件）：

```
strata serve: fatal GPU error (injected (STRATA_INJECT_FATAL): an illegal memory access was encountered):
              the engine ends so that the server can start it again
```

**上游 7 个单元测试全过**（`cd /src && python3 -m unittest serve.test_fatal_gpu_restart`）→ `Ran 7 tests ... OK`，含：
- 一次致命死亡记一次（多个请求看到同一具尸体只算一次）
- 普通死亡不计入
- 10 分钟内 3 次 → `EngineDied`，之后同引擎再问仍拒绝
- 窗口过后重新计数（输出里能看到 `1 of 3` → `2 of 3` → `3 of 3` 的真实递进）
- 普通 ERR 仍是 400（`test_an_ordinary_engine_error_stays_a_bad_request`）

---

## 4 反向判据：普通错误没有被误判成 503

| 场景 | 结果 |
|---|---|
| `messages: []` | **400** `invalid_request_error`（服务端直接拒，不到引擎） |
| 之后的正常请求 | 200 / 0.4 s，**引擎 pid 未变**（139）⇒ 没有被误重启 |

`max_tokens=400000`（超 262144）返回 200 —— 说明这个参数被 clamp 到上限，不构成 ERR，无法用它造普通错误；该路径由上游单测覆盖。

---

## 5 性能：零回归

同一脚本、同参数（`--prefill-words 4100 --n 9 --decode-tokens 256`）：

| 指标 | `8e92c662`（W935） | **`cf2ba243`（本轮）** | Δ |
|---|---|---|---|
| prefill median | 8.853 s | **8.868 s** | **+0.17%**（CV 1.1%，<2×CV） |
| decode 稳态（rep6–9） | 78.4–81.0，median 79.4 | **80.56 / 78.61 / 79.46 / 79.42，median 79.44** | **+0.05%** |

decode 全段 median 76.30 是被 rep1–3 预热拖的（47.44 → 67.22 → 72.39），按 W920 纪律只取饱和段。

补丁的常驻开销是每个 decode 窗口一次 `hipPeekAtLastError()`（线程局部读取），与计算路径无关。

---

## 6 部署脆弱点（必须记住）

`/src` **不是 bind mount**（容器的两条 bind 只有 `/models`（只读）和 `/data`（读写）），`server.py` 是**镜像层内容**。所以：

- 打补丁 = `docker cp` 进容器，**容器一重建就丢**；
- 已把补丁副本持久化到 **`/data/w936/server.py.r77`** 与 `/data/w936/test_fatal_gpu_restart.py.r77`（`/data` 是 bind，容器重建不丢）；
- 容器重建后**必须**：`cp /data/w936/server.py.r77 /src/serve/server.py`，否则引擎会打 `ERR fatal GPU error:` 而服务端按老的 400 逻辑处理（不会崩，但退化成原行为）；
- 根治办法是把 `server.py` 烘进镜像（重建镜像），见 P261。

引擎二进制在 `/data/bin`（bind），不受容器重建影响。

---

## 7 踩坑：`clang | grep | head` 会让 clang 死于 SIGPIPE

第一次编译「成功」了却得到旧对象（2,128,952 B，`strings | grep -c "fatal GPU error"` = **0**），链接后二进制 md5 与原来**一模一样**。

根因：命令写成

```bash
clang++ ... 2>&1 | grep -E "error|Error" | head -20
```

`head -20` 读满就退出并关管道 → `grep` 拿到 EPIPE → `clang` 收到 **SIGPIPE 被杀死**，对象只写了一半（且 `set -e` 看不到，因为管道退出码是 `head` 的）。

⇒ **纪律 ⑪（新增）：编译器输出必须重定向到文件再看，禁止接 `head`/`grep` 短管道。`rc` 要单独取。**

```bash
clang++ ... > /tmp/cc.log 2>&1; echo "CC_RC=$?"; grep -E "error:" /tmp/cc.log | head
```

改法后：`CC_RC=0`、对象 2,133,992 B（+5,040）、新字符串 2 处。

---

## 8 产物与回滚

| 项 | 值 |
|---|---|
| 引擎 | `/data/bin/strata-0.1.55t` = **`cf2ba243…`**（40,772,296 B）；旧件 `/data/bin/strata.bak-8e92c662` |
| server.py | `/src/serve/server.py` = **`7dfcc000…`**；备份 `/data/w936/server.py.bak`（原版 `b1aa1d36`） |
| config | **`fcf4df5b…`** —— 与 W932 采纳时**逐字节相同**（注入 env 已移除，env 9 项） |
| 合并补丁 | `~/strata166/patches/r77_fatal_gpu_on_mainline.patch`（相对主线，含 `5a13c34f` + 本补丁） |
| 实验树 | `~/strata166/work/r77`（generate.cpp `12fb89c7`、server.py `7dfcc000`） |
| 归档 | `~/strata166/w936/strata-cf2ba243`、`cfg_r77.json` |

回滚（两步都要）：

```bash
docker exec strata166-407 sh -c "mv /data/bin/strata.bak-8e92c662 /data/bin/strata-0.1.55t"
docker exec strata166-407 sh -c "cp /data/w936/server.py.bak /src/serve/server.py"
docker restart strata166-407
```

（只回滚二进制会出问题：新引擎会打 `ERR fatal GPU error:`，而老 server.py 会把它当普通 400。）

---

## 9 这条补丁真正的价值与我们场景的匹配度

- **我们不常遇到** GPU 致命错（生产 restarts=0、连续运行 26 h+），但**跑实验时遇到过**（非法访存后整轮测试作废，还要人工重启）。
- 它的价值是**无人工干预**：503 可重试 + 下一请求自动拉起 + 三次防抖。对无人值守的 agent 循环是刚需。
- 代价：每个窗口一次 `hipPeekAtLastError()`（实测无回归）+ 一个 `_Exit(3)` 的代码路径（只在错误时走）。
- **未测**（上游也自述未测）：真实 GPU 故障（无法复现）、三次拒绝在**真实**服务上的表现（只有单测）、重启后从 saved slot 恢复会话是否完好。

---

## 10 与队列的关系

- R77 → **DONE**（采纳）。
- 新增 **R79**：重启后**会话/缓存恢复**是否完好（上游自述 `NOT tested: conversations coming back from saved slots after the restart`）。我们每次重启后 `expert cache` 会重建、`conversation cache` 从 `/data` 的 session 文件恢复，值得确认「致命错 → 自动重启」后多轮对话仍能续上（`reused` 比例）。
