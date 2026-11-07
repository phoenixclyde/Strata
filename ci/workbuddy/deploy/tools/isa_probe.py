#!/usr/bin/env python3
"""isa_probe.py -- Strata 设备代码的 ISA 反汇编/可编码性探针。

移植自 routeK 的 T5 规程（`_z_src/code_optimization_backlog.md` §T5）：
    objcopy -O binary --only-section=.hip_fatbin <bin> fatbin.bin
    llvm-objdump -d --arch-name=amdgcn --mcpu=gfx906 --disassemble-symbols=<mangled> <co>
    printf '<isa>' | llvm-mc -arch=amdgcn -mcpu=gfx906 -show-encoding   # 必须带反例

它回答的**只有**源码答不了的三件事：
  (1) 编译器实际发射了什么指令（源码只写"意图"）；
  (2) 这张卡能不能编码某条指令（ISA 可用性，与源码无关）；
  (3) 我们跑的这份二进制，和源说的是不是一回事（运行时产物 vs 源）。

源码里写 `__ockl_fdot2` 不代表编出来就是 `v_dot2_f32_f16`（routeK 的反例：
生产 P·V 实为 `v_pk_fma_f16`，1 指令 2 MAC => 照源重写的收益为零）。

用法（在容器内）：
  python3 isa_probe.py --bin /src/build-906/strata --out /tmp/isaprobe
    [--focus REGEX]        只对符号名匹配 REGEX 的 .co 出逐指令反汇编
    [--mcpu gfx906]
产出：
  fatbin.bin / code_XXX.co         抽出的设备 ELF
  isa_symbols.txt                 每个 .co 的符号表（只列 kernel 符号）
  isa_hist.txt                    全量指令助记符直方图（每个 .co）
  isa_focus.txt                   匹配 --focus 的符号逐指令反汇编
  isa_mc.txt                      ISA 可编码性探针（含反例）
"""
import argparse, hashlib, os, re, subprocess, sys, time

OBJCOPY = None
OBJDUMP = None
MC = None
BUNDLER = None


def find_tools():
    global OBJCOPY, OBJDUMP, MC, BUNDLER
    cands = ['', '/opt/rocm/llvm/bin/', '/opt/rocm/bin/']
    for name, var in (('objcopy', 'OBJCOPY'), ('llvm-objdump', 'OBJDUMP'), ('llvm-mc', 'MC'),
                      ('clang-offload-bundler', 'BUNDLER')):
        got = None
        for pre in cands:
            p = pre + name
            try:
                r = subprocess.run([p, '--version'], capture_output=True, timeout=30)
                if r.returncode == 0:
                    got = p
                    break
            except Exception:
                continue
        if got is None and var != 'BUNDLER':      # bundler 缺了可退回 ELF 雕取
            sys.exit('!! 找不到 %s' % name)
        globals()[var] = got


def carve(fatbin, outdir):
    """扫 \\x7fELF 雕出设备 ELF：用 ELF 头算总长（e_shoff + e_shnum*e_shentsize）。"""
    b = open(fatbin, 'rb').read()
    made, i = [], 0
    while True:
        i = b.find(b'\x7fELF', i)
        if i < 0:
            break
        cls = b[i + 4]                    # 1=32bit 2=64bit
        if cls == 2:
            shoff = int.from_bytes(b[i + 0x28:i + 0x30], 'little')
            shentsize = int.from_bytes(b[i + 0x3a:i + 0x3c], 'little')
            shnum = int.from_bytes(b[i + 0x3c:i + 0x3e], 'little')
        else:
            shoff = int.from_bytes(b[i + 0x20:i + 0x24], 'little')
            shentsize = int.from_bytes(b[i + 0x2e:i + 0x30], 'little')
            shnum = int.from_bytes(b[i + 0x30:i + 0x32], 'little')
        total = shoff + shnum * shentsize
        if total <= 0 or i + total > len(b):
            i += 4
            continue
        p = os.path.join(outdir, 'code_%03d.co' % len(made))
        open(p, 'wb').write(b[i:i + total])
        made.append((p, total))
        i += total
    return made


