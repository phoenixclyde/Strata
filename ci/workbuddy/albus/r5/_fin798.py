import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166-407
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 45; echo
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])"
echo "env_n=$(python3 -c "import json;print(len(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{})))")"
echo "gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor) residual=$(ps -ef | grep -cE '[a]b_p8|[m]t_decode|[m]t_phase')"
'''))
