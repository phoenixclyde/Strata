#!/bin/bash
# 穷人的采样 profiler：gdb 反复 attach，取每线程栈顶
set -u
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
OUT=/tmp/bt.txt
rm -f $OUT

python3 - <<'PY' &
import json,time,urllib.request,secrets
txt="prof "+secrets.token_hex(3)+" "+"The quick brown fox jumps over the lazy dog. "*200
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300).read()
open("/tmp/reqt.txt","w").write("%.2f\n"%(time.time()-t))
PY
REQ=$!
sleep 0.2
for i in $(seq 1 8); do
  echo "=== sample $i ===" >> $OUT
  sudo gdb -p $PID -batch -ex "thread apply all bt 3" 2>/dev/null | grep -E "^#0|^Thread" >> $OUT
  sleep 0.05
done
wait $REQ
echo "request wall: $(cat /tmp/reqt.txt)s"
echo "=== 栈顶函数频次（前 15）==="
grep -E "^#0" $OUT | sed 's/^#0 *//' | sed 's/ (.*//' | sed 's/^0x[0-9a-f]* in //' | sort | uniq -c | sort -rn | head -15
echo "=== 线程数每次 ==="
grep -c "^Thread" $OUT
