import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil
S = r'''
C=strata166-407
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
R=/home/albus/strata166/pr/k10
echo "container=$(docker inspect -f '{{.Id}}' $C | cut -c1-12)"
echo "state=$(docker inspect -f '{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}' $C)"
echo "image=$(docker inspect -f '{{.Config.Image}}' $C)"
echo "engine=$(pgrep -a -x strata-host | awk '{print $2}')"
echo "engine_md5=$(docker exec $C md5sum /data/bin/strata-0.1.57-attn | cut -d' ' -f1)"
echo "engine_size=$(docker exec $C stat -c%s /data/bin/strata-0.1.57-attn)"
echo "cfg=$(md5sum $CFG | cut -d' ' -f1)"
python3 -c "import json;d=json.load(open('$CFG'));print('cfg_exe='+d['exe'],'args='+str(len(d['args'])),'env='+str(len(d['env'])))"
echo "health=$(curl -s -m 8 localhost:8090/health | head -c 120)"
echo "memlock=$(docker inspect -f '{{.HostConfig.Ulimits}}' $C)"
echo "vram=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i 'used\|total' | head -2 | tr '\n' ' ')"
echo "slots=$(grep -a 'expert cache [0-9]* slots' $L | tail -1 | cut -c1-140)"
echo "borrows=$(grep -a 'borrows' $L | tail -1 | cut -c1-150)"
echo "kv=$(grep -a 'elastic K/V' $L | tail -1 | cut -c1-160)"
echo "errs=$(grep -ac 'could not map\|ERR the K/V could not' $L)"
echo "bin_count=$(ls -1 /home/albus/strata166/data/bin | grep -c 'strata-0.1')"
echo "tree=$(cd $R && echo $(git rev-parse --abbrev-ref HEAD)@$(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l))"
echo "hc4=$(md5sum /home/albus/strata166/data/bin/strata-0.1.57-hc4 | cut -d' ' -f1)"
'''
rc, out, err = _sshutil.run_remote(S, timeout=180)
print(out)
if err.strip(): print("ERR", err[-800:])
raise SystemExit(rc)
