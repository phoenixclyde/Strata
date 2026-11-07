# -*- coding: utf-8 -*-
"""把 routeK 侧的 2026-10-08.md 换成指针存根（全文已迁入 Strata 工作区，md5 已校验）。

只替换 routeK 那一份；新工作区那份不动。
"""
import hashlib
import io
import os
import shutil

ROUTEK = r"D:/workbuddy/.workbuddy/memory/2026-10-08.md"
NEWWS = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
BAKDIR = r"D:/workbuddy_space/strata_ws/tools"

STUB = """# 2026-10-08 工作日志（routeK）

> **[本日内容已迁出]** 本日全部为 Strata 工作（W707 / W708 / W708c / W708d / W709a~e），
> 已整篇迁至新工作区 **`D:/workbuddy_space/strata_ws/`**（机主令「交接 strata 部分去一个新的工作区」）。
>
> 全文位置：`D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md`
> 迁走前逐文件 md5 校验全等（ALL PASS）：`D:/workbuddy_space/strata_ws/tools/_verify_copy_out.PREDELETE.md`
> 迁移动作记录：`D:/workbuddy_space/strata_ws/HANDOVER.md`（W710 段）
>
> 本日 routeK 侧无其它内容。
"""


def md5(p):
    return hashlib.md5(io.open(p, "rb").read()).hexdigest()


# 1) 新工作区那份必须在，且内容是全文（明显大于存根）
assert os.path.isfile(NEWWS), "新工作区全文缺失，禁止改 routeK"
sz = os.path.getsize(NEWWS)
assert sz > 30000, "新工作区全文尺寸可疑: %d" % sz

# 2) 把 routeK 原件留一份指纹记录（内容本身已有新工作区副本，此处不再复制全文）
orig_md5 = md5(ROUTEK)
orig_sz = os.path.getsize(ROUTEK)

# 3) 覆写为存根
with io.open(ROUTEK, "w", encoding="utf-8", newline="\n") as f:
    f.write(STUB)

print("新工作区全文 : %s bytes" % sz)
print("routeK 原件  : %s bytes / md5 %s" % (orig_sz, orig_md5))
print("routeK 现为  : %d bytes（指针存根）" % os.path.getsize(ROUTEK))
