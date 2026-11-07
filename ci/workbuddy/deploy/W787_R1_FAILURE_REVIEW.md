# W787 R1 失败复盘：三次测量错误，以及由此暴露的目标判断错误

> 缘起：机主令「继续」，执行 `W786` 的 R1（对话复用补 `final_checkpoint`，预期 88 倍）。
> **结果：补丁正确编译、正确执行、零收益。生产已回滚到 `0.2.4`。**
> 本文记录三件事：① 我错在哪（三次测量错误）；② 真实基线是什么；③ 由此暴露的、比 R1 更重要的目标判断错误。

---

## 1 做了什么（都已回滚）

| 步骤 | 结果 |
|---|---|
| 写 `deploy/docker/patch_final_ckpt.py`（fail-closed，6 项自证） | 通过 |
| 本地副本试跑（`/tmp/gen_test.cpp`，md5 `ff384ffb…`） | diff 精确落在 `generate.cpp:9905-9918` |
| 改 `Dockerfile-0.2.4`（COPY + RUN + 指纹断言） | 备份 `Dockerfile-0.2.4.bak_before_r1` |
| `docker build -t strata-gfx906:0.2.4r1` | `[160/160]` RC=0，镜像 6.96 GB |
| 镜像验收 | `strata 0.1.49.2`、二进制 34,771,696 B（+128 B）、`final_checkpoint count: 2`、Q6K=OFF |
| 切生产 | ready 45-69 s，slots 9901 不变 |
| **效果** | **`0 reused`，三轮全零** |

**补丁确实生效了**——引擎日志每个请求都打 `1 checkpoints`，说明新分支被走到、checkpoint 被存下。

## 2 为什么零收益（三层原因，逐层挖出来的）

### 2.1 第一层：存进去的 checkpoint 被 park 时的 `drop_superseded` 删掉

日志逐字：

```
strata serve: conversation cache: dropped 1 superseded copy of this conversation; parked=3
strata serve: conversation cache: parked 7418 tokens in 194.9 ms; parked=4 ... evictions=1
```

源码 `generate.cpp:9492`（`park_current_body` 内）注释说明了设计意图：

> `#342: before make_room evicts oldest-first, the copies of this conversation a turn back go (they hold nothing the outgoing chain does not, apart from the tail this conversation rewrote)`

**「整段长度」的 checkpoint 必然被出站链（live）覆盖，所以被判定为冗余副本删掉。** 这也解释了为什么 16,384 的 checkpoint 有效（它短于整段，不被完全覆盖），而 7,342 的（等于整段）无效。

### 2.2 第二层：我的三个测试脚本，没有一个还原真实对话形态

| 脚本 | 构造 | 为什么错 |
|---|---|---|
| `w778_mt.py`（W778 用的） | 三轮共享 base，结尾分别是「第一轮/第二轮/第三轮」 | **分支场景**：三轮 prompt 互不为前缀，零复用是**正确行为**，不是缺陷 |
| `_append_turns.py`（本轮第一版） | 追加时加了 `"\n答1："` 标签 | 破坏了「上一轮 prompt + 原始生成」的前缀关系 |
| `_chat_turns.py`（本轮第二版） | 每轮 append 的 user 消息都含完整 `ctx` | **ctx 重复两次** => turn2 prompt 14,651（≈2×7,342），自己跨过了 8192 |
| `_chat_real.py`（最终正确版） | ctx 只在第 1 轮出现，后续只发新问题 | —— |

**前三个都"通过"了，因为它们的失败方式正好符合我想看到的结论（零复用）。**

### 2.3 第三层：真实基线一直是好的

`0.2.4`（**无补丁**）上，`_chat_real.py` 三次连续追问：

| 轮 | prompt | read | reused | prompt_ms | wall |
|---|---|---|---|---|---|
| 1 | 7,349 | 7,349 | 0 | 15,330 | 16.7 s |
| 2 | 7,377 | **33** | **7,344** | **685** | **1.7 s** |
| 3 | 7,393 | **21** | **7,372** | **558** | **1.5 s** |

