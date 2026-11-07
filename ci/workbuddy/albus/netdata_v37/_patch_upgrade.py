# -*- coding: utf-8 -*-
"""upgrade_netdata_image.sh：把「换官方基础镜像」补成**自动重建派生层**的完整动作。
原来的坑（脚本头注释自己写了）：换完基础镜像后必须**手工**再跑 build_image.sh，
否则容器里 /opt/rk-health/* 与 custom/gpu.html 全没了 —— 页面直接 404。
机主 2026-11-05 要求「更新镜像时都不影响」，那就不能靠人记得。
"""
import io, hashlib, shutil, time

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/upgrade_netdata_image.sh"
s = io.open(P, encoding="utf-8").read()
bak = P + ".bak_v37_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copyfile(P, bak)

pairs = []

# A) 更正过时的「页面在宿主目录」叙述
old_a = '''# 「更新镜像后要不要重做」的答案（本脚本依赖的既有事实，均已实测）：
#   * 三个命名卷 netdataconfig / netdatalib / netdatacache 原样复用
#     => 容器内 /etc/netdata（go.d.conf、go.d/nvidia_smi.conf、netdata.conf）与历史数据都在
#   * 14 条 bind 由 recreate_netdata.sh 复刻
#     => gpu.html / health.json / 采集器 / 看板 JSON 都在宿主目录，根本不在镜像里
#   * rk-health-collector.{service,timer} 在宿主 /etc/systemd/system，与容器无关
#   * routeK 探针在 /home/albus/routeK/run，与容器无关
#   所以正常情况**不需要重做任何东西**；本脚本末尾会用 verify_netdata.sh 把这一点验成判据。'''
new_a = '''# 「更新镜像后要不要重做」的答案（2026-09-22 容器化之后的现况）：
#   * **页面 / 采集器 / 看板 JSON 全部在派生镜像层里**（/opt/rk-health/* 与
#     /usr/share/netdata/web/custom/*），宿主那份 web/ 只在 RK_OVERLAY=1 时才会被采用。
#     => 换官方镜像 = 换掉整个派生层 => 必须重建，这一步**本脚本自动做**（见 [5b]）。
#   * 三个命名卷 netdataconfig / netdatalib / netdatacache 原样复用
#     => go.d.conf、nvidia_smi.conf、netdata.conf、历史数据都在
#   * 宿主侧已无任何采集服务（无 systemd timer/unit）；容器内的采集循环随容器自起
#   * routeK 探针在 /home/albus/routeK/run（宿主），由容器内的 nsenter 只读调用
#   所以「换镜像」= 重建派生层 + 重建容器；数据/配置/页面都不用人工重做。
#   末尾用 verify_netdata.sh 把这一点验成判据（含 img_selfcontained：不挂卷也能自带全部件）。'''
pairs.append(("A", old_a, new_a))

# B) 前置：派生层构建上下文必须在，否则重建完就是残的
old_b = '''[ -f "$VER" ] || { echo "FATAL: 核验器不在 $VER"; exit 4; }'''
new_b = '''[ -f "$VER" ] || { echo "FATAL: 核验器不在 $VER"; exit 4; }
# [!] 换镜像会让容器丢掉整个派生层（页面/采集器/看板 JSON）。重建它需要的上下文必须**先**在，
#     否则会走到一半留下一个「官方镜像 + 没有页面」的容器。这里提前 fail-closed。
BUILD="$OPS/build_image.sh"
CTX="$OPS/image"
[ -f "$BUILD" ] || { echo "FATAL: 缺 $BUILD —— 无它则换镜像后页面与采集器全丢，拒绝执行"; exit 4; }
for f in Dockerfile entrypoint.sh rk-health-collect.sh \\
         assets/gpu.html assets/gpu-dashboard.json assets/gpu-overview-addon.json; do
  [ -s "$CTX/$f" ] || { echo "FATAL: 构建上下文缺 $CTX/$f（派生层无法重建），拒绝执行"; exit 4; }
done'''
pairs.append(("B", old_b, new_b))

# C) 第 5 步：先落官方镜像、再重建派生层、再落派生镜像
old_c = '''# ---------------------------------------------------------------- 5 重建
echo "[5/6] 重建容器 ..."
bash "$REC" || { echo "FATAL: 重建失败（脚本文件已备份在 $REC.bak_$STAMP）"; exit 6; }'''
new_c = '''# ---------------------------------------------------------------- 5 重建（两段）
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
bash "$REC" || { echo "FATAL: 重建派生容器失败（备份 $REC.bak_$STAMP）"; exit 6; }'''
pairs.append(("C", old_c, new_c))

# D) 收尾提示里的编号与措辞
old_d = '''echo "[6/6] 核验（这条决定「要不要重做」）..."'''
new_d = '''echo "[8/9] 核验（含 img_selfcontained：不挂卷也自带页面/采集器）..."'''
pairs.append(("D", old_d, new_d))

old_e = '''echo "OK: 镜像已更新为 $NEWID，核验全绿，无需重做任何配置与页面。"'''
new_e = '''echo "OK: 基础镜像已更新为 $NEWID，派生层已自动重建并落位，核验全绿。"
echo "    页面与采集器都在镜像里（/usr/share/netdata/web/custom、/opt/rk-health），宿主零服务。"'''
pairs.append(("E", old_e, new_e))

for tag, old, new in pairs:
    n = s.count(old)
    assert n == 1, "%s 命中 %d 次" % (tag, n)
    s = s.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
back = io.open(P, encoding="utf-8").read()
for tag, _, new in pairs:
    assert new.split("\n")[0].strip() in back, tag
assert back.count("build_image.sh") >= 3
print("OK", P, len(back.encode()), hashlib.md5(back.encode()).hexdigest())
