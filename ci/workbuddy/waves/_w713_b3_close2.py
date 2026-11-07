# B3 落盘（更正）：更新既有 P31 的 evidence/verdict/value，而不是新增行
import base64, collections, hashlib, io, os, shutil, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

raw = open(REG, "rb").read()
print("register md5(before) =", hashlib.md5(raw).hexdigest())
shutil.copy2(REG, REG + ".bak_w713b3_" + time.strftime("%Y%m%d_%H%M%S"))
lines = raw.decode("utf-8").splitlines()
hdr = lines[0].split("\t")
IE, IV, IVal = hdr.index("evidence"), hdr.index("verdict"), hdr.index("value")

EV = ("W713 B3 两轮（0.1.41 / -405 / Z0=off；双会话 x 3 轮交替）。"
      "**第 1 轮测试域无效**：用合成 `Answer:` 拼历史 => 前缀与上一轮不逐 token 一致；机制行 0 命中、追问 TTFT 不塌（两臂 12.1~12.6 s）"
      " => 已按真实 chat messages 结构重跑。"
      "第 2 轮（`[user(doc+Q1), assistant(A1), user(Q2), ...]`）：臂 A 无该 flag / 臂 B = 1024 MiB。"
      "**机制成立**（臂 B 新增 8 行）：`conversation cache: parked 5529/5606/5677 tokens in 172-260 ms`、"
      "`restored 5477/5551 tokens (checkpoint) in 27-38 ms`；并出现 1 次 `skip parking (snapshot 533 MiB exceeds available budget)`"
      "（快照随会话增长约 305 -> 677 MB/会话 => 1024 MiB 会被吃穿，采纳建议取 2048~4096）。"
      "**体验量级收益**：追问 TTFT **12.2 s -> 1.2~1.4 s（-88%~-90%）**（6 次追问 5 次命中，1 次预算不足回落 12.6 s）；"
      "臂 A 全部 6 轮约 12.1~12.6 s（无 parking）。"
      "**未决**：答案一致性 —— 两臂出现『同一内容在不同臂给出不同 md5』且呈互换模式，无法排除探针串位、也无法排除该路径非确定性；"
      "上游 parity 工具（`tools/conversation_cache_parity.py`）会独占 GPU 顺序加载引擎，需专门窗口")
VD = "候选：机制与收益已实证（追问 -88~-90%）；**答案一致性未决 => 暂不采纳**，先跑上游 parity（并建议预算 2048~4096）"

n = 0
out = []
for ln in lines:
    if ln.strip() and ln.split("\t")[0] == "P31":
        c = ln.split("\t")
        assert c[hdr.index("name")] == "--conversation-cache-mib", "P31 名字变了: %s" % c[hdr.index("name")]
        c[IVal] = "1024"
        c[IE], c[IV] = EV, VD
        ln = "\t".join(c); n += 1
    out.append(ln)
assert n == 1, "P31 命中 %d" % n
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
print("register md5(after)  = %s | 行=%d %s | CR=%d BAN=%d"
      % (hashlib.md5(raw2).hexdigest(), len(rows) - 1, dict(st), raw2.count(b"\r"),
         sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)))
b4 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
r = subprocess.run([r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe", "-u",
                    os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gen_config rc=%d generated identical=%s" % (r.returncode, b4 == hashlib.md5(open(GEN, "rb").read()).hexdigest()))
b64 = base64.b64encode(raw2).decode("ascii")
s = ("set -u\nD=/home/albus/strata166/params\n"
     "cp -f $D/PARAM_REGISTER.tsv $D/PARAM_REGISTER.tsv.bak_w713b3_$(date +%%Y%%m%%d_%%H%%M%%S)\n"
     "base64 -d > $D/PARAM_REGISTER.tsv <<'__R_EOF__'\n%s\n__R_EOF__\n"
     "echo remote_md5=$(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)\n") % b64
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=120)
print(p.stdout.decode("utf-8", "replace").strip())
