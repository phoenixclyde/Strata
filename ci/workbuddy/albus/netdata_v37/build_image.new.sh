#!/bin/bash
# ============================================================================
# 构建 rk-netdata 派生镜像  —— 2026-09-22 Albus
# 166 侧位置：/home/albus/netdata/ops/build_image.sh
# 构建上下文：/home/albus/netdata/ops/image/
#   Dockerfile · entrypoint.sh · rk-health-collect.sh · assets/{gpu.html,*json}
#
# 为什么需要它（机主 2026-09-22 08:32 交办）：
#   「确保镜像更新后以上动作不用重新弄，拉起来就有；以上所有内容都在容器内解决，
#     不要在主系统留什么服务。」
#   => 采集器 / 页面 / 看板 JSON 全部固化进镜像层；宿主侧不再有 systemd timer。
#   本脚本把「打好派生镜像 + 把 recreate_netdata.sh 指向它」变成一条命令。
#
# 基础镜像按 **image ID 钉死**（不是 tag）：tag :latest 会漂，一 pull 就顺带升级
#   netdata。要升级 netdata 版本：先跑 upgrade_netdata_image.sh 换官方基础镜像，
#   再跑本脚本重建派生层。
#
# 幂等：tag 带时间戳，每次 build 产出新 tag；旧镜像保留。
# 回滚：把 recreate_netdata.sh 的 IMG= 行改回想要的 ID（本脚本改前会留 .bak_<stamp>），
#       然后 bash recreate_netdata.sh。
#
# 退出码：0 成功；2 前置缺失；3 build 失败；5 IMG 行改写失败
# ============================================================================
set -u

OPS=/home/albus/netdata/ops
CTX="$OPS/image"
REC="$OPS/recreate_netdata.sh"
STAMP=$(date +%Y%m%d_%H%M%S)
TAG="rk-netdata:$STAMP"

# ---------------------------------------------------------------- 1 前置
[ -d "$CTX" ] || { echo "FATAL: 构建上下文不存在: $CTX"; exit 2; }
for f in Dockerfile entrypoint.sh rk-health-collect.sh \
         assets/gpu.html assets/gpu-dashboard.json assets/gpu-overview-addon.json; do
  [ -s "$CTX/$f" ] || { echo "FATAL: 缺少 $CTX/$f"; exit 2; }
done
[ -s "$REC" ] || { echo "FATAL: 找不到 $REC"; exit 2; }

# [v50 2026-11-05] FROM 必须是**固定 base**，不能取运行中容器的镜像。
#   取运行镜像 => 每次构建都叠在上一份派生镜像上，层数无上限增长；本次实测叠到 125 层
#   直接 "max depth exceeded" 构建失败，而脚本照样 echo 出 TAG，recreate 仍用旧 IMG
#   => 「以为发布了，其实没发布」。现在把 base 钉在 BASE_IMAGE 文件里（一行镜像引用）。
PINNED="$OPS/BASE_IMAGE"
if [ -f "$PINNED" ] && [ -s "$PINNED" ]; then
  BASE="$(head -1 "$PINNED" | tr -d '[:space:]')"
else
  BASE="rk-netdata-base:6ac52ba4145c"      # netdata/netdata v2.11.0-151-nightly
  printf '%s\n' "$BASE" > "$PINNED"
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
if false; then
  # [!] BuildKit 的 FROM **不接受 image ID** —— 传 sha256:<id> 会被当成 registry 引用
  #   去 docker.io 解析，报 "load metadata for docker.io/library/sha256:..." 而失败
  #   （2026-09-22 实测踩过）。所以先给当前运行镜像打一个本地 tag，再用 tag 去 FROM。
  SHORT=$(printf '%s' "$BASE" | sed 's/^sha256://' | cut -c1-12)
  BASETAG="rk-netdata-base:$SHORT"
  docker tag "$BASE" "$BASETAG" >/dev/null 2>&1 || { echo "FATAL: 无法给基础镜像 $BASE 打 tag"; exit 3; }
  docker image inspect "$BASETAG" >/dev/null 2>&1 || { echo "FATAL: $BASETAG 打 tag 后仍不存在"; exit 3; }
