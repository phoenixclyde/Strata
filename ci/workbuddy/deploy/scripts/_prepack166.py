# -*- coding: utf-8 -*-
"""166 容器内：1) 找 PLE 表所在分片  2) 核对引擎 flag  3) 跑 iq_pack --compat-bf16 出 pack。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) PLE 表(per_layer_token_embd.weight)在哪个分片 ==="
docker exec strata166 bash -lc '
python3 - <<PYEOF
import sys, glob
sys.path.insert(0, "/src/tools")
from gguf_reader import GGUFFile
for p in sorted(glob.glob("/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-0000*-of-00004.gguf")):
    try:
        g = GGUFFile(p)
    except Exception as e:
        print("  ERR", p, e); continue
    names = [t.name for t in g.tensors]
    hits = [n for n in names if n in ("per_layer_token_embd.weight",) or "per_layer" in n]
    print("  %-58s tensors=%-5d PLE=%s" % (p.split("/")[-1], len(names), hits[:3]))
    if hits:
        for t in g.tensors:
            if t.name in hits:
                try: print("      %s  type=%s  shape=%s  bytes=%s" % (t.name, t.ggml_type_name if hasattr(t,"ggml_type_name") else "?", getattr(t,"shape",""), t.expected_bytes()))
                except Exception as e: print("      ", e)
PYEOF
' 2>&1 | sed 's/^/  /'
echo
echo "=== 2) /src/data 里有什么（expert-profile / draft_vocab）==="
docker exec strata166 ls -l /src/data 2>&1 | head -20
echo
echo "=== 3) 引擎 flag 核对（budget / mtp / spec / prefill / kv / pool）==="
docker exec strata166 bash -lc '/src/build-906/strata --help 2>&1 | grep -E -- "--resident-budget-gib|--mtp|--spec|--prefill|--kv|--pool-workers|--expert-cache\b|--adapt-every|--pcie-frac|--native|--ple|--max-context|--pack"' 2>&1 | sed 's/^/  /'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:600])
