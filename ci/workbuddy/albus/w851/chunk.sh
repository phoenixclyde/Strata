set +e
D=/home/albus/strata166/gfx029
echo "===== [1] f16_inplace 的 T 是什么（调用点） ====="
grep -rn "f16_inplace" "$D/src/prefill/"*.cpp "$D/src/prefill/"*.cu "$D/include" 2>/dev/null | head -12
echo
echo "===== [2] prefill chunk 大小（策略/参数） ====="
grep -rn "prefill_chunk\|chunk_tokens\|chunk_size\|kChunk" "$D/src/prefill/prefill.cpp" 2>/dev/null | head -14
echo "--- 日志里的 chunk 痕迹:"
docker exec strata166-407 bash -lc "grep -aiE 'prefill.*chunk|chunk.*token' /data/strata-huihui-ud-iq4_xs.log | tail -5"
echo
echo "===== [3] 生产 args 里与 prefill 有关的 ====="
python3 -c "
import json;a=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))['args']
for i,x in enumerate(a):
    if 'prefill' in x or 'chunk' in x or 'batch' in x: print('  ', x, a[i+1] if i+1<len(a) and not a[i+1].startswith('--') else '')
"
