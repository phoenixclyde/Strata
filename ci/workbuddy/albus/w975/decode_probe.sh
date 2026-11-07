#!/bin/bash
# decode 基线：短 prompt + 128 token 生成，取最稳的一次
set -u
python3 - <<'PY'
import json,time,urllib.request
for i in range(3):
    txt="decode probe %d. Explain in one paragraph why a cache hierarchy matters."%i
    body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":128,"temperature":0.0}).encode()
    t0=time.time()
    r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
    u=r["usage"]; dt=time.time()-t0
    print("  run%d wall=%.2fs prompt=%d out=%d  %.2f tok/s"%(i+1,dt,u["prompt_tokens"],u["completion_tokens"],u["completion_tokens"]/dt))
PY
grep -oE "decode timing: 4 windows.*" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -1 | cut -c1-150
