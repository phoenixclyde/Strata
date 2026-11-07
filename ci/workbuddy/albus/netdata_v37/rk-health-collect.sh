#!/bin/sh
# rk-health-collect.sh（容器版）-----------------------------------------------
# 目的：给 netdata 看板（gpu.html 顶栏状态组）供数 —— Z0 三条 / 污染维 / 系统健康。
#
# 与宿主版 _z_health_collect.sh 的关系：
#   同一份口径，搬到容器内执行。**判据一字未改**：污染的判决与计数仍由 routeK 的权威
#   探针产出，本脚本只转抄，不重算。
#
# 为什么可以在容器内跑到宿主视角：
#   * 探针：容器内以 root 执行
#       nsenter -t 1 -m -n -u -i -- /bin/sh /home/albus/routeK/run/_rk78_pollution.sh
#     nsenter 切到宿主的 mount/net/uts/ipc 命名空间 => 宿主的路径、命令（rocm-smi /
#     docker / journalctl）、时区、sudo 全部可用，**探针输出与宿主直跑逐令牌一致**。
#     容器保留了 --pid host 与 --cap-add SYS_ADMIN/SYS_PTRACE，nsenter 才成立。
#     另需 --device /dev/kfd 等，否则 rocm-smi 拿不到 VRAM（node 不可见 + device cgroup）。
#   * Z0 / VRAM / THP / governor / meminfo / loadavg / uptime：容器内直读，实测与宿主同值。
#   * netdata alarms API：容器 network=host，curl 127.0.0.1:19999 即达。
#
# 取不到值的策略（与宿主版同）：写 null，页面显示 "--" 且不置颜色。
#   **额外加一道诚实性守卫**：探针自报 ok 但它判 CLEAN 而显存维的输入缺失时，
#   判决改标 CLEAN_UNVERIFIED_VRAM 并置 probe_partial => 不把「取不到」当「正常」。
#
# 用法：rk-health-collect.sh           跑一次
#       rk-health-collect.sh loop      常驻，每 RK_COLLECT_INTERVAL（默认 10）秒跑一次
# 产物：/usr/share/netdata/web/custom/health.json（原子写）
# ---------------------------------------------------------------------------
set -u

OUTDIR=${RK_COLLECT_OUTDIR:-/usr/share/netdata/web/custom}
OUT=$OUTDIR/health.json
TMP=$OUTDIR/.health.json.$$.tmp
POLL=${RK_COLLECT_PROBE:-/home/albus/routeK/run/_rk78_pollution.sh}
PLOG=/tmp/_rk_health_pollution.txt
NS="nsenter -t 1 -m -n -u -i --"

# ---------------------------- loop 模式 ----------------------------
if [ "${1:-}" = "loop" ]; then
  IV=${RK_COLLECT_INTERVAL:-10}
  echo "COLLECT_LOOP_START $(date -Is 2>/dev/null) interval=${IV}s outdir=$OUTDIR"
  while :; do
    "$0" || echo "COLLECT_LOOP_ERR rc=$?"
    sleep "$IV"
  done
fi

[ -d "$OUTDIR" ] || { echo "COLLECT_ABORT=no_outdir:$OUTDIR"; exit 9; }

# ---------- 1. Z0 三条（sysfs 现读；按 vendor 认卡，不写死 cardN ----------
PERF=null
VRAM_SYS=null
# [v33 2026-09-22 机主问「卡在不在算」] 利用率**本来就读得到**，只是全链没人读：
#   宿主 sysfs `.../gpu_busy_percent`（166 实测可读）。探针全文 0 处利用率读数。
#   读法与本段 PERF / VRAM_SYS 同规（按 vendor 认卡、不写死 cardN），
#   零跨仓、不碰探针的 56 令牌约定。
GPU_BUSY=null
for d in /sys/class/drm/card*/device; do
  # [v36 2026-10-27] 追加 power_dpm 可读判据：vendor 相同但无 DPM 节点的卡（理论情形，
  #   如多张 AMD 集显/假卡）不得遮蔽真 MI50（遮蔽 = Z0 静默读到空值）。
  [ -r "$d/vendor" ] || continue
  [ "$(cat "$d/vendor" 2>/dev/null)" = "0x1002" ] || continue
  [ -r "$d/power_dpm_force_performance_level" ] || continue
  if [ -r "$d/power_dpm_force_performance_level" ]; then
    v=$(cat "$d/power_dpm_force_performance_level" 2>/dev/null)
    [ -n "$v" ] && PERF=$v
  fi
  if [ -r "$d/mem_info_vram_used" ]; then
    v=$(cat "$d/mem_info_vram_used" 2>/dev/null)
    [ -n "$v" ] && VRAM_SYS=$v
  fi
  # [v33] 利用率（百分比整数）。amdgpu 的这个节点在某些内核/固件组合下不存在 =>
  #   取不到就留 null（页面显示 -- 且**不置色**），**不冒充 0** ——
  #   0% 与「读不到」语义完全相反（前者=空闲，后者=不可知），这正是不许恒真绿灯的理由。
  if [ -r "$d/gpu_busy_percent" ]; then
    v=$(cat "$d/gpu_busy_percent" 2>/dev/null)
    [ -n "$v" ] && GPU_BUSY=$v
  fi
  break
done

THP=null
if [ -r /sys/kernel/mm/transparent_hugepage/enabled ]; then
  v=$(sed -n 's/.*\[\([a-z]*\)\].*/\1/p' /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null)
  [ -n "$v" ] && THP=$v
fi

