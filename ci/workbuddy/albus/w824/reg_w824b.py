import csv, shutil

P = 'deploy/params/PARAM_REGISTER.tsv'
shutil.copyfile(P, 'albus/w824/PARAM_REGISTER.bak2.tsv')
rows = list(csv.reader(open(P, encoding='utf-8'), delimiter='\t'))
hdr, body = rows[0], rows[1:]

ADD = {
    'P156': ['P156', 'ENV', 'STRATA_GFX906_ATTN_REDUCE12=1（attn 分块的另一种归约）', '1', 'prefill-attn',
             'ADOPTED', '需 query swizzle + INT8 池（我们 k8v4 满足）', '—', 'P152/P155',
             'W824：两对独立配对（N1/A1 与 N1b/A1b），同容器内重复性 **0.1%**。'
             '4563 token 的 prefill GPU timeline：N1 7034 / N1b 7027 → A1 **6765** / A1b **6757**，即 **−3.8%**（−269 ms）。'
             '相位定位精确：`qsa attn` 1089/1091 → **810/811 ms（−25.6%）**，其余相位逐项不变'
             '（gate/up 1534→1538、gemm down 988→989、gdn 801→801、hc read 586→586、dequant 611→613、ple 37→32）。'
             'wall 同步：1453 −1.5%、2498 −2.6%、4568 −3.7%。'
             '解码不变：tok/s 45.9/44.5 对 45.8/45.3；ms/window 38.2/37.7 对 36.9/36.7 但 tokens/window 也降（1.79/1.66 对 1.65/1.64），净持平。'
             '生产冒烟（新容器、无 TIMING）：4568 token **7.07 s**，臂内受控基线 7.73 s。',
             '采纳。**质量未验**：换的是归约顺序（`attn_chunk_kernel<3,false,true,true>`），不保证逐位等价，'
             '下一步应量 teacher-forced KL（7 vs 0 那套同法）。回滚：删掉该 env。'],
    'P157': ['P157', 'ENV', 'STRATA_DENSE_MMQ=1（dense GEMM 走 MMQ）', '未启用', 'prefill-gemm',
             'N/A', '需 STRATA_PREFILL_MMQ=ON，而它要求 STRATA_ENABLE_HIP=ON', '既有 gfx906 构建（STRATA_HIP_GFX906）', '—',
             'W824：`prefill/gemm.cu:1205` 的 `native_mmq()` 整个函数包在 `#if defined(STRATA_PREFILL_MMQ) && defined(__HIPCC__)` 里；'
             'CMakeLists 是 `option(STRATA_PREFILL_MMQ … OFF)`，只有 ON 时才 `target_compile_definitions(... STRATA_PREFILL_MMQ=1)`；'
             '而 `if(STRATA_PREFILL_MMQ AND NOT STRATA_ENABLE_HIP) message(FATAL_ERROR)`，'
             '同时 AMD_HIP.md 明确 `STRATA_HIP_GFX906` **拒绝** `STRATA_ENABLE_HIP`（一次只允许一个 HIP 后端）。'
             '⇒ 在 gfx906 上结构性不可用，不必花重启去试。（二进制里那条 "dense MMQ on" 字符串来自别处的同名字面量，不代表该路径被编入。）',
             '不适用。gfx906 的 K-quant 专家 MMQ 走的是另一条 `STRATA_MMQ_KQUANTS`（已开）。'],
}

out, seen = [], set()
for r in body:
    if r[0] == 'P153':
        r[10] = r[10].rstrip() + '\n【W824 第三测】V1 臂（同法、带 decode timing）：tok/s 中位 45.1，基线 N1 45.9/N1b 44.5，' \
                 'ms/window 38.1 对 38.2/37.7 ⇒ 第三次得到"无差异"。三测一致，定案。'
    if r[0] in ADD:
        seen.add(r[0]); out.append(ADD[r[0]])
    else:
        out.append(r)
for k, v in ADD.items():
    if k not in seen:
        out.append(v)

with open(P, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(hdr); w.writerows(out)
print('rows', len(out), 'bad_cols', [r[0] for r in out if len(r) != 11])
