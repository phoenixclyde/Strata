**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（未变）；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:45:25Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮**未动用**，零改动零重启） |
| 8 | 本轮改动 | 生产零改动、零重启；引擎 md5 与 config md5 均未变；本轮对引擎做了 30 秒只读 attach 采样（失败，见第七节） |

**二、主线** gfx906/mi50 @ f013f9b6 · tag `mi50-0.2.10-r32-20-gf013f9b6` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；回滚件未用；代码面 0 提交（只动 `deploy/`）。
**四、进度** 265 条 / 已结 185 / **69.8%**；队列 R95（`P335` 归因需一次容器级改动）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、ROCm 到底是多少：两套，上一轮我写的那句是猜的

| 位置 | 版本 | 证据 |
|---|---|---|
| **宿主** | **ROCm 6.4.4** | `/opt/rocm-6.4.4` 目录；`rocprofv3 --version` → `1.3.5` |
| **容器（引擎所在）** | `.info/version` = **10.1.0**；env `ROCM_BUILD=**7.14.0-gfx906+20260802001858**`（自建 gfx906 分支） | `docker exec … cat /opt/rocm/.info/version`；`docker inspect … .Config.Env` |

上一轮我写的是「5.7/6.x」——**没查就写**。真实情况是：宿主 6.4.4、容器 10.1.0（自建 gfx906 构建），两套不同。

## 六、「Requires ROCm 7+ 所以 profiler 不可用」也是错的

那条要求写在 Graphsignal（第三方集成）的文档里，**不是 rocprofiler-sdk 自己的要求**。容器里：

- `rocprofiler-sdk` **1.3.5** 在，`rocprofv3` 在 `/opt/rocm/bin`；
- `librocprofiler-sdk-attach.so.1.3.5` **在**（支持 attach 模式）；
- 缺的是 `librocprofiler-sdk-tool.so`（tool 插件）。

也就是说：**版本够、SDK 在、attach 库在**，我上一轮那句结论整个作废。

## 七、于是当场试了 attach，失败原因不是版本，是权限

```
E1105 ... rocattach.cpp:596] rocprofiler-sdk-rocattach: rocattach_attach_tree could not record tree session for root pid 18
RuntimeError: Calling attach in /opt/rocm/lib/librocprofiler-sdk-rocattach.so returned non-zero status 1
```

两次尝试（带 `--attach-children`、关掉它）都是同一句。查环境：`kernel.yama.ptrace_scope = 1`，容器 `Privileged=false`、`CapAdd=null` —— **没有 `SYS_PTRACE`**，非子进程不可 attach。这是机制层面的解释，不是猜。

**生产在这次尝试里没有受影响**：`/health` ok、restarts 仍 0、引擎 md5 与 config md5 都未变；采样窗口里那个 2K 请求跑完了（3127 tokens / 6.539 s / **478 tok/s**，比基线 513 低，是 profiler 开销）。

## 八、这对 R95 意味着什么

`host grouping` 的 91 ms（`prefill.cpp:4663` 的 `d2h_sync`，相位自 `prefill.cpp:4655` 起算，sync 语义见 `pinned_ring.hpp:105`）**仍未归因**，但现在有两条明确的路，且都要一次容器级改动：

1. **路 A**：容器加 `--cap-add=SYS_PTRACE` 重起（config 不变，1 次重启≈45 s），之后 `rocprofv3 --attach <pid> --hip-trace` 可**零停机**采样，拿到每个 `hipStreamSynchronize` 的阻塞时长；
2. **路 B**：`rocprofv3 -- <engine>` 启动引擎（停机 ~2 分钟），但要先确认 tool 插件库——**当前不在**。

⇒ `P309`（树内两个事件）仍是唯一不依赖容器改动的归因手段；`host grouping` 维持「机制未定位」，`bundle` 里那一行也照旧标 UNLOCALIZED。

## 九、举一反三：这一轮抓到的是「引用的二手结论」

「Requires ROCm 7+」是我从第三方集成文档里读来的，套到自家引擎上就变成了错的结论——**典型的把别人文档的适用范围当成自己的**。同类错误这个项目里已经出现过三次：`#22174 +17%` 的方向、`#31188` 的性能栏、`v_mfma` 是否存在。规矩收紧：**凡引用外部结论，必须写清「谁的文档、对谁成立」**，否则只能作为线索不能作为判据。

## 十、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py:139` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节（`W832` / `PROGRESS` / `PARAM_REGISTER` / `ID_MAP` / `AUDIT_INDEX` / `AUDIT26`）。本轮新增：`§6.5 回写·W1017`、`P334`（版本事实更正）、`P335`（attach 卡在 ptrace，两条路），并把 W1016 §七 那句就地划掉、指回 W1017。
