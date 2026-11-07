import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1018（主线跟上游：208 个提交、零冲突并到 v0.2.11；顺带修好一个静默失效的构建脚本）

机主令「主线跟上游」。此前每轮报告都写「上游 `ffa80d73`」——**那个 sha 是两个月前的**，`git fetch` 之后：

```
ffa80d73..9f7d977d  main -> upstream/main        (new tag: v0.2.11)
ahead=63  behind=208
```

「落后 0 / 领先 0」那句一直说的是 `origin/gfx906/mi50`（自己的远端），**不是上游**。两条不同的比较被写成一个词，
和 `1.91×` 那类错误同源：**口径没写清就等于说错**。

**合并本身零冲突。** `git merge-tree --write-tree HEAD upstream/main` 先预演：rc=0、0 条 `CONFLICT`；
于是 `--no-ff` 真合并 `e21b1b01`：**338 文件 +21,481 / −1,187**。

进来的 **引擎面只有 3 个 TU**，其余是 app / catalog / Docker / Mac / tests：

| 文件 | 上游改了什么 | 对我们的影响 |
|---|---|---|
| `src/prefill/prefill.cpp` | `STRATA_GFX12_RING`：gfx12 专属的更深 ring（R9700 4K +12.5%、UD-Q4 +6.9~9.5%；16K 略负），**`STRATA_GFX12_RING=0` 关闭** | **gfx906 不走这条分支**；反而从另一侧印证 `R98`：ring 深度是**卡相关**的（他们要 192/256，我们 768 更慢 0.5–0.6%） |
| `src/prefill/gemm.cu` | 与 Q5_0 同族的 dot 偏移整理 | 我们盘上 down 是 Q5_1、gu 是 Q4_K/Q5_K，**Q5_0 不在盘上** |
| `src/prefill/gemm_w16_parity.cu` | 与上面配套的 parity 用例 | 只影响测试 |

上游那条 `aa678f10`（Q5_0 的 −16 偏移取「量化激活之和」，CUDA/HIP + SYCL）值得记一笔：它说明**同族类型之间的一个常量偏移**
曾经漏在 Q5_0 上。我们不用 Q5_0，但要记这条判据：**换 pack 类型时必须逐族核 `Σq` 偏移**（Q5_1/Q4_0 上游写明本来就有）。

**验证（都是机械的）**

- `bash ci/strata-ci check` → **23 checks / 0 failed**；`python3 ci/round_gate.py --ci` → **PASS**。
- `ci/build.sh --file src/prefill/gemm.cu` → 编译 + 归档 + 链接通过，`strata` **42,924,432 → 42,924,600 B**（md5 `ae085365… → 327c9476…`）。
- `ci/build.sh --file src/prefill/prefill.cpp` → 见下条（先失败，修好后 14.6 s 通过）。

**顺带查出的门缺陷（`P337`）**：`ci/build.sh` 用 `grep -- '-x hip -c'` 找编译行，而 **host C++ TU 不带 `-x hip`**
（`prefill.cpp` 的 ninja 命令行是 `... -c CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o`）⇒ 脚本只打印
`COMPILE LINE NOT FOUND` 并 `exit 11`，而**调用方的 for 循环接着跑下一个文件**，于是看起来像"跑过了"。
这正是本轮最容易漏的一处：合并后最重要的那个 TU 恰好是 host C++。已改成匹配 ` -c `（排除 `-E -M`），
实测 `prefill.cpp` 14.6 s 通过、重链接 md5 不变（确定性）。

**未做（明确划界）**：合并后的二进制**没有部署、没有运行期验证**。生产仍是 `eea5ea37…` / `strata-0.1.56-090`。
要不要把 v0.2.11 的树变成新二进制，走的是 build → bench → compare → deploy 那条门，不是这次「跟上游」的一部分。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1018" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
# 0.1: add the upstream row (the plan never tracked it; the chat did)
anchor = "| **唯一队列** |"
row = ("| **主线 / 上游基线** | 树 = `v0.2.11-67-ge21b1b01`（上游 `9f7d977d`，208 提交已于 `e21b1b01` 零冲突并入）；"
       "**生产二进制未重编**，仍是 `0.1.56-090` | `git describe --tags`；`git rev-list --count upstream/main..HEAD` |\n")
if "主线 / 上游基线" not in s:
    i = s.index(anchor)
    s = s[:i] + row + s[i:]
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P336", "上游 208 提交零冲突并到 `v0.2.11`（`e21b1b01`，338 文件 +21481/−1187），引擎面只有 3 个 TU", "W1018", "DONE",
  "**W1018 立**：`fetch` 后 `ffa80d73..9f7d977d`、tag `v0.2.11`，分叉 **ahead 63 / behind 208**（此前报告的「落后 0 / 领先 0」是 vs `origin`，不是上游）。"
  "`merge-tree` 预演 0 冲突 → `--no-ff` `e21b1b01`：338 文件。引擎面仅 `prefill.cpp`（gfx12 专属 `STRATA_GFX12_RING`）、`gemm.cu`、`gemm_w16_parity.cu`；"
  "验证：`strata-ci check` 23/0、`round_gate --ci` PASS、gemm.cu 编译+重链接 42,924,432→42,924,600 B。**未部署、未运行期验证**。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1018"),
 ("B8工程", "P337", "`ci/build.sh` 对 host C++ TU 静默失效（只匹配 `-x hip -c`）——已修并实测 `prefill.cpp`", "W1018", "DONE",
  "**W1018 立**：`prefill.cpp` 的 ninja 行是 host C++（无 `-x hip`），脚本 grep 不到 ⇒ 只打印 `COMPILE LINE NOT FOUND` 并 exit 11，"
  "**调用方 for 循环继续跑下一个文件**，看起来像跑过了；合并后最重要的 TU 恰好是它。改为匹配 ` -c `（排除 `-E -M`）后 14.6 s 通过、重链接 md5 不变。",
  "ci/build.sh"),
 ("B4上游移植", "P338", "上游两项与我们无关但有判据价值：Q5_0 的 −16 `Σq` 偏移、`STRATA_GFX12_RING` 反向印证 R98", "W1018", "DONE_NEG",
  "**W1018 立**：`aa678f10`（Q5_0 的 −16 偏移取量化激活之和）——我们盘上无 Q5_0（down=Q5_1/Q8_0、gu=Q4_K/Q5_K），无行为变化；"
  "但立判据：**换 pack 类型必须逐族核 `Σq` 偏移**。`STRATA_GFX12_RING`（gfx12 专属、R9700 4K +12.5%）gfx906 不生效，且反向印证 `R98`「ring 深度是卡相关」（他们 192/256 更好、我们 768 更慢）。",
  "ci/prefill_phases/PREFILL_PHASES.tsv"),
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
