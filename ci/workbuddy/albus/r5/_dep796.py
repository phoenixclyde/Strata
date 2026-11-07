import subprocess, base64, hashlib
HOST="albus@192.168.50.166"
GEN=r"D:/workbuddy_space/strata_ws/deploy/params/generated/strata-huihui-ud-iq4_xs.json"
REMOTE="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
def sh(s, t=300):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
raw=open(GEN,'rb').read(); pl=base64.b64encode(raw).decode("ascii")
print("local md5", hashlib.md5(raw).hexdigest())
print(sh("ts=$(date +%Y%m%d_%H%M%S); cp -f " + REMOTE + " " + REMOTE + ".bak_w796_$ts && echo bak_w796_$ts; "
         "echo '" + pl + "' | base64 -d > " + REMOTE + ".tmp && mv " + REMOTE + ".tmp " + REMOTE + " && md5sum " + REMOTE, t=120))
print(sh("docker restart strata166-407 >/dev/null 2>&1; for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo ready=${i}s; break; }; sleep 1; done", t=330))
print(sh('curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)[\'engine\'];print(\'slots\',e[\'expert_slots\'],\'vram\',e[\'vram_free_mib\'],\'ver\',e[\'version\'])"\n'
         'python3 -c "import json;print(sorted(json.load(open(\'' + REMOTE + '\')).get(\'env\',{}).items()))"\n'
         'grep -a "qsa select:" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2', t=120))
