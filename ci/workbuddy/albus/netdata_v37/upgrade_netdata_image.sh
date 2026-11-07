#!/bin/bash
# ============================================================================
# netdata 换镜像（升级 / 回退版本）—— 不动任何数据与配置  —— 2026-09-21 Albus
# 166 侧位置：/home/albus/netdata/ops/upgrade_netdata_image.sh
#
# 为什么需要它：
#   recreate_netdata.sh 里的 IMG 是**硬编码的旧镜像 ID**。直接重跑那个脚本 = 回到旧镜像
#   （静默无变化，看起来"重建成功"其实什么都没换）。本脚本把「换镜像」变成一条命令：
#       bash upgrade_netdata_image.sh netdata/netdata@sha256:<新 ID>   # 本地已有的镜像
#       bash upgrade_netdata_image.sh netdata/netdata:latest           # 没有就 docker pull
#
# [!] 2026-09-22 起本项目跑的是 **rk-netdata 派生镜像**。本脚本只负责换 netdata
#   官方基础镜像；换完**必须立刻跑 build_image.sh 重建派生层**，否则容器里没有
#   /opt/rk-health/*，采集器整个丢掉（verify_netdata.sh 的 cfile_collector 会 FAIL）。
#
# 「更新镜像后要不要重做」的答案（2026-09-22 容器化之后的现况）：
#   * **页面 / 采集器 / 看板 JSON 全部在派生镜像层里**（/opt/rk-health/* 与
#     /usr/share/netdata/web/custom/*），宿主那份 web/ 只在 RK_OVERLAY=1 时才会被采用。
#     => 换官方镜像 = 换掉整个派生层 => 必须重建，这一步**本脚本自动做**（见 [5b]）。
#   * 三个命名卷 netdataconfig / netdatalib / netdatacache 原样复用
#     => go.d.conf、nvidia_smi.conf、netdata.conf、历史数据都在
#   * 宿主侧已无任何采集服务（无 systemd timer/unit）；容器内的采集循环随容器自起
#   * routeK 探针在 /home/albus/routeK/run（宿主），由容器内的 nsenter 只读调用
#   所以「换镜像」= 重建派生层 + 重建容器；数据/配置/页面都不用人工重做。
#   末尾用 verify_netdata.sh 把这一点验成判据（含 img_selfcontained：不挂卷也能自带全部件）。
#
# 安全：改 IMG 行前先备份 + 断言"IMG= 行恰 1 处"；核验失败**不自动回滚**（避免误判导致
#       反复重建），而是打印出可直接粘贴的回滚命令。
# 退出码：0 成功且全绿；2 用法错；3 pull 失败；4 IMG 行不唯一；5 改写未生效；6 重建失败；7 核验未通过
# ============================================================================
set -u

OPS=/home/albus/netdata/ops
REC="$OPS/recreate_netdata.sh"
VER="$OPS/verify_netdata.sh"
NEW="${1:-}"

if [ -z "$NEW" ]; then
  echo "用法: bash $0 <新镜像 ID 或 tag>"
  echo "  例: bash $0 netdata/netdata@sha256:abcdef0123..."
  echo "  例: bash $0 netdata/netdata:latest          # 本地没有会先 pull"
  echo "当前脚本里的 IMG: $(grep -m1 '^IMG=' "$REC" 2>/dev/null || echo '(未找到)')"
  echo "运行中容器的镜像: $(docker inspect netdata --format '{{.Image}}' 2>/dev/null || echo '(容器不在)')"
  exit 2
fi

[ -f "$VER" ] || { echo "FATAL: 核验器不在 $VER"; exit 4; }
# [!] 换镜像会让容器丢掉整个派生层（页面/采集器/看板 JSON）。重建它需要的上下文必须**先**在，
#     否则会走到一半留下一个「官方镜像 + 没有页面」的容器。这里提前 fail-closed。
BUILD="$OPS/build_image.sh"
CTX="$OPS/image"
[ -f "$BUILD" ] || { echo "FATAL: 缺 $BUILD —— 无它则换镜像后页面与采集器全丢，拒绝执行"; exit 4; }
for f in Dockerfile entrypoint.sh rk-health-collect.sh \
         assets/gpu.html assets/gpu-dashboard.json assets/gpu-overview-addon.json; do
  [ -s "$CTX/$f" ] || { echo "FATAL: 构建上下文缺 $CTX/$f（派生层无法重建），拒绝执行"; exit 4; }
done

STAMP=$(date +%Y%m%d_%H%M%S)

