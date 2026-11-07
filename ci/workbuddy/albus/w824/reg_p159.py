import csv, shutil

P = 'deploy/params/PARAM_REGISTER.tsv'
shutil.copyfile(P, 'albus/w824/PARAM_REGISTER.bak4.tsv')
rows = list(csv.reader(open(P, encoding='utf-8'), delimiter='\t'))
hdr, body = rows[0], rows[1:]

row = ['P159', 'ENV', 'STRATA_HC_Q8=1 的实际数据来源（--compat-bf16 舍入是否被吃到）',
       '1（读 GGUF 原始 Q8_0）', 'precision/compat', 'CONFIRMED',
       '需 --native（native_dense_gguf 非空）+ 单卡', '—', 'P152',
       'W824：`generate.cpp:3809-3812` 在 `native_dense_gguf` 为空时**默认取 `--native` 的 GGUF**，我们一直传 --native；'
       '`native_dense.cpp:398-424` 的 `if (hc_q8_env()) for (gguf.tensors())` 只挑 `type==8` 且 `hc_q8_name()` 的张量，'
       '**直接 cudaMemcpy GGUF 的原始 Q8_0 字节**到 hc_q8 缓冲；同文件 426 起的"再量化"分支只处理 `ref.hc_q8==nullptr`（GGUF 里没有的行）。'
       '日志佐证：`216 MiB of weights loaded from /data/packs/ud-q4_k_xl (495 canonical tensors skipped: served natively)`，'
       '而 194 个 hc 张量的 BF16 副本合计 1.19 GiB ⇒ **包里那 194 份舍入值从未被读**。'
       '⇒ 打包器的 `--compat-bf16` 舍入（compat-bf16.json 记 194 hc + 1 ple_value，source_type Q8_0）在我们这种 '
       '"--native + HC_Q8" 运行下**不生效**；文档说的 6-9% ppl 差距只适用于 pack-only 运行或 HC_Q8 关闭（上游 setup 在 AMD 上不写这个开关）。',
       '结论确认：我们吃的是原始 Q8_0，不吃舍入。残余仅 `blk.1.ple_value.weight`（6,553,600 B BF16，非 hc_q8 名字）；'
       'dense.bin 里那 1.19 GiB BF16 hc 副本是死重（永不读，不值得清）。不建议为此改源码。']

body.append(row)
with open(P, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(hdr); w.writerows(body)
print('rows', len(body), 'bad_cols', [r[0] for r in body if len(r) != 11])
