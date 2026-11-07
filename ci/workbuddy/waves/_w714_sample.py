# 抽样哈希对账：/models 的 3 分片 与 166 现役 /weights 的 3 分片（首/中/尾各 32 MB）
import base64, hashlib, os, subprocess

WEIGHTS = "/home/albus/strata166/weights"
MODELS = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
SH = ["Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
      "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf",
      "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf"]
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

script = """set -u
for s in %s; do
  for d in %s %s; do
    f="$d/$s"
    [ -f "$f" ] || { echo "MISSING $f"; continue; }
    sz=$(stat -c %%s "$f")
    a=$(dd if="$f" bs=1M count=32 2>/dev/null | md5sum | cut -d' ' -f1)
    b=$(dd if="$f" bs=1M skip=$(( sz/1048576/2 )) count=32 2>/dev/null | md5sum | cut -d' ' -f1)
    c=$(dd if="$f" bs=1M skip=$(( sz/1048576 - 33 )) count=32 2>/dev/null | md5sum | cut -d' ' -f1)
    echo "$(basename $d) $s size=$sz head=$a mid=$b tail=$c"
  done
done
""" % (" ".join(SH), WEIGHTS, MODELS)

p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
print(out)
# 对账
rows = [l for l in out.splitlines() if " size=" in l]
import collections
groups = collections.defaultdict(dict)
for l in rows:
    parts = l.split()
    loc = parts[0]
    name = parts[1]
    kv = dict(x.split("=", 1) for x in parts[2:])
    groups[name][loc] = kv
print("=== 对账（weights vs models）===")
for name, g in groups.items():
    w, m = g.get("weights"), g.get("models")
    if not w or not m:
        print("  %-52s 有一侧缺失" % name); continue
    same = all(w[k] == m[k] for k in ("size", "head", "mid", "tail"))
    print("  %-52s %s  size %s / %s  head %s  mid %s  tail %s" %
          (name, "**相同**" if same else "**不同**", w["size"], m["size"],
           "same" if w["head"] == m["head"] else "DIFF", "same" if w["mid"] == m["mid"] else "DIFF",
           "same" if w["tail"] == m["tail"] else "DIFF"))
