# -*- coding: utf-8 -*-
"""把新踩的本机长期坑追加到用户级 MEMORY.md（跨项目通用）。"""
import os

P = os.path.expanduser('~/.workbuddy/MEMORY.md')
ANCHOR = 'MSYS/Git Bash 会静默改写「以 / 开头的命令行参数」'

ADD = """

- **MSYS/Git Bash 会静默改写「以 / 开头的命令行参数」（2026-10-05 实测，跨项目通用，代价 6.3GB）**：
 从 Bash 工具调原生程序（python/ssh 等）时，形如 `/home/albus/xxx` 的参数会被改写为
 `C:/Users/clyde/.workbuddy/binaries/PortableGit/versions/1.2.0/home/albus/xxx` 才交出去。
 症状极隐蔽：**程序收到的是被改写的路径、远端 `mkdir -p` 造出 `/home/albus/C:/Users/...` 的垃圾树、
 而 ssh 返回 rc=0 且本地进度条显示"传成功"**。判别法：脚本里 print 出的目标路径出现
 `PortableGit` 字样即被改写。
 ⇒ **根治：远端路径一律写死在脚本常量里，绝不作为 argv 从命令行传入**；
 别把路径直接交给远端 shell（`tar -C <path>` 这类同样中招）。
 附带纪律：跨机搬运后**必须远端核 size/sha256**，只看本地进度条等于没验。
- **跨机搬大文件的本机实测（2026-10-05，本机 → 局域网 Ubuntu）**：ssh 单流 **52 MB/s**、
 4 流聚合 **76 MB/s**（加 aes128-gcm/关压缩反而降到 41 MB/s）。
 ⚠ **用 `tar czf - | ssh 'tar xzf -'` 只跑到 1.2 MB/s —— 瓶颈是管道里的 gzip，不是网络**；
 搬不可压缩的大文件一律**裸流**（每文件一条 `ssh 'cat > 目标'`），并行度按文件数给。
"""

b0 = open(P, 'rb').read()
assert ANCHOR.encode('utf-8') not in b0, '锚已存在'
data = ADD.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
with open(P, 'ab') as f:
    f.write(data)
b1 = open(P, 'rb').read()
assert b1.startswith(b0) and b0.count(b'\r') == b1.count(b'\r'), '自证失败'
print('USER MEMORY APPEND OK  %d -> %d B  (+%d)' % (len(b0), len(b1), len(b1) - len(b0)))
