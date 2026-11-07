set +e
python3 - <<'PY'
import json, time, urllib.request
def ask(text, mt):
    body = {"messages":[{"role":"user","content":text}],"max_tokens":mt,"temperature":0,"seed":7}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type":"application/json"})
    t0=time.time(); r=urllib.request.urlopen(req,timeout=600); j=json.load(r)
    u=j.get("usage") or {}
    return time.time()-t0, u.get("completion_tokens"), u.get("prompt_tokens")
P="请用一段话描写秋天，要求语句连贯、不少于一百字。"
for i in range(2):
    a=ask(P,8); b=ask(P,264)
    dt=b[0]-a[0]; dn=(b[1] or 0)-(a[1] or 0)
    print("arm%d  short %.2fs/%s tok  long %.2fs/%s tok  => 纯解码 %.1f tok/s  (%.2f ms/tok)"
          % (i,a[0],a[1],b[0],b[1],dn/dt,1000*dt/dn))
# TTFT on a fresh ~8k prompt
pad="甲乙丙丁戊己庚辛壬癸"*800
t0=time.time(); r=urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8090/v1/chat/completions",
    data=json.dumps({"messages":[{"role":"user","content":pad+"\n请只回答一个字。"}],"max_tokens":1,"temperature":0}).encode(),
    headers={"Content-Type":"application/json"}),timeout=600)
j=json.load(r); w=time.time()-t0; pt=(j.get("usage") or {}).get("prompt_tokens")
print("TTFT  prompt_tokens=%s  wall=%.2fs  => %.1f tok/s prefill" % (pt,w,(pt or 0)/w))
PY
echo "=== 缓存分配/槽位 ==="
docker exec strata166-407 bash -lc "grep -aiE 'conversation cache|slot size|3 MiB|per slot' /data/strata-huihui-ud-iq4_xs.log | tail -5"
