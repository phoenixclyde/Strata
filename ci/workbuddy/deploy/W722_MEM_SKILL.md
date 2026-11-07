# W722 ---- 「压 MEMORY.md 必须走技能」落成铁律 + 技能入口适配到本站

- 日期：2026-10-09 19:5x（本机时间）
- 机主令：**「压 memory.md 用技能，变成铁律。」**（这是该项目第 5 次强调同一条纪律）
- **先认错**：最近几轮压 `MEMORY.md`（W718-W721）我都是**自己写脚本**，没走技能。
  技能里正记着这条反复的教训（`W583` / `W585f` / `W596` / `W607` / `W609b` 共 5 次同型），
  而我仍重演了一遍。
- **结论先说**：① 技能的唯一入口 `mem_slim.py` 是 **routeK 专用**（路径硬编码），本站用不了；
  ② 已把它**适配到本站**（`deploy/tools/mem_slim.py`，与原件 diff 恰 16 行，全部落在预期 6 处）；
  ③ **本次改动全程走技能入口**（写门 + 五断言 + 归档 `Z-1` + 独立核验 `VERIFY = OK`）；
  ④ 已把"压本件必须走技能入口"写进 `MEMORY.md` §1 铁律。

---

## 1 为什么不能直接用技能的工具

技能 `routek-memory-slim` 定的唯一入口是 `D:/workbuddy/_z_tools/mem_slim.py`，但它**路径硬编码**：

| 常量 | 值（routeK） |
|---|---|
| `MEM` | `D:/workbuddy/.workbuddy/memory/MEMORY.md` |
| `DETAIL` | `D:/workbuddy/.workbuddy/memory/MEMORY_DETAIL.md` |
| `COUNTER` | `D:/workbuddy/_z_tools/.mem_slim_wave.json` |

实测证据：对本站跑它，`check` 报 **`MEM chars = 2977`** ---- 那是 **routeK 的件**，不是本站的 2889。

=> 「用技能」在本站的正确落地方式 = **把技能的唯一入口适配过来**，而不是每次重新写一套脚本。

---

## 2 适配（`deploy/tools/mem_slim.py`）

改动**只有 6 处**（与原件 `22633 B` -> 本站 `22707 B`）：

| # | 改动 |
|---|---|
| 1 | docstring 标题：`（routeK 项目）` -> `（strata_ws 适配版；技能 routek-memory-slim）` |
| 2 | `MEM` -> 本站 `MEMORY.md` |
| 3 | `DETAIL` -> 本站 `MEMORY_DETAIL.md`（**新建**，239 B） |
| 4 | `COUNTER` -> `deploy/tools/.mem_slim_wave.json` |
| 5-6 | 编号体系判据：`T\d+` -> **`P\d+`**（本站用 P00..P99/V00..V02，没有 routeK 的 `T*`）；该行在源码里**出现 2 次**（`plan` 与 `_land` 各一） |

**自证**：`difflib` 逐行 diff = **恰 16 行（+8 / -8）**，全部落在上表 6 处；`py_compile` 通过。
**未改动**的部分包含技能的全部机制：写门（`SKILL.md` md5 凭证）、五断言、
T313 计数门（同波 `plan` <= 2 次）、归档、落盘读回、7 项独立核验 ---- **一条都没动**。

---

## 3 本次改动（全程走技能入口）

**命令**：`python deploy/tools/mem_slim.py plan plan_w722.json` -> `apply`

```
WAVE: cnt=1/2
GATE OK: 已读技能（指纹 0fc29a99cd09db831f57afb3f128143f）      <- 写门：本轮 Read 到的 SKILL.md md5
AFTER  chars=2870 bytes=4483  (余量 130)
  [PASS] 字符 <= 3000 / 字节 <= 7000 / LF-only / BAN == 0 / P 编号存在 n=13 / 指针 MEMORY_DETAIL.md 在位
PLAN VERDICT = PASS (可 apply)
--- apply ---
ARCHIVED Z-1 : DETAIL 239 -> 5001 bytes (+4762)                    <- 先归档，后写（保命顺序）
WROTE MEM chars=2870 bytes=4483 md5=02682424dfc2ae4abdc4eab8e11b87cc
  [PASS] LF-only / chars<=2900 / bytes<8000 / BAN==0 / P 编号齐 / DETAIL 前缀未改 / DETAIL 含压缩前原文
VERIFY = OK
```

