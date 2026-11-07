set +e
C=strata166-407
L=/data/strata-huihui-ud-iq4_xs.log
echo "===== [1] 生产 env 全量（7 条） ====="
docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}'
echo
echo "===== [2] 配置里的 env 段（引擎实际收到的） ====="
python3 -c "
import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
e=d.get('env') or {}
for k in sorted(e): print('  %-28s = %s' % (k, e[k]))
print('  env_n =', len(e))
"
echo
echo "===== [3] 关键：表是否真的在生效（tuned_launches / fallbacks） ====="
docker exec "$C" bash -lc "grep -a 'rocBLAS tuning' $L | tail -6"
echo "--- tuned_launches 出现次数:"
docker exec "$C" bash -lc "grep -ac 'tuned_launches' $L || echo 0"
echo
echo "===== [4] f16 prompt 路径的痕迹 ====="
docker exec "$C" bash -lc "grep -aiE 'prompt f16|f16 prompt|HIP_PROMPT_F16|f16_inplace|prefill gemm: (strata|rocblas)' $L | tail -8"
echo
echo "===== [5] 源码：STRATA_HIP_PROMPT_F16 的默认值与作用 ====="
grep -n "STRATA_HIP_PROMPT_F16" /home/albus/strata166/gfx029/src/prefill/*.cu /home/albus/strata166/gfx029/src/prefill/*.cpp /home/albus/strata166/gfx029/src/prefill/*.hpp 2>/dev/null | head -12
