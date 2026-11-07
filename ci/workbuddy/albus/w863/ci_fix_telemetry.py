# -*- coding: utf-8 -*-
"""[W863] Restore the sampler thread references our downstream patch dropped.

Why: our PCIe-bandwidth patch replaced
    self._thread = threading.Thread(...); self._thread.start()
with an anonymous thread.  Upstream v0.2.9 added
serve/test_responses.NoLeakedSampler, which reads `telemetry._thread` to prove a stopped
server ends its sampler -> the attribute is None -> the test fails (CI red on every
gfx906/* branch, green on main).

Run on 166.  Edits pr/strata-fork/serve/telemetry.py in place, keeps a .w863bak copy.
"""
import hashlib
import os
import shutil

P = "/home/albus/strata166/pr/strata-fork/serve/telemetry.py"

OLD_START = """        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()
        if self._bw_cards and len(self._bw_cards) == len(self.gpus):
            threading.Thread(target=self._bw_loop, daemon=True).start()
"""

NEW_START = """        self._stop = threading.Event()
        # [ours] the references are kept: a stopped server joins them, and
        # serve/test_responses.NoLeakedSampler reads `_thread` to prove the sampler ends.
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if self._bw_cards and len(self._bw_cards) == len(self.gpus):
            self._bw_thread = threading.Thread(target=self._bw_loop, daemon=True)
            self._bw_thread.start()
"""

OLD_CLOSE = '''    def close(self):
        """Ends the sampler thread (a server that stops, a test's service): it used to run for the life of the process."""
        self._stop.set()
'''

NEW_CLOSE = '''    def close(self):
        """Ends the sampler threads (a server that stops, a test's service): they used to run for the life of the process."""
        self._stop.set()
        for t in (getattr(self, "_thread", None), getattr(self, "_bw_thread", None)):
            if t is not None and t is not threading.current_thread():
                t.join(timeout=5.0)
'''

src = open(P, encoding="utf-8").read()

if "self._thread = threading.Thread" in src:
    print("ALREADY PATCHED (self._thread present) - nothing to do")
    raise SystemExit(0)

for old, new, tag in ((OLD_START, NEW_START, "start"), (OLD_CLOSE, NEW_CLOSE, "close")):
    if src.count(old) != 1:
        print("ABORT: %s anchor found %d times (expected 1)" % (tag, src.count(old)))
        raise SystemExit(2)
    src = src.replace(old, new, 1)

bak = P + ".w863bak"
if not os.path.exists(bak):
    shutil.copy2(P, bak)
    print("backup ->", bak)

open(P, "w", encoding="utf-8").write(src)
print("patched:", P)
print("md5 ->", hashlib.md5(open(P, "rb").read()).hexdigest())
