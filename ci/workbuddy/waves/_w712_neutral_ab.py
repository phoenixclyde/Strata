# W712 中性验证：0.1.40.4 与 0.1.40.2 背靠背同一探针 A/B（同 prompt / 同参数 / 同一天）
#   顺序： bench(404) -> switch to 402 -> bench(402) -> switch back to 404 -> 最终核验
#   探针 = /home/albus/strata166/data/bench_prefix.py 400（约 18,083 token，3 chunk）
import subprocess, base64, time

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_neutral_ab.out.txt"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

script = r"""
set -u
LOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
P=/home/albus/strata166/data/bench_prefix.py
BENCHARG=${BENCHARG:-400}

bench() {  # $1 = tag
  local tag=$1 n0
  n0=$(wc -l < "$LOG")
  echo "########## BENCH $tag ##########"
  date '+%F %T'
  docker inspect -f 'container={{.Name}} image={{.Config.Image}} started={{.State.StartedAt}}' strata166-404 2>/dev/null || true
  timeout 900 python3 -u "$P" "$tag" "$BENCHARG"
  echo "---------- engine log lines for $tag ----------"
  sed -n "$((n0+1)),\$p" "$LOG" | grep -E 'prompt [0-9]+ tokens|drafts accepted|expert cache hit|decode expert|resident RAM' | tail -n 12
}

switch_to() {  # $1 = container to run
  local want=$1 other
  if [ "$want" = "strata166-404" ]; then other=strata166-402; else other=strata166-404; fi
  echo "########## SWITCH -> $want ##########"
  docker stop -t 30 "$other" >/dev/null 2>&1 || true
  docker start "$want" >/dev/null
  local i=0
  while [ $i -lt 300 ]; do
    if [ "$(curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/v1/models 2>/dev/null)" = "200" ]; then
      echo "ready after ${i}s"; docker ps --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}'; return 0
    fi
    sleep 5; i=$((i+5))
  done
  echo "NOT READY after 300s"; return 1
}

echo "=== W712 neutrality A/B start ==="
bench 404
switch_to strata166-402    || { echo "ABORT: could not switch to 402"; exit 2; }
bench 402
switch_to strata166-404    || { echo "ABORT: could not switch back to 404"; exit 3; }
echo "########## FINAL STATE ##########"
docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}'
echo "engine cmdline:"
docker exec strata166-404 sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "$x";; esac; done' | head -1
echo "live md5: $(md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json | cut -d" " -f1)"
echo "=== W712 neutrality A/B done ==="
"""
b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
log("launching A/B (~6 min)")
p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "-o", "ServerAliveInterval=15", "albus@192.168.50.166", "base64 -d | bash"],
    input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=1200)
log("A/B ssh rc=%d" % p.returncode)
out = p.stdout.decode("utf-8", "replace")
f.write(out + "\n")
if p.stderr.strip():
    f.write("STDERR:\n" + p.stderr.decode("utf-8", "replace") + "\n")
f.close()
print(out[-5000:])
print("STDERR:", p.stderr.decode("utf-8", "replace")[-400:])
