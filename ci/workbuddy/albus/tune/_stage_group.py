# -*- coding: utf-8 -*-
"""解析 decode GPU stages 行，按语义分组，输出 ms/window 与 per-token。
数据来源：2026-10-25 04:2x-04:4x，生产 = 0.2.4/0.1.49.2，无 --resident-experts，HC_Q8=1。
"""
import re, sys, io

ROWS = {
 "M_21827": ("strata decode GPU stages (ms/window): GDN layers: q8+qkv/q-idx gemv 3.83 conv 0.22 ab 0.99 z 2.63 rec 0.73 out-proj 2.40 router+plan+bell 2.80 shared+quant 2.00 waitA 0.37 VRAM hits 6.67 waitB 0.41 PCIe grp 0.58 waitCPU 0.44 copy+combine 0.61 (gap) 0.06 head 1.94   hc0 norm 0.48   hc0 down 1.33   hc0 up 1.26   hc1 norm 0.06   hc1 down 1.26   hc1 up 1.27 | QSA layers: q8+kv-idx 0.15 k/v+norm-rope 0.43 kv+idx append 0.32 q+q-idx 2.15 scores+topk 1.24 kv-resolve 0.02 attention 2.07 gate 0.12 out-proj 0.80 router+plan+bell 0.94 shared+quant 0.66 waitA 0.13 VRAM hits 2.21 waitB 0.16 PCIe grp 0.19 waitCPU 0.19 copy+combine 0.21 (gap) 0.02   hc0 norm 0.02   hc0 down 0.44   hc0 up 0.42   hc1 norm 0.02   hc1 down 0.44   hc1 up 0.42 | total 46.13 ms/window over 98 windows", 3.33),
 "S_2813": ("strata decode GPU stages (ms/window): GDN layers: q8+qkv/q-idx gemv 4.03 conv 0.22 ab 1.04 z 2.79 rec 0.73 out-proj 2.51 router+plan+bell 2.78 shared+quant 2.06 waitA 0.37 VRAM hits 7.10 waitB 0.41 PCIe grp 0.59 waitCPU 0.34 copy+combine 0.60 (gap) 0.06 head 2.02   hc0 norm 0.51   hc0 down 1.40   hc0 up 1.31   hc1 norm 0.06   hc1 down 1.33   hc1 up 1.32 | QSA layers: q8+kv-idx 0.15 k/v+norm-rope 0.44 kv+idx append 0.33 q+q-idx 2.22 scores+topk 0.76 kv-resolve 0.02 attention 2.12 gate 0.12 out-proj 0.83 router+plan+bell 0.94 shared+quant 0.69 waitA 0.13 VRAM hits 2.34 waitB 0.19 PCIe grp 0.20 waitCPU 0.20 copy+combine 0.21 (gap) 0.02   hc0 norm 0.02   hc0 down 0.46   hc0 up 0.44   hc1 norm 0.02   hc1 down 0.47   hc1 up 0.44 | total 47.35 ms/window over 94 windows", 3.44),
 "L_99387": ("strata decode GPU stages (ms/window): GDN layers: q8+qkv/q-idx gemv 2.93 conv 0.21 ab 0.77 z 1.99 rec 0.76 out-proj 1.88 router+plan+bell 2.77 shared+quant 1.66 waitA 0.37 VRAM hits 4.80 waitB 0.52 PCIe grp 0.53 waitCPU 0.87 copy+combine 0.59 (gap) 0.06 head 1.53   hc0 norm 0.35   hc0 down 1.02   hc0 up 1.04   hc1 norm 0.06   hc1 down 0.97   hc1 up 1.05 | QSA layers: q8+kv-idx 0.13 k/v+norm-rope 0.38 kv+idx append 0.30 q+q-idx 1.82 scores+topk 2.70 kv-resolve 0.02 attention 1.60 gate 0.12 out-proj 0.63 router+plan+bell 0.93 shared+quant 0.55 waitA 0.12 VRAM hits 1.55 waitB 0.18 PCIe grp 0.18 waitCPU 0.32 copy+combine 0.20 (gap) 0.02   hc0 norm 0.02   hc0 down 0.34   hc0 up 0.35   hc1 norm 0.02   hc1 down 0.34   hc1 up 0.35 | total 39.90 ms/window over 17 windows", 2.12),
}

