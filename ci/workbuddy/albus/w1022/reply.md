**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`） |
| 2 | 运行中引擎 | `strata-0.1.57-001`，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B，`--version` = strata 0.1.57 |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T18:17:34Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = **unlimited**（`--ulimit memlock=-1:-1`，本轮补回）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-090`、`strata-0.1.56-091`、镜像 `0.2.10-101`、旧容器 `strata166-407-old`；`ci/rollback.sh --exe …` |
| 8 | 本轮改动 | 镜像重建 4 次（元数据补全）、容器重建 4 次、引擎未变、config 未变；disk = build = running = `5e63174d…` |

**二、主线** gfx906/mi50 @ 372106ed · tag `mi50-0.2.11-r33-8` · **落后上游 0 / 领先上游 71**（线性，0 merge commit）· 工作树脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 4 次（同一棵树，补元数据）；**重启 4 次**（容器重建）；停机合计约 4 分钟；回滚件未动用；代码面 4 提交。
**四、进度** 283 条 / 已结 203 / **71.7%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、生产用的 llama.cpp 是 **b11062 / 3cf03257**，而且从 0.2.8 起没动过

上一份报告我把「版本」写完就收工，**漏了依赖的版本**。查出来它不是一句话能答完的，四种取证互相独立：

| 角度 | 看到的东西 |
|---|---|
| 权威声明 | `third_party/ggml/VERSION.txt` = `3cf03257f219afbe7334045ff7c6a06ac68c627d Sun Sep 20 16:08:11 2026 +0800`；`CMakeLists.txt:2078` 逐字："otherwise the pinned upstream commit (third_party/ggml/VERSION.txt)" |
| 第二份副本 | `.github/workflows/metal-build.yml:29` → `LLAMA_CPP_COMMIT: 3cf03257…`（与上一致） |
| 这是什么版本 | GitHub API：2026-09-20，am17an，"CUDA: enable sparse fa for qwen4 (#28770)"；`git ls-remote` 显示 **`refs/tags/b11062`** 正指向它 |
| 镜像里是哪份 | `/src/third_party/llama.cpp` 整树 hash **`6feee58927d5f1efd38e72bbc1db061d`**（2824 文件 / 166,037,690 B） |
| 编进引擎的是哪份 | 构建挂载 `ref/llama_3cf0325` **同 hash**；`_ci_all.txt` 里 `/llama.cpp/` 引用 **93 处**、链接 `libggml-cpu.a`/`libggml-base.a`；二进制里留着 `/llama.cpp/ggml/src/…` 的 debug 路径 |
| 变了没有 | `0.2.8p2 / 0.2.9-101 / 0.2.10-101 / 0.2.11-101` 四镜像整树 hash **全等** ⇒ 跟上游 v0.2.11 **没有动 llama.cpp** |

## 六、记录本身是残的：7 位前缀 + 没有树指纹

`BUILD-IMAGE.json` 原来写 `"llama_cpp": "3cf0325"`。两个问题：

1. **7 位前缀不可校验**——前缀会碰撞，也不告诉你树里是什么；
2. **没有任何树指纹**——镜像可以整棵换掉 vendored llama.cpp 而**不动一个版本字符串**，那时四个指针全是绿的。

第二点才是要害：一个 vendored 依赖的"版本"不是字符串，是**一棵树**。字符串能改对，树能被换掉。

## 七、于是它变成第五个指针，而且按内容校验

`ci/release_check.py` 从 6 项扩到 **10 项**（`release_check.py:103` 读两处声明、`:117` 比树 hash）：

| 行 | 判据 |
|---|---|
| `llama.cpp pin (upstream)` | 先读 `third_party/ggml/VERSION.txt`（构建真正服从的那份），再读 workflow，**两处必须一致**；不一致即失败，不是"挑一个信" |
| `llama.cpp pin (release)` | `BUILD-IMAGE.json` 的 `llama_cpp` 必须是**完整 40 位**且等于上游 pin |
| `llama.cpp tree (image)` | 构建时写入 `llama_cpp_tree`，运行时在镜像内**重算整树 hash** 比对 |
| `llama.cpp in engine build` | `_ci_all.txt` 必须有 `/llama.cpp/` 引用（0 次 = 引擎从别处编的） |

第一版只读 workflow——那是**副本**，这是读 `CMakeLists.txt:2078` 的注释才发现的，改完两处都读。

`ci/selftest_pin.py` 用四个临时 repo 证明它会红：错 pin / 两处声明冲突 / 无 pin / 引擎没引用，**4/4**，已接进 `round_gate --ci`（`ci/round_gate.py:85` 是接线处；无 docker 时打印 `SKIP(no docker)` 而非假绿；`ci/selftest_pin.py:65` 是收尾那行）。Dockerfile 里也断言了树 hash（`ci/docker/Dockerfile-gfx906-0.2.11:33` 写常量、`:51` 不符即 `exit 1`），并且这份 Dockerfile 已**纳入仓库**——此前它只存在于 `build-ctx-211`，等于不可重现。

## 八、顺手抓到一次真漂移：容器重建漏了 memlock，连丢五次

`docker inspect` 逐字段比对新旧容器，18 个 HostConfig 键里**只有一处不同**：

```
new  Ulimits = []
old  Ulimits = [{"Name":"memlock","Hard":-1,"Soft":-1}]
```

容器内 `ulimit -l` 因此从 `unlimited` 掉到 **8192 KB**。W1021 重两次、W1022 重三次，**五次都没带**——因为我的记录写的是**结果**（"ulimit -l = unlimited"）而不是**flag**（`--ulimit memlock=-1:-1`），照结果拼命令行就丢了。

速度只差 0.27–0.28%（2K 528.94→**530.43**、8K 714.10→**716.02**），原因是 pinned ids 的工作集 `T*K*4*48 ≈ 3.2 MB`（拷贝点 `src/prefill/prefill.cpp:4680`）**刚好在 8 MB 默认上限内**。不是"不重要"，是"这次刚好没越界"：chunk 放大或 ring 加深就会越界。现在重建后必须跑 `diff_container.py`，差 0 才算复刻成功。

## 九、教训：写"结果"的笔记，重建时一定会丢东西

这轮两个缺陷是同一个形状——**记录的是现象，不是来源**：

- 版本记录写 `3cf0325`（现象：一个短号），丢掉了"树"这个实体；
- 容器记录写 `ulimit -l unlimited`（现象：一个观测值），丢掉了产生它的那个 flag。

判据再加一条：**凡是"以后要照着重做"的记录，必须写下产生现象的那个输入**（完整 sha、完整 flag、完整命令），而不是现象本身。

## 十、门与同步

`release_check` **PASS**（10/10）；`ROUND_GATE` **PASS**（VERIFY / PHASES / BUNDLE / SELF_TEST 7/7 / SELFTEST 4/4）；`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1022`、`§0.1` 新增「依赖 pin（llama.cpp）」行、`P350`（pin 事实）、`P351`（第五指针）、`P352`（`set -e` 下的健康等待）、`P353`（memlock 漂移）。
