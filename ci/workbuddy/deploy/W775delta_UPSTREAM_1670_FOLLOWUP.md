> **[!] 已作废（2026-10-11 19:4x）**：机主令删除我们在 `#1670` 的全部评论并停止跟进 => 本更正稿**不再发出**。
> 被更正的对象（comment `6107050493` 的括注、以及 comment `6106913235` 的复述）**已随评论一并删除**，故无需再更正。
> 保留本件仅为审计链完整（AUDIT5-A1 的记录）。

# `#1670` follow-up 更正（两件事：括注误合 + 07:59 reply 的复述）

> 目标：`Niko1221/Strata` issue **#1670**（[Feature]: Layer-major prefill for streamed experts）
> 事由：**AUDIT5-A1** 与**本件背景核**发现我们自己的三条评论里有两处需更正。
> 状态：**待机主过目**（未发）。
> 依据：166 生产日志 `data/strata-huihui-ud-iq4_xs.log`（本机副本 `deploy/tmp/_audit5_ev/`）。

## 0 我们在该 issue 的三条评论（据实）

| comment id | 时间 | 大小 | 内容 | 现态 |
|---|---|---|---|---|
| `6083995120` | 2026-10-09T15:29:40Z | 642 B | 数据点：本机「提示读取不是 PCIe 瓶颈」+「file tier 不是瓶颈」 | **结论已被自己撤回**（comment `6107050493`） |
| `6106913235` | 2026-10-11T07:59:32Z | 1,173 B | reply：layer-major 在本机不激活 + 不移植 | **其中一句复述了上面已撤回的结论，本次一并撤回** |
| `6107050493` | 2026-10-11T08:17:28Z | 2,022 B | correction：撤回 10-09 的结论 | **正文一处括注把三条不同请求的数字合成了同一条，本次更正** |

## 1 要发的正文（英文）

```text
Two corrections to our comments on this issue.

1. In our correction of 2026-10-11T08:17Z we wrote:

   (a single request: 64,649 MB from storage, 79,756 MB of expert reads, 222,659 major faults)

   Those three numbers are the per-request maxima of three *different* requests, not one:

     a    60-token cold request  : OS read  64,649.1 MB from storage (  1,406 major faults)
     a  64,026-token cold request : OS read  27,429.5 MB from storage (222,659 major faults)
     a 110,793-token cold request : OS read   3,375.7 MB from storage (      0 major faults)

   The aggregate figures in that comment are unaffected: over 198 requests the file tier
   pulled 371,808 MB from storage for 1,099,239 MB of expert reads (about 34%).

2. Our reply of 2026-10-11T07:59Z repeated the 2026-10-09 claim - "The earlier data point also
   applies to the streamed case ... a large reduction in re-reads would buy much less here".
   That sentence is withdrawn as well. Our correction only named the 2026-10-09 comment, but
   the same claim in the 07:59Z reply is just as wrong: on the cold path the file tier *is*
   the bottleneck (371,808 MB of the 1,099,239 MB of expert reads came from real storage).

Neither correction touches our other conclusion, which stands: layer-major does not activate
in our configuration, because we run resident experts rather than --mmap-experts.
```

<!-- albus-checkin -->
