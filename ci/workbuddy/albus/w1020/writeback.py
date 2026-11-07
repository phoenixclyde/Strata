import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1020（镜像/容器/引擎一起跟到 v0.2.11；并回答「引擎还是 0.1.56？」）

**1. 合并上来的树一开始是编不过的。** 上轮只验了 `prefill.cpp` 与 `gemm.cu` 两个 TU，这次全量 154 个 TU 一编，
四处失败——v0.2.11 的 ggml（pin `3cf0325`）删掉了 `ggml_prec` 这条模板参数：

| 上游改动 | 我们的调用点 | 修法 |
|---|---|---|
| `mul_mat_q_case<type, prec>` → `<type>` | 26 处（`moe_mmq.cu`、`mmq_kq_lib.cu`、`mmq_nvfp4_w4a4/w4a8.cu`） | 去掉 `GGML_PREC_Q8/Q4` 实参 |
| `ggml_cuda_mmq_get_config(type,J,fallback,cc,prec)` → `(type,J,fallback,cc)` | 5 处（`moe_mmq.cu`） | 同上 |
| `new_pool_for_device(context&,int,int)` → `(int device,int stream)` | `ggml_cuda_host.cu` | 改 override 签名 |

提交 `30e42ca8` + `53720031`。**教训**：link 成功但 `compile_fails>0` 是**混合二进制**（旧 `.o` 被复用），
所以重编前必须 `rm -f strata`——这是本轮第二次差点把混合产物当成"编过了"。

**2. 引擎真的编出来了，而且是干净的。** `rm -f strata` 后全量重编：**154/154 通过、`LINK_OK`**，
`strata` 42,947,080 B、md5 `972fb977…`。

**3. 镜像。** 完整 Dockerfile 在 `pip` 那步失败（tuna 源 01:32 不可达），改成**分层**：
`FROM strata-gfx906:0.2.10-101` + 只换 `/src`（引擎本来就不在镜像里），不需要网络。产出：

- `strata-gfx906:0.2.11-101`（9 分钟、15.7 GB）；
- `/src/serve/server.py` md5 `5758d818…`（0.2.10 是 `ecf3cfc5…`）⇒ **镜像里的树真的是 v0.2.11**；
- `BUILD-IMAGE.json` = `{v0.2.11 (9f7d977d), commits_on_top 65, engine 0.1.56, llama_cpp 3cf0325, base 0.2.10-101}`（这一行的 engine 字段随后被第 5 条否掉）。

**4. 部署与容器。** `ci/deploy.sh --apply` 过 gate/tag/identity，`cp .new → mv`，改 exe 指向
`/data/bin/strata-0.1.56-091`，重启 **46 s** 后 `/health` ok，权重账 499 矩阵/3619.14 MiB 与改前一致，
VRAM 33,497,014,272 B。容器用同一套参数（`/dev/kfd`、`/dev/dri`、`--group-add video`、`/data` rw、`/models` ro、
`--shm-size 64m`、`--ipc host`）从新镜像重建，**60 s** 后 ok；旧容器 `strata166-407-old` 停着留作回滚。

**5. 机主问「引擎还是 0.1.56？」——是，而且这是个真问题。** 版本串来自 `CMakeLists.txt:11` 的
`project(strata VERSION ...)`，上游 v0.2.11 已经把它改成 **0.1.57**；但我们没有重跑 cmake，
`build.ninja` 里缓存的是 `-DSTRATA_VERSION="0.1.56"` ⇒ 刚部署的 `-091` 是"**新引擎、旧标签**"，
指针不一致。处理：把 `_ci_all.txt` 里 154 条命令的版本串全部改成 `0.1.57`（`grep -c 0.1.57` = 154、`0.1.56` = 0），
从新镜像重编，产物以 `strata-0.1.57-001` 重新部署。**这条补进技能**：版本号是第 4 个指针（tag / BUILD-IMAGE.json /
binary / **编译期 `-DSTRATA_VERSION`**），换上游后必须确认 cmake 缓存里的宏跟着走。

**6. 顺手量了一下新引擎**（`cfg_apply --record-only`，n=6/3，冷 prompt）：

