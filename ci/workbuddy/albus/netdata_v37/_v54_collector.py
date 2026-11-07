# -*- coding: utf-8 -*-
"""v54-1：采集器补 SATA 的等价 SMART 字段（Device Statistics 标准字段 + 180/187/199）"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/rk-health-collect.sh"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

OLD = '''        out["life"] = life
        out["hours"] = raw(9)
        out["written"] = None
        out["lba_w"] = raw(241)
        out["realloc"] = raw(5)
        out["spare"] = raw(180)
'''

NEW = '''        out["life"] = life
        out["hours"] = raw(9)
        out["lba_w"] = raw(241)
        out["realloc"] = raw(5)
        out["spare"] = raw(180)     # SATA：未使用的备用块**个数**（不是百分比）
        out["uncorr"] = raw(187)    # Reported_Uncorrect：不可纠正错误计数
        out["crc"] = raw(199)       # UDMA_CRC_Error_Count：SATA 链路 CRC 错
        # [v54] SATA 没有 NVMe 那四项。等价物分两处取，都只用**标准字段**：
        #   1) ATA Device Statistics（GP Log 0x04，ACS 标准）：Logical Sectors Written/Read，
        #      单位恒为逻辑扇区（本盘 512B）—— 不随厂商变。
        #   2) 厂商 SMART 属性：180 备用块 / 187 不可纠正 / 199 UDMA CRC。
        # [!] 属性 241 不能当"已写入"用：本盘 241=12874，而 Device Statistics 实测写入
        #   27,000,010,226 扇区 ×512B = 13.82 TB —— 12874 × 1 GiB 恰好 = 13.82 TB，
        #   说明这块盘 241 的单位是 1 GiB（不是 LBA）；写 256 MiB 时 241 一动不动（不足 1 单位）。
        #   单位随厂商而异（32MiB / LBA / 1GiB 都见过）=> 只用标准字段，不猜。
        out["written"] = None
        blk = d.get("logical_block_size") or 512
        try:
            r2 = subprocess.run(["/usr/sbin/smartctl", "-j", "-l", "devstat", "/dev/" + dev],
                                capture_output=True, timeout=10)
            ds = json.loads((r2.stdout or b"{}").decode("utf-8", "replace"))
            tab2 = {}
            for pg in ((ds.get("ata_device_statistics") or {}).get("pages") or []):
                for row in (pg.get("table") or []):
                    if row.get("name"):
                        tab2[row["name"]] = row.get("value")
            sw = tab2.get("Logical Sectors Written")
            sr = tab2.get("Logical Sectors Read")
            if isinstance(sw, int):
                out["written"] = sw * blk
            if isinstance(sr, int):
                out["read"] = sr * blk
            pu = tab2.get("Percentage Used Endurance Indicator")
            if isinstance(pu, int):
                out["endurance_used"] = pu   # 只做交叉校验，不上屏（与属性 231 有冲突，见 SKILL）
        except Exception as e:
            out["ds_err"] = str(e)[:60]
'''

assert s.count(OLD) == 1, s.count(OLD)
s = s.replace(OLD, NEW)

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
