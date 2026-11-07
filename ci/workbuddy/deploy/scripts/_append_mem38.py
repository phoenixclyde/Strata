# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：pkill 自伤 + 引擎硬杀导致 server 僵尸占端口"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-09] **[!] 两个自伤坑：`pkill -f` 匹配自身 + 硬杀引擎后 server 变僵尸占端口**

### 一、症状链（现象与真因完全不像，值得记）
- 现象：改了 `--max-context 131072` 后重启，新实例报
  `server.py: error: port 8090 is already in use`，但 `rocm-smi` 显示 **VRAM 只用 10.8 MB（引擎其实已死）**，
  而 `curl 127.0.0.1:8090/v1/models` 竟还回 **http=200**（旧 server 仍对外应答）⇒ 看着像"端口被别的东西占了"
- 真因（`ps -eo pid,ppid,etime,pcpu,args` 一查即明）：
```
1246  bash -lc ... setsid nohup python3 serve/server.py ...   <- 启动壳，还活着
1247  python3 serve/server.py --port 8090                     <- 旧 server 本体，仍攥着 8090
1249  [strata] <defunct>                                      <- 僵尸：引擎被 -9 杀掉，父进程没收尸也没退出
```
  ⇒ **引擎被 SIGKILL 后，`serve/server.py` 不会自己发现并退出**（它会一直等/挂着），端口因此不释放；
  与"引擎优雅退出 → server 跟着 exit"是两种行为（16:39 那次重启用的是默认 SIGTERM，就顺利退了）

### 二、[!] `pkill -f` 把自己杀掉
- `docker exec ... bash -lc 'pkill -f "build-906/strata"; ...'` —— **bash 自己的 cmdline 里就含 `build-906/strata`**
  ⇒ `pkill -f` 匹配到自身 → 杀掉自己的 shell ⇒ **后面所有清理命令一条都没执行**，
  而且 `docker exec` 输出为空（第一次重启时"step 0 输出全空"就是这个），极易误判为"已清干净"
- **自免写法**：把模式写成**不会被自身匹配的正则**——
  `pkill -f "build-906/[s]trata"` / `pkill -f "serve/[s]erver.py"`
  （自身 cmdline 含字面 `[s]`，不匹配该正则；目标进程的 `strata`/`server.py` 照常匹配）

### 三、定式（本机以后照这个做）
1. **先杀 server，再杀引擎**；两条都用 `[s]` 自免模式，或直接按 PID 杀（最稳）：
   `for p in $(ps -eo pid,args | grep -E "server\\.py|build-906/strata" | grep -v grep | awk '{print $1}'); do kill -9 $p; done`
2. 启动前**必须确认端口空**；容器里**没有 `ss`/`fuser`**（只有 `pkill`/`pgrep`），
   所以"端口是否空闲"只能靠 `ps` 找残留，或直接看新实例日志头几行
3. 容器内进程异常时，**用 `ps -eo pid,ppid,etime,pcpu,args` 看父子与僵尸**，别只看 `ps aux | grep`
4. `curl /v1/models` 回 200 **不等于引擎活着**（旧 server 会照常应答）⇒ 判活要看引擎进程 + VRAM + 新日志
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old + TXT)
print('appended, size now', os.path.getsize(p), 'B')
