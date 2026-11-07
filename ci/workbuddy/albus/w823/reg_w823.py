import csv, shutil

P = 'deploy/params/PARAM_REGISTER.tsv'
shutil.copyfile(P, 'albus/w823/PARAM_REGISTER.bak.tsv')
rows = list(csv.reader(open(P, encoding='utf-8'), delimiter='\t'))
hdr, body = rows[0], rows[1:]

ADD = {
    'P150': ['P150', 'CONFIG', 'model_name / aliases（换权重后名字没跟着改）',
             'qwen3.8-flash-next-ud-q4_k_xl-abliterated + alias 旧名', 'identity', 'FIXED',
             '仅元数据，需重启生效', '—', '—',
             'W824：权重早就是 UD-Q4_K_XL（引擎日志 `--pack /data/packs/ud-q4_k_xl --native ...UD-Q4_K_XL-00001-of-00004`、'
             'arena 71.7 GiB、blob 3.99 MB），但 `/v1/models` 仍报 `...ud-iq4_xs-abliterated`。'
             '根源是配置里显式的 `model_name` 字段（server.py:8072 `default_model_name` 只在该字段缺失时才按 family 取名），'
             '不是从权重推导。已改为与权重一致，并把旧名放进 `aliases`（server.py:3828，`model_names()` 含别名，'
             '6937 行会拒绝不在其中的 model）——否则客户端里已填旧名的会被 model 校验拒掉。',
             '元数据偏差，不影响推理；改名必须同时留 alias。'],
    'P151': ['P151', 'ENV', 'STRATA_FILE_CACHE_OLD_RULE', '保持默认（gfx906=旧规则）', 'file-cache', 'REJECTED',
             '—', '—', 'PLE 常驻 / 竞技场载入', 
             'W823：AMD_HIP.md 写明 gfx906 **故意**保留旧的文件层缓存规则——MI50 上内核回收 HMM 追踪的 arena 时 ROCm 队列会被挂起'
             '（#1752，KevinX8：文件层不再冲刷页缓存后 prompt 46 -> 360 tok/s）。`=0` 会把这个保护拿掉。'
             '这与 W810「55.43 GiB 竞技场缓冲流冲掉 26.8 GiB PLE 表」是同源现象 ⇒ 是设计取舍，不是 bug。',
             '不要设 0；要 PLE 常驻只能加内存或停掉占 52 GB 的 ComfyUI。'],
}

out = []
seen = set()
for r in body:
    i = r[0]
    if i == 'P146':
        r[5] = 'DEFERRED'
        r[10] = (r[10].rstrip() +
                 '\n【W823 复核（10-29，换权重之后）】上游仍无 x86 Qwen 新引擎：最新 release 0.2.7（引擎 0.1.52）；'
                 'tag v0.2.7.1 = 引擎 0.1.53，但其 127 提交/132 文件里引擎面 32 个文件全是 dsv41(DeepSeek)/Metal/'
                 'nv_defaults/sm_121(DGX Spark)，零个 x86 Qwen HIP 改动；main 也停在 0.1.53，自 10-28 08:11 起无提交。'
                 '**K-quant 路径两版几乎逐字节相同**（我们现在跑的就是这条路）：`mmq_kq_loader.cpp` 124->124 行 +-0；'
                 '`moe_mmq.cu` 的 K-quant 分派未变，新增融合 swiglu 与 trellis 类型均在 `#if !defined(__HIPCC__)` 或 SM60 专用；'
                 '`native_mmvq.cu` 673 行改动**全部在 `#if !defined(__HIPCC__)` 内**，HIP 只多一个空桩；'
                 '`expert_cache.cpp` 95 行是 Windows/NVML + STRATA_EXPERT_NIBBLE；45 个引擎文件的补丁里含 HIP/gfx906 的新增行为 0。'
                 '唯二实质项：`STRATA_PLE_AUTO_RAM`（0.2.7 默认开，准入需 表26.8+竞技场71.7+headroom≈105 GB 对分配前可用，'
                 '本机常态 60 余 GB ⇒ 必拒，回落 direct，与今天一致）；#3602 PLE reader 挂死 / #1503 会话 KV 串用（正确性，非速度）。'
                 '⇒ 维持不升级。')
    if i not in ADD:
        out.append(r)
    else:
        seen.add(i)
        out.append(ADD[i])
for k, v in ADD.items():
    if k not in seen:
        out.append(v)

with open(P, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(hdr); w.writerows(out)
print('rows now', len(out), 'added', [k for k in ADD if k not in seen or k in ADD])
bad = [r[0] for r in out if len(r) != 11]
print('bad cols', bad)
