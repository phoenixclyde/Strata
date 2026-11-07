# -*- coding: utf-8 -*-
"""Merge our AMD-PCIe-bandwidth additions into the current (0.2.8) serve/telemetry.py.
Keeps upstream's newer sampler robustness; only our five additions are applied. Idempotent + anchored."""
import io, py_compile, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'D:/workbuddy_space/strata_ws/albus/w830/tel_now.py'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'D:/workbuddy_space/strata_ws/albus/w830/tel_merged.py'
t = io.open(SRC, encoding='utf-8').read()
if 'BW_REFRESH_S' in t and 'def bw(' in t:
    print('already merged; nothing to do')
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(t)
    raise SystemExit(0)

need = ['import re', 'import time', 'HISTORY = 60', 'class _Amd', 'def _read(', 'def sample(']
for n in need:
    assert n in t, 'missing prerequisite: %s' % n

done = []

# 1) the refresh constant
a = 'HISTORY = 60\n'
assert t.count(a) == 1
t = t.replace(a, a + 'BW_REFRESH_S = 5.0            # how often the AMD PCIe bandwidth is re-read (a `pcie_bw` read costs a second)\n')
done.append('constant')

# 2) _Amd.name(): check the FRU name against the memory the driver reads
a = ('        try:\n'
     '            with open(os.path.join(self.dev, "product_name"), encoding="utf-8") as f:\n'
     '                return f.read().strip() or "AMD Radeon"\n'
     '        except (OSError, TypeError):\n'
     '            return "AMD Radeon"\n')
assert t.count(a) == 1, 'name() anchor count=%d' % t.count(a)
b = ('        try:\n'
     '            with open(os.path.join(self.dev, "product_name"), encoding="utf-8") as f:\n'
     '                nm = f.read().strip() or "AMD Radeon"\n'
     '        except (OSError, TypeError):\n'
     '            return "AMD Radeon"\n'
     '        # [ours] the FRU string can disagree with the memory that is fitted (a re-badged card, a FRU\n'
     '        # left at the wrong SKU); the card\'s own configuration wins for the capacity in the name.\n'
     '        m = re.search(r"\\b(\\d+)\\s?GB\\b", nm, re.I)\n'
     '        total = self._int(os.path.join(self.dev, "mem_info_vram_total"))\n'
     '        if not m or not total:\n'
     '            return nm\n'
     '        want = int(round(total / float(1 << 30)))\n'
     '        return nm if int(m.group(1)) == want else nm[:m.start()] + "%dGB" % want + nm[m.end():]\n')
t = t.replace(a, b)
done.append('name()')

# 3) _Amd.bw(): the driver's PCIe bandwidth counters
a = ('        return {"pcie_gen": gen, "pcie_gen_max": gen, "pcie_own_gen": own_gen, "pcie_width": width,\n')
assert t.count(a) == 1, 'link() tail anchor count=%d' % t.count(a)
lines = t.split('\n')
idx = [i for i, l in enumerate(lines) if l.startswith(a[:-1])][0]
# insert after the two-line return of link()
ins = [
    '',
    '    def bw(self):',
    '        """[ours] The card\'s PCIe bandwidth in MB/s over the driver\'s last counting second, or None.',
    '',
    '        amdgpu\'s `pcie_bw` is "<received msgs> <posted requests sent> <mps>"; the documented estimate is',
    '        `(received + sent) * mps`.  A read blocks for about a second, so the caller must not put it on the',
    '        1 Hz sampling path - see Telemetry._bw_loop.  None on APUs/older cards (no such file).',
    '        """',
    '        txt = _Amd._read(self.dev or "", "pcie_bw")',
    '        if not txt:',
    '            return None',
    '        try:',
    '            c0, c1, mps = (int(x) for x in txt.split()[:3])',
    '        except (ValueError, TypeError):',
    '            return None',
    '        return (c0 + c1) * mps / 1e6',
]
# find the end of that return statement (may span two lines)
end = idx
while '}' not in lines[end]:
    end += 1
lines[end + 1:end + 1] = ins
t = '\n'.join(lines)
done.append('bw()')

# 4) Telemetry.__init__: the second thread
a = ('        self._stop = threading.Event()\n'
     '        self._thread = threading.Thread(target=self._loop, daemon=True)\n'
     '        self._thread.start()\n')
if t.count(a) != 1:
    a = ('        self._stop = threading.Event()\n'
         '        threading.Thread(target=self._loop, daemon=True).start()\n')
assert t.count(a) == 1, 'init anchor count=%d' % t.count(a)
b = ('        # [ours] AMD sysfs cards: `pcie_bw` costs a second per read, so it is read off the 1 Hz path.\n'
     '        self._bw_cards = [g for _, g in self.gpus if hasattr(g, "bw")]\n'
     '        self._bw = None                              # (time, [MB/s per card]), see _bw_loop\n'
     '        self._stop = threading.Event()\n'
     '        threading.Thread(target=self._loop, daemon=True).start()\n'
     '        if self._bw_cards and len(self._bw_cards) == len(self.gpus):\n'
     '            threading.Thread(target=self._bw_loop, daemon=True).start()\n')
t = t.replace(a, b)
done.append('init thread')

# 5) sample(): publish gpu_pcie_rx_mb
a = '        s["disk_read_mb"], s["disk_write_mb"] = self._disk()\n'
assert t.count(a) == 1, 'sample anchor count=%d' % t.count(a)
b = a + ('        with self.lock:                              # [ours] the AMD cards\' PCIe bandwidth\n'
         '            if self._bw:\n'
         '                v = [x for x in self._bw[1] if x is not None]\n'
         '                if v:\n'
         '                    s["gpu_pcie_rx_mb"] = round(sum(v), 2)\n')
t = t.replace(a, b)
done.append('sample inject')

# 6) the bw sampler loop, before _loop()
a = '    def _loop(self):\n'
assert t.count(a) == 1
b = ('    def _bw_loop(self):\n'
     '        """[ours] The AMD cards\' PCIe bandwidth, read away from the 1 Hz sampler: `pcie_bw` counts over a\n'
     '        one-second window and blocks for that second, so reading it in sample() would halve every series."""\n'
     '        while not self._stop.is_set():\n'
     '            vals = []\n'
     '            for g in self._bw_cards:\n'
     '                try:\n'
     '                    vals.append(g.bw())\n'
     '                except Exception:  # noqa: BLE001 - telemetry must never take the server down\n'
     '                    vals.append(None)\n'
     '            with self.lock:\n'
     '                self._bw = (time.time(), vals)\n'
     '            self._stop.wait(BW_REFRESH_S)\n'
     '\n'
     '    def _loop(self):\n')
t = t.replace(a, b)
done.append('_bw_loop')

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(t)
py_compile.compile(OUT, doraise=True)
print('merged parts:', done)
print('bytes %d -> %d ; py_compile OK' % (len(io.open(SRC, encoding='utf-8').read()), len(t)))
