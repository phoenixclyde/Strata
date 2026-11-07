cd /home/albus/strata166/pr/strata-fork || exit 1
C=strata166-407
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "===== 容器 / 镜像 ====="
docker inspect "$C" --format 'id={{.Id}} image={{.Config.Image}} imgid={{.Image}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
echo "===== 引擎 ====="
PID=$(pgrep -f strata-0.1.56-090 | head -1)
md5sum "/proc/$PID/exe" | awk '{print "running_md5=" $1}'
stat -Lc "size=%s" "/proc/$PID/exe"
EXE=$(python3 -c 'import json;print(json.load(open("'"$CFG"'"))["exe"])')
DISK=$(printf '%s' "$EXE" | sed 's#^/data/#/home/albus/strata166/data/#')
md5sum "$DISK" | awk '{print "disk_md5=" $1}'
md5sum /home/albus/strata166/build-tab/strata | awk '{print "build_md5=" $1}'
awk '/^VmLck:/{print "VmLck=" $2 " kB"}' "/proc/$PID/status"
echo "===== config ====="
md5sum "$CFG" | awk '{print "config_md5=" $1}'
python3 - "$CFG" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
a = c["args"]
print("exe=" + c["exe"])
print("args=%d env=%d" % (len(a), len(c["env"])))
print("args_list=" + " ".join(a))
print("env_list=" + " ".join(sorted(c["env"].keys())))
PY
echo "===== health / ulimit ====="
curl -s -m 5 localhost:8090/health | head -c 160; echo
docker exec "$C" bash -lc 'ulimit -l' 2>/dev/null | sed 's/^/ulimit_l=/'
echo "===== 显存布局 ====="
n=$(grep -an "engine started" "$LOG" | tail -1 | cut -d: -f1)
sed -n "${n},$((n+400))p" "$LOG" | grep -aiE "expert cache|borrows|VRAM free" | tail -3 | cut -c1-140
echo "===== git ====="
git status -sb | head -1
git describe --tags --always 2>/dev/null | sed 's/^/tag=/'
git rev-list --left-right --count '@{u}...HEAD' | awk '{print "behind=" $1 " ahead=" $2}'
git status --porcelain | wc -l | sed 's/^/dirty=/'
git log -1 --format='HEAD=%h' 
git rev-parse --short @{u} | sed 's/^/upstream_short=/'
