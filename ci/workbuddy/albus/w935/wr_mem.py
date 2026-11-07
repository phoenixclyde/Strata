# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 09:3x W935 · 采纳 `5a13c34f`（PLE 提限）：机主指出我判早了（1 次重启，引擎 → 8e92c662）
- **我上一轮判「已被 `--ulimit memlock=-1` 绕过」只对一半**：`--ulimit` 是**部署依赖**（重建容器漏带就退回 8 MiB），而补丁让引擎**自己**提限 ⇒ 若宿主 dockerd 设 `LimitMEMLOCK=infinity`，容器可不再需要该参数。机主说「这个可以做」是对的。
- **三场景实测**（`prlimit` 喂 limit + 复刻补丁逻辑的小程序）：**soft=8M/hard=unlimited ⇒ 提限 8→1536 MiB、mlock(512 MiB) OK**（补丁存在意义的那一档）；soft=hard=8M（dockerd 默认）⇒ 提不动（`max>cur` 不成立）；unlimited ⇒ 正确跳过、零动作。生产侧：`PLE table locked in RAM 1.7-1.9 s`、`VmLck 26.82 GiB`、**无 `raised to` 行**。
- **干净版二进制 `8e92c662`**（主线 d963c791 + 仅此一条，40,769,720 B / +22,944）：验证「干净」的判据 —— PLE 两个新字符串各 1、**R66 三补丁与 R68 的四个符号全为 0**。
- **构建踩坑（重要，写进 W935 §3）**：①`ninja <target>` 会先跑 `Re-running CMake`，而缓存里 `STRATA_GGML_DIR=/llama.cpp` 在镜像内不存在 ⇒ `add_subdirectory` 失败；②想 `touch` build.ninja 到未来绕开 —— **失败**（`CMakeCache.txt`/`rules.ninja` 是 root 所有，且 build.ninja 还依赖 `/out/CMakeFiles/cmake.verify_globs`）；③`ninja` 只在容器里。**可行做法：从 `build.ninja` + `CMakeFiles/rules.ninja` 逐字抄编译/链接命令手工执行**（rule `command` + build 行的 DEFINES/INCLUDES/FLAGS；链接从 `build strata:` 行展开，`$LINK_FLAGS`/`$LINK_PATH` 是空占位符要删）。
- **性能无回归**：prefill 8.790→**8.853**(+0.7%, CV 0.9%)、decode 80.58→**79.4**(−1.5%, CV 12.8%)。
- **未做（待机主定）**：宿主 `/etc/systemd/system/docker.service.d/memlock.conf` 加 `LimitMEMLOCK=infinity` ⇒ 彻底去掉容器 `--ulimit` 依赖。**代价：`systemctl restart docker` 会重启本机所有容器**。
- **构建目录状态变化**：`gfx029-build/strata` 现在是 **8e92c662**（不再是 9d9cbe17）；`libstrata_kernels.a`/`libstrata_prefill.a` 已换为干净版，备份 `.bak_w935` / `.bak_9d9cbe17`。
- **生产**：引擎 `8e92c662`、config `fcf4df5b`（`--prefill auto:16384`、`--kv k8v4`、env 9）、PLE locked、`/health ok`、restarts=0；回滚 `/data/bin/strata.bak-a97f4479`。
- **队列**：`~~…~~ → ~~R78~~ → **R77** → **R74** → R49 → R50 → R30′`。进度 **162 条 / 101 已结 = 62.3%**，主线 **134 / 101 = 75.4%**。
- 产物：`deploy/W935_PLE_RAISE_LIMIT_ADOPT.md`；`PROGRESS.tsv` R78(DONE)；`PARAM_REGISTER` **P260**；`W832` 队列；探针 `albus/w935/rlimit_probe.cpp`。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
