import urllib.request, json, os, hashlib, time

BASE = "http://192.168.50.166:19999"
OUT = os.path.dirname(os.path.abspath(__file__))

def get(path, timeout=12):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "albus-probe"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def save(name, data):
    p = os.path.join(OUT, name)
    with open(p, "wb") as f:
        f.write(data)
    print("%-28s %8d  %s" % (name, len(data), hashlib.md5(data).hexdigest()))
    return p

for name, path in [
    ("gpu.html", "/custom/gpu.html"),
    ("health.json", "/custom/health.json"),
    ("contexts.json", "/api/v3/contexts"),
    ("info.json", "/api/v1/info"),
    ("alarms.json", "/api/v1/alarms?all"),
]:
    try:
        save(name, get(path))
    except Exception as e:
        print("%-28s ERR %s" % (name, e))

# 只留需要的 charts 描述，避免几十 MB
try:
    ch = json.loads(get("/api/v1/charts", 30))
    keep = ("sensors.", "disk.", "system.", "amd", "cpu.", "mem.", "nvidia_smi.", "net.", "systemd", "zram", "bcache", "smartd", "hdparm", "nvme", "io.")
    slim = {k: v for k, v in ch["charts"].items() if k.lower().startswith(keep)}
    with open(os.path.join(OUT, "charts_slim.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)
    print("charts_slim.json   %d / %d charts" % (len(slim), len(ch["charts"])))
except Exception as e:
    print("charts ERR", e)
print("now", time.strftime("%Y-%m-%d %H:%M:%S"))
