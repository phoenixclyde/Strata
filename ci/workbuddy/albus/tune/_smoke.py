import json, urllib.request, urllib.error

body = {
    "model": "qwen3.8-flash-next-ud-iq4_xs-abliterated",
    "messages": [{"role": "user", "content": "一句话确认在线。"}],
    "max_tokens": 40,
    "temperature": 0,
}
req = urllib.request.Request(
    "http://127.0.0.1:8090/v1/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    d = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    print("reply:", d["choices"][0]["message"]["content"][:60])
    print("usage:", d.get("usage"))
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read().decode()[:300])
except Exception as e:
    print("ERR", type(e).__name__, e)
