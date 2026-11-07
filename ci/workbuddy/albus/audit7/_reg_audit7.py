import io, shutil, time

REG = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
shutil.copy2(REG, REG + '.bak_audit7_' + time.strftime('%Y%m%d_%H%M%S'))

lines = io.open(REG, encoding='utf-8-sig').read().splitlines()
header, body = lines[0], lines[1:]

out = []
hit = {'P91': 0, 'P95': 0, 'P96': 0}

for ln in body:
    f = ln.split('\t')
    assert len(f) == 11, (len(f), f[0])

    if f[0] == 'P91':
        f[9] += (' 【AUDIT7 P2-1/P2-2 更正 2026-10-25 06:3x】三点必须同时读：'
                 '① 46.35 是四次 run（46.13/46.44/46.90/46.26）的**中位数**，分项却取自单次 run（46.13），'
                 '按公布值相加是 46.11，差 0.24 属「中位数 vs 单次」，不是算错；'
                 '② 百分比列的分母是 **46.1（单次）**，不是 46.35（验证：10.08/46.1=21.9%、7.42/46.1=16.1%、6.13/46.1=13.3% 全对）；'
                 '③ **本基线测于 governor=performance**（10-22 至 10-25 06:0x），生产现为 schedutil，见 P97。'
                 '另：日志现存 M 档 GPU-stages total 为 45.97/46.44/47.20/54.03，无 46.35 —— 原始四条未留档，46.35 不可单独复现。')
        f[10] = ('supersedes P87；**使用前必读 evidence 的三点更正**：派生的中位数不可当单次值、百分比分母是 46.1、'
                 '且 governor 口径与现生产不同（P97）')
        hit['P91'] += 1

    elif f[0] == 'P95':
        f[9] += (' 【AUDIT7 更正 2026-10-25 06:3x】① 16.1% 的分母是 **decode GPU stages 的 46.35**（GPU-only），'
                 '不是墙钟 51.58；跨口径比较会低估约 11%。'
                 '② 「13.6% 占用」错 2 倍：gfx906 `Wavefront Size: 64`，256 线程 = 4 个 wavefront（非 8 warp），'
                 '每 CU 容量 40 wavefront => 10%，聚合 **6.8%**（`rocminfo` 实测 60 CU / Max Work-item 2560）。'
                 '③ 根因细分：**主因是 grid=41 < 60 CU**；shared 34 KB 在「块数 < CU」时**不是约束**，'
                 '所以 `W788` 的路径 A（降 TILEV 提高每 SM 块数）结构上无效，见 P96。')
        f[10] = ('保留；占用率数值已更正为 6.8%，且「shared 是约束」这一推论撤销（块数才是）')
        hit['P95'] += 1

    elif f[0] == 'P96':
        f[5] = 'REJECTED'
        f[9] += (' 【AUDIT7 P1-2/P1-3 判定 2026-10-25 06:3x，源码级反证，**未实测**】路径 A（TILEV 2560->1280）'
                 '结构上不可能有效，三条独立理由：'
                 '① `DOWN_BLOCKS = LR/WARPS` 与 TILEV 无关，grid 恒 41，而 CU 有 60 => 减小 shared 不会让第二块落到同一 CU；'
                 '② 小 tile 省的是「8 token 装进一次 launch」，实测 chunk = 64KiB/(tv*4) 为 6(tv=2560)/8(tv=1280)，'
                 '而我们的 avg T=3.33-3.47，两种 tile 都只有一次 launch；'
                 '③ `TQ = TILEV/8/32` 从 10 降到 5，每 lane 在飞权重块减半，方向为负。'
                 '=> 臂 B 不必跑；要治 19 个 CU 空转只能**加块数**（split-K 或行切细），见 `W789_R5_TILEV_VERDICT.md §5`。')
        f[10] = ('REJECTED（源码级反证，未实测）；镜像/容器留档勿用；后续只做「加块数」方向')
        hit['P96'] += 1

    out.append('\t'.join(f))

assert all(v == 1 for v in hit.values()), hit

new_row = '\t'.join([
    'P97', 'decode', '基线 governor 口径', 'performance(历史) / schedutil(现生产)', 'measure', 'REFERENCE',
    '', '', '',
    ('【AUDIT7 P1-4 2026-10-25 06:3x】`performance` 是 W776（10-22）为测预填影响而设，'
     '**直到 06:0x 才改回 `schedutil`**。期间的 P91（04:3x）、W788（05:2x）、R5 臂 A（05:5x）**全部测于 performance 下**。'
     '现生产：`intel_cpufreq`（passive）、44 核全 `schedutil`、无持久化文件（重启默认即 schedutil）。'
     '后果：现存 decode 基线（46.35/47.35/39.90、51.58、53.17、53.02）其系统状态与生产不一致，'
     '任何拿它们做对照的 A/B 都会把 governor 差异算进改动里。'),
    ('口径约束：任何 A/B 必须当场记录 governor 并前后一致；若要长期以 schedutil 为基线，'
     '需在下次必要重启后重测三档（不为此单独重启）'),
])

out.append(new_row)
io.open(REG, 'w', encoding='utf-8', newline='\n').write(header + '\n' + '\n'.join(out) + '\n')
print('register patched: P91/P95/P96 updated, P97 added; rows=%d' % (len(out) + 1))
