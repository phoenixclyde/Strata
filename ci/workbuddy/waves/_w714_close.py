# 收尾：同步 path 相关文档/记忆 + 记录 W714 结果 + 查 vision 需要编哪个目标
import io, os, subprocess, base64

WS = r"D:/workbuddy_space/strata_ws"
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
led = []


def rep(p, old, new, tag=""):
    full = os.path.join(WS, p)
    t = io.open(full, encoding="utf-8").read()
    n = t.count(old)
    if n != 1:
        led.append(("MISS", p, "%d" % n, tag or old[:44])); return False
    io.open(full, "w", encoding="utf-8", newline="\n").write(t.replace(old, new))
    led.append(("OK", p, "", tag or old[:44])); return True


# 1) 文档里 weights 绑定的描述 -> /models
rep("PROJECT.md", "| `/home/albus/strata166/weights` | 模型权重 |",
    "| `/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/` | **模型权重（2026-10-08 起）**：3 分片 + `mmproj-...BF16.gguf`；容器挂 `/models:ro` |",
    "PROJECT 权重路径") or None
rep("deploy/configs/workbuddy-strata166.md",
    "| **图片输入** | ❌ **不勾** | 实测 **HTTP 400**：`this server was started without the vision encoder` |",
    "| **图片输入** | ❌ **暂不勾** | 实测 **HTTP 400**：`this server was started without the vision encoder`。"
    "mmproj 已就位（`/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/mmproj-Qwen3.8-Flash-Next-BF16.gguf`，907.5 MB），"
    "但**镜像里没有 `strata-vision` 二进制** => 启用需先重编镜像（多编一个目标）+ 写 `vision` 段 |",
    "配置件 图片输入")

# 2) 日志
LOG = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
io.open(LOG, "a", encoding="utf-8", newline="\n").write("""
## W714b 模型落位与切换（2026-10-08 23:52-00:05，机主令「按你的来」）
- `/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/`：3 分片 + mmproj。**先硬链接被 cp 拒（same file），改真拷贝**；
  实测**链接数 1**（独立 inode）、与 `/weights` 在 **0/50/99 MB 三处抽样哈希全 SAME**、size 逐件相符。
- **注意（空间）**：`df` 全程 685G 未变 => 本机 XFS 支持 **reflink**（coreutils 9 的 `cp` 默认 `--reflink=auto`）
  => 副本与原件**共享块（CoW）**，所以拷贝瞬时且**不额外占空间**；删掉 /weights 的实体名后，块只被 /models 引用（**不释放空间是对的**）。
- register **P01 `--native` 改指 /models**：`64fdf7a6...` -> `9afa9e189f9d6a6155ff95048f8650bb`；新 config `69aa8607bd0a58dc79466b1b71d6a4f9`；
  已推 166（register + generated + LIVE）。
- **新容器 `strata166-406`**（binds = `data:/data` + `/models:/models:ro`，**去掉 weights**）已建并切换：
  22:56:15 起 -> **23:59:21 ready（180 s）**。**180 s 是正常代价**：/models 是**新 inode**，页缓存对它们是冷的 => 首次读盘。
- 复验：`verify_config.py` **PASS=16 / FAIL=0**（容器自动识别 -406；**P01 以新值 PASS**）；冒烟 `/v1/models` 200、chat 200；
  引擎启动行实测 `--native /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/...`。
- **/weights 处理**：删掉 3 个实体文件，目录改为**符号链接 -> /models/unsloth/...**。
  理由：旧容器 -405/-404/-402/-401/strata166 的 `-v .../weights:/weights:ro` 仍能解析到同一批字节 => **回滚能力保住**；
  而"正在用的那份实体"已按要求删掉（数据只在 /models 一份）。
- **vision 未启用**（下一步）：镜像里**只有 `strata` 目标，没有 `strata-vision`** =>
  要启用需重编镜像（多编一个 ninja 目标）+ 写 `vision` 段（`SETUP_VISION = {exe, mmproj, model, gpu, max_tokens, threads}`）+ 新容器 + 复验。
- 证据：`deploy/tmp/`（无新件）；日志 166 `/home/albus/strata166/w712/modelcopy2.log`、`switch.log`。
""")
print("日志已追加")
for x in led:
    print("  %-5s %-34s %-4s %s" % x)

# 3) vision 要编的目标名（查 CMakeLists）
B = r"D:/workbuddy_space/strata_ws/deploy/tmp/src411/Strata-0.1.41"
L = io.open(os.path.join(B, "CMakeLists.txt"), encoding="utf-8", errors="replace").read().splitlines()
print("=== CMake 里 vision 相关目标 ===")
for i, l in enumerate(L):
    if "vision" in l.lower() and ("add_executable" in l or "add_library" in l or "target" in l or "OUTPUT_NAME" in l):
        print("  %5d %s" % (i + 1, l[:150]))