def parse(s):
    body, total = s.split("| total ")
    tot = float(total.split()[0])
    seg = body.split("| QSA layers:")
    gdn, qsa = seg[0], seg[1]
    gdn = gdn.split("GDN layers:")[1].strip()
    def toks(part):
        # 统一把 "hc0 norm 0.48   hc0 down 1.33" 这类空格分隔转成 key/val 对
        out = {}
        raw = re.sub(r"\s+", " ", part).strip()
        keys = ["q8+qkv/q-idx gemv","conv","ab","z","rec","out-proj","router+plan+bell",
                "shared+quant","waitA","VRAM hits","waitB","PCIe grp","waitCPU","copy+combine",
                "(gap)","head","hc0 norm","hc0 down","hc0 up","hc1 norm","hc1 down","hc1 up",
                "q8+kv-idx","k/v+norm-rope","kv+idx append","q+q-idx","scores+topk","kv-resolve",
                "attention","gate"]
        # 逐个用 key 切
        res = {}
        for k in keys:
            m = re.search(re.escape(k) + r"\s+([0-9.]+)", raw)
            if m:
                res[k] = float(m.group(1))
        return res
    g, q = toks(gdn), toks(qsa)
    return tot, g, q

GROUPS = [
 ("expert_flow", ["VRAM hits","waitB","waitCPU"]),
 ("hc_proj", ["hc0 norm","hc0 down","hc0 up","hc1 norm","hc1 down","hc1 up"]),
 ("quant_dense_gemv", ["q8+qkv/q-idx gemv","q+q-idx","q8+kv-idx"]),
 ("router", ["router+plan+bell"]),
 ("attention", ["attention","scores+topk"]),
 ("out_proj", ["out-proj"]),
 ("z", ["z"]),
 ("shared_quant", ["shared+quant"]),
 ("head", ["head"]),
 ("ab_rec", ["ab","rec"]),
 ("kv_misc", ["k/v+norm-rope","kv+idx append","kv-resolve"]),
 ("conv_gate", ["conv","gate"]),
 ("copy", ["copy+combine"]),
 ("pcie", ["PCIe grp"]),
 ("waitA", ["waitA"]),
 ("gap", ["(gap)"]),
]

print("=== ms/window by group ===")
hdr = "%-18s" % "group" + "".join("%12s" % k for k in ROWS)
print(hdr)
data = {}
for name, keys in GROUPS:
    row = []
    for tag, (s, T) in ROWS.items():
        tot, g, q = parse(s)
        v = sum(g.get(k,0)+q.get(k,0) for k in keys)
        row.append(v)
    data[name] = row
    print("%-18s" % name + "".join("%12.2f" % v for v in row))

print("%-18s" % "SUM") ; 
for i, tag in enumerate(ROWS):
    tot, g, q = parse(ROWS[tag][0])
    print("  %-12s total=%.2f  sum_groups=%.2f  diff=%+.2f" % (tag, tot, sum(data[n][i] for n,_ in GROUPS), sum(data[n][i] for n,_ in GROUPS)-tot))

print()
print("=== share of total (%) ===")
print("%-18s" % "group" + "".join("%12s" % k for k in ROWS))
for name,_ in GROUPS:
    row = data[name]
    print("%-18s" % name + "".join("%12.1f" % (v / parse(ROWS[tag][0])[0] * 100) for v, tag in zip(row, ROWS)))

print()
print("=== per-token (ms) ===")
print("%-18s" % "group" + "".join("%12s" % k for k in ROWS))
for name,_ in GROUPS:
    row = data[name]
    print("%-18s" % name + "".join("%12.2f" % (v / ROWS[tag][1]) for v, tag in zip(row, ROWS)))
print("%-18s" % "TOTAL/token" + "".join("%12.2f" % (parse(ROWS[tag][0])[0] / ROWS[tag][1]) for tag in ROWS))
