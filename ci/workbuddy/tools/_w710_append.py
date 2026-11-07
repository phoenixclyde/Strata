# -*- coding: utf-8 -*-
"""向新工作区的 2026-10-08.md 追加 W710（工作区独立）小节。幂等：已存在则不写。"""
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"

SEC = """## W710 ---- Strata 工作区独立（机主令「交接 strata 部分去一个新的工作区」）

- 建 `D:/workbuddy_space/strata_ws/`：`deploy/`（原 `D:/strata166/`）· `waves/`（原 `D:/workbuddy/_z_rk81/`）· `.workbuddy/memory/` · `tools/`。
- **搬前校验**：`tools/_verify_copy.py` 逐文件 md5 比对，两处 `ALL PASS`（deploy 6,698 文件 / 219,152,974 B；waves 165 文件 / 582,840 B）；**校验通过才删原**。
- **侦察结论**：routeK 权威件（`D:/workbuddy/_z_src/*.md`）对本工作区**零引用**；唯一外部引用是技能 `flashnext-engine-selection/SKILL.md`（3 行指向 `deploy/docker/`，已改）。
- **就地修一处**：`waves/_gh.py` 的 `TOKF` 改指新址（运行时真要读的只有它）。
- **未迁**：`D:/Strata/`（11.2 GB Windows 部署包，7194 文件），机主令**留原地**，本工作区只记外部引用。
- 新增件：`PROJECT.md`（自包含入口）· `MAP_OLD_TO_NEW.md`（路径映射）· `.workbuddy/memory/MEMORY.md`（长期记忆种子）。
- 历史件里的旧路径**逐字保留**（是证据，不篡改），换算见 `MAP_OLD_TO_NEW.md`；routeK 侧原 `2026-10-08.md` 改为指针存根。
"""

old = io.open(LOG, encoding="utf-8").read()
cr = old.count("\r")
if "## W710" in old:
    print("SKIP: W710 already present")
    raise SystemExit(0)
if not old.endswith("\n"):
    old += "\n"
new = old + "\n" + SEC
assert "\r" not in new, "CR leaked"
with io.open(LOG, "w", encoding="utf-8", newline="\n") as f:
    f.write(new)
print("orig CR count = %d" % cr)
print("appended: %d -> %d bytes" % (len(old.encode("utf-8")), len(new.encode("utf-8"))))
