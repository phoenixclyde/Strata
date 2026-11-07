# -*- coding: utf-8 -*-
"""追加今日日志：[W-Strata-05] 权重校验通过 + MSYS 路径改写大坑 + 166 侧构建/传输启动。"""
import os

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-05.md'
ANCHOR = '## [W-Strata-05]'

ADD = """

## [W-Strata-05] 权重 sha256 全过 + **[!] MSYS 路径改写大坑** + 166 侧镜像/传输启动

### 一、UD-Q4_K_XL 下载校验：**全过**
按 `setup.py` 的 `UNSLOTH_SHARDS` 钉死值逐个核 sha256（本机 SATA/NVMe 读到 ~980 MB/s）：
`00001` 10,946,624 B · `00002` 49,859,583,136 B · `00003` 49,376,141,504 B · `00004` 12,087,983,520 B
—— **四个全部 `sha256 match`，合计 111.33 GB，ALL_OK=True**（落 `D:\\idm\\Strata-UDQ4KXL\\`）。
⇒ 从 ModelScope 8 连接下载 + Content-Range 硬校验这条链路，连 111GB 都是逐字节可信的。

### 二、**[!] 新踩的大坑：Git Bash(MSYS) 会把「以 / 开头的命令行参数」改写成 Windows 路径**
**症状**：`python _push166raw.py "/home/albus/strata166/weights" a.gguf ...` 里，
Python 收到的 remote_dir 变成了
`C:/Users/clyde/.workbuddy/binaries/PortableGit/versions/1.2.0/home/albus/strata166/weights`
（MSYS root 前缀 + 原路径），于是**远端的 `mkdir -p` 造出了一棵 `/home/albus/C:/Users/...` 的目录树**，
文件全写错地方 —— 而 `ssh` 返回 **rc=0、毫无报错**，本地进度条也显示"传成功"。
**损失**：166 上 6.3 GB 垃圾（已 `rm -rf` 清掉，磁盘回到 272G）。
**判别法**：脚本里 print 出来的目标路径一旦出现 `C:/Users/.../PortableGit/...` 就是被改写了。
**根治**：**远端路径一律写死在 Python 脚本的常量里**，绝不作为 argv 从 Bash 工具传进去；
更别用 `tar ... -C <path>` 这种把路径直接交给远端 shell 的形式。传完必须**远端核 size（+sha256）**，
不能只看本地进度条。

### 三、内网吞吐实测（本机 → 166，不可压缩数据）
| 方式 | 吞吐 |
|---|---|
| ssh 单流（默认选项） | **51.96 MB/s** |
| ssh 单流 + aes128-gcm + Compression=no | 41.22 MB/s |
| ssh **4 条并行** | **75.89 MB/s（聚合）** |
- ⚠ 之前用 `tar czf - | ssh 'tar xzf -'`（`mode='w|gz'`）只跑到 **1.2 MB/s** —— **瓶颈是管道里的 gzip，不是网络**。
  搬大文件一律**裸流**（每文件一条 `ssh 'cat > 目标'`），并行度按文件数给。
- 111.33 GB 按 4 片并行（0.01 / 49.86 / 49.38 / 12.09）≈ **62 MB/s，ETA ~27 分钟**，日志 `D:\\strata166\\logs\\_push_weights.txt`。
- 推送器 `_push166v2.py`：**含断点续传**（先 `stat -c %s` 比对远端 size，一致则跳过；不一致则删了重传）+ 传后逐文件核 size。

### 四、166 侧新镜像构建已启动
- 构建上下文 `/home/albus/strata166/build-ctx/`（`Dockerfile` 3.1KB + `transfer/` 47.7MB + `.dockerignore` 只放行这两个）
  —— 刻意与写满权重的 `weights/` 分开，避免 docker build 把 111GB 当上下文。
- `setsid nohup docker build --progress=plain -t strata-gfx906:0.1.39 -f .../Dockerfile .../build-ctx > logs/build-image.log 2>&1 &`
  （脱离 ssh，pid 1584576）
- 底座 `docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete` **本地没有，正在拉**。
- 已确认远端 apt 源可达（archive.ubuntu.com / tuna / aliyun 全 OK）⇒ Dockerfile 里 apt 装 cmake/ninja 那步可行。

### 五、本轮新增脚本（都在 `D:\\strata166\\scripts\\`）
`_verify_udq4k.py`（sha256 校验）· `_push166.py`（tar 版，已被证慢，留作反例）· `_lan_speed.py`（吞吐基准）·
`_push166raw.py`（旧版，路径来自 argv —— **就是它踩了坑**）· `_find_wrongpath.py`（定位误写）·
`_push166v2.py`（**现行版**：路径写死 + 断点续传 + 远端核 size）· `_verify_ctx166.py`（上下文对拍）·
`_build166_image.py` / `_build166_image2.py`（166 侧建镜像）
"""

b0 = open(P, 'rb').read()
assert ANCHOR.encode('utf-8') not in b0, '锚已存在'
data = ADD.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
with open(P, 'ab') as f:
    f.write(data)
b1 = open(P, 'rb').read()
assert b1.startswith(b0) and b0.count(b'\r') == b1.count(b'\r'), '自证失败'
print('APPEND OK  %d -> %d B  (+%d)' % (len(b0), len(b1), len(b1) - len(b0)))
