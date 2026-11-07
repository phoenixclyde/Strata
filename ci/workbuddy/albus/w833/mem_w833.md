## W833（量化报告口径 + P1-a mega-arm，2026-10-31 12:39–12:55）

- **量化快照脚本** `albus/w833/state_q.py`（**在宿主机跑**）：镜像 / exe / args / env / 显存 / 专家缓存 / 提示借用 / 预热速度 /
  GPU util·temp·power·pcie / 累计请求 / health / 配置 md5 / 探针(decode+TTFT)。以后每轮先跑它。
- **生产基线（12:38/12:54 两次快照一致）**：镜像 `0.2.8p2`、`strata-0.1.54n2`、33 args、14 env、md5 `0d67f258`；
  VRAM **33.5/34.3 GB（97.4%）**；专家缓存 **7463 槽 / 21.79 GiB**；提示借用 **1578 槽 / 4.62 GiB**；预热 **7463 槽 1.8 s（12852 MB/s）**；
  GPU 空闲 0% / 55℃ / 17 W；探针：decode 128 tok 端到端 4.06 s、引擎自报 **50–51 tok/s**、TTFT(新 prompt) **1339 ms**。
- **P1-a mega-arm（10 项一起开）**：decode **51.45 → 51.30（−0.3%）**；read 1958 tok **直接崩**：
  `non-finite logits (#879) in a prompt window at position 1953` → 取消请求 + 丢弃会话，重试 position 1957 再犯。
  代价：`Q8_PACKED` 生效（`packed 84 Q8_0 matrices for decode (+1912.5 MiB)`）⇒ 专家缓存 **7463→6808（−655，−8.8%）**。
  ⇒ **整组否决**（数值非法 + 0 收益 + 白付 8.8% 缓存）。登记 **P212**。
- **手法教训（重复踩）**：脚本在容器内跑却用宿主路径（`/home/albus/...`）→ `FileNotFound`。**容器内路径一律 `/data/...`**；
  另 `grep -E` 不支持 `\d`，要用 `[0-9]+`。
