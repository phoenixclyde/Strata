# -*- coding: utf-8 -*-
"""[W863] Record the repository-setting layer (disabled workflows + the sha-pinning trap) in docs/DOWNSTREAM.md."""
P = "/home/albus/strata166/pr/strata-fork/docs/DOWNSTREAM.md"
src = open(P, encoding="utf-8").read()

ANCHOR = """- **未覆盖**：`src/` / `CMakeLists.txt` 不在任何 workflow 的 `paths` 里 ⇒ **引擎内核改动零 CI**。
  静态门（形状表 / `getenv` 存在性）可作为下一步；真机编译与逐位等价需要 self-hosted runner。"""

ADD = ANCHOR + """

### 仓库设置层（不在 git 里，clone 看不到）

2026-11-01 把 6 个与下游无关的 workflow 设为 `disabled_manually`
（`PUT /repos/{owner}/{repo}/actions/workflows/{id}/disable`，一条调用可逆）：

| 禁用的 | 为什么 |
|---|---|
| `Docker images` | 推的是 `ghcr.io/niko1221/strata`（上游 namespace），fork 里无意义 |
| `Intake` | 上游 issue/PR 治理；**带每日 cron**，会在 fork 上每天扫一次 issue |
| `Reopen` / `Title area` / `Scripts test` | 同上，都是 PR/issue 流程，我们不发 PR |
| `Metal build` | macOS PR 构建，我们没有 mac 改动 |

保留 active：`Minimal serving runtime`、`Portable monitor client`。
恢复任意一条：把 `disable` 换成 `enable` 即可。

> **不要改成"删文件"**：删文件就是一个下游补丁，每次 `rebase upstream/main` 都要解冲突，
> 也收不到上游以后对这些 workflow 的改进。设置层才是 fork 管 CI 的正确位置。

> ⚠️ **不要打开**仓库设置里的 `sha_pinning_required`。上游全部 workflow 用的是 `@v7` / `@v4` tag，
> 一旦强制 SHA pinning，这两条测试 workflow 会立刻全红——而我们不改上游文件。
> 这是"看起来更安全、实际把自己锁死"的选项。"""

if "### 仓库设置层（不在 git 里，clone 看不到）" in src:
    print("already recorded")
elif ANCHOR not in src:
    raise SystemExit("ABORT: anchor not found")
else:
    src = src.replace(ANCHOR, ADD, 1)
    open(P, "w", encoding="utf-8").write(src)
    print("recorded: repository-setting layer + sha-pinning trap")
