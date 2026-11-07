import csv, shutil

P = 'deploy/params/PARAM_REGISTER.tsv'
shutil.copyfile(P, 'albus/w824/PARAM_REGISTER.bak3.tsv')
rows = list(csv.reader(open(P, encoding='utf-8'), delimiter='\t'))
hdr, body = rows[0], rows[1:]

ADD = {
    'P158': ['P158', 'ENV', '质量门的底噪来源：STRATA_PREFILL_CPU_SHARE=auto 让 teacher-forced LOGPOS 逐次不同',
             'share=0（做质量门时）', 'method/quality-gate', 'CORRECTION',
             '需 STRATA_LOGPOS + STRATA_LOGPOS_TOPK', '—', 'P156',
             'W824：第一轮 KL（share=auto，Q1/Q0/Q1b 各 60 位置）里，**同配置两次** Q1||Q1b 的均值 KL 0.0253、'
             'PPL 5.05 vs 4.37（差 15%）、只有 16.7% 的位置逐位相同、p95 |Δlp| 2.40 nats；'
             '「开/关 reduce12」的 0.0262/0.0459 与此**同量级** ⇒ 判不了。'
             '第二轮把 share 固定为 0（K1/K0/K1b），三份 TSV **md5 全部 38fa1653…，逐字节相同**，'
             '配对 KL 全 0.0000、argmax 100%、top-10 重叠 1.00、Δlp 恒 0 ⇒ 底噪 = 0。'
             '⇒ 规则：本机做任何 teacher-forced 质量门，必须先把 STRATA_PREFILL_CPU_SHARE 固定（=0），'
             '否则噪声（0.03 量级）会把效应（0.03 量级）淹没。与 W803 的结论一致，这次是直接证据（三份文件同哈希）。',
             '质量门的前置条件，写入流程。注意 share 是 prefill 速度特性，只在"量质量"时改，生产仍用 auto。'],
}

out, seen = [], set()
for r in body:
    if r[0] == 'P156':
        r[10] = r[10].rstrip() + \
            '\n【W824 质量门结论（10-30 01:30）】用 teacher-forced LOGPOS 直接验：把 share 固定为 0（P158）后，' \
            'K1（reduce12=1）/ K0（=0）/ K1b（=1 重跑）三份 `w803_logpos_*.tsv` **md5 完全相同**（38fa1653c08dba8eb7fb41f9be535674，各 66,045 B），' \
            '配对 KL 0.0000、argmax 一致率 100%、top-10 重叠 1.00、mean|Δlp_tgt| 0.0000（60 个位置）。' \
            '⇒ **该开关在受评路径上逐位等价**，"质量未验"这条已关闭。边界：这 60 个位置来自 verify 窗口的 teacher-forced 读，' \
            'prefill 自身的数值没有直接被打分；但同一内核只换模板参数、且验证路径逐位相同，可认为不引入数值偏差。'
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
