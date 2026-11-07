set +e
D=/home/albus/strata166/gfx029
DATA=/home/albus/strata166/data
cd "$D" || exit 1
git ls-files > "$DATA/w849_files.txt"
echo -n "tracked files = "; wc -l < "$DATA/w849_files.txt"
echo "===== [1] 宿主编译树（= HEAD 工作区）逐文件 md5 ====="
( cd "$D" && while IFS= read -r f; do [ -f "$f" ] && md5sum "$f"; done < "$DATA/w849_files.txt" ) > "$DATA/w849_host.md5"
echo -n "  host md5 行数 = "; wc -l < "$DATA/w849_host.md5"
echo "===== [2] 容器 /src 逐文件 md5 ====="
docker exec strata166-407 python3 - <<'PY' > "$DATA/w849_img.md5" 2>"$DATA/w849_img.err"
import hashlib, os
n = 0
with open("/data/w849_files.txt", encoding="utf-8") as fh:
    for line in fh:
        rel = line.rstrip("\n")
        if not rel:
            continue
        p = os.path.join("/src", rel)
        if not os.path.isfile(p):
            continue
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        print("%s  %s" % (h.hexdigest(), rel))
        n += 1
import sys
print("count=%d" % n, file=sys.stderr)
PY
echo -n "  img md5 行数 = "; wc -l < "$DATA/w849_img.md5"
cat "$DATA/w849_img.err" | tail -2 | sed 's/^/  /'
echo "===== [3] 比对 ====="
python3 - <<'PY'
host = {}
for ln in open("/home/albus/strata166/data/w849_host.md5", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if not ln: continue
    h, p = ln.split("  ", 1)
    host[p] = h
img = {}
for ln in open("/home/albus/strata166/data/w849_img.md5", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if not ln: continue
    h, p = ln.split("  ", 1)
    img[p] = h
same = sum(1 for p in host if p in img and host[p] == img[p])
diff = [p for p in host if p in img and host[p] != img[p]]
miss = [p for p in host if p not in img]
print("  两边都有且相同 : %d" % same)
print("  两边都有但不同 : %d" % len(diff))
print("  镜像里缺失     : %d" % len(miss))
for p in diff[:10]: print("    DIFF", p)
for p in miss[:10]: print("    MISS", p)
PY
