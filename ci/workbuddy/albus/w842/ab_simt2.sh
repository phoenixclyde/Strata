#!/bin/bash
# W842: R1 臂组 —— STRATA_SELECT_SIMT=2（移植上游 #3073）在 gfx906 上到底有没有用
#   臂：A = n3 + SIMT=1（现生产）｜A2 = n4 + SIMT=1（零副作用对照）｜B = n4 + SIMT=2
#   判据：read 1958/3718/6666/24000 的 ms（引擎日志 `read in`）+ decode 的 ms/win
#   纪律：无论成败恢复生产（trap EXIT）
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
# 注意：config 里的 exe 必须是**容器内路径** /data/...（用宿主路径会让启动器 FileNotFoundError）
B3=/data/bin/strata-0.1.54n3
B4=/data/bin/strata-0.1.54n4
H3=$DATA/bin/strata-0.1.54n3
H4=$DATA/bin/strata-0.1.54n4
BUILD=/home/albus/strata166/src028/build-028r/strata
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w842_simt2_$STAMP.txt
ARMS=${*:-"A A2 B"}

cp -a "$BUILD" "$H4" || exit 1
chmod +x "$H4"
docker exec "$C" test -x "$B4" || { echo "PREFLIGHT FAIL: $B4 容器内不可执行" | tee -a "$OUT"; exit 1; }
echo "[deploy] n4 容器内路径=$B4 md5=$(md5sum $H4 | cut -d' ' -f1)  build md5=$(md5sum $BUILD | cut -d' ' -f1)" | tee -a "$OUT"
cp "$CFG" /tmp/w842_prod.json

restore() {
  cp /tmp/w842_prod.json "$CFG" 2>/dev/null
  docker restart "$C" >/dev/null 2>&1
  for i in $(seq 1 420); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored $(date +%H:%M:%S)" >> "$OUT"
}
trap restore EXIT

setcfg() {  # $1=exe $2=simt("" = 不设)
  python3 - "$CFG" "$1" "$2" <<'PYX'
import json, sys
cfg, exe, simt = sys.argv[1], sys.argv[2], sys.argv[3]
base = json.load(open("/tmp/w842_prod.json"))
d = dict(base)
d["exe"] = exe
e = dict(base.get("env") or {})
if simt == "":
    e.pop("STRATA_SELECT_SIMT", None)
else:
    e["STRATA_SELECT_SIMT"] = simt
d["env"] = e
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  cfg exe=%s simt=%s env_n=%d args_n=%d" % (exe.split("/")[-1], simt or "-", len(e), len(d.get("args") or [])))
PYX
}

run() {  # $1=arm $2=exe $3=simt
  local arm=$1 exe=$2 simt=$3
  setcfg "$exe" "$simt" >> "$OUT"
  docker restart "$C" >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
    [ "$i" -gt 25 ] && docker ps --format "{{.Status}}" | grep -q "^Restarting" && { echo "  ABORT: container restarting (i=$i)" >> "$OUT"; break; }
    sleep 1; done
  [ "$ok" = "0" ] && { echo "  ABORT arm $arm: 未就绪" >> "$OUT"; return 1; }
  local mark
  mark=$(docker exec "$C" bash -lc "wc -l < $LOG")
  echo "=== ARM $arm exe=$(basename $exe) SIMT=${simt:-unset} ready=${ok}s $(date +%H:%M:%S)" >> "$OUT"
  # 选路自证：哪个 scorer 真的被选中
  docker exec "$C" bash -lc "grep -a 'qsa select' $LOG | tail -2" | sed 's/^/  SEL /' >> "$OUT"
  # read 四档（新容器必须 >=2 预热）
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$arm" "$DATA/w842_read_$arm.json" 3718,6666,24000 2 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
  # decode（三条 prompt，200 token）
  ( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 "$arm" "$DATA/w842_gen_$arm.json" dec_corpus.json 200 3 ) >> "$OUT" 2>&1
  # 引擎自己的 read 行（真值）
  docker exec "$C" bash -lc "tail -n +$((mark+1)) $LOG | grep -aE 'read in [0-9]+ ms'" | tail -8 | sed 's/^/  READ /' >> "$OUT"
  # decode 相位（ms/window）
  docker exec "$C" bash -lc "tail -n +$((mark+1)) $LOG | grep -aE 'strata decode timing|drafts accepted'" | tail -6 | cut -c1-190 | sed 's/^/  DT /' >> "$OUT"
  curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  ENGINE slots=%d vram_free=%d pcie_frac=%s' % (e['expert_slots'], e['vram_free_mib'], e.get('pcie_frac')))" >> "$OUT" 2>&1
  echo >> "$OUT"
}

echo "# W842 SIMT=2 臂组 $STAMP arms='$ARMS'" >> "$OUT"
for a in $ARMS; do
  case "$a" in
    A)  run A  "$B3" "1" ;;
    A2) run A2 "$B4" "1" ;;
    B)  run B  "$B4" "2" ;;
    *)  echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

# 收尾：生产指回 n4 + 不显式设 SIMT（引擎配方给 1，行为与实验前等价；同时让 PROVENANCE 门禁变绿）
setcfg "$B4" "" >> "$OUT"
docker restart "$C" >/dev/null 2>&1
for i in $(seq 1 420); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored-prod(n4,SIMT=配方1) ${i}s $(date +%H:%M:%S)" >> "$OUT"; break; }; sleep 1; done
trap - EXIT
echo "== DONE $OUT"
