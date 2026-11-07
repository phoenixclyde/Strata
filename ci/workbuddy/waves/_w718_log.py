import io, os

P = r"D:/workbuddy/.workbuddy/memory/2026-10-08.md"
if not os.path.isfile(P):
    io.open(P, "w", encoding="utf-8", newline="").write("# 2026-10-08 工作日志（routeK）\n")
b = open(P, "rb").read()
assert b.count(b"\r") == 0
t = b.decode("utf-8")

SEG = """

## W707 ---- Strata 升到 v0.1.40.2 + 常驻容器 + 开机自启（机主令「拉最新版本情况，并升级，作为常驻容器，开机启动」）

### 版本与补丁面（这是本次升级的实质）
- 查得最新 = **`v0.1.40.2`（2026-10-07T12:13:49Z 发布，即当天）**；我们手上是 `v0.1.40.1`（10-06 09:53）。
  仓库 `pushed_at` 也是当天，16.7k stars，一周发 20 个 release ⇒ **引用其状态必须带查询时刻**。
- **补丁面逐处实测（对照 v0.1.40.1 的 H1~H5）**：
  | 处 | 0.1.40.2 |
  |---|---|
  | H1 `strata_hip.h` cudaFuncSetAttribute 宏->模板函数 | **上游已修**（行 163） |
  | H2 `fused_gr.cu` 裸 `return;` -> `return false;` | **上游已修**（行 1743，注释 `the gfx906 STRATA_GR_SPLIT read`） |
  | H3 `mtp.cpp` stream-priority 门 | **上游已修**（行 420 `&& !defined(STRATA_HIP_GFX906)`） |
  | H4 `vmm.cpp` `<cuda.h>` 门 | **上游已修**（行 3） |
  | **H5 `CMakeLists.txt` q6_k 实例门** | **仍需打**（`moe_mmq.cu:219` 在 `__HIPCC__` 下调 `mul_mat_q_case<GGML_TYPE_Q6_K>`；CMakeLists 注释自认 "q6_k is HIP only"） |
  | **H6 `strata_hip.h` 补 `cudaEventBlockingSync`** | **新增 —— 上游漏了** |
- **H6 的发现**：首次构建在 `[118/139]` 失败：`prefill.cpp:399:99: error: use of undeclared identifier 'cudaEventBlockingSync'`。
  做**映射审计**（对比两个 hip_compat 头的全部 `cuda*` define，wave32 `hip_compat/cuda_runtime.h` vs gfx906 `platform/hip_compat/strata_hip.h`）
  => 只差 `cudaEventBlockingSync`（**被用到**，行 399）与 `cudaDevAttrIntegrated`（**已被上游 `#if ... && !defined(STRATA_HIP_GFX906)` 正确 gate**，`expert_cache.cpp:31`）
  ⇒ **只补前者**。这与技能 §7.2 的 H1 是**同族问题**（gfx906 专用头与 wave32 头不同步）。
- 产出 `patch_gfx906_402.py`（v3）：**H1~H4 改为「验证」**、H5+H6「打补丁」，全 fail-closed。
  本机两遍验证：第 1 遍 `patched=2 / verified=4`，第 2 遍 `patched=0 / verified=6` ⇒ **幂等**。
  **本机验证抓到一个 bug**（`NameError: HDR` —— v3 里 H1 改用 verify() 后没再定义 HDR）⇒ 修掉后才传 166，省下一次白构建。

### 构建与部署
- `build-ctx-402`：底座 `docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete`
  + `strata-src-0.1.40.2.zip`（**166 自己经 gh-proxy 下载，8 秒**；sha256 `7d595d4a…`，与本机下载**逐字节一致**）
  + 复用 `llama.cpp-3cf0325.tar.gz`（`LLAMA_CPP_COMMIT` 与 0.1.40.1 相同 ⇒ 未重下）。
- 镜像 **`strata-gfx906:0.1.40.2`（`125cb5b1bbfd` / 6.57GB）**；镜像内自证：`project(strata VERSION 0.1.40.2)`、
  引擎 binary 24,862,088 B / md5 `10cb60648180ca7463f51848bbd88a21`、补丁落点 H1:163 / H6:52 / H5:1270 全中。
- 容器 **`strata166-402`** / 端口 8090；旧 `strata166-401` 已 `Exited (137)`（保留可回滚）。

### [!] 机主质疑纠正了我一个多余动作
- 我先上了 **systemd**（`/etc/systemd/system/strata166.service`）。机主问「**容器开机自启动要 systemd 吗？另外 5 个容器也是 systemd 吗**」。
- 据实查：**166 上 5 个常驻容器（open-webui / netdata / comfyui-cu130 / portainer / searxng）全部用 Docker 原生
  restart policy**（2 个 `always`、3 个 `unless-stopped`）；`/etc/systemd/system/*.service` 里**没有任何 docker 相关 unit**
  （唯一一个是我刚建的）。机制 = `docker.service`（enabled）开机起 => 带 `--restart` 的容器自动拉起。
- ⇒ **撤回 systemd**（disable + 删 unit + 删软链 + daemon-reload），改用 **`--restart unless-stopped`** 重建容器。
  根因：`--rm` 与 restart policy 互斥，故重建（去掉 `--rm`、加 `-d`）。
- **通用教训**：往一台机器上加"新机制"之前，**先看那台机器同类东西是怎么做的** —— 一致性优于"我认为更好"。

### 终态与验证（全实测）
- 容器：`status=running` / **`restart=unless-stopped`**；`docker ps` 里与另 5 个并列。
- `/v1/models` → **200**，`n_ctx=262144`，status `loaded`；**冷启动 READY 仅 20s**（页缓存热）。
- 真实推理：`content="OK"` / `finish_reason=stop`，**`draft_n=3 / draft_n_accepted=3`**（MTP 3/3）。
- 工具调用：`finish_reason=tool_calls` -> `{"city":"Shanghai"}`。
- 资源：VRAM 33.93 GB；RAM `used 42 / available 82` GB。
- 磁盘：682G/935G（73%）。旧镜像 `0.1.39`(6.52GB) 与 `0.1.40.1`(6.55GB) **暂留待机主定**（回滚用）。

### 产物
- 本机：`D:/strata166/docker/patch_gfx906_402.py`(v3) · `Dockerfile-0.1.40.2` · `configs/workbuddy-strata166.md`（已改 0.1.40.2 口径）
- 166：`/home/albus/strata166/build-ctx-402/` · `logs/build-402b.log` · `logs/inspect-401-backup.json`（旧容器配置备份）
- 探针：`_z_rk81/_pr81~_pr107*.py` 及 `.out.txt`
"""

io.open(P, "w", encoding="utf-8", newline="").write(t + SEG)
nb = open(P, "rb").read()
print("log %s bytes=%d CR=%d" % (P.split("/")[-1], len(nb), nb.count(b"\r")))
tt = nb.decode("utf-8")
for k in ["## W707", "0.1.40.2", "H6", "unless-stopped", "systemd"]:
    print("  has %-16s : %s" % (k, k in tt))
