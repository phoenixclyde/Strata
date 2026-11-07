#!/usr/bin/env python3
"""W909: carve every amdgcn ELF code object out of a .hip_fatbin blob by scanning ELF headers.

We do not parse the clang offload-bundle container (its layout changed in LLVM 20+); instead we
locate each 0x7fELF that declares e_machine == EM_AMDGPU (224) and let the section header table
tell us where the object ends.
"""
import struct, sys, os, hashlib

EM_AMDGPU = 224

def size_from_shdrs(data, base, maxlen):
    if len(data) - base < 64:
        return 0
    e_shoff, = struct.unpack_from('<Q', data, base + 0x28)
    e_shentsize, e_shnum = struct.unpack_from('<HH', data, base + 0x3A)
    if e_shoff == 0 or e_shnum == 0 or e_shentsize < 64:
        return 0
    end = 0
    for i in range(e_shnum):
        off = base + e_shoff + i * e_shentsize
        if off + 64 > len(data):
            break
        sh_offset, sh_size = struct.unpack_from('<QQ', data, off + 0x18)
        end = max(end, sh_offset + sh_size)
    # the section header table itself sits after the last data section, and objdump insists on reading it
    end = max(end, e_shoff + e_shnum * e_shentsize)
    if end == 0:
        return 0
    return min(end, maxlen)

def main(path, outdir):
    data = open(path, 'rb').read()
    os.makedirs(outdir, exist_ok=True)
    n = 0
    total = 0
    seen = set()
    i = 0
    while True:
        j = data.find(b'\x7fELF', i)
        if j < 0:
            break
        i = j + 4
        if data[j + 4] != 2 or data[j + 5] != 1:      # 64-bit LSB only
            continue
        e_machine, = struct.unpack_from('<H', data, j + 0x12)
        if e_machine != EM_AMDGPU:
            continue
        size = size_from_shdrs(data, j, len(data) - j)
        if size < 1024:
            continue
        name = '%s/co_%03d_off%d.elf' % (outdir, n, j)
        blob = data[j:j + size]
        h = hashlib.sha1(blob).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        open(name, 'wb').write(blob)
        n += 1
        total += size
    print('carved %d amdgcn code objects, %.1f MiB total' % (n, total / 1048576.0))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