| 指标 | v0.2.10（w1013-base） | v0.2.11（-091） | 差 |
|---|---:|---:|---:|
| prefill@2000 | 513.65 tok/s | **532.58** | **+3.7%**（band 2.02） |
| prefill@8000 | 684.62 | **716.14** | **+4.6%**（band 0.18） |
| TTFT@2K | 4.096 s | 3.910 s | −4.5% |
| decode | 35.82 tok/s | 34.83 | −2.8%（band 10.96，噪声内） |

⇒ 换上游这一趟**不是白换**：2K/8K 各 +3.7%/+4.6%，decode 不变。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1020" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
s = s.replace("树 = `mi50-0.2.11-r33-2`（rebase 到上游 `9f7d977d` / v0.2.11，线性，behind 0 / ahead 64）；**生产二进制未重编**，仍是 `0.1.56-090`；**镜像仍是 `0.2.10-101`（`/src` 为 v0.2.10 树）**",
              "树 = `mi50-0.2.11-r33-3`（v0.2.11 + 两处 API 移植，线性）；**镜像 `strata-gfx906:0.2.11-101`（`/src` = v0.2.11）**；引擎 `strata-0.1.56-091`（md5 `972fb977…`，`-DSTRATA_VERSION` 仍 0.1.56，正在按 0.1.57 重编）")
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P344", "v0.2.11 的两处 ggml API 变更：`mul_mat_q_case`/`mmq_get_config` 去掉 prec、`new_pool_for_device` 改签名", "W1020", "DONE",
  "**W1020 立**：全量 154 TU 首编 4 处失败，皆因 v0.2.11 的 ggml(3cf0325) 删了 `ggml_prec` 模板参数：`mul_mat_q_case<type,prec>`→`<type>`（26 处）、"
  "`ggml_cuda_mmq_get_config(...,prec)`→`(...,cc)`（5 处）、`new_pool_for_device(context&,int,int)`→`(int,int)`（1 处）。提交 `30e42ca8`/`53720031`；移植后 154/154 通过、`LINK_OK`、md5 `972fb977…`。",
  "ci/build.sh"),
 ("B8工程", "P345", "镜像分层构建：`FROM 0.2.10-101` 只换 `/src`（完整 Dockerfile 的 pip 步骤不可用）", "W1020", "DONE",
  "**W1020 立**：完整 Dockerfile 在 pip（tuna 源）失败；改用分层：`FROM strata-gfx906:0.2.10-101` + 新源码包 + 钉住的 llama.cpp，无网络 9 分钟出 `strata-gfx906:0.2.11-101`（15.7 GB）。"
  "验证：`/src/serve/server.py` md5 `5758d818…`（≠0.2.10 的 `ecf3cfc5…`）、`BUILD-IMAGE.json` 已更新、`iqp.cpp` 在。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1020"),
 ("B5本机缺口", "P346", "第 4 个指针：编译期 `-DSTRATA_VERSION` 缓存 —— 新引擎被打成 0.1.56（源码已是 0.1.57）", "W1020", "OPEN",
  "**W1020 立**：`CMakeLists.txt:11` 上游已是 `project(strata VERSION 0.1.57)`，但 `build.ninja` 缓存 `-DSTRATA_VERSION=\\\"0.1.56\\\"` ⇒ 部署的 `-091` 是「新引擎、旧标签」。"
  "修：`_ci_all.txt` 154 条命令全改 0.1.57（`grep -c 0.1.57`=154、`0.1.56`=0）后重编，以 `strata-0.1.57-001` 重新部署。版本号共**四个指针**：tag / BUILD-IMAGE.json / binary / 编译期宏。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1020"),
 ("B6判定探针", "P347", "v0.2.11 引擎首测：prefill@2K +3.7%、@8K +4.6%、decode 噪声内", "W1020", "DONE",
  "**W1020 立**：`cfg_apply --record-only` n=6/3 冷 prompt：prefill@2000 513.65→**532.58 tok/s（+3.7%，band 2.02）**、@8000 684.62→**716.14（+4.6%，band 0.18）**、"
  "TTFT@2K 4.096→3.910 s、decode 35.82→34.83（band 10.96，噪声内）。⇒ 换上游本身带来 3.7–4.6% 的 prefill 收益。",
  "ci/state/cfg/w1020-newbin.json"),
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