def hist(co, mcpu):
    r = subprocess.run([OBJDUMP, '-d', '--arch-name=amdgcn', '--mcpu=' + mcpu, co],
                       capture_output=True, timeout=300)
    txt = r.stdout.decode('utf-8', 'replace')
    h = {}
    # llvm-objdump 的指令行形如：\t<助记符> <操作数>   // <地址>: <编码>
    # 助记符在**行首**，地址/编码在 **// 注释**里（不要拿地址当行首匹配）。
    for ln in txt.splitlines():
        if not re.search(r'//\s*[0-9A-Fa-f]+:', ln):
            continue
        m = re.match(r'\s*([a-z][a-z0-9_.]*)', ln)
        if m:
            h[m.group(1)] = h.get(m.group(1), 0) + 1
    return txt, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--focus', default=None)
    ap.add_argument('--mcpu', default='gfx906')
    a = ap.parse_args()
    find_tools()
    os.makedirs(a.out, exist_ok=True)
    fb = os.path.join(a.out, 'fatbin.bin')

    # [0] 溯源（ki 技能铁律：dump 只与它的构建一样可靠 -- 必须连同 md5/mtime 记录）
    print('== [0] 溯源 ==')
    blob = open(a.bin, 'rb').read()
    st = os.stat(a.bin)
    prov = ['binary = %s' % a.bin, 'md5 = %s' % hashlib.md5(blob).hexdigest(),
            'size = %d B' % st.st_size,
            'mtime = %s' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)),
            'tool = isa_probe.py']
    for ln in prov:
        print('   ' + ln)

    print('== [1] 抽 .hip_fatbin ==')
    r = subprocess.run([OBJCOPY, '-O', 'binary', '--only-section=.hip_fatbin', a.bin, fb],
                       capture_output=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(fb):
        sys.exit('!! objcopy 失败: %s' % r.stderr.decode('utf-8', 'replace')[:300])
    print('   %s -> %d B' % (fb, os.path.getsize(fb)))

    print('== [2] 解包设备对象 ==')
    # 陷阱（W740 实测）：对**链接后的可执行文件**，`clang-offload-bundler -unbundle` 只吐 1 个成员
    # （本机 .hip_fatbin 里实际有 59 个设备 ELF；ki 技能针对的是每个 .hip.o，而 build-906 里 .hip.o 计数 = 0）。
    # => 可执行文件一律以 **ELF 雕取**为主；bundler 只用于 `-list` 校验目标三元组。
    co = carve(fb, a.out)
    print('   雕出 %d 个设备 ELF' % len(co))
    if not co and BUNDLER:
        r = subprocess.run([BUNDLER, '-list', '-type=o', '-input', fb], capture_output=True, timeout=120)
        for ln in r.stdout.decode('utf-8', 'replace').splitlines():
            if a.mcpu in ln:
                gp = os.path.join(a.out, 'gpu.o')
                r2 = subprocess.run([BUNDLER, '-unbundle', '-type=o', '-targets=' + ln.strip(),
                                     '-input', fb, '-output', gp], capture_output=True, timeout=300)
                if r2.returncode == 0 and os.path.exists(gp):
                    co = [(gp, os.path.getsize(gp))]
                    print('   （雕取为空）退回 bundler -> gpu.o %d B' % os.path.getsize(gp))
                break
    if BUNDLER:
        r = subprocess.run([BUNDLER, '-list', '-type=o', '-input', fb], capture_output=True, timeout=120)
        prov.append('bundle targets = %s' % r.stdout.decode('utf-8', 'replace').strip().replace('\n', ', '))
    open(os.path.join(a.out, 'isa_provenance.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(prov) + '\n')

    print('== [3] 反汇编 + 直方图 ==')
    KEYOPS = ('v_dot8_i32_i4', 'v_dot4_i32_i8', 'v_dot2_f32_f16', 'v_pk_fma_f16',
              'v_mfma_f32_16x16x16f16', 'v_perm_b32', 'v_and_b32_e32', 'v_lshrrev_b32_e32',
              'v_lshlrev_b32_e32', 'v_or_b32_e32', 'v_bfe_u32', 'v_fmac_f32_e32')
    GT = {}
    symf = open(os.path.join(a.out, 'isa_symbols.txt'), 'w', encoding='utf-8', newline='\n')
    histf = open(os.path.join(a.out, 'isa_hist.txt'), 'w', encoding='utf-8', newline='\n')
    focf = open(os.path.join(a.out, 'isa_focus.txt'), 'w', encoding='utf-8', newline='\n')
    rx = re.compile(a.focus) if a.focus else None
    for p, sz in co:
        txt, h = hist(p, a.mcpu)
        for k, v in h.items():
            GT[k] = GT.get(k, 0) + v
        symf.write('### %s (%d B)\n' % (os.path.basename(p), sz))
        for ln in txt.splitlines():
            if re.search(r'^[0-9a-f]+\s+<', ln):
                symf.write('   %s\n' % ln.strip())
        histf.write('### %s  (%d 条指令, %d 种)\n' % (os.path.basename(p), sum(h.values()), len(h)))
        for k, v in sorted(h.items(), key=lambda x: -x[1])[:24]:
            histf.write('   %-28s %6d\n' % (k, v))
        histf.write('\n')
        if rx:
            for sym in re.findall(r'^[0-9a-f]+\s+<([^>]+)>:', txt, re.M):
                if rx.search(sym):
                    r2 = subprocess.run([OBJDUMP, '-d', '--arch-name=amdgcn', '--mcpu=' + a.mcpu,
                                         '--disassemble-symbols=' + sym, p],
                                        capture_output=True, timeout=300)
                    focf.write('### %s :: %s\n' % (os.path.basename(p), sym))
                    focf.write(r2.stdout.decode('utf-8', 'replace'))
                    focf.write('\n')
    symf.close(); histf.close(); focf.close()

    tot = sum(GT.values())
    cf = open(os.path.join(a.out, 'isa_census.txt'), 'w', encoding='utf-8', newline='\n')
    cf.write('设备对象数 = %d\n总指令 = %d\n' % (len(co), tot))
    for k in KEYOPS:
        cf.write('  %-26s %8d\n' % (k, GT.get(k, 0)))
    cf.write('\n-- 全助记符 top 30 --\n')
    for k, v in sorted(GT.items(), key=lambda x: -x[1])[:30]:
        cf.write('  %-28s %8d\n' % (k, v))
    cf.close()
    print('   设备对象 %d 个 / 总指令 %d ; v_dot4_i32_i8=%d  v_dot8_i32_i4=%d  v_dot2_f32_f16=%d' % (
        len(co), tot, GT.get('v_dot4_i32_i8', 0), GT.get('v_dot8_i32_i4', 0), GT.get('v_dot2_f32_f16', 0)))

    print('== [4] ISA 可编码性探针（必须带反例）==')
    probes = [
        ('v_dot8_i32_i4 v0, v1, v2, v3', True, 'routeK 说 gfx906 支持 = 原生 packed nibble'),
        ('v_dot4_i32_i8 v0, v1, v2, v3', True, 'int8 dot4（现役 dp4a 的目标）'),
        ('v_dot2_f32_f16 v0, v1, v2, v3', True, 'packed fp16 dot2（vd 为 VGPR 对，4 操作数）'),
        ('v_mfma_f32_16x16x16f16 v0, v1, v2, v3', False, '反例：gfx906 无 MFMA，必须报 not supported'),
    ]
    mcf = open(os.path.join(a.out, 'isa_mc.txt'), 'w', encoding='utf-8', newline='\n')
    for asm, want, note in probes:
        r = subprocess.run([MC, '-arch=amdgcn', '-mcpu=' + a.mcpu, '-show-encoding'],
                           input=(asm + '\n').encode(), capture_output=True, timeout=60)
        ok = (r.returncode == 0)
        verdict = 'OK' if ok == want else '**与预期不符**'
        line = '%-46s rc=%d expect=%s -> %s   [%s]  %s' % (
            asm, r.returncode, 'support' if want else 'reject', verdict, note,
            (r.stdout or r.stderr).decode('utf-8', 'replace').strip().replace('\n', ' | ')[:150])
        print('   ' + line)
        mcf.write(line + '\n')
    mcf.close()
    print('== 产出在 %s ==' % a.out)


if __name__ == '__main__':
    main()
