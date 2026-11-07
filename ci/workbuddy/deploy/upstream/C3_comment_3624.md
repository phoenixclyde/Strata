# C3 draft — comment on #3624 (Linux arena O_DIRECT)

> Post as a comment on https://github.com/Niko1221/Strata/pull/3624

Independent data point for this PR, from a box where the buffered load does more than cost time.

**Box:** Radeon Instinct MI50 32 GB (gfx906), 128 GB RAM, Ubuntu 22.04, Docker, engine 0.1.49.2
(0.2.4p4), Qwen3.8-Flash-Next UD-IQ4_XS, 262144 context, `--expert-cache auto` (9873 slots, 22.25 GiB),
`--pcie-frac 0.20`. The expert arena is 55.43 GiB of a 128.7 GB machine.

**Load rates on the same SATA SSD (Fanxiang S100Pro), from the engine's own line:**

| start | `loaded 55.43 GiB at` | ready |
|---|---|---|
| cold (pack not in page cache) | 0.27 / 0.35 / 0.36 / 0.40 GiB/s | 201-280 s |
| warm (pack in page cache) | 3.02 / 4.47 GiB/s | 42-46 s |

`STRATA_UNBUFFERED_LOAD=1` changes nothing here, as your PR text says (Linux only raises the reader
count). The 3.02 GiB/s row is a plain start with the flag *unset*, right after a warm one, which is the
control that makes the point: the whole difference is the page cache.

**What the buffered load costs besides time.** With `--ple-io ram` (set by hand, not by setup), the
26.8 GiB table is touched into the page cache first (`PLE table loaded (not locked) (--ple-io ram) in
84.2 s`; `mlock` fails here, `ulimit -l` is 8 MB, so the pages are ordinary file pages). The arena load
then streams 55.43 GiB through that same cache and pushes the table out: at the end of the run the
`00002-of-00003` mapping holds **986 MB** of resident pages (from 26.5 GB measured over the VMA right
after startup), and the host `Cached` drops 78.6 → 43.8 GB.

The visible effect is that `--ple-io ram` stops being `ram`: the first prompt's PLE time is 8 ms
(0.3% of the prompt's GPU timeline, the table really is in memory), and every later prompt is back to
641 / 1128 / 1024 ms — the same as `--ple-io direct`. With `sync; echo 1 > /proc/sys/vm/drop_caches`
before the start, the table keeps 25.0-26.6 GiB for the whole run and the prompt at 2493 tokens goes
4997 → 4296 ms (-14%).

So on this machine the buffered arena load is not only 6-11x slower than a warm one, it also destroys
the working set that another feature just paid 85 s to build. An O_DIRECT branch would fix both at once,
which may be worth saying in the PR description.

Two things I would like to know while this is open:

1. Does the O_DIRECT path still populate the page cache at all? If it does not, users who start twice in
   a row lose the 12-18 s second start they get today.
2. Would you take a separate, smaller change: after startup, `mincore()` the PLE mapping and log the
   resident share, so a `--ple-io ram` that quietly fell out of RAM says so instead of looking healthy?
   Right now the only line is `loaded (not locked)` and then nothing.
