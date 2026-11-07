#!/bin/bash
set -u
BIN=/home/albus/strata166/data/bin/strata-0.1.56-090
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
OUT=/tmp/bt2.txt
rm -f $OUT

python3 - <<'PY' &
import json,time,urllib.request,secrets
txt="prof2 "+secrets.token_hex(3)+" "+"The quick brown fox jumps over the lazy dog. "*200
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300).read()
open("/tmp/reqt2.txt","w").write("%.2f\n"%(time.time()-t))
PY
sleep 0.2
for i in $(seq 1 6); do
  echo "=== s$i ===" >> $OUT
  sudo gdb "$BIN" -p $PID -batch -ex "thread apply all bt 3" 2>/dev/null | grep -E "^#0" >> $OUT
  sleep 0.05
done
wait
echo "wall=$(cat /tmp/reqt2.txt)s"
echo "== 栈顶频次 =="
grep -E "^#0" $OUT | sed 's/^#0 *//' | sed 's/ (.*//' | sort | uniq -c | sort -rn | head -12
