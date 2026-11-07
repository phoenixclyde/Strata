# W935 · 采纳 `5a13c34f`（PLE 提限）：补丁能救的那一档实测成立，当前状态下完全静默

> 执行 2026-11-04 09:0x–09:3x，1 次重启，生产**已换二进制**（`a97f4479` → `8e92c662`）。

---

## 0 结论

| 项 | 结果 |
|---|---|
| 补丁 | `5a13c34f`：mlock 前把 `RLIMIT_MEMLOCK` 的 soft 提到 hard；失败时给出「需要多少 / 允许多少 / 怎么改」 |
| **它真能救的那一档** | **soft=8 MiB + hard=unlimited** ⇒ 实测提限 **8 → 1536 MiB**，`mlock(512 MiB)` **OK** |
| dockerd 默认（soft=hard=8 MiB） | 提不动（`max > cur` 不成立）—— 需要同时改 dockerd |
| 当前生产（unlimited/unlimited） | **完全静默**（条件不满足，零动作），行为与补丁前一致 |
| 性能 | 无回归（prefill +0.7%、decode −1.5%，均在 CV 内） |
| 生产 | **`8e92c662`**（主线 + 仅此一条补丁），`/health ok` |

---

## 1 为什么我一开始判错了

我上一轮判「已被 `--ulimit memlock=-1` 绕过」——**这只对了一半**。

`--ulimit` 是**部署依赖**：重建容器时漏掉就退回 8 MiB。而补丁让引擎**自己**提限，两者不等价。

真正的价值路径：

```
现在:       容器 --ulimit memlock=-1  ⇒  soft=hard=unlimited   （补丁无事可做）
若改 dockerd: LimitMEMLOCK=infinity   ⇒  容器 soft=8M hard=unlim  （补丁救场）
                                        ⇒ 容器不再需要 --ulimit 参数
```

**⇒ 补丁把「必须记得带容器参数」变成「引擎自己能搞定」** —— 前提是 hard 足够大。

---

## 2 三场景实测（`prlimit` 喂 limit + 复刻补丁逻辑的小程序）

```
A: soft=8M, hard=unlimited     before soft=8.0 MiB hard=infinity
                               raised: 8.0 MiB -> 1536.0 MiB     ← 补丁生效
                               mlock(512 MiB) -> OK

B: soft=8M, hard=8M            no raise needed/possible (cur<need=1, max>cur=0)
   （dockerd 默认）             mlock(512 MiB) -> Cannot allocate memory

C: unlimited, unlimited        no raise needed/possible (cur<need=0)
   （当前生产）                 mlock(512 MiB) -> OK
```

**A 是补丁存在的意义**；B 说明它不能替代 dockerd 配置；C 说明它不改变我们现在的行为。

生产侧同样验证：`PLE table locked in RAM (1.7–1.9 s)`、`VmLck 28,125,140 kB = 26.82 GiB`、**没有 `raised to` 行**。

---

## 3 干净版二进制是怎么来的（踩坑记录）

要求：**主线 `d963c791` + 只加这一条补丁**，不能带 R66/R68（那是 `work/r66` 那棵树的 DONE_NEG 补丁）。

### 踩到的坑

1. `ninja <target>` 会先跑 `Re-running CMake`，而缓存里 `STRATA_GGML_DIR=/llama.cpp` 在镜像内不存在 ⇒ `add_subdirectory "/llama.cpp/ggml"` 失败。
2. 想用 `touch` 把 `build.ninja` 的 mtime 推到未来绕开重配置 —— **失败**：`CMakeCache.txt` / `CMakeFiles/rules.ninja` 是 root 所有，albus 改不动；而且 `build.ninja` 还依赖 `/out/CMakeFiles/cmake.verify_globs`。
3. `ninja -t commands` 在**宿主**上不可用（`ninja: command not found`，只在容器里）。

### 可行的做法（不用 ninja）

**从 `build.ninja` 与 `CMakeFiles/rules.ninja` 逐字抄出编译/链接命令，手工执行**：

