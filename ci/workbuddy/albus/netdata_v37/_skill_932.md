
### 9.32 SATA 盘缺的那四项怎么补（2026-11-05 03:10）
机主发现右卡（Fanxiang S100Pro 1TB / sda）有四格是 `--`：「已写入 / 可用备用 / 介质错误 / 关键告警」。
**结论：四项都能拿到，但来源和 NVMe 完全不同 —— 去找 ATA 的"等价物"，不要硬套 NVMe 字段。**

| 卡片槽位 | NVMe 来源 | SATA 来源 |
|---|---|---|
| 已写入 | Data Units Written × 512000 B | **ATA Device Statistics (GP Log 0x04) 的 Logical Sectors Written × 512 B** |
| 可用备用 | Available Spare % | 属性 **180** Unused_Rsvd_Blk_Cnt_Tot（**个数**，不是百分比） |
| 介质错误 | Media Errors | 属性 **187** Reported_Uncorrect（优先取 devstat page 4 同名字段） |
| 关键告警 | Critical Warning 位图 | 属性 **199** UDMA_CRC_Error_Count（优先取 devstat page 6 Interface CRC） |

**为什么必须用 Device Statistics**：ACS 把这几项标准化了（page1:0x018 Logical Sectors Written、
page1:0x028 Logical Sectors Read、page4:0x008 Reported Uncorrectable、page6:0x018 Interface CRC、
page7:0x008 Percentage Used Endurance Indicator，见 ACS-4 9.5.7.3），单位确定（512B 扇区）。
`smartctl -j -a` **不含** devstat，必须单独跑 `smartctl -j -l devstat /dev/sdX`。

**[!] 厂商属性 241/242 不能当字节数用**：单位随厂商/型号而异（社区实测 Intel 是 32 MiB，
本机这块是 **1 GiB**）。判据是**做一次已知写入**：
`dd if=/dev/zero of=/tmp/x bs=1M count=256 conv=fsync` → 241 一动不动（<1 单位）；
而 `12874 × 1 GiB = 13.82 TB` 与 devstat 的 27×10⁹ 扇区完全对上。=> 单位靠实测，不靠猜。

**[!] 寿命两个口径会打架，要能判定谁对**：本盘 devstat 的 Percentage Used = 12%，而属性 231
归一化是 98（= 已用 2%）。判定靠**厂标 TBW**：S100PRO 1TB 标 600 TBW，13.82 TB / 600 = 2.3%
≈ 属性值；12% 反推只有 ~115 TBW，与厂标不符 => 用属性值，并把冲突写进悬停提示。
**不要因为"标准字段更权威"就无脑选它 —— 要先拿第三方可核对量（TBW）验一遍。**

健康判据也要分型：SATA 把 **187 > 0** 并入"告警"（真介质错误），**199 只标黄不判死**
（CRC 是线缆/背板/接触问题，不是盘的介质故障）。