GOV=null
if [ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
  v=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
  [ -n "$v" ] && GOV=$v
fi

# ---------- 2. 污染：nsenter 进宿主命名空间，转抄权威探针的令牌 ----------
: > "$PLOG"
PROBE_ERR=""
if [ -f "$POLL" ] || $NS /bin/sh -c "test -f '$POLL'" 2>/dev/null; then
  # [!] 先清 bootlog：探针的 BOOTLOG 是硬编码的宿主 /tmp 路径，若残留一个非本进程属主的
  #     同名文件，探针第 98 行 `: > $BOOTLOG` 会失败并整支退出（2026-09-22 实测）。
  $NS /bin/sh -c 'rm -f /tmp/_rk78_bootlog.txt' 2>/dev/null
  $NS /bin/sh -c "exec /bin/sh '$POLL'" > "$PLOG" 2>/dev/null
else
  PROBE_ERR=probe_not_found
fi
# 令牌一行一个（v1.4 起探针保证），最朴素的取值方式就够
tok(){ sed -n "s/^$1=//p" "$PLOG" 2>/dev/null | head -n 1; }

PROBE_OK=0
VERDICT=$(tok POLLUTION_VERDICT | cut -d' ' -f1)
if [ -n "$VERDICT" ]; then PROBE_OK=1
elif [ -z "$PROBE_ERR" ]; then PROBE_ERR=probe_no_verdict
fi
PROBE_TOKEN_N=$(grep -c '=' "$PLOG" 2>/dev/null); PROBE_TOKEN_N=${PROBE_TOKEN_N:-0}
# [!] 上面那个口径不稳：它把内核日志正文行里出现的等号也计进去（同一台机实测 IDLE 56 行、
#     车在飞 62 行），因此**不能**拿它当「探针是否完整跑完」的判据。行首令牌才是真口径。
PROBE_TOKEN_STRICT=$(grep -c '^[A-Z][A-Z0-9_]*=' "$PLOG" 2>/dev/null); PROBE_TOKEN_STRICT=${PROBE_TOKEN_STRICT:-0}
# 探针 v1.10 + cz30/DF-130（2026-09-22 14:18）= 56 个行首令牌。探针再升级时须同步此值，
# 否则页面会报「探针输出变多、看板可能漏取新判据」（这正是 2026-09-22 那次漏取的成因）。
PROBE_TOKEN_EXPECT=${RK_PROBE_TOKEN_EXPECT:-56}
# 探针若中途 abort（如 cd_failed / bootlog 写不进），只有极少数令牌 => 记下原因
PROBE_ABORT=$(tok POLL_ABORT)
PEXIT=$(tok POLLUTION_EXIT)
OOPS_RUN=$(tok OOPS_RUN_N)
OOPS_BOOT=$(tok OOPS_BOOT_N)
OOPS_ALL=$(tok OOPS_ALL_N)
RATIO=$(tok VRAM_RATIO_VS_CLEAN)
VRAM_USED=$(tok VRAM_USED_B)
CLEAN_VRAM=$(tok CLEAN_VRAM_B)
PAGEFAULT=$(tok PAGEFAULT_N)
VMFAIL=$(tok GPUVM_MAP_FAIL_N)
BOX=$(tok BOX_STATE | cut -d' ' -f1)
# [v33 2026-09-22 机主质疑「busy 到底指什么」] 探针 BOX_STATE=BUSY 的判据是**三路或**
#   （_rk78_pollution.sh:361-365）：
#     CARS   = ps -eo args | grep -E '_rk_run_car'               （发车脚本进程）
#     SERVES = ps -eo args | grep -E 'serve_27b_routeK'          （vllm serve 进程）
#     RKN    = docker ps | grep -cE '^(rk_|.*_prevdrv_|.*_kept_)'（任务容器）
#   它**不看 CPU 占用、不看 A 卡在不在算**，本机也没有 N 卡。
#   原实现 `cut -d' ' -f1` **把括号里的三路计数丢了** => 页面只看得见 BUSY 一个词，
#   于是把「serve 在跑」也读成「有车在飞」（实测用例：car=0 serve=1 仍是 BUSY，
#   且探针判决行自己就写「车在飞」—— 见 README §9.17 用例 5）。
#   三路令牌探针**早就 echo 了**（:350 / :351 / :358）=> 零跨仓，如实转抄。
BOX_CAR=$(tok RK_CAR_PROC_N)
BOX_SERVE=$(tok RK_SERVE_PROC_N)
BOX_CTR=$(tok RK_CAR_CONTAINER_N)
# [v36 2026-10-27] 常驻推理服务 strata serve 的进程数（探针 BOX 三路判据**不认识它**，
#   2026-10-27 实测：serve 握 33.9GB / KFD 1 进程，探针判 IDLE + VRAM_LEAK rc=3）。
#   与探针的 RK_SERVE 同一手法（ps 现数、grep -v grep）；只报**原始计数**，页面只转述。
#   ps 走容器 --pid host，与宿主同视图；数不到（异常）由页面按 null 显示 --。
# [v37 2026-11-05] 判据放宽（实测漏检）：v36 用 `grep -F "strata --serve"` 只认**字面**那种
#   调用形态；生产容器里跑的是 `/data/bin/strata-0.1.56-090 --serve ...`（带版本号后缀）
#   => 命中 0 => 页面归因失效 => 顶栏在**生产服务常驻**时恒显「显存泄漏 3088x」红色假警。
#   现按「二进制名以 strata 开头 + 紧跟 --serve」匹配，两种形态都覆盖。
#   [!] 只数**持有显存的 --serve 本尊**，不数包装进程（server.py / strata-vision）。
STRATA_SERVE=$(ps -eo args 2>/dev/null | grep -E 'strata[A-Za-z0-9._-]* --serve' | grep -v grep | wc -l | tr -d " ")
# [v37] 生产推理服务的**包装进程**数（serve/server.py --engine strata，即 8090 那套）。
#   它本身不持 KFD，但它是「这台机在对外提供推理」的判据之一：容器名千变万化
#   （strata166-407 / arm-A / .pre-w920b），进程命令行更稳定。页面把两个计数**取或**。
PROD_SRV=$(ps -eo args 2>/dev/null | grep -F 'serve/server.py --engine strata' | grep -v grep | wc -l | tr -d " ")
DOCKER=$(tok DOCKER_RUNNING_N)
KLOGSRC=$(tok KLOG_SRC)
UP_SINCE=$(tok UPTIME_SINCE)
GPU_HW=$(tok GPU_HWFAULT_TOKEN)
GPU_HW_CARLOG=$(tok GPU_HWFAULT_TOKEN_CARLOG)
MEM_PRESSURE=$(tok MEM_PRESSURE_TOKEN)
MEM_AVAIL_PCT=$(tok MEM_AVAIL_PCT)
COMMIT_PCT=$(tok COMMIT_RATIO_PCT)
# [!] 探针 v1.10 + cz30/DF-130（2026-09-22 14:18）新增的判定条件，此前采集器**一个都没转抄**
#     => 看板完全看不见「oops 已按签名剔族」这件事：oops=0 到底是真 0，还是被剔掉了，
#     屏幕上分不出来。以下 8 项即该次新增（外加页面显示硬件维所需的 4 路计数与页面刻度）。
OOPS_RUN_RAW=$(tok OOPS_RUN_RAW_N)
OOPS_CONST_MODE=$(tok OOPS_CONST_MODE)
OOPS_CONST_RUN=$(tok OOPS_CONST_RUN_N)
OOPS_CONST_ALL=$(tok OOPS_CONST_ALL_N)
KLOG_OVR_TAKEN=$(tok KLOG_OVR_TAKEN)
KLOG_OVR_FAIL=$(tok KLOG_OVR_FAIL)
KLOG_LINES=$(tok KLOG_LINES)
PAGEFAULT_T=$(tok PAGEFAULT_T)
GFX_FAULT=$(tok GFX_FAULT_TOKEN)
GPU_HW_KLOG=$(tok GPU_HWFAULT_TOKEN_KLOG)
MEMACC_KLOG=$(tok MEMACC_KLOG_N)
COREDUMP_KLOG=$(tok COREDUMP_KLOG_N)
CARLOG_MEMACC=$(tok CARLOG_MEMACC_N)
CARLOG_COREDUMP=$(tok CARLOG_COREDUMP_N)
# [v31f 2026-09-22 机主提问] 车日志通道的**覆盖度**必须一起转抄 ——
#   探针早就 echo 了这两个令牌（:266 CARLOG_SCAN_N / :269 CARLOG_FAULT_FILES），
#   采集器此前**一个都没读**，于是页面无法区分「扫了 3 份、0 命中」与「一份都没扫到」。
#   为什么这个区分是必需的：车日志是**收车那一刻**才落盘
#   （routeK `run/_rk_bench_generic_v3.sh:62-63`：注释原文「FULL CONTAINER LOG DUMP
#   （收车前落盘）」+ `docker logs $CAR > $DUMP`）=> **有车在飞时，该车不在扫描范围内**；
#   而探针 1c 段实证这族签名（Memory access fault by GPU node / GPU coredump）
#   **只在车日志出现、内核侧恒 0** => 开车时那个 0 的车日志半边可能是空扫。
#   探针侧不改（跨仓 + 牵动判决语义），只在此如实转抄覆盖度，交由页面呈现。
CARLOG_SCAN=$(tok CARLOG_SCAN_N)
CARLOG_FAULT_FILES=$(tok CARLOG_FAULT_FILES)

# [!] 显存取数来源标注：探针走 rocm-smi（需 --device /dev/kfd），采集器另有一条 sysfs 路。
#     两路实测同值（2026-09-22），但**来源必须标出来**，不能让人以为一定是探针给的。
if [ -n "$VRAM_USED" ]; then VRAM_SRC=probe_rocm_smi
elif [ -n "$VRAM_SYS" ]; then VRAM_SRC=collector_sysfs
else VRAM_SRC=none
fi

# [!] 诚实性守卫（与探针自身的 UNKNOWN_KLOG / UNKNOWN_BASE 同规）：
#     探针报了 ok 却判 CLEAN，而显存维的两个输入有一个是空的 => 该维其实没成立，
#     不得照抄 CLEAN。标 PROBE_PARTIAL，页面必须显式提示。
PROBE_PARTIAL=0
if [ "$PROBE_OK" = "1" ] && [ "$VERDICT" = "CLEAN" ]; then
  if [ -z "$VRAM_USED" ] || [ -z "$CLEAN_VRAM" ]; then
    VERDICT=CLEAN_UNVERIFIED_VRAM
    PROBE_PARTIAL=1
  fi
fi

# ---------- 2c. 开机闸门 + 目标态（v31 新增）----------
# [!] 机主 2026-09-22 22:1x 交办：顶栏要覆盖 routeK 侧那份状态通报的全部项。这批项分两族，
#     **都不是污染判决的输入**，故不扩 routeK 权威探针 —— 它的「行首令牌 = 56」是被验收
#     套件 `_rk78_acc_v3.sh` 依赖的硬约定（与 T92 同族：被依赖的令牌不得擅改），且跨仓改件
#     另有落盘手续。改由本采集器直取：一处取数、一处口径。
#   族 A「开机闸门」= 本 boot 是否干净开机。grep 串与「双路交叉核对」**逐字照抄** routeK 的
#     `run/_rk_bootgate.sh`（五项全 0 才放行），另加同族的 `K_WARN_LBAR`。
#     [!] K_WARN_LBAR 有判别力，不是凑数：`amdgpu_vm.c:2526` 的 WARN_ONCE 在出厂参数下
#     每次 boot 恒 2 条（GFX VM + compute VM 各一次，旧 boot 亦然，实测无例外）；现在读到
#     0 正是「乙（vm_update_mode=0）生效」的独立读数 —— 机主 2026-09-22 22:1x 报
#     `KWARN=0` 即此。故本格必须留在屏上，且与乙格互证。
#   族 B「目标态四项」= 发车前 甲（cmdline 的 iommu=pt）/ 乙（vm_update_mode）/
#     配置（/etc/modprobe.d/amdgpu.conf）/ 现场（KFD 进程数 + 本 boot 发车数）。
# [!] 口径：本段全部是 **boot 累计**（事件语义，T96）——「本 boot 是否已发生」，不是增量。
#     与「有没有车」无关，车在飞也照取（唯 KFD 维在页面上按有车挂起 —— 它是残留判据）。
# [!] 成本实测（2026-09-22 22:1x，166 容器内）：dmesg 1735 行 / journalctl -k -b 0 1732 行，
#     单次取数 < 1s；本段每轮多读两份内核日志快照（探针自己那一份另算 —— 两者串不同、
#     语义不同，不得互相替代）。全部 nsenter 调用套 timeout，拿不到就写 null，不拖采集循环。
# [!] 诚实性守卫（照搬 bootgate 的「先证取证手段有效」）：某一路取不到日志时，该路六项
#     一律输出 NA（不是 0）=> 页面显示 -- 且不置色。若照搬 grep -c 的空管道行为，
#     会得到一条**假 CLEAN** —— 那正是 bootgate 明文防的事。
TO=""
command -v timeout >/dev/null 2>&1 && TO="timeout 25"

# 族 B：文件系统路径（/etc、/run）与容器不同，必须 nsenter 到宿主命名空间；
#        sysfs 与 /proc/cmdline 虽是全局的，一并在这里取以保口径一致。
#        T_ROUTE_OK 是**通路哨兵**：它不在 => 整条通路没跑起来 => 所有值按 null 处理，
#        不许把「取不到」落成「0 台车 / 未发车」。
TGTLOG=$($TO $NS /bin/sh -c '
echo "T_ROUTE_OK=1"
echo "T_CMDLINE_PT=$(grep -o iommu=pt /proc/cmdline 2>/dev/null | wc -l | tr -d " ")"
echo "T_VUM=$(cat /sys/module/amdgpu/parameters/vm_update_mode 2>/dev/null)"
echo "T_CONF_MD5=$(md5sum /etc/modprobe.d/amdgpu.conf 2>/dev/null | cut -c1-32)"
echo "T_KFD_PROC=$(ls -1 /sys/class/kfd/kfd/proc 2>/dev/null | wc -l | tr -d " ")"
# [v32 2026-09-22 裁定 L3] 发车标记文件**跨 boot 不清除**，而它的格式实测为
#   `<车数> <boot_id>`（166 实测 /tmp/rk_boot_cars = `1 17964182-b8bc-4c07-...`，
#   生产者 routeK `run/_rk_sweepw7.sh:85-86`，NF=2）。原实现只取首字段 =>
#   会把**上一个 boot 的车数**当成本 boot 的（跨 boot 残留 = 假读数）。
#   现在第二字段必须等于本 boot 的 boot_id，否则按「本 boot 未发车」记 0（输出空）。
#   carf_stale=1 表示「文件里有车数但 boot_id 对不上」=> 单独报出，不静默丢。
T_LINE=$(cat /run/rk_boot_cars /tmp/rk_boot_cars 2>/dev/null | head -1)
T_CN=$(printf '%s' "$T_LINE" | cut -d " " -f1)
T_CB=$(printf '%s' "$T_LINE" | cut -d " " -f2)
T_BI=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
echo "T_BOOT_ID=$T_BI"
echo "T_CARF_BOOT=$T_CB"
if [ -n "$T_CN" ] && [ -n "$T_CB" ] && [ "$T_CB" = "$T_BI" ]; then
  echo "T_CARF=$T_CN"
  echo "T_CARF_STALE=0"
else
  echo "T_CARF="
  if [ -n "$T_CN" ]; then echo "T_CARF_STALE=1"; else echo "T_CARF_STALE=0"; fi
fi
' 2>/dev/null)

# 族 A：内核日志双路（d 路 = dmesg -> sudo dmesg；j 路 = journalctl -k -b 0 -> sudo 同款）。
#        两路各取一份快照、各数六项，前缀 B_d_ / B_j_。
BOOTLOG2=$($TO $NS /bin/sh -c '
snap(){
  L=$(mktemp "${TMPDIR:-/tmp}/_rk_health_klog.XXXXXX" 2>/dev/null) || L="/tmp/_rk_health_klog.$$"
  : > "$L" 2>/dev/null
  SRC=none
  if [ "$1" = "d" ]; then
    if dmesg > "$L" 2>/dev/null && [ -s "$L" ]; then SRC=dmesg
    elif sudo -n dmesg > "$L" 2>/dev/null && [ -s "$L" ]; then SRC=sudo_dmesg; fi
  else
    if journalctl -k -b 0 --no-pager > "$L" 2>/dev/null && [ -s "$L" ]; then SRC=journalctl_k_b0
    elif sudo -n journalctl -k -b 0 --no-pager > "$L" 2>/dev/null && [ -s "$L" ]; then SRC=sudo_journalctl_k_b0; fi
  fi
  echo "B_${1}_SRC=$SRC"
  if [ "$SRC" = "none" ]; then
    echo "B_${1}_LINES=NA"
    for k in LBAR ITE LOCKUP SDMA1 PAGE1 RING; do echo "B_${1}_${k}=NA"; done
  else
    echo "B_${1}_LINES=$(wc -l < "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_LBAR=$(grep -c "CPU update of VM recommended only for large BAR system" "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_ITE=$(grep -c "Invalidation Time-out" "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_LOCKUP=$(grep -ci "LOCKUP" "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_SDMA1=$(grep -c "IB test failed on sdma1" "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_PAGE1=$(grep -c "IB test failed on page1" "$L" 2>/dev/null | tr -d " ")"
    echo "B_${1}_RING=$(grep -c "ring test failed" "$L" 2>/dev/null | tr -d " ")"
  fi
  rm -f "$L"
}
snap d
snap j
' 2>/dev/null)

# ---------- 3. 系统健康 ----------
ALARMS=$(curl -s --max-time 5 'http://127.0.0.1:19999/api/v1/alarms?all=true' 2>/dev/null \
  | python3 -c '
import sys, json
try:
    j = json.load(sys.stdin)
except Exception:
    sys.exit(0)
a = j.get("alarms") or {}
w = c = n = u = i = 0
for v in a.values():
    s = (v.get("status") or "").upper()
    if s == "CRITICAL": c += 1
    elif s == "WARNING": w += 1
    elif s == "CLEAR": n += 1
    elif s == "UNDEFINED": u += 1
    elif s == "UNINITIALIZED": i += 1
print(w, c, n, u, i)
' 2>/dev/null)
AL_W=$(echo "$ALARMS" | awk '{print $1}')
AL_C=$(echo "$ALARMS" | awk '{print $2}')
AL_N=$(echo "$ALARMS" | awk '{print $3}')
AL_U=$(echo "$ALARMS" | awk '{print $4}')
AL_I=$(echo "$ALARMS" | awk '{print $5}')

SWAP_USED=$(free -b 2>/dev/null | awk '/^Swap:/{print $3}')
SWAP_TOTAL=$(free -b 2>/dev/null | awk '/^Swap:/{print $2}')

# ---------- 3.5 内存全量 + SSD SMART（v37 2026-11-05） ----------
# 内存：直接读 /proc/meminfo（容器 --pid host、/proc 未隔离 => 与宿主同视图）。
#   为什么不沿用页面从 system.ram 四维反推：netdata 的 system.ram 只有 free/used/cached/buffers
#   四维，反推出的「总量」漏掉 SReclaimable/Slab；而它的 "used" 是 total-free-cached-buffers，
#   与 `free` 的 "used = total - available" 是两个口径（差在可回收缓存）。
#   页面原先用前者当「内存占用」，于是「缓存吃掉一半内存」时读数偏小、与实际观感不符。
#   这里给**原始量**，口径由页面显式声明（已用 = total - available，缓存单列）。
# SSD：镜像自带 smartctl（/usr/sbin/smartctl），但要 --device 才看得见块设备
#   （device cgroup；recreate_netdata.sh 已加 /dev/nvme0 /dev/nvme0n1 /dev/sda）。
#   60s 一刷：SMART 查询有成本，而温度/寿命/通电小时变化极慢；缓存落 /tmp。
SYS_JSON=$(RK_SSD_TTL="${RK_SSD_TTL:-60}" /usr/bin/python3 - <<'PY'
import json, os, subprocess, time

def mem():
    d = {}
    try:
        with open("/proc/meminfo") as fh:
            for ln in fh:
                k, v = ln.split(":", 1)
                p = v.strip().split()
                if p:
                    d[k] = int(p[0]) * 1024
    except Exception:
        return None
    def g(k):
        return d.get(k, 0)
    return {"total": g("MemTotal"), "free": g("MemFree"), "available": g("MemAvailable"),
            "buffers": g("Buffers"), "cached": g("Cached"), "sreclaim": g("SReclaimable"),
            "shmem": g("Shmem"), "slab": g("Slab"),
            # [v37b] Unevictable/Mlocked：mlocked 的页缓存不可回收，却仍被多数人
            #   当成"缓存=可腾"；它正是 available 远小于 free+cache 的原因
            #   （2026-11-05 实测 Unevictable 26.8GiB / Cached 43.9GiB / available 16.0GiB）。
            "unevict": g("Unevictable"), "mlocked": g("Mlocked"),
            "swap_total": g("SwapTotal"), "swap_free": g("SwapFree")}

CACHE = "/tmp/.rk_ssd_cache.json"

def one(dev):
    try:
        r = subprocess.run(["/usr/sbin/smartctl", "-j", "-a", "/dev/" + dev],
                           capture_output=True, timeout=10)
        d = json.loads((r.stdout or b"{}").decode("utf-8", "replace"))
    except Exception as e:
        return {"err": str(e)[:80]}
    dev_info = d.get("device") or {}
    out = {"model": d.get("model_name") or dev_info.get("model_name") or dev,
           "ok": 1 if (d.get("smart_status") or {}).get("passed") else 0}
    cap = d.get("user_capacity") or d.get("nvme_total_capacity")
    if isinstance(cap, dict):
        out["cap"] = cap.get("bytes")
    elif isinstance(cap, int):
        out["cap"] = cap
    out["temp"] = (d.get("temperature") or {}).get("current")
    proto = (dev_info.get("protocol") or "").lower()
    h = d.get("nvme_smart_health_information_log")
    if proto.startswith("nvme") or h:
        h = h or {}
        pu = h.get("percentage_used")
        out["kind"] = "nvme"
        out["life"] = None if pu is None else max(0, 100 - int(pu))
        out["spare"] = h.get("available_spare")
        # [v37c] 备用空间阈值：健康判据是「spare < 该盘自报阈值」，
        #   阈值随盘而异（不是统一 10%），必须整盘读取而不是拿常量比。
        out["spare_th"] = h.get("available_spare_threshold")
        duw = h.get("data_units_written")
        out["written"] = None if duw is None else int(duw) * 512000
        out["hours"] = h.get("power_on_hours")
        out["crit"] = h.get("critical_warning")
        out["media_err"] = h.get("media_errors")
    else:
        tab = (d.get("ata_smart_attributes") or {}).get("table") or []
        A = {}
        for x in tab:
            A[x.get("id")] = x
        def raw(i):
            x = A.get(i)
            return None if not x else (x.get("raw") or {}).get("value")
        out["kind"] = "sata"
        life = None
        for i in (231, 177):
            if i in A and A[i].get("value") is not None:
                life = int(A[i]["value"])
                break
        out["life"] = life
        out["hours"] = raw(9)
        out["lba_w"] = raw(241)
        out["realloc"] = raw(5)
        out["spare"] = raw(180)     # SATA：未使用的备用块**个数**（不是百分比）
        out["uncorr"] = raw(187)    # Reported_Uncorrect：不可纠正错误计数
        out["crc"] = raw(199)       # UDMA_CRC_Error_Count：SATA 链路 CRC 错
        # [v54] SATA 没有 NVMe 那四项。等价物分两处取，都只用**标准字段**：
        #   1) ATA Device Statistics（GP Log 0x04，ACS 标准）：Logical Sectors Written/Read，
        #      单位恒为逻辑扇区（本盘 512B）—— 不随厂商变。
        #   2) 厂商 SMART 属性：180 备用块 / 187 不可纠正 / 199 UDMA CRC。
        # [!] 属性 241 不能当"已写入"用：本盘 241=12874，而 Device Statistics 实测写入
        #   27,000,010,226 扇区 ×512B = 13.82 TB —— 12874 × 1 GiB 恰好 = 13.82 TB，
        #   说明这块盘 241 的单位是 1 GiB（不是 LBA）；写 256 MiB 时 241 一动不动（不足 1 单位）。
        #   单位随厂商而异（32MiB / LBA / 1GiB 都见过）=> 只用标准字段，不猜。
        out["written"] = None
        blk = d.get("logical_block_size") or 512
        try:
            r2 = subprocess.run(["/usr/sbin/smartctl", "-j", "-l", "devstat", "/dev/" + dev],
                                capture_output=True, timeout=10)
            ds = json.loads((r2.stdout or b"{}").decode("utf-8", "replace"))
            tab2 = {}
            for pg in ((ds.get("ata_device_statistics") or {}).get("pages") or []):
                for row in (pg.get("table") or []):
                    if row.get("name"):
                        tab2[row["name"]] = row.get("value")
            sw = tab2.get("Logical Sectors Written")
            sr = tab2.get("Logical Sectors Read")
            if isinstance(sw, int):
                out["written"] = sw * blk
            if isinstance(sr, int):
                out["read"] = sr * blk
            # 标准字段优先：page 4 "Number of Reported Uncorrectable Errors"、
            #   page 6 "Number of Interface CRC Errors" 与属性 187/199 是同一个量，
            #   但标准字段有定义的单位与语义；本盘这两个页面没实现 => 回落到属性值。
            u2 = tab2.get("Number of Reported Uncorrectable Errors")
            c2 = tab2.get("Number of Interface CRC Errors")
            if isinstance(u2, int):
                out["uncorr"] = u2
            if isinstance(c2, int):
                out["crc"] = c2
            pu = tab2.get("Percentage Used Endurance Indicator")
            if isinstance(pu, int):
                out["endurance_used"] = pu   # 只做交叉校验，不上屏（与属性 231 有冲突，见 SKILL）
        except Exception as e:
            out["ds_err"] = str(e)[:60]
    return out

res = None
try:
    ttl = int(os.environ.get("RK_SSD_TTL") or 60)
    if time.time() - os.stat(CACHE).st_mtime < ttl:
        with open(CACHE) as fh:
            res = json.load(fh)
except Exception:
    res = None
if not res:
    res = {"ts": int(time.time()), "disks": {}}
    for dev in ("nvme0n1", "sda"):
        res["disks"][dev] = one(dev)
    try:
        with open(CACHE, "w") as fh:
            json.dump(res, fh)
    except Exception:
        pass
print(json.dumps({"mem": mem(), "ssd": res}, separators=(",", ":")))
PY
)
LOAD1=$(cut -d' ' -f1 /proc/loadavg 2>/dev/null)
UP=$(cut -d. -f1 /proc/uptime 2>/dev/null)

# ---------- 4. 组装 JSON（原子写：先临时再 mv ----------
PERF="$PERF" GOV="$GOV" THP="$THP" VRAM_SYS="$VRAM_SYS" \
PROBE_OK="$PROBE_OK" PROBE_ERR="$PROBE_ERR" VERDICT="$VERDICT" PEXIT="$PEXIT" \
PROBE_TOKEN_N="$PROBE_TOKEN_N" PROBE_PARTIAL="$PROBE_PARTIAL" PROBE_ABORT="$PROBE_ABORT" \
PROBE_TOKEN_STRICT="$PROBE_TOKEN_STRICT" PROBE_TOKEN_EXPECT="$PROBE_TOKEN_EXPECT" \
OOPS_RUN_RAW="$OOPS_RUN_RAW" OOPS_CONST_MODE="$OOPS_CONST_MODE" \
OOPS_CONST_RUN="$OOPS_CONST_RUN" OOPS_CONST_ALL="$OOPS_CONST_ALL" \
KLOG_OVR_TAKEN="$KLOG_OVR_TAKEN" KLOG_OVR_FAIL="$KLOG_OVR_FAIL" KLOG_LINES="$KLOG_LINES" \
PAGEFAULT_T="$PAGEFAULT_T" GFX_FAULT="$GFX_FAULT" GPU_HW_KLOG="$GPU_HW_KLOG" \
MEMACC_KLOG="$MEMACC_KLOG" COREDUMP_KLOG="$COREDUMP_KLOG" \
CARLOG_MEMACC="$CARLOG_MEMACC" CARLOG_COREDUMP="$CARLOG_COREDUMP" \
CARLOG_SCAN="$CARLOG_SCAN" CARLOG_FAULT_FILES="$CARLOG_FAULT_FILES" \
VRAM_SRC="$VRAM_SRC" UP_SINCE="$UP_SINCE" \
BLOB_BOOT="$BOOTLOG2" BLOB_TGT="$TGTLOG" \
GPU_HW="$GPU_HW" GPU_HW_CARLOG="$GPU_HW_CARLOG" \
MEM_PRESSURE="$MEM_PRESSURE" MEM_AVAIL_PCT="$MEM_AVAIL_PCT" COMMIT_PCT="$COMMIT_PCT" \
OOPS_RUN="$OOPS_RUN" OOPS_BOOT="$OOPS_BOOT" OOPS_ALL="$OOPS_ALL" \
RATIO="$RATIO" VRAM_USED="$VRAM_USED" CLEAN_VRAM="$CLEAN_VRAM" \
PAGEFAULT="$PAGEFAULT" VMFAIL="$VMFAIL" BOX="$BOX" DOCKER="$DOCKER" KLOGSRC="$KLOGSRC" \
BOX_CAR="$BOX_CAR" BOX_SERVE="$BOX_SERVE" BOX_CTR="$BOX_CTR" GPU_BUSY="$GPU_BUSY" \
STRATA_SERVE="$STRATA_SERVE" PROD_SRV="$PROD_SRV" SYS_JSON="$SYS_JSON" \
AL_W="$AL_W" AL_C="$AL_C" AL_N="$AL_N" AL_U="$AL_U" AL_I="$AL_I" \
SWAP_USED="$SWAP_USED" SWAP_TOTAL="$SWAP_TOTAL" LOAD1="$LOAD1" UP="$UP" \
python3 - "$TMP" <<'PY'
import json, os, sys, time

def s(k):
    v = os.environ.get(k, "")
    return v if v not in ("", "null") else None

def i(k):
    try:
        return int(float(os.environ.get(k, "")))
    except Exception:
        return None

def f(k):
    try:
        return round(float(os.environ.get(k, "")), 2)
    except Exception:
        return None

# [v32 2026-09-22 裁定 L4] **不舍入**的浮点。专给 VRAM_RATIO_VS_CLEAN 用：
#   探针是**按未舍入值**判档的（awk 直接比较 VRAM_USED/CLEAN），
#   而这里原先用 f() round 到 2 位 => 页面的 hsRatioLvl(p.ratio) 拿到的就是**已舍入值**
#   => 边界上会与探针档位差一档（真值 1.4999：探针判 ok，JSON 给 1.5，页面判 warn）。
#   判档输入必须与探针同源 => 传全精度；显示端（页面）自己按 2 位渲染。
def fraw(k):
    try:
        return float(os.environ.get(k, ""))
    except Exception:
        return None

GATE_ITEMS = ("lbar", "ite", "lockup", "sdma1", "page1", "ring")

def kv(blob):
    d = {}
    for ln in (blob or "").splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d

def gnum(d, k):
    try:
        return int((d.get(k) or "").strip())
    except Exception:
        return None

def pick(*ns):
    # [v31d 2026-09-22 审计修复] fail-closed：**两路齐才算**。
    #   原实现取「非 None 里的最大值」=> 单路日志读不到时照出另一路的值并染绿，
    #   而 routeK `run/_rk_bootgate.sh` 在任一路 NA 时判 BAD / 拒绝发车
    #   （`case "$x" in ''|*[!0-9]*) eval "$v=NA";;` + `if [ "$a" = "NA" ] || [ "$b" = "NA" ]`）
    #   => 旧实现把 fail-closed 翻成了 fail-open，与 README §6.5.4 的「等价」声明不符。
    if any(n is None for n in ns):
        return None
    return max(ns)

# [v32 2026-09-22 裁定 L6] 证据充分性前置 —— **逐字照抄** routeK `run/_rk_bootgate.sh:41-42`：
#   该脚本在判「干净」之前先证「取证手段有效」：journalctl -k -b 0 行数 >= 100 且
#   dmesg 行数 >= 1000，否则 VERDICT=UNVERIFIED、rc=8、**拒绝发车**。
#   本采集器此前只把 lines 转抄进 JSON、**从不拿它判** => 日志短得显然不完整
#   （例如环形缓冲只剩 3 行）时照样给六项 0 => 假 CLEAN。那是一道缺失的 fail-closed 闸门。
#   阈值口径与 bootgate 逐字一致（j>=100 / d>=1000），不自行改动。
EV_TH = {"j": 100, "d": 1000}

def ev_ok(tag):
    ln = gnum(bt, "B_" + tag + "_LINES")
    return (ln is not None) and (ln >= EV_TH[tag])

# [!] EV_D / EV_J 的**赋值**不在这里 —— 必须等 bt 就绪（见下方 `bt = kv(...)` 之后）。
#   本处只定义函数。v32 首版正是把赋值写在这一行，而 `bt` 在下面 40 行才定义
#   => 运行期 NameError => 采集器每轮都崩，health.json 永不产出。
#   [教训] `PY_AST=OK`（语法树）对**执行顺序**是盲的：语法全对、跑起来立刻死。
#   故本轮另加一道**执行级**闸门（喂假 env 真跑这段 Python 段，断言产出 JSON）。

def pickg(tag, key):
    """取某一路的某项；该路**证据不充分**（行数低于 bootgate 前置）则视为 null。

    [!] 与 pick() 分层：pickg 管「该路本身可不可用」，pick 管「两路齐才算」。
    """
    if not (EV_D if tag == "d" else EV_J):
        return None
    return gnum(bt, "B_" + tag + "_" + key.upper())

def route(d, tag):
    return {k: pickg(tag, k) for k in GATE_ITEMS}

def gsum(*ks):
    vs = [i(k) for k in ks]
    return None if any(v is None for v in vs) else sum(vs)

bt = kv(os.environ.get("BLOB_BOOT"))
# [v32 裁定 L6] 证据充分性在 **bt 就绪之后**求值（见上方 ev_ok 定义处的说明）。
EV_D = ev_ok("d")
EV_J = ev_ok("j")
tg = kv(os.environ.get("BLOB_TGT"))
# [v37] 内存全量 + SSD SMART（由 shell 段算好，紧凑 JSON 经 env 传入；解析失败按空处理，
#   页面据此显示 -- 且不置色 —— 与「取不到值不冒充 0」同规）。
try:
    SJ = json.loads(os.environ.get("SYS_JSON") or "{}")
except Exception:
    SJ = {}
d = {
    "ts": int(time.time()),
    "src": "rk-health-collector/container",
    "z0": {"perf": s("PERF"), "gov": s("GOV"), "thp": s("THP")},
    "poll": {
        "probe_ok": os.environ.get("PROBE_OK") == "1",
        "probe_err": s("PROBE_ERR"),
        "probe_abort": s("PROBE_ABORT"),
        "probe_token_n": i("PROBE_TOKEN_N"),
        "probe_token_strict": i("PROBE_TOKEN_STRICT"),
        "probe_token_expect": i("PROBE_TOKEN_EXPECT"),
        "probe_partial": os.environ.get("PROBE_PARTIAL") == "1",
        "verdict": s("VERDICT"), "exit": i("PEXIT"),
        "oops_run": i("OOPS_RUN"), "oops_boot": i("OOPS_BOOT"), "oops_all": i("OOPS_ALL"),
        # [!] cz30/DF-130：oops_run 已是**按签名剔除平台常量族之后**的值；原始量在
        #     oops_run_raw，剔族规则在 oops_const_mode（drop=已剔 / anomaly=同 boot 超 1 次
        #     故不剔（紧约束）/ unknown=拿不到内核日志）。
        "oops_run_raw": i("OOPS_RUN_RAW"),
        "oops_const_mode": s("OOPS_CONST_MODE"),
        "oops_const_run": i("OOPS_CONST_RUN"), "oops_const_all": i("OOPS_CONST_ALL"),
        "klog_ovr_taken": i("KLOG_OVR_TAKEN"), "klog_ovr_fail": s("KLOG_OVR_FAIL"),
        "klog_lines": i("KLOG_LINES"),
        "ratio": fraw("RATIO"),
        "vram_used": i("VRAM_USED"), "vram_clean": i("CLEAN_VRAM"),
        "vram_sysfs": i("VRAM_SYS"),
        "vram_src": s("VRAM_SRC"),
        "uptime_since": s("UP_SINCE"),
        "gpu_hwfault": s("GPU_HW"), "gpu_hwfault_carlog": s("GPU_HW_CARLOG"),
        # [v31] 机主 2026-09-22 22:1x：`gpu_hwfault` 是 ZERO/SEEN 枚举，他要求「数值项就用
        #   数表示」。本字段 = 四路计数的**合计**（内核通道 memacc + coredump，车日志通道
        #   memacc + coredump）。它与枚举 token **同源**（token 就是这四路的布尔化）=> 属
        #   同义项合并：页面只显示这一个数字，token 与四路分量进 title。
        #   任一路取不到（内核日志不可读 => NA）即 null => 页面显示 -- 且不置色 ——
        #   部分和会假装「更干净」（T7/T13 同族：取不到值不得当条件满足）。
        "gpu_fault_n": gsum("MEMACC_KLOG", "COREDUMP_KLOG", "CARLOG_MEMACC", "CARLOG_COREDUMP"),
        "mem_pressure": s("MEM_PRESSURE"),
        "mem_avail_pct": f("MEM_AVAIL_PCT"), "commit_pct": f("COMMIT_PCT"),
        "pagefault": i("PAGEFAULT"), "pagefault_t": i("PAGEFAULT_T"), "vmfail": i("VMFAIL"),
        # 第 4 维（硬件访问故障）：探针只判「看见/没看见」，两通道各记一份
        "gfx_fault": s("GFX_FAULT"),
        "hwfault_klog": s("GPU_HW_KLOG"),
        "memacc_klog": i("MEMACC_KLOG"), "coredump_klog": i("COREDUMP_KLOG"),
        "carlog_memacc": i("CARLOG_MEMACC"), "carlog_coredump": i("CARLOG_COREDUMP"),
        # [v31f] 车日志通道的覆盖度（详见上方令牌转抄处注释）。
        #   carlog_scan_n = 本 boot 内被扫到的车日志份数；0 => 本 boot 还没有已收车的
        #   落盘日志（**不是**「没有故障」）。carlog_fault_files = 命中的文件名清单
        #   （探针空时给字面 <none>）。两者都只是**如实转抄**，不参与任何判决。
        "carlog_scan_n": i("CARLOG_SCAN"),
        "carlog_fault_files": s("CARLOG_FAULT_FILES"),
        "box": s("BOX"), "docker": i("DOCKER"), "klog_src": s("KLOGSRC"),
        # [v33] BOX 的三路明细（探针 BOX_STATE 括号里那三个数，此前被 cut 丢掉）。
        #   页面据此把写死的「有车」改成**按实际在飞的东西说话**：只有 box_car>0
        #   才叫「有车」，只有 serve 就叫 serve，只有任务容器就叫容器。
        #   三路任一路取不到 => 页面一律用不指名的「作业」，**不猜**。
        "box_car": i("BOX_CAR"), "box_serve": i("BOX_SERVE"), "box_ctr": i("BOX_CTR"),
        # [v33] GPU 利用率（宿主 sysfs gpu_busy_percent，按 vendor 认卡现读）。
        #   null = 该节点不存在或读不到 => 页面 -- 且不置色。这是全链**唯一**能回答
        #   「A 卡在不在算」的读数（探针侧无此读数，见 README §9.18 B 类）。
        "gpu_busy_pct": i("GPU_BUSY"),
        # [v36] 常驻 strata serve 进程数（0=没有；null=ps 没跑成，页面 --）。页面据此
        #   在 VRAM_LEAK 时把归因写进判决格（"泄漏"二字是否成立取决于它，探针不参与）。
        "strata_serve": i("STRATA_SERVE"),
        # [v37] 生产推理服务包装进程数（serve/server.py --engine strata）。与 strata_serve
        #   取或构成「有服务在用卡」的判据；两者都是**原始计数**，判决仍归探针。
        "prod_srv": i("PROD_SRV"),
    },
    "boot": {
        # 开机闸门（族 A）。判据与 routeK `run/_rk_bootgate.sh` 等价（fail-closed）：
        # 六项各取 dmesg / journalctl -k -b 0 双路，**两路齐才算**、取两路最大值
        # => 任一路非 0 即非干净；任一路拿不到日志则该维为 null（页面 -- 且不置色，
        # 不放行任何部分读数）。[v31d 审计修复] 旧实现取「非 None 最大值」，
        # 单路 NA 时照样出绿点 —— 那是 fail-open，与 bootgate 相反。
        # src_* = 每一路实际走过的取数通道（none = 该路拿不到日志）。
        "src_d": bt.get("B_d_SRC"), "src_j": bt.get("B_j_SRC"),
        "lines_d": gnum(bt, "B_d_LINES"), "lines_j": gnum(bt, "B_j_LINES"),
        "sdma1": pick(pickg("d", "sdma1"), pickg("j", "sdma1")),
        "page1": pick(pickg("d", "page1"), pickg("j", "page1")),
        "ring": pick(pickg("d", "ring"), pickg("j", "ring")),
        "ite": pick(pickg("d", "ite"), pickg("j", "ite")),
        "lockup": pick(pickg("d", "lockup"), pickg("j", "lockup")),
        "lbar": pick(pickg("d", "lbar"), pickg("j", "lbar")),
        # [v32] 证据充分性（行数是否够）必须一并报出 —— 否则页面「六项全 --」与
        #   「探针没跑」看起来一样。
        "ev_d": EV_D, "ev_j": EV_J, "ev_th_d": EV_TH["d"], "ev_th_j": EV_TH["j"],
        "raw_d": route(bt, "d"), "raw_j": route(bt, "j"),
        # 本 boot 已发车数：标记文件 `车数 boot_id`，取首字段；通路 OK 且文件为空/非数
        # => 0（本 boot 未发车）。通路没跑起来 => null（不冒充 0）。
        # [!] 空值归 0（= 未发车），只有**通路没跑起来**才留 null —— 上一版把这两种
        #     情形混成一个 null，页面会把「本 boot 一台车都没发」显示成 `--`。
        "carf": ((gnum(tg, "T_CARF") or 0) if tg.get("T_ROUTE_OK") == "1" else None),
        "carf_raw": (tg.get("T_CARF") or None) if tg.get("T_ROUTE_OK") == "1" else None,
        # [v32 裁定 L3] boot_id 校验的产物：carf_boot = 标记文件里记的 boot_id，
        #   carf_stale = 1 表示「有车数但 boot_id 对不上」=> 那是**上一个 boot 的残留**，
        #   此时 carf 已按 0（本 boot 未发车）输出，残留事实单独报出。
        "carf_boot": (tg.get("T_CARF_BOOT") or None) if tg.get("T_ROUTE_OK") == "1" else None,
        "carf_stale": (gnum(tg, "T_CARF_STALE") if tg.get("T_ROUTE_OK") == "1" else None),
        "boot_id": (tg.get("T_BOOT_ID") or None) if tg.get("T_ROUTE_OK") == "1" else None,
    },
    "tgt": {
        # 目标态四项（族 B）。甲/乙的期望值由**页面**给定（与 Z0 三条同规：非探针产出）。
        "cmdline_pt": gnum(tg, "T_CMDLINE_PT"),   # 甲：/proc/cmdline 里 iommu=pt 的个数
        "vum": gnum(tg, "T_VUM"),                 # 乙：/sys/module/amdgpu/parameters/vm_update_mode
        "conf_md5": tg.get("T_CONF_MD5") or None, # 配置：/etc/modprobe.d/amdgpu.conf
        "kfd_proc": gnum(tg, "T_KFD_PROC"),       # 现场：打开 KFD 的进程数（收车后应归 0）
    },
    "sys": {
        "alarms_warn": i("AL_W"), "alarms_crit": i("AL_C"), "alarms_eval": i("AL_N"),
        "alarms_undef": i("AL_U"), "alarms_uninit": i("AL_I"),
        "swap_used": i("SWAP_USED"), "swap_total": i("SWAP_TOTAL"),
        "load1": f("LOAD1"), "uptime": i("UP"),
    },
    # [v37] /proc/meminfo 全量（字节）。页面据此算「已用 = total - available」并把缓存单列，
    #   不再从 system.ram 四维反推（那条路漏 SReclaimable，且 used 口径与 free 不一致）。
    "mem": SJ.get("mem") or {},
    # [v37] 每块盘的 SMART 关键量（温度 / 寿命剩余 / 已写入 / 通电小时 / 备用块）。
    #   disks 下按设备名索引；取不到时该盘内是 {"err": "..."} => 页面 -- 且不置色。
    "ssd": SJ.get("ssd") or {},
}
out = sys.argv[1]
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write("\n")
print("COLLECT_JSON", out, os.path.getsize(out))
PY
RC=$?

if [ "$RC" -eq 0 ] && [ -s "$TMP" ]; then
  mv -f "$TMP" "$OUT" || { rm -f "$TMP"; echo "COLLECT_ABORT=mv_failed"; exit 9; }
  echo "COLLECT_OK $OUT $(wc -c < "$OUT") bytes verdict=$(tok POLLUTION_VERDICT | cut -d' ' -f1)"
else
  rm -f "$TMP"
  echo "COLLECT_ABORT=build_failed rc=$RC"
  exit 9
fi