```bash
# rule（rules.ninja）:
#   command = ${LAUNCHER}${CODE_CHECK}/opt/rocm/llvm/bin/clang++ $DEFINES $INCLUDES $FLAGS \
#             -MD -MT $out -MF $DEP_FILE -o $out -c $in
# build 行（build.ninja）给出该对象的 DEFINES / INCLUDES / FLAGS
```

流程：`rsync -a --exclude=.git` 建干净树 → `patch -p1` 打补丁 → 编 `ngram.cpp.o`（新）→ `ar r libstrata_kernels.a` → 编 `prefill.cpp.o` / `generate.cpp.o`（**覆盖回主线版**）→ `ar r libstrata_prefill.a` → 链接。

链接命令同样从 `build strata:` 行 + `HIP_EXECUTABLE_LINKER__strata_Release` 的 command 展开（`$LINK_FLAGS`/`$LINK_PATH` 是空占位符，删掉）。

### 验证「干净」的判据

| 符号 | 期望 | 实测 |
|---|---|---|
| `this program may lock only` | 1 | **1** |
| `raised to … for the PLE table` | 1 | **1** |
| `STRATA_PF_GROUP_SCRATCH` | 0 | **0** |
| `STRATA_PREFILL_ROUTED_STREAM` | 0 | **0** |
| `STRATA_PF_HC_REGION` | 0 | **0** |
| `STRATA_SERVE_STOP_BOUND` | 0 | **0** |

产物 `8e92c662`，40,769,720 B（比 `a97f4479` 的 40,746,776 大 **22,944 B**，与 24 行补丁 + 字符串相符）。

---

## 4 性能（无回归）

| 指标 | 换二进制前（`a97f4479`） | 换后（`8e92c662`） | Δ |
|---|---|---|---|
| prefill（6.3K，n=9） | 8.790 s / ~722 tok/s | **8.853 s / 716** | +0.7%（CV 0.9%） |
| decode（256 tok，n=9 稳态） | 80.58 tok/s | **79.4**（78.4–81.0） | −1.5%（CV 12.8%） |

补丁只在 mlock 前多一次 `getrlimit`（一次系统调用），与计算路径无关。

---

## 5 一个可选项（未做，需你定）

要彻底摆脱容器 `--ulimit` 依赖，需要在宿主加：

```ini
# /etc/systemd/system/docker.service.d/memlock.conf
[Service]
LimitMEMLOCK=infinity
```

然后 `systemctl daemon-reload && systemctl restart docker`。

**代价：`restart docker` 会重启这台机器上的所有容器。** 目前我们只有 `strata166-407`（外加保留的 `strata166-407.pre-w920b` 回滚容器），但仍属系统级变更 —— **我没有动**。

做了之后：新建容器不带 `--ulimit` 也能锁 26.8 GiB，补丁自动把 soft 提到 hard。

---

## 6 生产状态

| 项 | 值 |
|---|---|
| 引擎 | **`8e92c662`**（主线 + `5a13c34f`） |
| config | `fcf4df5b`（未变：`--prefill auto:16384`、`--kv k8v4`、env 9 项） |
| PLE | `locked in RAM` 1.7–1.9 s，`VmLck = 26.82 GiB` |
| 容器 ulimits | `memlock soft=hard=unlimited`（`--ulimit` 仍保留） |
| 健康 | `/health ok`、restarts=0 |
| 回滚 | `/data/bin/strata.bak-a97f4479`（`mv` 回去 + restart） |
| 构建目录 | `gfx029-build/strata` 现在是 `8e92c662`（不再是 `9d9cbe17`） |

---

**【AUDIT24 口径注记】**
**代理件**：§38-52 的 A 档（8→1536 MiB、mlock 512）是用**复刻补丁逻辑的小程序**测的，不是真实二进制 in-situ；生产 `unlimited` 档完全静默这一点是实测（两臂 rep6–9），不受影响。
