# 四件套报告 · 填空模板（2026-11-04 16:0x 固化，机主第 3 次指出丢字段）

> 用法：**先跑 `bash deploy/tools/snap2.sh`（远端 8 字段）+ `python tools/progress.py`（进度）+ 复制 `W832 §6.5` 的队列行，再填本模板，最后跑 `python tools/report_lint.py <草稿>`，PASS 才发。**
> 机主原话（2026-11-04 15:5x）：「第一项缺 arg env，最后一项缺队列……你为什么一直会丢东西，这个不能固化下来吗？」
> ⇒ 固化的意思不是"我记得写"，而是**机械校验不通过就不许发**。

---

## 一、生产容器（**10 字段** + 3a/3b 明细，一项都不能少）

| # | 项 | 必填内容 | 反例（我犯过的） |
|---|---|---|---|
| 1 | 容器 / 镜像 | 容器 id **前 12 位** + 镜像 tag + image id 前 12 | 只写 tag |
| 2 | 运行中引擎 | `/proc/<pid>/exe` 的 **32 位 md5** + 字节数 + `--version` | 只写短 md5 |
| 3 | **config** | **md5 + exe 路径 + args 条数 + env 条数 + args/env 明细（或指向快照）** | 只写 md5（被指出两次） |
| 3a | args 明细 | **全部 `N` 个 `--flag`（逐个列出，≥15 个）** | 写「未变」 |
| 3b | env 明细 | **全部 9 个变量名（逐个列出）** | 写「同上」 |
| 4 | 健康 | `/health` 的 status + restarts + StartedAt + max_context | 只写 ok |
| 5 | 资源隔离 | `ulimit -l` + `VmLck` | 漏 |
| 6 | 显存布局 | `expert cache N slots / X GiB` + `borrows M slots (Y GiB)` + `VRAM free Z MiB` | 只写 cache |
| 7 | 回滚件 | 旧容器名 + 旧引擎文件名 + **一条可直接执行的命令** | 漏命令 |
| 8 | 本轮改动 | `零` 或逐项；**必须写 `disk = build = running` 三方 md5** | 漏第 8 项（W940 事故就是它能兜住） |
| 9 | ROCm（容器内） | `.info/version` + HIP 运行时 + clang 版本 | 写「ROCm 7.x」 |
| 10 | llama.cpp | 构建所用 tag / commit（40 位） | 只写版本号 |

> **W1043 结构铁律（机主指出「第一张是空表」后加）**：
> ① 表头与分隔行**列数必须相等**，否则 GFM 根本不把这段识别成表；
> ② 每个数据行**必须也是 3 列**——`3a`/`3b` 曾从 `| 3a | args 明细 | … |` 被写成
> 两列的 `| 3a args 明细 | … |`，GFM 会**补一个空的「值」单元格**，加上第二列超长把表撑出屏幕，
> 看起来就是「空表」（W1038–W1042 连续五轮）；
> ③ 没数据的字段写 `—`，**不许留空单元格**；
> ④ 表格前后各留一个空行（markdownlint MD058），否则部分解析器把首行并进段落；
> ⑤ 这五条由 `tools/report_lint.py` 的 `T0–T4` 机械判定，`--self-test` 6/6 负向用例。

## 二、主线（6 项）

`branch@commit` · `tag` · 上游 `commit + tag` · 落后/领先（`rev-list --left-right --count`）· 工作树脏行数 · 远端是否一致

## 三、本次落生产（4 项）

逐项改动 + **回滚命令** + **重启次数** + **累计停机时长**

## 四、进度（4 项 + **队列**）

`N 条 / 已结 M / 百分比`（取自 `tools/progress.py`）· 主线同口径 · 死块池 · **有序队列（≥5 个 R 编号，用 → 串；已结条目加 ~~删除线~~）**

---

## 自检（发之前必须跑）

```bash
python tools/report_lint.py <report.md>     # 必须 PASS
python tools/report_lint.py --self-test     # 门本身必须 6/6 PASS（负向用例不能退化为 no-op）
python tools/report_depth.py <report.md>    # 内容够不够
```

lint 检查的是**可复核性**，不是文风：12 位容器 id、32 位 md5、`args N`/`env M`、队列长度与顺序、
以及第一张表的 **T0–T4 结构**（空表 / 少列 / 空值 / 表前后空行），缺一条就 FAIL。
W1043 之前的 lint 只查「全文有没有关键词」，所以空表能连过五轮——**门验的对象错了，看起来还是绿的**。
