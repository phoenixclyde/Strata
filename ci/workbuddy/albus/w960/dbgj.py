# -*- coding: utf-8 -*-
"""Add a one-line debug print of the J our pick_J chose (STRATA_MMQ_DEBUG_J=1)."""
import io, sys

W = sys.argv[1]
p = W + "/src/prefill/moe_mmq.cu"
s = io.open(p, encoding="utf-8").read()
old = """    return best > 0 ? best : 64;
}"""
new = """    if (const char* dbg = std::getenv("STRATA_MMQ_DEBUG_J")) {
        (void) dbg;
        std::fprintf(stderr, "pick_J: type=%d ncols=%lld fallback=%d -> J=%d\\n",
                     t, (long long) ncols, (int) fallback, best > 0 ? best : 64);
    }
    return best > 0 ? best : 64;
}"""
if "STRATA_MMQ_DEBUG_J" in s:
    print("already")
elif old in s:
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    print("debug print added")
else:
    print("anchor MISS")
