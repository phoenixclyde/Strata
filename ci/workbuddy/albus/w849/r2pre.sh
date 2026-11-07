set +e
C=strata166-407
echo "===== [1] 专家缓存是否已经"全驻留、无淘汰" ====="
docker exec "$C" bash -lc 'grep -aE "expert cache auto|expert cache [0-9]+ slots|PROFILE|no eviction|evict" /data/strata-huihui-ud-iq4_xs.log | tail -6'
echo
echo "===== [2] /metrics：缓存与 PCIe 读量 ====="
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); e=d['engine']; h=d['hardware']; t=d['totals']; cc=d.get('conversation_cache',{})
print('  expert_slots      =', e.get('expert_slots'), '/ primary', e.get('expert_slots_primary'))
print('  expert_cache_mib  =', e.get('expert_cache_mib'))
print('  arena_mib         =', e.get('arena_mib'))
print('  pcie_frac         =', e.get('pcie_frac'))
print('  gpu_pcie_rx_mb    =', h.get('gpu_pcie_rx_mb'), '  (累计/窗口? 见 history)')
for k in ('evictions','evicted','misses','hits'):
    if k in cc: print('  cc.%s ='%k, cc[k])
print('  requests 记录数   =', len(d.get('requests',[])))
print('  totals.requests   =', t.get('requests'), ' prompt_tokens', t.get('prompt_tokens'), ' output', t.get('output_tokens'))
"
echo
echo "===== [3] 近期每条请求的命中率与 PCIe 占比 ====="
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin)
rs=d.get('requests',[])[-8:]
for r in rs:
    print('  ptok=%-6s hit=%-6s pcie_share=%-7s decode=%s' % (r.get('prompt_tokens'), r.get('hit_rate'), r.get('pcie_share'), r.get('decode_tok_s')))
"
echo
echo "===== [4] history 里的 pcie rx 时间序列（看有没有持续读盘/读内存） ====="
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); h=d.get('history',{})
rx=h.get('gpu_pcie_rx_mb') or []
vals=[v for v in rx if isinstance(v,(int,float))]
print('  样本数 =', len(rx), ' 非空 =', len(vals))
if vals: print('  最近 10 个 =', [round(v,2) for v in vals[-10:]], ' 最大 =', round(max(vals),2))
"
echo
echo "===== [5] 专家总数 vs 槽位（判断能不能全驻留） ====="
docker exec "$C" bash -lc 'grep -aE "experts|pack" /data/strata-huihui-ud-iq4_xs.json 2>/dev/null | head -3; python3 -c "
import json;d=json.load(open(\"/data/strata-huihui-ud-iq4_xs.json\"));a=d[\"args\"]
print(\"  --pack\", a[a.index(\"--pack\")+1]); print(\"  --expert-cache\", a[a.index(\"--expert-cache\")+1] if \"--expert-cache\" in a else \"?\")
print(\"  --vram-reserve-mib\", a[a.index(\"--vram-reserve-mib\")+1])"'
ls -l /home/albus/strata166/data/packs/ud-q4_k_xl/ 2>/dev/null | head -4
