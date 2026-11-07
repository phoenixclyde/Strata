### 4.3 P1-a　gfx1151 剩余 10 项开关的 mega-arm（2026-10-31 12:39–12:54）

**为什么这么测**：19 项里我们开了 2 项（`GDN_HEAD`/`GDN_PP`）、测过 5 项（全部 ±1.5%），**还剩 12 项从未测**。
逐项测要 12×2 次启动（≈2 h），所以先**一次全开**：若合计仍 <2%，整轴关闭。

**臂**（同镜像 `0.2.8p2`、同 exe `n2`、同 33 args；mega 只是 env 14→24）
mega 加的 10 项：`GDN_CONVL2` `GDN_NOY` `CVEC_FUSE` `HCD_EXACT` `TOPK_REG_MIN_BLOCKS=4096` `Q8_PACKED` `Q6_PACKED` `TSUM` `QFUSE` `PLE_BATCH`
（`PF_PAD` 无 `PF_GEMM` 时惰性、`SH_STREAM` 已单独测否，均未纳入。）

| 指标 | base（生产） | mega（+10 项） | 差 |
|---|---:|---:|---|
| 启动就绪 | 255 s | 249 s | −2%（噪声） |
| decode（8 × 128 tok，中位） | **51.45 tok/s** | **51.30 tok/s** | **−0.3%** |
| read 1958 tok | 4042 ms | **失败（non-finite）** | — |
| read 3718 tok | 6032 ms | — | — |
| read 6666 tok | 9750 ms | — | — |
| 专家缓存槽位 | **7463**（21.79 GiB） | **6808**（19.87 GiB） | **−655（−8.8%）** |

**两条硬结论**

1. **decode 侧 0 收益**：10 项全开，decode 只差 −0.3%（两臂各 8 条，噪声量级）。
   ⇒ 这一轴在 decode 上**再无可挖**，与 §6.8 已测的 5 项一致。
2. **prefill 侧直接算错**：第一条 1958-token 的 prompt 在 **position 1953** 报
   `non-finite logits (#879) in a prompt window`，引擎取消请求并**丢弃整个会话**；重试又在第一个 decode 窗口的 position 1957 报同样的错。
   ⇒ 不是慢，是**数值非法**（NaN/Inf）。10 项里有某个把长 prompt 的 prefill 算崩了。

**白付的代价**：`Q8_PACKED` 确实生效了（启动行 `packed 84 Q8_0 matrices for decode (+1912.5 MiB)`），
于是专家缓存从 7463 掉到 6808 槽（−8.8%）。**decode 没变快，却先丢了 8.8% 的缓存。**

**该不该落生产**：**不落，整组否决**。理由按权重排：① 数值非法（正确性问题，比性能严重）；② decode 0 收益；③ 白付 8.8% 缓存。

**下一步（若要救单项）**：用**单条长 prompt 探针**做二分 —— 起一组、发一条 1958-token 请求，看是否 non-finite，一次启动 ≈ 5 min。
但既然 decode 已证 0 收益，只剩"prefill 可能更快"这一条理由，**优先级低于数值债（P0-c）**。
