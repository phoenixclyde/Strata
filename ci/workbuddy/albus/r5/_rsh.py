import subprocess, base64, os
HOST = "albus@192.168.50.166"

def sh(s, t=120):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8", "replace")

def push(local, remote, t=60):
    pl = base64.b64encode(open(local, "rb").read()).decode("ascii")
    return sh("echo '%s' | base64 -d > %s && echo OK" % (pl, remote), t=t)

def cfg(args=None, env=None, unset=(), path="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"):
    """Patch the model config in place; returns the resulting env/args summary."""
    py = r'''
import json, sys
p = "%s"
d = json.load(open(p))
for k in %r:
    d.get("env", {}).pop(k, None)
for k, v in (%r or {}).items():
    d.setdefault("env", {})[k] = v
if %r is not None:
    d["args"] = %r
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("env_n=%%d args=%%s" %% (len(d.get("env", {})), json.dumps(d.get("args"), ensure_ascii=False)))
''' % (path, list(unset), env or {}, args, args)
    pl = base64.b64encode(py.encode()).decode("ascii")
    return sh("echo '%s' | base64 -d > /tmp/_cfg.py && python3 /tmp/_cfg.py" % pl, t=60)

def restart(wait=300):
    return sh("docker restart strata166-407 >/dev/null 2>&1; "
              "for i in $(seq 1 %d); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && "
              "{ echo ready=${i}s; break; }; sleep 1; done" % wait, t=wait + 30)
