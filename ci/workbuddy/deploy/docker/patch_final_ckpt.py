# -*- coding: utf-8 -*-
"""[W786 R1] Store one checkpoint when the whole prompt read finishes.

Problem (measured on 0.2.4 / engine 0.1.49.2, 2026-10-25):
  A conversation of 7,343 tokens got `reused = 0` on three consecutive turns
  (15.3 / 15.0 / 15.2 s each), while `conversation_cache` kept parking states
  (parked 2 -> 4, bytes 994 -> 1,649 MB). Nothing ever restored them because
  nothing was ever saved for that prompt:
    * `periodic_checkpoint` needs `done >= pp_next_check` (8,192 by default);
    * `tail_checkpoint` needs `pp_total - done > max(1, short_read)`, which is 0
      for a prompt that ends inside its last chunk.
  19,469 tokens fares better (turn 2 reuses 16,384 and drops 40.1 -> 7.8 s) but its
  last partial chunk (3,085 tokens) is re-read every turn for the same reason.

Fix: one extra checkpoint at the end of the read. It saves exactly the state
`checkpoint_at` already saves at a chunk boundary, so the K/V contents are
unchanged (the `as_tail` flag only affects eviction order, and `checkpoint_at`
de-duplicates by `ids.size() == L`).

Gate: `STRATA_FINAL_CKPT` — unset or non-zero = on (a fix), `0` = off (A/B arm).
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "/src/src/program/generate.cpp"
s = io.open(P, encoding="utf-8").read()

# ---- 1) 在 periodic 之后插入 final 的判定 ----
ANCHOR = "            const bool periodic_checkpoint = o.prompt_cache_every > 0 && done >= pp_next_check;"
assert s.count(ANCHOR) == 1, "anchor(periodic) count = %d" % s.count(ANCHOR)

INSERT = ANCHOR + """
            // [W786 R1] The read can finish inside its last chunk, where neither branch above fires:
            // periodic needs done >= pp_next_check (8,192), tail needs pp_total - done > short_read (0 here).
            // Without this the whole conversation is stored by nothing and every later turn re-reads it.
            // A prompt that already crossed a boundary ends with a partial tail; this stores that tail too.
            const char* final_env = std::getenv("STRATA_FINAL_CKPT");
            const bool final_checkpoint = (final_env == nullptr || std::atoi(final_env) != 0) &&
                o.prompt_cache > 0 && o.prompt_cache_every > 0 && !multi_gpu && done >= pp_total && done >= 1;"""

s = s.replace(ANCHOR, INSERT, 1)

# ---- 2) 并入同一个 if 分支 ----
OLD_IF = "            if (periodic_checkpoint || tail_checkpoint) {"
NEW_IF = "            if (periodic_checkpoint || tail_checkpoint || final_checkpoint) {"
assert s.count(OLD_IF) == 1, "anchor(if) count = %d" % s.count(OLD_IF)
s = s.replace(OLD_IF, NEW_IF, 1)

# ---- 3) 改后自证（fail-closed）----
checks = [
    ("final cond", s.count("const bool final_checkpoint = (final_env == nullptr || std::atoi(final_env) != 0)"), 1),
    ("if merged", s.count(NEW_IF), 1),
    ("old if gone", s.count(OLD_IF), 0),
    ("env read", s.count('"STRATA_FINAL_CKPT"'), 1),
    ("periodic kept", s.count(ANCHOR), 1),
    ("tail kept", s.count("const bool tail_checkpoint = o.prompt_cache_tail"), 1),
]
bad = [n for n, got, want in checks if got != want]
assert not bad, "post-patch assertions failed: %s" % [(n, g, w) for n, g, w in checks if g != w]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W786 R1 patched:", P, "bytes", len(s))
for n, got, want in checks:
    print("  [OK] %-14s %d" % (n, got))
