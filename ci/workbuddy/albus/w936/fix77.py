#!/usr/bin/env python3
# W936 fix: actually write the R77 status change back (previous script only appended R79)
import io
p = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(p, encoding="utf-8").read().split("\n")
hit = False
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R77":
        if f[7] == "DONE":
            print("already DONE"); hit = True; break
        f[6] = "1"
        f[7] = "DONE"
        f[8] += (" 【W936 实测 2026-11-04 11:2x｜3 次重启，生产已采纳】移植 e1b27d54 四部分：generate.cpp(+43，1 处上下文冲突："
                 "上游插入点靠 engine_main，而我们是 0.2.10 之前的裸 main，改为插在 int main 之前，四个调用点按原样插)、"
                 "server.py(+46，干净)、test_fatal_gpu_restart.py(+82)、ds4_main.cpp(+38，我们不跑 DeepSeek 路径)。"
                 "无 HIP 宏门控(P257 不适用)。**实测**：STRATA_INJECT_FATAL=2 注入 → 首请求 **HTTP 503**(1.3s，"
                 "报文 fatal GPU error and the engine ended: injected ...; the next request restarts it) → 引擎 _Exit(3) → "
                 "**下一请求内自动重启(268.8s)并正常出 8 token** → 后续 200/0.4s；标志文件生效后不再注入。"
                 "**语义**：注入数的是 decode 窗口不是请求(max_tokens=8 就要 2 窗口)，故命中在 req1。**服务端记账**"
                 "(docker logs 而非引擎日志)：engine ended (exit code 3) and is started again ... (1 of 3 allowed in 10 minutes) + "
                 "the engine had stopped (exit code 3); starting it again。**上游 7 个单测全过**"
                 "(含 1/3→2/3→3/3 递进、普通 ERR 仍 400、同尸体只算一次)。**反向**：messages=[] → 400 且引擎 pid 不变。"
                 "**性能零回归**：prefill 8.853→8.868(+0.17%，CV 1.1%)、decode 稳态 79.44 vs 79.4。二进制 8e92c662→cf2ba243"
                 "(+2576 B)。**部署脆弱点**：/src 不是 bind(只有 /models 与 /data)，server.py 是镜像层内容 ⇒ 容器重建会丢，"
                 "已持久化 /data/w936/server.py.r77 并立 P261。**新坑**：clang 输出接 | grep | head 会 SIGPIPE 杀死 clang，"
                 "对象半截、链接后 md5 不变，静默假成功 ⇒ 纪律 ⑪。产物：W936、patches/r77_fatal_gpu_on_mainline.patch、"
                 "work/r77、归档 w936/")
        lines[i] = "\t".join(f)
        hit = True
        print("R77 -> DONE (written)")
        break
if not hit:
    print("FAIL: R77 not found")
# strip trailing blank lines
while lines and not lines[-1].strip():
    lines.pop()
io.open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("written, lines =", len(lines))
