import subprocess, base64
def sh(s, t=115):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
for k in 1 2 3; do python3 - <<'PY'
import json, urllib.request, hashlib
body = {"model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
        "messages": [{"role": "user", "content": "请只回答两个字：好的"}],
        "max_tokens": 8, "temperature": 0}
req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as r:
    m = json.loads(r.read().decode())["choices"][0]["message"]
txt = (m.get("content") or "") + "|" + (m.get("reasoning_content") or "")
print("det_sha16=%s len=%d %r" % (hashlib.sha256(txt.encode()).hexdigest()[:16], len(txt), txt[:40]))
PY
done
''', t=110))
