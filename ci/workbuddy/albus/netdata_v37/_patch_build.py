# -*- coding: utf-8 -*-
"""把 build_image.sh 的 FROM 从「运行中的派生镜像」改成**固定的基础镜像**。
不改的后果（本次实测）：每次构建 = 上一次派生镜像 + N 层，今天叠到 125 层触发
  ERROR: failed to prepare ... max depth exceeded
构建静默失败，TAG 已 echo 出来但镜像没生成，recreate 仍用旧 IMG => 「以为部署了，其实没部署」。
"""
import io, hashlib, sys

sys.path.insert(0, r"D:/workbuddy_space/strata_ws/albus/netdata_v37")
from sshrun import run

P = "/home/albus/netdata/ops/build_image.sh"
rc, s, _ = run("cat " + P, timeout=60)
assert rc == 0 and len(s) > 1000, (rc, len(s))
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

OLD = '''BASE=$(docker inspect netdata -f '{{.Image}}' 2>/dev/null || echo "")
BASETAG=""
if [ -n "$BASE" ]; then'''

NEW = '''# [v50 2026-11-05] FROM 必须是**固定 base**，不能取运行中容器的镜像。
#   取运行镜像 => 每次构建都叠在上一份派生镜像上，层数无上限增长；本次实测叠到 125 层
#   直接 "max depth exceeded" 构建失败，而脚本照样 echo 出 TAG，recreate 仍用旧 IMG
#   => 「以为发布了，其实没发布」。现在把 base 钉在 BASE_IMAGE 文件里（一行镜像引用）。
PINNED="$OPS/BASE_IMAGE"
if [ -f "$PINNED" ] && [ -s "$PINNED" ]; then
  BASE="$(head -1 "$PINNED" | tr -d '[:space:]')"
else
  BASE="rk-netdata-base:6ac52ba4145c"      # netdata/netdata v2.11.0-151-nightly
  printf '%s\\n' "$BASE" > "$PINNED"
fi
echo "   BASE_IMAGE(固定) = $BASE  （升级底座请改 $PINNED）"
BASETAG=""
case "$BASE" in
  sha256:*|"")
    if [ -n "$BASE" ]; then
      SHORT=$(printf '%s' "$BASE" | sed 's/^sha256://' | cut -c1-12)
      BASETAG="rk-netdata-base:$SHORT"
      docker tag "$BASE" "$BASETAG" >/dev/null 2>&1 || { echo "FATAL: 无法给基础镜像 $BASE 打 tag"; exit 3; }
    else
      echo "FATAL: BASE_IMAGE 为空"; exit 3
    fi ;;
  *)
    BASETAG="$BASE" ;;
esac
if [ -n "$BASETAG" ]; then
  docker image inspect "$BASETAG" >/dev/null 2>&1 || { echo "FATAL: FROM 用的 $BASETAG 不存在"; exit 3; }
fi
if false; then'''

assert s.count(OLD) == 1, s.count(OLD)
s = s.replace(OLD, NEW)

# 构建失败必须能被上层看到：给 build 加 --progress=plain 不收，改为构建后校验产物存在且层数有界
OLD2 = '''NEWID=$(docker image inspect "$TAG" -f '{{.Id}}')
echo "   产物 $TAG => $NEWID"'''
NEW2 = '''NEWID=$(docker image inspect "$TAG" -f '{{.Id}}' 2>/dev/null || echo "")
if [ -z "$NEWID" ]; then echo "FATAL: build 没有产出镜像 $TAG"; exit 4; fi
LAYERS=$(docker image inspect "$TAG" -f '{{len .RootFS.Layers}}')
if [ "$LAYERS" -gt 40 ]; then
  echo "FATAL: 层数 $LAYERS 异常（FROM 又指到派生镜像了？）"; exit 4
fi
echo "   产物 $TAG => $NEWID（层数 $LAYERS）"'''
assert s.count(OLD2) == 1, s.count(OLD2)
s = s.replace(OLD2, NEW2)

if crlf:
    s = s.replace("\n", "\r\n")
data = s.encode("utf-8")
loc = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/build_image.new.sh"
io.open(loc, "wb").write(data)
from sshrun import push
push(loc, P)
rc, out, err = run("bash -n " + P + " && echo BASH_OK && wc -c " + P, timeout=60)
print(out, err)
