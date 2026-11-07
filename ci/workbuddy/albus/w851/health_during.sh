set +e
echo "===== tune 期间生产是否被干扰（requests 增量 + 健康） ====="
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;d=json.load(sys.stdin)
print('  totals.requests =', d['totals']['requests'])
e=d['engine']; print('  slots=%d vram_free=%d' % (e['expert_slots'], e['vram_free_mib']))
"
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 90; echo
echo "--- GPU 占用（tune 在跑）:"
rocm-smi --showuse 2>/dev/null | head -8 || docker exec strata166-407 rocm-smi --showuse 2>/dev/null | head -8
