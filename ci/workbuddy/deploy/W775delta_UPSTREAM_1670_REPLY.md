# `#1670` 回复正文（已发上游）

> 目标：`Niko1221/Strata` issue **#1670**
> 状态：**已发** 2026-10-11T07:59:32Z，comment id **`6106913235`**（POST **201** + 回读逐字节一致；body 1,173 B / md5 `7aa25d678fd0066601b347e47b2baf5f`）
> https://github.com/Niko1221/Strata/issues/1670#issuecomment-6106913235
> 授权：机主 2026-10-11「你确认是事实就可以发 / 你定」
> **[!] 2026-10-11 19:4x 已从上游删除**（机主令「不要跟了、把我们的内容都删掉」；DELETE HTTP 204、回读 404）。本件仅作我方留档。

```text
Thanks for the branch and the exact configuration.

We checked whether it can pay on our box, and it does not activate there. Layer-major
applies with streamed experts (as you note, and it is the --mmap-experts path in the
engine). We run resident experts: `--expert-profile data/expert-profile.bin
--expert-cache auto --resident-budget-gib 76`, with no `--mmap-experts` and no
`--stream-experts`. The engine reports `resident RAM mode: 33.44 GiB in RAM, 9761 in
the GPU cache` with adaptive swaps, so the S/512 file-tier re-read that layer-major
removes is not on our path at all.

The earlier data point also applies to the streamed case: on that MI50 the engine
streams about 1.83 distinct experts per layer and moves about 0.5-1.2 GB/s of expert
bytes against a 15.75 GB/s link (about 7%), with the experts it needs mostly already
resident. So a large reduction in re-reads would buy much less here than on the 6 GB
card.

Given that, we will pass on porting it to HIP/gfx906 - it would have to compile there
first, and the gain we can predict on this box is small. If a HIP data point in
streamed mode would be useful to you, we can still try.
```

<!-- albus-checkin -->
