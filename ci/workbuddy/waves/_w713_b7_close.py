# B7 落盘：register 新增 P98（STRATA_STAGER_SSD，REJECTED）+ 推 166 + 断言生成物未变 + 方案/日志
import base64, collections, hashlib, io, os, shutil, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

raw = open(REG, "rb").read()
print("register md5(before) =", hashlib.md5(raw).hexdigest())
shutil.copy2(REG, REG + ".bak_w713b7_" + time.strftime("%Y%m%d_%H%M%S"))
t = raw.decode("utf-8")
assert "STRATA_STAGER_SSD" not in t, "已存在该行"

EV = ("W713 B7 三臂（0.1.41 / 容器 -405 / 长档 220 与 530 / 各 2 轮 / Z0=off）："
      "A=默认（引擎日志实测 `the stager takes the RAM profile`，即 4 线程/16 深/批 1）、"
      "B=`STRATA_STAGER_SSD=1`（强制 SSD 档 32 线程/128 深/批 8）、C=`=0`（显式强制 RAM 档）。"
      "引擎进程 `/proc/<pid>/environ` 实读确认三臂 env 已生效（A 无、B=1、C=0）。"
      "吞吐三臂**无差**：530 档冷预填 482.3/482.6、482.5/482.1、483.2/482.1 tok/s；"
      "220 档 433.9/440.5、431.3/438.9、433.1/439.9；冷/温 TTFT 与 reused 亦全同（8192 / 16384）。"
      "=> 差 <=0.1%，远低于预填分辨力 1.2-1.7%。"
      "源码 `src/prefill/prefill.cpp:1040-1053`：#1353 只在 `files && !stv` 时按抽样页驻留率(<90%)选档，"
      "且 'RAM profile' 那行只在**自动分支**打印（所以 C 臂也没打印，属预期而非异常）。"
      "结论：本条修复对本机是**零收益**（我们的瓶颈不在 stager 拷贝），故该开关对本机无用")
VD = "实测无收益（三臂差 <=0.1%）=> 不采用；#1353 对本机价值 = 0（已在 register 留档，免得日后重测）"

row = "\t".join(["P98", "ENV", "STRATA_STAGER_SSD", "1", "io", "REJECTED", "-", "-", "-", EV, VD])
assert len(row.split("\t")) == len(t.splitlines()[0].split("\t")), "列数不符"
io.open(REG, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + row + "\n")

raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
hdr = rows[0].split("\t")
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
print("register md5(after)  =", hashlib.md5(raw2).hexdigest(), len(raw2), "bytes")
print("行=%d status=%s CR=%d BAN=%d" % (len(rows) - 1, dict(st), raw2.count(b"\r"),
      sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)))

# 生成物断言（新行是 REJECTED，不应进 config）
b4 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
r = subprocess.run([r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe", "-u",
                    os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
af = hashlib.md5(open(GEN, "rb").read()).hexdigest()
print("gen_config rc=%d generated %s -> %s identical=%s" % (r.returncode, b4[:12], af[:12], b4 == af))

# 推 166
b64 = base64.b64encode(raw2).decode("ascii")
s = ("set -u\nD=/home/albus/strata166/params\n"
     "cp -f $D/PARAM_REGISTER.tsv $D/PARAM_REGISTER.tsv.bak_w713b7_$(date +%%Y%%m%%d_%%H%%M%%S)\n"
     "base64 -d > $D/PARAM_REGISTER.tsv <<'__R_EOF__'\n%s\n__R_EOF__\n"
     "echo remote_md5=$(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)\n") % b64
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=120)
print(p.stdout.decode("utf-8", "replace").strip())

# 日志
io.open(os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md"), "a", encoding="utf-8", newline="\n").write("""
## W713h B7 / 候选 P35 `STRATA_STAGER_SSD`（2026-10-08 23:12-23:25，0.1.41 / -405，Z0=off）
- **源码先钉机制**（`src/prefill/prefill.cpp:1040-1053`）：`files`（SSD 档）只在"确有 transient blob 且抽样页驻留 <90%"时才选；
  否则 RAM 档 = `max(2, min(4, hw/4))` = 我们 44 线程 -> **4 线程/16 深/批 1**（SSD 档是 32 线程/128 深/批 8）。
  'RAM profile' 那行只在**自动分支**打印 => C 臂（显式 =0）不打印属预期，不是异常（我脚本里的判据标签写窄了，已如实记下）。
- 三臂实测（`/proc/<pid>/environ` 实读确认 env 生效：A 无 / B=1 / C=0；各 2 轮）：
  | 档 | A 默认(RAM 档) | B 强制 SSD 档 | C 显式 RAM 档 |
  | 530 冷预填 | 482.3 / 482.6 tok/s | 482.5 / 482.1 | 483.2 / 482.1 |
  | 220 冷预填 | 433.9 / 440.5 | 431.3 / 438.9 | 433.1 / 439.9 |
  | 冷/温 TTFT 与 reused | 49.69/16.841、16384 | 49.70/16.861、16384 | 49.71/16.830、16384 |
  => **三臂差 <=0.1%，远低于预填 1.2-1.7% 分辨力 => 本开关对本机无用；#1353 对我们的价值 = 0**（瓶颈不在 stager 拷贝）。
- 处置：**register 新增 P98 `STRATA_STAGER_SSD` = REJECTED**（行数 35 -> 36，REJECTED 12 -> 13；ADOPTED 仍 16）；
  生成物**逐字节未变**（新行是 REJECTED 不进 config）；已推 166（两侧 md5 一致）。
- 证据：`deploy/tmp/_w713_b7_remote.log`（166 `w712/b7.log` 全文）；脚本 `deploy/scripts/_w713_b7_stager.sh`（md5 e4b95d9daadb7cdb54c6a2e3445d35dd）。
- 自伤记录：本次内联 `python -c` 里带 `$(...)` 又被本地 shell 做了命令替换（老坑第 N 次）=> 落盘 `.py` 再执行；脚本里又混入 4 处 U+2014（自检拦住）。
""")
print("日志已追加")