else
  echo "WARN: 读不到运行中容器的镜像 ID（容器不在？），退回用 Dockerfile 里的 ARG 默认值。"
fi
echo "== [1/5] 构建上下文 =="
find "$CTX" -type f -printf '   %f  %s B\n' | sort
echo "   BASE(运行中容器镜像)=${BASE:-<Dockerfile 默认>}"
echo "   BASETAG(FROM 用)    =${BASETAG:-<Dockerfile 默认>}"
echo "   TAG=$TAG"

# ---------------------------------------------------------------- 2 build
echo "== [2/5] docker build =="
if [ -n "$BASETAG" ]; then
  docker build --build-arg BASE="$BASETAG" -t "$TAG" "$CTX" || { echo "FATAL: build 失败"; exit 3; }
else
  docker build -t "$TAG" "$CTX" || { echo "FATAL: build 失败"; exit 3; }
fi
NEWID=$(docker image inspect "$TAG" -f '{{.Id}}' 2>/dev/null || echo "")
if [ -z "$NEWID" ]; then echo "FATAL: build 没有产出镜像 $TAG"; exit 4; fi
LAYERS=$(docker image inspect "$TAG" -f '{{len .RootFS.Layers}}')
if [ "$LAYERS" -gt 40 ]; then
  echo "FATAL: 层数 $LAYERS 异常（FROM 又指到派生镜像了？）"; exit 4
fi
echo "   产物 $TAG => $NEWID（层数 $LAYERS）"

# ---------------------------------------------------------------- 3 指纹
# 「这镜像里到底装了什么」必须可核对，而不是凭印象 —— 审计铁律。
echo "== [3/5] 镜像内容指纹（可复算） =="
docker run --rm --entrypoint /bin/sh "$TAG" -c '
  for p in /opt/rk-health/rk-health-collect.sh /opt/rk-health/entrypoint.sh \
           /usr/share/netdata/web/custom/gpu.html \
           /usr/share/netdata/web/custom/gpu-dashboard.json \
           /usr/share/netdata/web/custom/gpu-overview-addon.json; do
    printf "   %-56s %s\n" "$p" "$(md5sum "$p" 2>/dev/null | cut -d" " -f1)"
  done
  printf "   %-56s %s\n" "netdata -v" "$(netdata -v 2>&1 | head -1)"
' || { echo "WARN: 指纹采集失败（镜像仍已构建）"; }

# ---------------------------------------------------------------- 4 指向
# 与 upgrade_netdata_image.sh 同一套手法：断言 IMG= 行恰 1 处后再改，改完核验。
echo "== [4/5] 把 recreate_netdata.sh 指向新镜像 =="
N=$(grep -c '^IMG="' "$REC" || true)
if [ "$N" != "1" ]; then echo "FATAL: $REC 的 IMG= 行数=$N（期望 1），拒绝改"; exit 5; fi
OLD=$(grep -m1 '^IMG="' "$REC" | sed 's/^IMG="\(.*\)"$/\1/')
cp -p "$REC" "$REC.bak_img_$STAMP"
sed -i 's|^IMG=".*"$|IMG="'"$NEWID"'"|' "$REC"
if ! grep -qF "$NEWID" "$REC"; then
  echo "FATAL: IMG 行改写未生效，回滚"
  cp -p "$REC.bak_img_$STAMP" "$REC"
  exit 5
fi
echo "   IMG: $OLD"
echo "     -> $NEWID"
echo "   （备份 $REC.bak_img_$STAMP）"

# ---------------------------------------------------------------- 5 记账
echo "== [5/5] 记账 =="
{
  echo "TAG=$TAG"
  echo "ID=$NEWID"
  echo "BASE=${BASE:-<dockerfile-default>}"
  echo "BUILT_AT=$STAMP"
  echo "REC_BAK=$REC.bak_img_$STAMP"
} > "$OPS/LAST_IMAGE_BUILD.txt"
cat "$OPS/LAST_IMAGE_BUILD.txt"

echo "---------------------------------------------------------------"
echo "OK: 派生镜像已就绪并已指向。下一步重建容器："
echo "  bash $OPS/recreate_netdata.sh && bash $OPS/verify_netdata.sh"
