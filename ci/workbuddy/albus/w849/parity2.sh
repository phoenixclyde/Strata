set +e
DATA=/home/albus/strata166/data
# 把脚本放进 /data（容器内可见）
cp /home/albus/strata166/data/w849_files.txt "$DATA/w849_files.txt" 2>/dev/null
echo "===== [1] 容器内逐文件 md5（脚本走 /data，不靠 stdin） ====="
docker exec strata166-407 python3 /data/w849_img_md5.py > "$DATA/w849_img.md5" 2> "$DATA/w849_img.err"
echo -n "  img md5 行数 = "; wc -l < "$DATA/w849_img.md5"
tail -2 "$DATA/w849_img.err" | sed 's/^/  /'
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
same = sum(1 for p in host if p in img and host[p] == img[p])
diff = [p for p in host if p in img and host[p] != img[p]]
miss = [p for p in host if p not in img]
print("  HEAD 树文件数        : %d" % len(host))
print("  镜像 /src 覆盖数     : %d" % len(img))
print("  两边都有且相同       : %d" % same)
print("  两边都有但不同       : %d" % len(diff))
print("  镜像里缺失           : %d" % len(miss))
for p in diff[:12]: print("    DIFF", p)
for p in miss[:12]: print("    MISS", p)
PY
