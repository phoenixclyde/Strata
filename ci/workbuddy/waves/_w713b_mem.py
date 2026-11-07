# 记忆追加：CPU 侧实测（Intel/无AVX-512）+ 0.1.41 镜像已建 + 全量账
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W713b CPU 侧实测 + 0.1.41 镜像 + 全量账（2026-10-08 22:1x-22:3x）
机主提醒「我们是 amd 的卡但是 intel 的 cpu，你再看看」=> 按"卡与 CPU 分开判"重列 relevance。
- **CPU 实测（166，22:1x）**：Intel Xeon E5-2696 v4 @2.20GHz / 44 逻辑核；**AVX2=44、FMA=44、BMI2=44；
  AVX-512(f/vl/bw/vnni) 全部 = 0**。引擎日志自认：
  `strata generate: this CPU has no AVX-512: the expert kernels run on AVX-2 (multi-token for the i-quant gate/up rows)`
  + `CPU pool tasks/phase: 66 (automatic), participating threads: 22` => 我们跑 AVX2 专家内核 + 22 参与线程。
- **由此修正两处判读**：① #795「CPU 无 AVX-512 时崩溃」由"与我无关"升级为 **CPU 侧最该看一眼的风险项**
  （官方措辞是 hardening，且新增的构建期反汇编 + Intel SDE 检查对我们"从源码自建"是白拿的保障 => 0.1.41 构建已把这条压住）；
  ② **P23 `STRATA_PREFILL_CPU_SHARE` 在 AMD 卡上仍值得测**（0.1.41 只把**默认**开给 NVIDIA 单卡，官方写 "AMD is as before"
  = AMD 保持 opt-in，不是不支持），且我们 22 线程有富余；同族 `STRATA_PREFILL_CPU_SHARE_MAX=3072` 并入 B2 次级臂。
- **0.1.41 镜像已建好**：`strata-gfx906:0.1.41` / `c45268e786e1` / 6.57 GB / 22:14:46；
  引擎 binary 24,982,264 B / md5 `160611838796d4b172ec3a642ccd988d`；`strata --version` = `strata 0.1.41`；
  构建日志**实测打出 `PATCH_SURFACE_ZERO`**（`patched=0 / verified=6 / failed=0`）。**容器 -405 与切换未做**。
- **全量账写进 `deploy/W713_PLAN.md` §6**（18,508 B / 219 行 / CR=0 / BAN=0）：**已做 11 项**（迁移+删原件、0.1.40.4 升级+中性A/B、
  0.1.41 镜像、W709 三项 ADOPTED、机制三实证、A2 解码分母、B1 九格矩阵、B1b 首轮、固化审计+P34 入 register、CPU 实测、闸门方案）；
  **没做 14 项**（W1 切换、W2 闸门脚本、B1b 收口三件、B7/P35 STAGER_SSD、B3、B2、B6、B4、B5、0.1.41 lend-coverage 告警观察、
  C4、C5、C1、C3）；**重做 6 项**（0.1.40.x 全部读数须在 0.1.41 重取、B1b 的"答案是否变"检查(上一轮漏项)、
  0.1.40.1 历史读数只作存档、上一轮对抗性审计、把"中性验证"升级为每版例行闸门、CPU 侧判读）。
- 不得引用的件：`deploy/logs/_w727.out.txt`（测试域无效）。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note))
