set +e
DATA=/home/albus/strata166/data
cat > "$DATA/w849_img_md5.py" <<'PY'
import hashlib, os, sys
count = 0; missing = 0
with open("/data/w849_files.txt", encoding="utf-8") as fh:
    for line in fh:
        rel = line.rstrip("\n")
        if not rel: continue
        p = os.path.join("/src", rel)
        if not os.path.isfile(p):
            missing += 1; continue
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        print("%s  %s" % (h.hexdigest(), rel)); count += 1
print("count=%d missing=%d" % (count, missing), file=sys.stderr)
PY
echo "===== [1] 容器内逐文件 md5 ====="
docker exec strata166-407 python3 /data/w849_img_md5.py > "$DATA/w849_img.md5" 2> "$DATA/w849_img.err"
echo -n "  img md5 行数 = "; wc -l < "$DATA/w849_img.md5"
tail -1 "$DATA/w849_img.err" | sed 's/^/  /'
echo "===== [2] 比对 ====="
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
same = sum(1 for p in host if p in img and img[p] == host[p])
diff = [p for p in host if p in img and img[p] != host[p]]
miss = [p for p in host if p not in img]
print("  HEAD 树文件数    : %d" % len(host))
print("  镜像覆盖数       : %d" % len(img))
print("  相同             : %d" % same)
print("  不同             : %d" % len(diff))
print("  镜像缺失         : %d" % len(miss))
for p in diff[:12]: print("    DIFF", p)
for p in miss[:12]: print("    MISS", p)
PY
