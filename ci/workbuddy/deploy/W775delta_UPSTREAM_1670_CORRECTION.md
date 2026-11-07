# `#1670` 更正正文（retraction of the file-tier claim）

> 目标：`Niko1221/Strata` issue **#1670**
> 事由：我方 2026-10-09 在该 issue 写过 "the file tier is not our bottleneck" / "experts ... mostly already resident"，**被本机冷路径数据反证** => 主动撤回。
> 状态：**已发**（comment `6107050493`，2026-10-11T08:17:28Z，body 2,022 B / md5 `714d7d6e5e900898a5db333a76fafb4c`，回读逐字节一致）
> **AUDIT4 更正**：本行原写「待发」，与 W28B/W28D 的「已发」不一致，现据实回填。
> **[!] 2026-10-11 19:4x 已从上游删除**（同上）；本件是删除前的历史留档。

```text
Correction to our comment of 2026-10-09 on this issue.

We wrote that "the file tier is not our bottleneck" and that the experts "are mostly already
resident". Our own logs contradict that, so we are retracting it instead of leaving it standing.

On that same box (MI50 32 GB, gfx906, UD-IQ4_XS, resident experts, 262144 context) the experts do
not all fit. The engine reports three tiers on every start:

  resident RAM mode: 33.45 GiB of experts in RAM (page-locked), 9761 in the GPU cache
  FileExpertSource: RAM budget 76.00 GiB: 14819 of the 33.45 GiB of experts the GPU cache does not
    hold, by profile rank; the rest are read from the files
  the file tier reads through the file cache (re-checked with the RAM copy built (33.45 GiB):
    ... 22.0 GiB of experts read from the files ...)

Reading a prompt streams every expert once per chunk, so a cold prompt (no prefix reuse) pulls the
lower two tiers, including real storage. Over 198 requests in our log:

  file tier I/O this request: the OS read 371,808 MB from storage in total for 1,099,239 MB of
    expert reads
  (a single request: 64,649 MB from storage, 79,756 MB of expert reads, 222,659 major faults)

That is about 34% of expert reads coming from real storage - the same "third outside the RAM
budget" your documentation describes. Cold prompts (reused = 0; 76 of 196) took a median of 12.6 s
to read, p90 38.6 s, max 252 s. On the host, netdata recorded windows with GPU utilization at 0%
while the CPU was about 51% busy and disk reads peaked at 356 MB/s.

So our earlier number was taken in a warm window (the page cache still held the experts) and must
not be read as "the file tier is never the bottleneck". It is the bottleneck for cold prompts,
which is most of what this box sees.

This does not change our conclusion about layer-major for our configuration (we run resident
experts, not --mmap-experts, so it does not activate there), but the file-tier sentence in the
earlier comment was wrong and is withdrawn.
```

> **[AUDIT5-A1 补遗 2026-10-11 19:xx]** 上引正文第 28 行 `(a single request: 64,649 MB from storage, 79,756 MB of expert reads, 222,659 major faults)` ---- **三值分属三条不同请求**（`64,649.1 MB` 属一条 60-token 首请求 `L2829/L2834`；`79,756.2 MB` 属 110,793-token 请求 `L2569`；`222,659` 属 64,026-token 请求 `L2842`）。
> 该括注**已随 comment `6107050493` 发出** => 需发一条 follow-up 更正；草稿见 `deploy/W775delta_UPSTREAM_1670_FOLLOWUP.md`（**待机主过目后发**）。

<!-- albus-checkin -->
