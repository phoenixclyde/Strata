#!/bin/bash
set -u
. /home/albus/strata166/ci/config.sh
H=/home/albus/strata166/gfx029-build
TS=$(date -Is)

echo "=== 0) 修前现场 ==="
md5sum $BIN/strata-0.1.55t $BIN/strata.bak-a97f4479 $BIN/strata.bak-8e92c662 | sed "s#$BIN/##"
echo "cfg exe: $(python3 -c "import json;print(json.load(open('$CFG'))['exe'])")"

echo
echo "=== 1) 建三个版本文件（一一对应，不改内容） ==="
cp -f $BIN/strata.bak-a97f4479 $BIN/strata-0.1.55u   && echo "strata-0.1.55u <- a97f4479"
cp -f $BIN/strata.bak-8e92c662 $BIN/strata-0.1.55v   && echo "strata-0.1.55v <- 8e92c662"
cp -f $BIN/strata-0.1.55t      $BIN/strata-0.1.55w   && echo "strata-0.1.55w <- cf2ba243 (was wrongly squatting on .55t)"
chmod 755 $BIN/strata-0.1.55u $BIN/strata-0.1.55v $BIN/strata-0.1.55w

echo
echo "=== 2) 把 .55t 还原成账本里那个 e0c6f250 ==="
cp -f $H/strata.bak-e0c6f250 $BIN/strata-0.1.55t && chmod 755 $BIN/strata-0.1.55t
md5sum $BIN/strata-0.1.55t

echo
echo "=== 3) 三件与账本逐一核对 ==="
for n in t u v w; do printf "%-16s %s\n" "strata-0.1.55$n" "$(md5sum $BIN/strata-0.1.55$n | cut -c1-32)"; done

echo
echo "=== 4) 补三条账本（标 retro，tag 记 - 以暴露 provenance 断裂） ==="
[ -f "$HISTORY" ] || { echo "no ledger"; exit 1; }
cp -f "$HISTORY" "$HISTORY.bak_w937"
{
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "2026-11-03T21:25:00+08:00" "strata-0.1.55u" "a97f4479eb17113d741c5362a5777b48" "89cd61d7" "d963c79145d17bb501d3f6211f966d11277c3e19" "-" "-" "-" "retro-recorded 2026-11-04T11:4x: W913 6 次重启后运行件从已删除 inode e0c6f250 切到磁盘件 a97f4479（.hip_fatbin 逐字节相同）"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "2026-11-04T09:14:00+08:00" "strata-0.1.55v" "8e92c662d8384bad585845285c3c6b9c" "fcf4df5b" "d963c79145d17bb501d3f6211f966d11277c3e19" "-" "-" "-" "retro-recorded 2026-11-04T11:4x: W935 装 5a13c34f(PLE 提限)，主线+1 补丁，零回归"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "2026-11-04T11:31:52+08:00" "strata-0.1.55w" "cf2ba243f908fe1b9d058d66b761c00f" "fcf4df5b" "d963c79145d17bb501d3f6211f966d11277c3e19" "-" "-" "-" "retro-recorded 2026-11-04T11:4x: W936 装 e1b27d54(fatal GPU 自退)+server.py 7dfcc000；主线+2 补丁"
} >> "$HISTORY"
tail -3 "$HISTORY" | cut -f1,2,3,6 | sed 's/\t/ | /g'

echo
echo "=== 5) config 的 exe 指向 w（与运行中的 cf2ba243 同一份字节） ==="
cp -f "$CFG" "$BACKUPS/$(basename "$CFG").w937_$TS" 2>/dev/null || { mkdir -p "$BACKUPS"; cp -f "$CFG" "$BACKUPS/$(basename "$CFG").w937_$TS"; }
python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
old = d["exe"]
d["exe"] = "/data/bin/strata-0.1.55w"
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("exe:", old, "->", d["exe"])
PY

echo
echo "=== 6) 证明 rollback --last 现在指向正确的那一个（dry run） ==="
bash /home/albus/strata166/ci/strata-ci rollback --last 2>&1 | head -8
