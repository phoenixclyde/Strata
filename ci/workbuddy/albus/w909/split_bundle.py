#!/usr/bin/env python3
"""W909: split a Clang offload bundle (.hip_fatbin) into its individual code objects.

Format (clang/lib/Driver/OffloadBundler.cpp):
  header: u32 Magic=0x0B17C0DE, u32 Version, u32 BundleCount, u32 BundleInfoOffset (v2+)
  bundle info array at BundleInfoOffset: per entry u32 Offset, u32 Size, u32 IdLen, then Id (padded to 8)
"""
import struct, sys, os

MAGIC = 0x0B17C0DE

def main(path, outdir):
    data = open(path, 'rb').read()
    magic, version, count, info_off = struct.unpack_from('<IIII', data, 0)
    if magic != MAGIC:
        sys.exit('bad magic %08x' % magic)
    print('magic ok  version=%d  bundles=%d  info_off=%d  file=%d bytes'
          % (version, count, info_off, len(data)))
    os.makedirs(outdir, exist_ok=True)
    pos = info_off
    made = 0
    for i in range(count):
        off, size, idlen = struct.unpack_from('<III', data, pos)
        pos += 12
        bid = data[pos:pos + idlen].decode('utf-8', 'replace')
        pos += idlen
        pos = (pos + 7) & ~7          # entries are 8-byte aligned
        blob = data[off:off + size]
        kind = 'hsaco' if bid.startswith('hip') or bid.startswith('hipv4') else 'host'
        name = '%s/%03d_%s.%s' % (outdir, i, bid.replace(':', '_').replace('/', '_'), kind)
        open(name, 'wb').write(blob)
        print('%03d  off=%-10d size=%-9d %s' % (i, off, size, bid))
        made += 1
    print('wrote %d objects to %s' % (made, outdir))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