# ---------------------------------------------------------------- 1 新镜像就位
if ! docker image inspect "$NEW" >/dev/null 2>&1; then
  echo "[1/6] 本地无此镜像，尝试 pull: $NEW"
  docker pull "$NEW" || { echo "FATAL: pull 失败"; exit 3; }
fi
NEWID=$(docker image inspect "$NEW" --format '{{.Id}}')
echo "[1/6] 新镜像 ID = $NEWID"

# ---------------------------------------------------------------- 2 幂等
CUR=$(docker inspect netdata --format '{{.Image}}' 2>/dev/null || echo '(容器不在)')
CURIMG=$(grep -m1 '^IMG=' "$REC" | sed 's/^IMG="\(.*\)"$/\1/')
echo "[2/6] 运行中容器镜像 = $CUR"
echo "      脚本里的 IMG   = $CURIMG"
if [ "$NEWID" = "$CUR" ] && [ "$NEWID" = "$CURIMG" ]; then
  echo "SKIP: 新镜像与当前完全相同，不重建。只跑一次核验："
  bash "$VER"
  exit $?
fi

# ---------------------------------------------------------------- 3 改前存档
bash "$VER" "$OPS/verify_before_upgrade_$STAMP.txt" >/dev/null 2>&1 || true
docker inspect netdata > "$OPS/inspect_before_upgrade_$STAMP.json" 2>/dev/null || true
cp -p "$REC" "$REC.bak_$STAMP"
echo "[3/6] 改前存档: verify_before_upgrade_$STAMP.txt / inspect_before_upgrade_$STAMP.json"

# ---------------------------------------------------------------- 4 原子改写 IMG 行
N=$(grep -c '^IMG="' "$REC" || true)
if [ "$N" != "1" ]; then echo "FATAL: IMG= 行数=$N（期望 1），拒绝改"; exit 4; fi
sed -i 's|^IMG=".*"$|IMG="'"$NEWID"'"|' "$REC"
AFTER=$(grep -m1 '^IMG=' "$REC")
echo "[4/6] IMG 行改写为: $AFTER"
if ! grep -qF "$NEWID" "$REC"; then
  echo "FATAL: 改写未生效，回滚脚本文件"
  cp -p "$REC.bak_$STAMP" "$REC"
  exit 5
fi

# ---------------------------------------------------------------- 5 重建（两段）
# [5a] 先用**新官方镜像**把容器落下来。
#      为什么要落一次：build_image.sh 的 FROM 取的是「**运行中容器**的镜像」
#      （BASETAG=$(docker inspect netdata .Image)），不落这一步它会拿旧基础镜像去构建，
#      你以为升级了、其实没有（这是 build_image 的既有约定，不改它）。
echo "[5/9] [5a] 用新官方镜像重建容器（此刻页面/采集器暂时缺失，下一步补回来）..."
bash "$REC" || { echo "FATAL: 重建失败（脚本文件已备份在 $REC.bak_$STAMP）"; exit 6; }

# [5b] 重建派生层：把页面/采集器/看板 JSON 重新打进去，并把 recreate 的 IMG 指回派生镜像。
echo "[6/9] [5b] 重建派生层（页面 + 采集器 + 看板 JSON 进镜像）..."
bash "$BUILD" || {
  echo "FATAL: 派生层构建失败。当前容器跑的是**没有页面的官方镜像**。"
  echo "       回滚：cp -p $REC.bak_$STAMP $REC && bash $REC"
  exit 6
}

# [5c] 用派生镜像再落一次容器（此时页面/采集器都在）。
echo "[7/9] [5c] 重建容器（落派生镜像）..."
bash "$REC" || { echo "FATAL: 重建派生容器失败（备份 $REC.bak_$STAMP）"; exit 6; }

# ---------------------------------------------------------------- 6 核验
echo "[8/9] 核验（含 img_selfcontained：不挂卷也自带页面/采集器）..."
bash "$VER" "$OPS/verify_after_upgrade_$STAMP.txt"
RC=$?
if [ "$RC" != "0" ]; then
  echo "############################################################"
  echo "核验未通过。回滚到旧镜像："
  echo "  sed -i 's|^IMG=.*|IMG=\"$CURIMG\"|' $REC"
  echo "  bash $REC"
  echo "或一步到位："
  echo "  cp -p $REC.bak_$STAMP $REC && bash $REC"
  echo "报告：$OPS/verify_after_upgrade_$STAMP.txt"
  echo "############################################################"
  exit 7
fi
echo "OK: 基础镜像已更新为 $NEWID，派生层已自动重建并落位，核验全绿。"
echo "    页面与采集器都在镜像里（/usr/share/netdata/web/custom、/opt/rk-health），宿主零服务。"
echo "报告：$OPS/verify_after_upgrade_$STAMP.txt"
