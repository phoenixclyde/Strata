#!/bin/bash
# W840-02 复核审计指控（只读，不改任何东西）
D=/home/albus/strata166/data
W=/home/albus/strata166/gfx906
echo "===== [1] 四条 KL 臂的 md5（指控：EG 与 E0 相同=开关没下发） ====="
md5sum $D/w833kl/E0.tsv $D/w833kl/E0b.tsv $D/w833kl/EM.tsv $D/w833kl/EG.tsv 2>/dev/null
echo "--- EG 臂配置里的 env ---"
python3 -c "import json;print(sorted((json.load(open('$D/w833_egdn.json')).get('env') or {}).items()))" 2>/dev/null || echo "cfg missing"
echo
echo "===== [2] P0-a 样本：sha 数与截断 ====="
python3 - <<'PY'
import json,io,collections
p="/home/albus/strata166/data/w832_tune_results.jsonl"
rs=[json.loads(l) for l in io.open(p,encoding="utf-8") if l.strip() and "tok_per_ms" in l]
print("records",len(rs))
sh=collections.Counter(r["sha"] for r in rs)
print("distinct sha",len(sh),"max share %.1f%%"%(100*sh.most_common(1)[0][1]/len(rs)))
short=[(r["axis"],r["value"],r["completion"]) for r in rs if r["completion"]!=512]
print("non-512:",short)
PY
echo
echo "===== [3] pool-workers: read1300 逐对比 ====="
python3 - <<'PY'
import json,io
rs=[json.loads(l) for l in io.open("/home/albus/strata166/data/w834_pool.out",encoding="utf-8") if l.strip().startswith("{")]
for arm in ("base","pw13"):
    v=[r["read_ms"] for r in rs if r["arm"]==arm and r["note"]=="read1300"]
    print(arm,"read1300",v)
PY
echo
echo "===== [4] 入口现状：n2 vs n3 ====="
for f in strata-0.1.54n2 strata-0.1.54n3; do
  B=/home/albus/strata166/data/bin/$f
  printf "  %-20s apply=%s banner=%s exact=%s\n" "$f" \
    "$(nm -C $B 2>/dev/null | grep -c apply_arch_defaults)" \
    "$(grep -a -c 'MI50-class' $B 2>/dev/null)" \
    "$(grep -a -c 'exact speed switches' $B 2>/dev/null)"
done
echo "--- 生产配置 ---"
python3 -c "import json;c=json.load(open('$D/strata-huihui-ud-iq4_xs.json'));print('  exe',c['exe'],'env',len(c['env']),sorted(c['env']))"
echo
echo "===== [5] 分支真相：commit 数 / +行 / 推送状态 ====="
cd $W || exit 1
echo "  shallow? $(git rev-parse --is-shallow-repository)"
echo "  HEAD $(git rev-parse --short HEAD)  count $(git rev-list --count HEAD 2>/dev/null)"
echo "  vs origin: $(git rev-list --count origin/gfx906/0.2.8-mi50..HEAD 2>/dev/null) unpushed"
git log --oneline -4 | sed 's/^/    /'
echo "  diff vs c62d5e3a:"; git diff --stat c62d5e3a..HEAD 2>/dev/null | tail -2 || echo "    (c62d5e3a not present in shallow clone)"
echo
echo "===== [6] 门禁项数与假绿标记 ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>/dev/null | grep -cE 'OK$'
echo "  BW_REFRESH_S 在上游 main 里: $(git -C $W show c62d5e3a:serve/telemetry.py 2>/dev/null | grep -c BW_REFRESH_S)"
echo "  cudaStreamCreateWithPriority 在上游 main 里: $(git -C $W show c62d5e3a:include/strata/platform/hip_compat/strata_hip.h 2>/dev/null | grep -c cudaStreamCreateWithPriority)"
echo
echo "===== [7] 显存百分比口径 ====="
python3 -c "print('  33.5/34.3 = %.2f%%' % (100*33.5/34.3))"
grep -a 'used' $D/w839_A.log 2>/dev/null | head -2 | cut -c1-120
