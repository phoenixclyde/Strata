# B3 落盘：会话 parking 实测（机制成立 + 量级收益）+ 答案一致性列为本轮**未决**
import base64, collections, hashlib, io, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

# 1) register 新增 P99（CANDIDATE，非 ADOPTED：答案一致性未决）
raw = open(REG, "rb").read()
assert "conversation-cache-mib" not in raw.decode("utf-8"), "已存在"
io.open(REG + ".bak_w713b3_" + time.strftime("%Y%m%d_%H%M%S"), "wb").write(raw)
EV = ("W713 B3 两轮（0.1.41 / -405 / Z0=off；双会话 x 3 轮交替，真实 chat messages 结构）："
      "**第 1 轮测试域无效**（用合成 `Answer:` 拼历史 => 前缀与上一轮不逐 token 一致；机制行 0 命中、追问 TTFT 不塌）"
      "---- 已在第 2 轮修正后重跑。第 2 轮：臂 A 无该 flag、臂 B `--conversation-cache-mib 1024`。"
      "机制（引擎日志实读，臂 B 新增 8 行）：`conversation cache: parked 5529/5606/5677 tokens in 172-260 ms; "
      "restored 5477/5551 tokens (checkpoint) in 27-38 ms`；**并出现 1 次 "
      "`skip parking (snapshot 533 MiB exceeds available budget)`**（快照随会话增长 ~305 -> 677 MB，1024 MiB 预算会被吃穿）。"
      "体验：追问 TTFT **12.2 s -> 1.2~1.4 s（-88%~-90%）**（6 次追问里 5 次命中；1 次因预算不足回落 12.6 s）。"
      "**未决**：答案一致性 ---- 两臂出现『同一内容在不同臂给出不同 md5』且呈互换模式，需专门核（可能是探针把两会话输出串位，"
      "也可能是该路径确有非确定性）；上游为此提供了 `tools/conversation_cache_parity.py`（会独占 GPU 顺序加载引擎，需专门窗口）。"
      "=> 判定：**机制成立、收益量级大**；采纳前须先过一致性关（并建议预算取 2048~4096 以免 skip）")
VD = "候选：机制与收益已实证（-88~-90%，但 6 次里 1 次因预算 skip）；**答案一致性未决 => 暂不采纳**，先跑 parity"
hdr = io.open(REG, encoding="utf-8-sig").read().splitlines()[0].split("\t")
row = "\t".join(["P99", "CLI", "--conversation-cache-mib", "1024", "session", "CANDIDATE",
                 "-", "-", "-", EV, VD])
assert len(row.split("\t")) == len(hdr)
io.open(REG, "w", encoding="utf-8", newline="\n").write(
    raw.decode("utf-8").rstrip("\n") + "\n" + row + "\n")
raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
print("register md5 %s -> %s | 行=%d %s | CR=%d BAN=%d"
      % (hashlib.md5(raw).hexdigest()[:12], hashlib.md5(raw2).hexdigest()[:12], len(rows) - 1, dict(st),
         raw2.count(b"\r"), sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)))
b4 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
r = subprocess.run([r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe", "-u",
                    os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gen_config rc=%d generated identical=%s" % (r.returncode, b4 == hashlib.md5(open(GEN, "rb").read()).hexdigest()))

# 推 166
b64 = base64.b64encode(raw2).decode("ascii")
s = ("set -u\nD=/home/albus/strata166/params\n"
     "cp -f $D/PARAM_REGISTER.tsv $D/PARAM_REGISTER.tsv.bak_w713b3_$(date +%%Y%%m%%d_%%H%%M%%S)\n"
     "base64 -d > $D/PARAM_REGISTER.tsv <<'__R_EOF__'\n%s\n__R_EOF__\n"
     "echo remote_md5=$(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)\n") % b64
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=120)
print(p.stdout.decode("utf-8", "replace").strip())

# 日志
io.open(os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md"), "a", encoding="utf-8", newline="\n").write("""
## W713i B3 / P31 `--conversation-cache-mib`（2026-10-08 23:29-23:40，0.1.41 / -405，Z0=off）
- **先自证测试域**：第 1 轮我用合成 `Answer:` 把上轮回答拼回单条 user 消息 => 前缀与上一轮不逐 token 一致 =>
  机制行 0 命中、追问 TTFT 不塌（两臂 12.1~12.6 s）。**据此判"测试域可能不成立"并按真实 chat messages 重跑**（本项目第三次踩这个坑，这次提前自查）。
- 第 2 轮（真实结构：`[user(doc+Q1), assistant(A1), user(Q2), ...]`）：
  **机制成立** ---- 臂 B 新增 8 行 `conversation cache:`：`parked 5529/5606/5677 tokens in 172-260 ms`、
  `restored 5477/5551 tokens (checkpoint) in 27-38 ms`；**且出现 1 次 `skip parking (snapshot 533 MiB exceeds available budget)`**。
  **体验量级收益**：追问 TTFT **12.2 s -> 1.2~1.4 s（-88%~-90%）**（6 次追问 5 次命中，1 次因预算不足回落 12.6 s）。
  => **快照约 305 -> 677 MB/会话**，1024 MiB 预算会被吃穿 => 若采纳应取 2048~4096。
- **未决（本轮不判）**：答案一致性 ---- 两臂出现"同一内容不同臂不同 md5"且呈**互换**模式；无法排除我的探针把两会话输出串位，
  也无法排除该路径确有非确定性。上游 `tools/conversation_cache_parity.py` 正是为此（会独占 GPU 顺序加载引擎，需专门窗口）。
- 处置：**register 新增 P99 `--conversation-cache-mib` = CANDIDATE**（机制+收益已实证，答案一致性未决 => 暂不采纳）；
  行数 36 -> 37 / CANDIDATE 7 -> 8；生成物**逐字节未变**；已推 166。
- 证据：`deploy/tmp/_w713_b3b_remote.log`（166 `w712/b3b.log`）；探针 `deploy/data/bench_conv.py`（真实结构版 md5 5e7d8c6b96bbfdd9b6cf1fd483c308b9）；
  脚本 `deploy/scripts/_w713_b3_convcache.sh`（md5 b5e70ebb472392c79f36213792765f24）。
""")
print("日志已追加")
