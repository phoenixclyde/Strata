# 旧路径 -> 新路径 映射表

**用途**：历史件（`W7xx` 报告正文、`waves/` 里的脚本）里的路径都是**迁移前**的写法，逐字保留未改（它们是证据，不是配置）。
引用或重跑之前，先按本表换算。

---

## 一、目录级映射

| 旧（迁移前） | 新（本工作区） | 备注 |
|---|---|---|
| `D:/strata166/` | `D:/workbuddy_space/strata_ws/deploy/` | 整体搬迁，6,698 文件 / 209 MB |
| `D:/workbuddy/_z_rk81/` | `D:/workbuddy_space/strata_ws/waves/` | 整体搬迁，165 文件 / 569 KB |
| `D:/Strata/` | **未迁，原地不动** | 11.2 GB Windows 部署包，仍是 `D:/Strata/` |
| `D:/workbuddy/.workbuddy/memory/2026-10-08.md` | `D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md` | 整篇迁入（原址留指针） |
| `D:/workbuddy/.workbuddy/memory/2026-10-07.md` | 同上路径下的 `2026-10-07.md` | 复制一份（routeK 侧原件保留，它是 routeK 的日志） |

---

## 二、已就地修好的（运行时仍在用，必须改）

| 文件 | 改动 | 原因 |
|---|---|---|
| `waves/_gh.py` | `TOKF` 由 `D:/workbuddy/_z_rk81/_tok.tmp` 改为 `D:/workbuddy_space/strata_ws/waves/_tok.tmp` | GitHub 凭据缓存路径，运行时读 |

---

## 三、刻意未改的（历史证据 / 一次性脚本）

搬过来的 `deploy/**`（含 `W709_*.md` 等 6 份交付件、`params/_batchA*.py`、`scripts/_*.py`）与 `waves/**`（`_pr*` / `_w*`）里，
大量出现 `D:/strata166/...`、`D:/workbuddy/_z_rk81/...`。这些是**当时的实测记录与一次性驱动**：

- 交付件正文里的路径 = 记录"当时产物在哪"，**改了就篡改证据**，故一律保留。
- 一次性驱动脚本已经跑完，其输出（`.out.txt`）本身就是证据；**重跑前**需按第一节换算路径。
- 线上仍在跑的只有 `_gh.py`（已改）与 `deploy/params/` 三件（`gen_config.py` / `verify_config.py` / `_mk_register.py`，
  实测不含写死的 `D:/strata166`，用相对/参数取路径，无需改）。

---

## 四、若要把历史件里的旧路径一次性重写

不建议（会破坏证据）。确需时，**先备份再改，并逐文件自证**（改后行数不变、仅路径片段变化）。
判据三条：① 无禁用码位；② 行数不变；③ 每处改动只涉及前缀替换。

---

## 五、迁移本身的证据

- 校验器：`tools/_verify_copy.py`；输出 `tools/_verify_copy_out.md`。
- 结论：两处源/目标 **文件集、字节数、md5 三者全等**（`ALL PASS`），才执行删除。
- 迁移时间：2026-10-08 19:2x ~ 19:4x CST。

---

## 六、原件已删除（2026-10-08 20:3x ~ 21:0x CST，机主批准）

`D:\strata166` 与 `D:\workbuddy\_z_rk81` **已不存在**。删除前做了三件事（fail-closed）：

1. **删除前置校验**：对新工作区重算两侧 (字节数, md5)，判据为 **源 ⊆ 目标**（比迁移期放宽，因为迁移后新工作区有新增件）；
   证据 `tools/_predelete_report.md`（实测：`D:\strata166` 6,697/6,698 逐字节相同 + 1 白名单；`_z_rk81` 164/165 + 1 白名单）。
2. **白名单两个**（目标侧是"有意更新过"的版本，删除前**快照留档**，快照 md5 与源件 md5 相等）：
   - `configs/workbuddy-strata166.md`（源 7,324 B / md5 `f7e5e2ae34516e8ccabeb8d17a71b097`，W712 升级前版本）
     -> `tools/snapshots_premigrate/strata166/configs/workbuddy-strata166.md`
   - `_gh.py`（源 3,042 B / md5 `84e9897ec4e515c31b13b53ecd0a064f`，TOKF 改指新址**之前**的版本）
     -> `tools/snapshots_premigrate/_z_rk81/_gh.py`
3. **分批删除**（每批 50 个文件），逐文件落 manifest：`tools/_delete_manifest_*.txt`；执行器 `tools/_predelete_verify_and_delete.py`（`--go`）与 `tools/_finish_predelete.py`。

**踩到的坑（记下来，下次别重复）**：删完文件后的**逐目录 `os.rmdir` 经过本机安全垫片极慢**（约 0.7 s/目录，739 个目录约 12 分钟），
表现与"进程卡死"完全一样（进度输出长时间不动、目录树还在）。**改用 PowerShell `Remove-Item -Recurse -Force` 收尾即秒过**。
=> 规律：**本机删除 700+ 个空目录不要用 Python 逐目录 rmdir**（见用户级记忆的反斜杠/垫片类缺陷清单）。
