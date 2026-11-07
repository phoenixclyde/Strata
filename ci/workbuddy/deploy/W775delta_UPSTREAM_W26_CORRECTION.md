# 上游更正件 ---- `#1923` 的 self-correction（正文逐字，可直接贴）

> 状态：**已发**（2026-10-11 15:26；comment `6106666399`，3,270 B / `2d2abf06...`，回读逐字节一致） ---- https://github.com/Niko1221/Strata/issues/1923#issuecomment-6106666399
> 纪律：无"提速"字样；主动交代"我们自己的基线选错了"；附可复现命令与指纹。

## 正文（English，逐字）

```text
Correction to our own report above.

We measured `fill-only 0.7086` with `tools/bench_eviction.py` and read it as "the engine's
current admission, so this is today's hit rate".  That was the wrong baseline.  `ExpertCache::admit`
never evicts, but the same startup path also builds the resident-RAM mode's **adaptive tier**, which
does move residents in and out.  On our box the production log says:

    strata generate: pre-filled 9761 of 9761 slots from the profile in 8.2 s (2881 MB/s); slot 0 verified
    strata generate: resident RAM mode: 33.44 GiB of experts in RAM (page-locked), 9761 in the GPU cache;
                     adaptive swaps exchange them with the GPU cache (no file reads)

Your own `tools/replay_cache_policy.py` is the model of that tier ("The simulated adaptive tier is
generate.cpp's adapt()").  Replaying the SAME `--dump-routing` trace, from the SAME shipped
`expert-profile.bin`, at the same 9,761 slots:

    profile only, no adaptation                            0.7086
    policy every 4, swaps 96, decay 0.70 (the engine's defaults)   0.9564   (11601 swaps)
    static oracle (top-9761 by this trace's own counts)     0.9669

so the tier already recovers about 99% of what that trace allows, and 0.9564 sits right on the
95.4-98.0% decode hit rate our production engine reports.  The five knobs match the engine's
defaults one for one: `adapt_every = 4` (`generate.cpp:577`), `adapt_decay = 0.7f` (`:578`),
`adapt_swaps = 96` (`:607`), `adapt_min_gain = 1.5f` (`:581`, compared at `:8174`), and the
candidate gate `u[e] >= 2.0f` (`:8165`).

So we withdraw the motivation "add an eviction policy to recover the 24-28 points".  What is left
is narrower, and we are not asking for it here:

  (a) machines that do NOT run the resident-RAM mode (there `adapt()` does not run at all) may
      still sit at the fill-only rate - that is a question about the tier's reach, not about
      adding a second eviction policy;
  (b) the `adapt_*` knobs themselves: making them busier did not help on our trace
      (`--every 1` -> 0.9556, a looser gate -> 0.9590, both within a point of 0.9564).

Two small observations while we were in there:

  1. `generate.cpp:5008` prints "expert cache %lld slots, %.2f GiB of VRAM; policy is\n" - the
     policy text is missing an argument, so the log line just ends with "policy is".
  2. `bench_eviction.py` describes `fill-only` as "the engine's current admission: ... the baseline
     a policy has to beat".  On a `--resident-*` engine that reads as "the engine's current hit
     rate", which is what led us here.  A word about `adapt()` in that docstring would have saved
     us the round.

Reproduce (no GPU needed):

    python tools/replay_cache_policy.py TRACE.bin data/expert-profile.bin 9761
    python tools/replay_cache_policy.py TRACE.bin data/expert-profile.bin 9761 --swaps 0
    python tools/bench_eviction.py TRACE.bin --slots 9761 --prefill data/expert-profile.bin \
           --policies fill-only,lru,lfu-decay,oracle

Trace: 16,211,712 B, md5 6b5f1e44788fc13fa598d4261d5cbcde (0.1.42, 48 layers x 512 experts,
3,838 positions x k=10).  Profile: 196,632 B, md5 ff1bc6544d3f2f0013e3e376632d33a8 - byte-identical
to the image's `/src/data/expert-profile.bin`.
```
