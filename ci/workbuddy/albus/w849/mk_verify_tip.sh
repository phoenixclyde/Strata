set +e
H=/home/albus/strata166/tmp/verify_tip.sh
cat > "$H" <<'EOS'
#!/bin/bash
# verify_tip.sh —— "生产是否就在分支顶端"的唯一检查（W849 立）
# 六项：① 分支/HEAD ② 工作区干净 ③ 与 origin 一致 ④ /src 逐文件 == HEAD 树 ⑤ 引擎二进制 == 构建产物 ⑥ 门禁
# 用法：bash ~/strata166/tmp/verify_tip.sh        （全部通过退出 0，否则 1）
set -u
TREE=${TREE:-/home/albus/strata166/gfx029}
C=${C:-strata166-407}
DATA=/home/albus/strata166/data
FAIL=0
say(){ printf '  %-22s %s\n' "$1" "$2"; }
bad(){ printf '  %-22s %s   <-- FAIL\n' "$1" "$2"; FAIL=1; }

cd "$TREE" || { echo "no tree"; exit 1; }

echo "== 1. 分支与提交 =="
BR=$(git rev-parse --abbrev-ref HEAD)
HEAD=$(git rev-parse HEAD)
say "branch" "$BR"
say "HEAD" "$(echo $HEAD | cut -c1-12)"
say "HEAD tree" "$(git rev-parse HEAD^{tree})"
say "upstream/main" "$(git rev-parse --short upstream/main)  ($(git log -1 --format=%s upstream/main | cut -c1-48))"
AB=$(git rev-list --left-right --count upstream/main...HEAD)
say "upstream ahead/behind" "$AB"
OB=$(git rev-list --left-right --count refs/remotes/origin/"$BR"...HEAD 2>/dev/null || echo "n/a")
say "origin ahead/behind" "$OB"
[ "$OB" = "0	0" ] || bad "origin 一致性" "$OB"

echo "== 2. 工作区 =="
D=$(git status --porcelain | wc -l)
[ "$D" = "0" ] && say "dirty" "0" || bad "dirty" "$D 个文件"

echo "== 3. /src 与 HEAD 树逐文件比对 =="
git ls-files > "$DATA/_tip_files.txt"
( while IFS= read -r f; do [ -f "$f" ] && md5sum "$f"; done < "$DATA/_tip_files.txt" ) > "$DATA/_tip_host.md5"
cat > "$DATA/_tip_img.py" <<'PY'
import hashlib, os
with open("/data/_tip_files.txt", encoding="utf-8") as fh:
    for line in fh:
        rel = line.rstrip("\n")
        if not rel: continue
        p = os.path.join("/src", rel)
        if not os.path.isfile(p): continue
        h = hashlib.md5()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
        print("%s  %s" % (h.hexdigest(), rel))
PY
docker exec "$C" python3 /data/_tip_img.py > "$DATA/_tip_img.md5" 2>/dev/null
python3 - <<'PY'
host = {}
for ln in open("/home/albus/strata166/data/_tip_host.md5", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if ln:
        h, p = ln.split("  ", 1); host[p] = h
img = {}
for ln in open("/home/albus/strata166/data/_tip_img.md5", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if ln:
        h, p = ln.split("  ", 1); img[p] = h
same = sum(1 for p in host if p in img and img[p] == host[p])
diff = [p for p in host if p in img and img[p] != host[p]]
miss = [p for p in host if p not in img]
print("  %-22s %d" % ("HEAD 文件数", len(host)))
print("  %-22s %d" % ("逐位相同", same))
print("  %-22s %d" % ("不同", len(diff)))
print("  %-22s %d" % ("镜像缺失", len(miss)))
for p in (diff + miss)[:8]: print("     ", p)
open("/home/albus/strata166/data/_tip_parity.txt","w").write("%d %d %d %d" % (len(host), same, len(diff), len(miss)))
PY
read N S DF MS < "$DATA/_tip_parity.txt"
[ "$N" = "$S" ] && [ "$DF" = "0" ] && [ "$MS" = "0" ] || bad "树==镜像" "same=$S/$N diff=$DF miss=$MS"

echo "== 4. 引擎二进制出处 =="
BIN=$(python3 -c "import json;print(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))['exe'])")
BINH=$(printf '%s' "$BIN" | sed 's#^/data/#/home/albus/strata166/data/#')
A=$(md5sum "$BINH" 2>/dev/null | cut -d' ' -f1)
B=$(md5sum /home/albus/strata166/gfx029-build/strata 2>/dev/null | cut -d' ' -f1)
say "deployed" "${A:0:16}"
say "build artifact" "${B:0:16}"
[ -n "$A" ] && [ "$A" = "$B" ] && say "一致" yes || bad "一致" no

echo "== 5. 容器/镜像 =="
say "image" "$(docker inspect "$C" --format '{{.Config.Image}}')"
say "started" "$(docker inspect "$C" --format '{{.State.StartedAt}}')"
say "restarts" "$(docker inspect "$C" --format '{{.RestartCount}}')"

echo "== 6. 门禁 =="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -2 | sed 's/^/  /'
bash /home/albus/strata166/tmp/verify_patches.sh >/dev/null 2>&1 || bad "gate" "FAIL"

echo
[ "$FAIL" = "0" ] && echo "TIP-OK  生产 = 分支顶端（$BR @ $(echo $HEAD | cut -c1-8)）" || echo "TIP-FAIL 有不合格项"
exit $FAIL
EOS
chmod +x "$H"
echo "written: $H"
