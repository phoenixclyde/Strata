# -*- coding: utf-8 -*-
"""Append P201 (the patch-loss incident + restoration) and P202 (the upgrade gate)."""
import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
lines = io.open(P, encoding='utf-8').read().rstrip('\n').split('\n')
head = lines[0].split('\t')

rows = [
    ['P201', 'INCIDENT',
     '本地补丁被覆盖式升级丢掉：CMakeLists 的 W793/W776 + serve/telemetry.py 的 TEL-PCIE；已全部恢复并验证',
     '已恢复：引擎 strata-0.1.54n2 + 镜像 strata-gfx906:0.2.8p1',
     'build', 'FIXED', '—', '—', 'P105/P107/P181/P186',
     '机械三方比对（上游 v0.2.7.1 5205 文件 / v0.2.8 5229 文件 vs src0271 7973 / src028 8002）：'
     'src0271 中 94 个文件与 v0.2.7.1 不同（=我们的改动），74 个保住、20 个被 0.2.8 覆盖；'
     '20 个里 19 个是"我们的树本就比 tag 旧"（README/INSTALL/metal/dsv41，diff 全负），'
     '只有 CMakeLists.txt（+18/-1）载有功能补丁：W793（gfx906 接 rocBLAS）与 W776（dflash2 只给该文件加 STRATA_USE_HIP）。'
     '另：serve/telemetry.py 的 TEL-PCIE（BW_REFRESH_S/_Amd.bw/_bw_loop/name 的 FRU 校验）在 10-27 升 0.1.53 时已丢。'
     '证据：构建日志 "private field rocblas_state_ is not used"（W793 缺失）→ 恢复后归零；'
     'build-028r/build.ninja 中 dflash2.cpp 的 DEFINES 含 -DSTRATA_USE_HIP=1（W776）；'
     '/metrics 重新出现 gpu_pcie_rx_mb（TEL-PCIE）；decode 46.27 tok/s 无回归；'
     'TTFT 常数项 1206→843 ms（边际不变）。W794 未丢（标记仍在 qsa_decode_attn.cu）。自加 2824 文件无一丢失。',
     '已修：见 deploy/W830_PATCH_LOSS_INCIDENT.md'],
    ['P202', 'PROCESS',
     '升级门禁：清单 + 门禁脚本 + "新树 vs 旧树"比对，三条硬规矩',
     '升级/重编/换镜像后必跑 verify_patches.sh',
     'process', 'ADOPTED', '—', '—', 'P201',
     '根因两条：(1) 整文件覆盖式升级，改动落在上游也会改的文件里就被静默覆盖；'
     '(2) 昨晚的自检比的是 src028 vs 上游 0.2.8 —— 被覆盖的文件"看起来等于上游"因而判成正常，'
     '正确比法是 src028 vs src0271（旧树）。规矩：①deploy/patches/LOCAL_PATCHES.tsv 为唯一清单，'
     '清单内文件一律不整文件覆盖、要 3-way 合并；②任何升级/重编/换镜像后跑 albus/w830/verify_patches.sh'
     '（8 项：树标记、build.ninja、镜像内文件、部署二进制 md5），GATE FAIL 不许部署；'
     '③两条金丝雀：构建不得出现 rocblas_state_ not used，-DSTRATA_USE_HIP=1 只许挂 dflash2.cpp。',
     '已落地，当前 8/8 PASS'],
]
for r in rows:
    assert len(r) == len(head), (len(r), len(head))
    lines.append('\t'.join(r))
io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('lines', len(lines))
for l in lines[-2:]:
    f = l.split('\t')
    print(f[0], '|', f[5], '|', f[2][:56])