**第 2 轮复用 7,344 token，prefill 从 15.3 s 降到 0.69 s（22 倍）；第 3 轮 0.56 s（27 倍）。**
所以 `W781` / `W786` 里「8K 以下对话从来没复用上」**是错的**，它是三个错误测试的产物。

## 3 由此暴露的更重要的错误：目标判断又偏了一次

`W786 §1` 用三档**单轮**测量得出「decode 只占端到端 0.5-43%，所以 decode 优化只值 1%」。这个推理在**单轮**下成立，但真实使用是**多轮**，而多轮的构成完全不同：

| 场景 | prefill | decode | 谁是大头 |
|---|---|---|---|
| 单轮长文档（首次） | 6.5 / 44.4 / 211 s | 4.9 / 5.1 / 1.1 s | **prefill（57-99.5%）** |
| **多轮追问（第 2 轮起）** | **0.69 s**（复用后） | 1.0 s（48 token 输出） | **decode** |
| 多轮 + 长输出（320 token） | 0.06 s（新增 30 token） | **5.1 s** | **decode 约 99%** |

=> **优化目标不是"decode 还是 prefill"，而是"首轮还是后续轮"**：
- **首轮**：prefill 是算力地板（GPU 100% + CPU 满载 + 磁盘 0 读），无可优化
- **后续轮**：复用已经把 prefill 压到 0.6 s 量级，**decode 才是唯一大头**

所以 `W786 §4` 把 GEMV（13.3%）/ router（8.1%）/ HC（16.1%）降到「端到端 0.2-0.4%」是**错的**。**但要写准（`AUDIT7 P2-4`）**：13.3% / 8.1% / 16.1% 是 **decode 内部**占比；只有当 decode 占端到端约 99%（输出 >=300 token）时它们才近似等于端到端占比，48 token 输出时 decode 只占 1.0/1.69 = 59%，对应端到端约 **7.9% / 4.8% / 9.5%**。结论不变（比 0.2-0.4% 高一个数量级），但引用必须带条件。

## 4 队列回到哪里

| 项 | W786 的判断 | W787 修正 |
|---|---|---|
| R1 对话复用 | 88 倍，第一优先 | **撤销**（不存在的问题；补丁与镜像留档不用于生产） |
| R2 溢出归因 | <= 3% | 不变（先证在 dispatch 路径） |
| R3 量化+dense GEMV | 端到端 0.2-0.4% | **回升到 13.3%**（多轮场景） |
| R4 路由 fp64 | 端到端 0.2-0.3% | **回升到 8.1%** |
| R5 HC 归因 | 待测 | **回升到 16.1%**（多轮场景下是最大单项） |
| R6 注意力 | M 7.2% / L 10.8% | 不变（L 档 `scores+topk` 翻倍仍是唯一随长度恶化的项） |
| R8 合规基线 | — | 不变 |

**新队列：R5（HC 16.1%）-> R3（GEMV 13.3%）-> R4（router 8.1%）-> R2（溢出）-> R6（注意力）-> R8。**

## 5 纪律（新增三条，都是这次栽出来的）

1. **测试构造必须先证明"它模拟的是真实客户端"**。判据：抓一次真实请求的 `prompt_tokens` 与构造值的比值。本轮 `_chat_turns.py` 的 turn2 是真实值的 2 倍，一眼可见，但我没看。
2. **"零复用 / 零收益 / 不生效"这类否定结论，必须先排除测试构造**。否定的结果太容易与预期吻合，是最容易自欺的一类。
3. **收益预期超过 10 倍的项，先做最小验证（1 行改动 + 单次请求），再投入 25 分钟编译**。本轮如果先用 `--prompt-cache-every 4096` 之类零成本手段验证"到底能不能复用"，就不会有这次重编。

## 6 现状

- 生产：`strata166-407` 已回滚到 **`strata-gfx906:0.2.4`**（`0.1.49.2` / slots 9901 / vram_free 642），ready 45 s
- 实验件留档不用于生产：镜像 `strata-gfx906:0.2.4r1`、容器 `strata166-407.r1`（已停）
- 补丁件留档：`deploy/docker/patch_final_ckpt.py`、`Dockerfile-0.2.4.bak_before_r1`
- 未改动的：config 与 register 的现役行（生产配置与 04:2x 完全一致）
