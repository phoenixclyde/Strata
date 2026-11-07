# 追加今日日志：B1 边界矩阵 + register P34 结论 + B1b 新假设
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W712d B1：--prompt-cache-every 三档边界（2026-10-08 21:06-21:24，Z0=off）
- 单变量三臂（8192 现役 / 16384 旧默认 / 32768 候选）x 三档长度（4,589 / 9,989 / 23,939 token），
  每臂独立 restart 并断言容器 /proc 里确实是该值；**9 个格子全部与机制预测吻合**。
- **<8k**：三臂 reused 恒 0，温 TTFT 10.472/10.496/10.464 s 约等于冷 10.83~10.88 s => 换任何值都无用（chunk 机制所限：
  该档确实建了 1 个 checkpoint，但**对齐要求**（边界须为 chunk 整数倍）才是决定性的）。
- **8-16k**：只有 8192 有效（reused=8192、温 5.866 s），16384/32768 得 0（温 23.066/23.147 s）=> W709 的单侧推断变双向实测。
- **>16k**：8192 与 16384 等效（reused=16384、温 16.990/16.989 s），32768 归零（温 50.181 s 约等于冷 49.99 s）
  => **"值越大越好"不成立**；**8192 是三档上都不劣的唯一档位**，P34 值不动。
- 收尾：生产 config 无条件拷回（md5 仍 d2b10f0c...）、verify_config.py PASS=15/FAIL=0、register 值未动只补
  P34 的 evidence/verdict（md5 a91b677e... -> 3bf819e3ccd3f54ed454154b14c3eb3f，35/16/12/7 不变，已同步 166）；
  重新 gen_config --write 后生产 config **逐字节未变**（identical=True）。
- 证据：`deploy/tmp/_w712_b1_remote.log`（166 的 b1.log 全文 12,162 B）、`_verify_after_b1*.out.txt`；
  远端 `b1.log` 与脚本 `/home/albus/strata166/w712/b1_cacheevery.sh`（md5 317f76ac5b652c2836a998962ff414f2）。
- **派生新假设 B1b（未测，已列方案首位）**：help 实读 `--prefill CHUNK` 支持显式尺寸（auto = 不超过 8192）。
  若 chunk 降到 4096（且 `--prompt-cache-every 4096` 对齐），4.6k prompt 就有 4096 边界可复用（约 89%），
  温 TTFT 有望 10.4 s -> 约 1.3 s。**风险必须同测**：小 chunk 可能降低长 prompt 预填吞吐（W709 只测过调大无收益，调小从未测）。
- 文档同步：`W712_UPGRADE.md` 新增 §3.2（矩阵）与 §3.3（B1b）；`W712_PLAN.md` B1 标完成、B1b 提到首位；
  `configs/workbuddy-strata166.md` 新增第十节（为什么短对话每轮都慢）。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note))
