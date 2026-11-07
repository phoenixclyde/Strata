#!/usr/bin/env python3
# W936 登记：R77 -> DONE，新增 R79；P261；W832 队列 + 纪律 11
import io, os

D = "D:/workbuddy_space/strata_ws/deploy"

# ---------- 1) PROGRESS: R77 -> DONE ----------
p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
done = False
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R77":
        f[6] = "1"
        f[7] = "DONE"
        f[8] += (" 【W936 实测 2026-11-04 11:2x｜3 次重启，生产已采纳】移植 e1b27d54 四部分：generate.cpp(+43，1 处上下文冲突："
                 "上游插入点靠 engine_main，而我们是 0.2.10 之前的裸 main，改为插在 int main 之前，四个调用点按原样插)、"
                 "server.py(+46，干净)、test_fatal_gpu_restart.py(+82)、ds4_main.cpp(+38，我们不跑 DeepSeek 路径)。"
                 "无 HIP 宏门控(P257 不适用)。**实测**：STRATA_INJECT_FATAL=2 注入 → 首请求 **HTTP 503**(1.3s，"
                 "报文 'fatal GPU error and the engine ended: injected ...; the next request restarts it') → 引擎 _Exit(3) → "
                 "**下一请求内自动重启(268.8s)并正常出 8 token** → 后续 200/0.4s；标志文件生效后不再注入。"
                 "**语义**：注入数的是 decode 窗口不是请求(max_tokens=8 就要 2 窗口)，故命中在 req1。**服务端记账**"
                 "(docker logs 而非引擎日志)：'engine ended (exit code 3) and is started again ... (1 of 3 allowed in 10 minutes)' + "
                 "'the engine had stopped (exit code 3); starting it again'。**上游 7 个单测全过**"
                 "(含 1/3→2/3→3/3 递进、普通 ERR 仍 400、同尸体只算一次)。**反向**：messages=[] → 400 且引擎 pid 不变。"
                 "**性能零回归**：prefill 8.853→8.868(+0.17%，CV 1.1%)、decode 稳态 79.44 vs 79.4。二进制 8e92c662→cf2ba243"
                 "(+2576 B)。**部署脆弱点**：/src 不是 bind(只有 /models 与 /data)，server.py 是镜像层内容 ⇒ 容器重建会丢，"
                 "已持久化 /data/w936/server.py.r77 并立 P261。**新坑**：clang 输出接 `| grep | head` 会 SIGPIPE 杀死 clang，"
                 "对象半截、链接后 md5 不变，静默假成功 ⇒ 纪律 ⑪。产物：W936、patches/r77_fatal_gpu_on_mainline.patch、"
                 "work/r77、归档 w936/")
        lines[i] = "\t".join(f)
        done = True
        print("R77 -> DONE")
        break
if not done:
    print("FAIL: R77 not found")

row = ["B10环境与版本", "R79",
       "「致命 GPU 错 → 自动重启」之后，多轮会话与缓存是否完好（上游自述 NOT tested: conversations coming back from saved slots after the restart）",
       "W936 §10", "count", "1", "0", "OPEN",
       "**W936 立（2026-11-04 11:2x）**：R77 已上线自动重启路径，但上游明确没测「重启后从 saved slot 回来的会话」。我们每次重启会重建 expert cache、"
       "conversation cache 从 /data 的 session 文件恢复。**做法**：用 STRATA_INJECT_FATAL 在 turn2 的 decode 窗口注入 → 引擎自退 → 自动重启 → "
       "turn3 继续追问同一个会话，读服务端日志的 reused 比例与首 token 延迟，对照无注入时的 99.68%。**判据**：reused ≥99%、turn3 不返回空、"
       "不需要客户端重发 turn1。**若 <99%** ⇒ 需要在 server 侧重放/预热，或把该场景写进运维手册（重启后首轮变慢属预期）",
       "W936;W922"]
with io.open(p, "a", encoding="utf-8") as f:
    f.write("\t".join(row) + "\n")
print("R79 appended")

# ---------- 2) PARAM_REGISTER: P261 ----------
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
pl = io.open(q, encoding="utf-8").read().split("\n")
p261 = ["P261", "部署形态", "server.py 的 R77 补丁只在镜像层（/src 不是 bind），容器重建会丢",
        "容器内 /src/serve/server.py = 7dfcc000（补丁版）；持久副本 /data/w936/server.py.r77",
        "运维", "ADOPTED", "容器重建后必须 cp /data/w936/server.py.r77 /src/serve/server.py，否则引擎打 ERR fatal GPU error: 而服务端按老 400 逻辑处理",
        "W936 §6", "2026-11-04", "",
        "【W936】docker inspect 显示 binds 只有 /models（ro）与 /data（rw），/src 是镜像层；server.py 与仓库 b1aa1d36 逐字节相同，"
        "打补丁后 7dfcc000。容器重建（如 W920 那两次）会静默退回旧行为：不崩、但 fatal GPU 错又变成 400。"
        "根治 = 重建镜像时把 patch 烘进去（未做）。引擎二进制在 /data/bin（bind），不受影响"]
while len(p261) < 11:
    p261.append("")
with io.open(q, "a", encoding="utf-8") as f:
    f.write("\t".join(p261) + "\n")
print("P261 appended")

# ---------- 3) W832: 队列 + 纪律 11 ----------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()

old_seq = [l for l in s.split("\n") if l.startswith("> **执行顺序（2026-11-04")]
if old_seq:
    old = old_seq[0]
    new = ("> **执行顺序（2026-11-04 11:3x 修）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → "
           "~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70~~ → ~~R75~~ → ~~R76~~ → ~~R65~~ → ~~R78~~ → ~~R77~~ → "
           "**R79**（重启后会话恢复）→ R74（W4A4 精度门）→ R49 → R50 → R30′ → M3")
    s = s.replace(old, new, 1)
    print("queue updated")
else:
    print("WARN: queue line not found")

anchor = "> **方法纪律追加（`W917` 2026-11-03 22:1x）**"
rule = ("> **方法纪律追加（`W936` 2026-11-04 11:3x）**：⑥ 编译器的输出**必须重定向到文件再看**，"
        "禁止接 `grep ... | head` 这类短管道 —— `head` 读满即退出并关闭管道，clang 收到 SIGPIPE 被杀，"
        "对象只写一半且退出码是 `head` 的 0，表现为「编译成功、链接出旧二进制」（本轮实测：对象 2,128,952 B 未变；"
        "改成 `> /tmp/cc.log 2>&1; echo CC_RC=$?` 后 2,133,992 B）。\n"
        "> ⑦ 引擎打了 `ERR xxx` 而服务端返回 503 还是 400，取决于 server.py 而不是二进制："
        "改 server.py 必须同时改容器内 `/src/serve/server.py`（镜像层，非 bind），并做「容器重建后仍在」的验证。\n>\n")
if anchor in s:
    s = s.replace(anchor, rule + anchor, 1)
    print("discipline added")
else:
    print("WARN: discipline anchor not found")

io.open(r, "w", encoding="utf-8").write(s)
