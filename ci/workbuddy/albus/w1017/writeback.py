import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1017（ROCm 到底是多少；profiler 卡在 ptrace，不在版本）

机主问「我们的 ROCm 是多少」——上一轮我写的是「5.7/6.x」，**没查就写**。查完是两套：

| 位置 | 版本 | 证据 |
|---|---|---|
| 宿主 | **ROCm 6.4.4** | `/opt/rocm-6.4.4`；`rocprofv3 --version` → `1.3.5` |
| 容器（引擎所在） | **`.info/version` = 10.1.0**，`ROCM_BUILD=7.14.0-gfx906+20260802001858`（自建 gfx906 分支） | `docker exec … cat /opt/rocm/.info/version`、`docker inspect … .Config.Env` |

**所以 W1016 §七 的「rocprofiler-sdk Requires ROCm 7+ ⇒ 不可用」是错的**：那条要求写在第三方集成（Graphsignal）
的文档里，不是 rocprofiler-sdk 的要求。容器里 **SDK 1.3.5 就在**，`rocprofv3` 与
`librocprofiler-sdk-attach.so.1.3.5` 都在；缺的是 `librocprofiler-sdk-tool.so`（tool 插件）。

**并且我当场试了 attach，失败原因是权限，不是版本：**

```
E1105 ... rocattach.cpp:596] rocprofiler-sdk-rocattach: rocattach_attach_tree could not record tree session for root pid 18
RuntimeError: Calling attach in /opt/rocm/lib/librocprofiler-sdk-rocattach.so returned non-zero status 1
```

`kernel.yama.ptrace_scope = 1`，容器 `Privileged=false`、`CapAdd=null`（**没有 `SYS_PTRACE`**）⇒ 非子进程不可 attach。
生产在这次尝试里**未受影响**（`/health` ok、restarts 仍 0、config md5 未变），窗口内那个 2K 请求跑完
（3127 tokens / 6.539 s / 478 tok/s，比基线低，是 profiler 开销）。

**归因手段的现状（`P335`）**：两条路都要一次容器级改动——

1. `--cap-add=SYS_PTRACE` 重起容器（配置不变，1 次重启），之后 `rocprofv3 --attach <pid> --hip-trace` 可零停机采样；
2. `rocprofv3 -- <engine>` 启动引擎（停机 ~2 分钟），但要先确认 tool 插件库存在——当前**不在**。

⇒ `P309`（树内两个事件）仍是唯一不依赖容器改动的归因手段；`host grouping` 的 91 ms 保持「机制未定位」。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1017" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
# correct the W1016 claim in place
old = "**外网（归因手段）**：ROCm 侧测量同步阻塞时间有现成仪器"
if old in s:
    s = s.replace(old, "**外网（归因手段）**（~~W1016 原文~~：见 `W1017` 更正——版本够、SDK 在，卡在 ptrace 权限）：ROCm 侧测量同步阻塞时间有现成仪器", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B5本机缺口", "P334", "ROCm 版本事实更正：宿主 6.4.4；容器 `.info/version` 10.1.0 / `ROCM_BUILD=7.14.0-gfx906`；SDK 1.3.5 在", "W1017", "DONE",
  "**W1017 立**：上一轮写的「5.7/6.x」是猜的。实测：宿主 `/opt/rocm-6.4.4`（`rocprofv3 --version` 1.3.5）；容器 `.info/version` **10.1.0**、env `ROCM_BUILD=7.14.0-gfx906+20260802001858`。"
  "`rocprofv3`、`librocprofiler-sdk-attach.so.1.3.5` 均在；缺 `librocprofiler-sdk-tool.so`。⇒ W1016 §七「Requires ROCm 7+ 故不可用」撤回。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1017"),
 ("B5本机缺口", "P335", "profiler attach 实测失败：`ptrace_scope=1` + 容器无 `CAP_SYS_PTRACE`；两条路都要容器级改动", "W1017", "OPEN",
  "**W1017 立**：两次 `rocprofv3 --attach 18` 均报 `rocattach_attach_tree could not record tree session for root pid 18` / `attach ... non-zero status 1`；`kernel.yama.ptrace_scope=1`、容器 `Privileged=false`、`CapAdd=null`。"
  "路 A：`--cap-add=SYS_PTRACE` 重起容器后零停机采样；路 B：`rocprofv3 -- <engine>` 启动（需 tool 插件，当前缺）。生产在尝试中未受影响（health ok、restarts=0、md5 未变）。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1017"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
