# 查 huihui 的 abliterated 模型到底在哪能下：ModelScope 详情/文件列表 API + hf-mirror 兜底
import json, urllib.request, urllib.parse, time

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "Mozilla/5.0 (curl/8.0)"), ("Accept", "application/json")]


def get(label, url, timeout=25, data=None, hdrs=None):
    req = urllib.request.Request(url, data=data, headers=hdrs or {})
    t0 = time.time()
    try:
        with op.open(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        print("== %-46s OK  %5.1fs  %d B" % (label, time.time() - t0, len(body)))
        return body
    except Exception as e:
        print("== %-46s ERR %5.1fs  %r" % (label, time.time() - t0, e))
        return None


MS = "https://www.modelscope.cn/api/v1/models/"
repos = [
    "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated",
    "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF",
    "orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF",
    "orcarouter/Qwen3.8-Flash-Next-Uncensored",
]
print("### A) ModelScope 仓库详情（有就是有镜像）")
for r in repos:
    b = get("MS detail " + r, MS + r)
    if b:
        try:
            j = json.loads(b)
            d = j.get("Data") or j
            print("      Name=%s  Downloads=%s  License=%s  Gated=%s" %
                  (d.get("Name"), d.get("Downloads"), d.get("License"), d.get("Gated")))
        except Exception:
            print("      (非 JSON)", b[:200])

print()
print("### B) ModelScope 文件列表（要 size / sha256）")
for r in ["huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated",
          "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF"]:
    b = get("MS files " + r, MS + r + "/repo/files?Revision=master")
    if b:
        try:
            j = json.loads(b)
            fs = (j.get("Data") or {}).get("Files") or []
            print("      文件 %d 个：" % len(fs))
            for f in fs[:25]:
                print("        %-58s %14s  sha256=%s" %
                      (f.get("Path"), f.get("Size"), str(f.get("Sha256") or f.get("Hash"))[:16]))
        except Exception:
            print("      (非 JSON)", b[:200])

print()
print("### C) hf-mirror 兜底（本机若能通，可读 HF 的仓元数据）")
for u in ["https://hf-mirror.com/api/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF",
          "https://hf-mirror.com/api/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated"]:
    b = get("hf-mirror " + u.split("models/")[-1][:40], u)
    if b:
        print("      ", b[:300])

print()
print("### D) ModelScope 搜索（POST 形态）")
post = json.dumps({"PageSize": 20, "PageNumber": 1, "Name": "Flash-Next"}).encode()
for u in ["https://www.modelscope.cn/api/v1/dolphin/models",
          "https://www.modelscope.cn/api/v1/models"]:
    b = get("MS search POST " + u.split("/api")[-1], u, data=post,
            hdrs={"Content-Type": "application/json"})
    if b:
        print("      ", b[:400])
