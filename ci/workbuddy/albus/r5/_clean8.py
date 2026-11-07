import subprocess, base64
def sh(s, t=400):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''python3 - <<'PY'
import json
p='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
d=json.load(open(p)); e=d.get('env',{})
for k in ('STRATA_DECODE_TIMING','STRATA_VERIFY_PROFILE','STRATA_PREFILL_TIMING'):
    e.pop(k, None)
d['env']=e
json.dump(d, open(p,'w'), indent=2, ensure_ascii=False)
print('env', sorted(e.items()))
PY''', t=120))
print(sh("docker restart strata166-407 >/dev/null 2>&1; for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo ready=${i}s; break; }; sleep 1; done", t=340))
print(sh('python3 -c "import json;print(json.load(open(\'/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json\')).get(\'env\',{}).get(\'STRATA_DECODE_TIMING\',\'ABSENT\'))"\n'
         'curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)[\'engine\'];print(\'slots\',e[\'expert_slots\'],\'vram\',e[\'vram_free_mib\'],\'ver\',e[\'version\'])"\n'
         'grep -ac "decode GPU stages" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log', t=120))