**ops 13 条**（`line_replace`，按行号整行替换 ---- 不传 `old` 串，规避中文引号匹配风险）：

| 行 | 作用 | 字符 |
|---|---|---|
| 3 | 加 `MEMORY_DETAIL.md` 指针（工具判据要求） | +8 |
| **22** | **加铁律：压本件必须走技能入口** | **+135** |
| 6 / 8 / 14 / 15 / 17 / 19 / 27 / 30 / 38 / 40 / 44 | 压缩（只压措辞，不删事实） | **-162** |

净 **2889 -> 2870**（余量 111 -> 130）。

**逐条增量（W735 按 `Z-1` 归档件逐行复算，可复现）**：行 3 `+8` · 行 22 `+135` · 压缩组 `-4/-32/-12/-37/-16/-1/-14/-1/-17/-4/-24` = **-162** => 合计 **-19**，与 2889->2870 一致。
**W735 更正**：压缩组原写 -149，与净变化不自洽（+8+135-149 = -6 != -19）；按 `plan_w722.json` 复算该组 = **-162**（+8+135-162 = -19），已改。

---

## 4 新立的铁律（`MEMORY.md` §1）

> **改本件（压/改 MEMORY.md）一律走技能入口 `deploy/tools/mem_slim.py`**
> （技能 `routek-memory-slim` 的适配版；机主令 2026-10-09 第 5 次强调）：命令 `auto 2900 [plan.json]`。
> **禁止**裸 Edit 挤牙膏 / 自写临时压缩脚本 / 先改后核 ---- 那会绕过技能里的 BAN/字符/归档断言，缺陷因此隐形。

**为什么这条不是"文字纪律"**（技能 `W609b` 的教训：条例拦不住行为）：
本入口把纪律做成了**可检的前置** ---- `plan` / `apply` 都先断言 `SKILL.md` 的 md5（写门），
不读技能就拿不到当前指纹；**且入口是唯一持有"归档 + 五断言 + 独立核验"的实现**。

---

## 5 两层核验

**第一层（工具内建）**：`VERIFY = OK`，7 项（LF-only / chars<=2900 / bytes<8000 / BAN==0 /
P 编号齐 / DETAIL 前缀未改 / DETAIL 含压缩前原文）。

**第二层（换实现 + 反推，13 项全绿）**：

| 判据 | 结果 |
|---|---|
| 归档原文指纹 == 压前基线 | `b8a5a4319dc6bd605c827018e6482701` **相等** |
| 行数不变（都 46 行） | 相等 |
| **差异行数 == 13**（= ops 数） | **恰 13 行** |
| 其余行逐字节相同 | 相同 |
| chars / CR / BAN / 节头 / 铁律 / 指针 / Z-1 | 全 PASS |

**报数六件**：字符 `2870` / 余量 `130`（对 3000 窗）/ 字节 `4483` /
md5 `02682424dfc2ae4abdc4eab8e11b87cc` / `cr 0` / `BAN 0`。

---

## 6 本波一条判据侧自伤（如实记录）

我第一版独立核验器报了 2 个 FAIL，**全是我自己的判据错**：
取 `Z-1` 内嵌原文时**混用了两套下标系**（`b` 算在 `seg` 系、切片却写在 `pre` 系），
于是"归档原文"多出 5 字符 / 2 行 => 指纹与行数双 FAIL。
**交付物本身没问题** ---- 同一次核验里"差异行数 == 13"是过的。

这与技能里 `W614` 记的坑**同族**（「切片类判据一律先打印边界，别凭 `+1` 数」），
本波第二版就改成**先打印 `seg[a:a+3]` / `seg[nl:nl+2]` / `seg[b-4:b]` 三个边界**，一次通过。
=> 再次印证：**核验器报红先怀疑判据**。

---

## 7 落点

| 件 | 说明 |
|---|---|
| `deploy/tools/mem_slim.py` | 技能唯一入口的本站适配版（22707 B，md5 `352c394d3fa6c1173fb78114eba14ce5`） |
| `deploy/tools/plan_w722.json` | 本次方案（13 ops，2795 B） |
| `deploy/tools/.mem_slim_wave.json` | T313 计数门状态 |
| `.workbuddy/memory/MEMORY_DETAIL.md` | 新建（239 -> 5001 B，含归档节 `Z-1` 与压前逐字原文） |
| `.workbuddy/memory/MEMORY.md` | 2870 字符 / md5 `02682424dfc2ae4abdc4eab8e11b87cc` |
