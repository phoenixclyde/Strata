# -*- coding: utf-8 -*-
"""[W863] Add the CI fix + CI-narrowing commits to the downstream ledger, and document the CI rule."""
import re

P = "/home/albus/strata166/pr/strata-fork/docs/DOWNSTREAM.md"
src = open(P, encoding="utf-8").read()

ROW4 = "| 4 | `docs: downstream maintenance note` | 本文件 | 文档 |"
NEW_ROWS = ROW4 + """
| 5 | `serve/telemetry: keep the sampler thread references` | 我们的 PCIe 带宽补丁把 `self._thread = Thread(...)` 改成了匿名线程；v0.2.9 新增的 `test_responses.NoLeakedSampler` 读这个属性判"停服后采样线程结束"，属性为 `None` ⇒ CI 在每条 `gfx906/*` 上红（`main` 绿）。`close()` 现在 join 两个采样线程 | 容器内两臂：`.w863bak` **FAIL**（报错与 CI 逐字一致）/ 修复版 **OK**；CI 见 run 41288894503 |
| 6 | `ci: narrow the two push-triggered workflows` | 只在 `main` / `gfx906/mi50` / `ci/**` 上跑 push，加 `concurrency` 取消旧 run；tag push 不再触发（测的还是已测过的代码）。`paths` 未改，rebase 时最多 4 行冲突 | 见 `deploy/CI_CD_POLICY.md`；push 一次即可看到新触发生效 |"""

if ROW4 not in src:
    raise SystemExit("ABORT: row 4 anchor not found")
if "| 5 | `serve/telemetry: keep the sampler thread references`" not in src:
    src = src.replace(ROW4, NEW_ROWS, 1)
    print("ledger: rows 5-6 added")
else:
    print("ledger: already has the new rows")

# distance line
m = re.search(r"\| 与上游距离 \| 落后 \*\*0\*\* / 领先 (\d+)", src)
if m:
    src = src[:m.start(1)] + "6" + src[m.end(1):]
    print("ledger: distance -> 落后 0 / 领先 6")

CI_SECTION = """
## CI（GitHub Actions）

上游的 CI 是**租来的**：它替我们守"补丁有没有破坏上游行为"，代价是我们得让它跑得对。

- **会冒烟的两条**：`terminal-minimal-server`（服务端 Python 套件，1298 个用例）和
  `terminal-portable-monitor`（监控客户端，ubuntu + windows 矩阵）。
- **触发收窄**：`push` 只在 `main` / `gfx906/mi50` / `ci/**` 上跑；`tag` 不触发；
  `concurrency` 取消同分支的旧 run。要在一个实验分支上要 CI，就开 `ci/<名字>`。
- **红灯判据**（按序）：① `main` 绿而本分支红 ⇒ 我们的补丁，必修；② 失败在
  `Install pinned runtime requirements` ⇒ 依赖/网络，别改代码；③ 报错是
  `AssertionError: unexpectedly None` ⇒ 优先怀疑我们删了上游新代码依赖的属性。
- **不屏蔽、不 job 级重试、不删测试**：这个门是唯一能发现"改 `serve/` 改坏了"的机器证据。
- **未覆盖**：`src/` / `CMakeLists.txt` 不在任何 workflow 的 `paths` 里 ⇒ **引擎内核改动零 CI**。
  静态门（形状表 / `getenv` 存在性）可作为下一步；真机编译与逐位等价需要 self-hosted runner。

完整过程与反证数据：`deploy/CI_CD_POLICY.md`（工作区文档，不进仓库）。
"""

if "## CI（GitHub Actions）" not in src:
    src = src.replace("\n## 跟随上游（四步）", CI_SECTION + "\n## 跟随上游（四步）", 1)
    print("ledger: CI section added")

open(P, "w", encoding="utf-8").write(src)
print("written:", P)
