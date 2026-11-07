# W775delta W4 ---- 逐桶账实测（`STRATA_DECODE_TIMING` + `STRATA_VERIFY_PROFILE`）

> 时间：2026-10-11 **20:00-20:06 CST**（停机共 **6 分钟**）｜机主令「你定吧」（承接「W4 的测量并在下一次车的窗口里做」）
> 做法：**不动生产 config**（用它的**副本** + 副本里换 `log` 路径、加两个测量 env）=> 起临时实例 `strata-w4`（port 8091）=> 发短/长两档请求 => 收引擎日志的分解行 => 停临时、恢复生产。
> 靶：`W749-B3` = 「逐桶账（per-bucket ledger）定位我们的长上下文代价」。

## 0 结论（先行）

1. **钩子打通，首份逐桶账到手**。正确入口是 **`STRATA_DECODE_TIMING=1`** + **`STRATA_VERIFY_PROFILE=1`**（`--serve` 模式，`DETAILS.md:298` 的 #610 节）。
   `--gpu-stages` **对我们不可用**：它拒绝 native（IQ）pack（源码 `generate.cpp:5727-5734` 的 `#610` 错误分支逐字 *"a native (IQ) pack has no per-layer graphs to replay"*）。
2. **唯一随上下文增长的 GPU 桶 = QSA 层的 `scores+topk`**：**0.87 -> 2.47 ms/window**（**+1.60**）---- 方向与 routeK 的「full_attn 是唯一随上下文增长的桶」**一致**。
3. **但它很小，量级不足以解释任何大差**：**+1.60 ms ÷ 约 40 ms(verify) = +4%**，且被同量级抖动抵消 => **总 `ms/window` 长短两档无显著差异**（短 51.56 vs 长 49.11，长档反而略低，噪声内）。
4. **我们 decode 的 GPU 时间主要由「专家面」构成**（非 attention 面）：`VRAM hits`（GDN 5.0-5.4 + QSA 1.6-1.8）与 `hc-read1+router`（4.9 + 1.7）各约 6.6-7.2 ms/window，`q8+qkv/q-idx gemv` 约 3.0，`head` 约 1.6；而 attention 系（`scores+topk` + `attention`）合计仅 **2.5-4.1 ms/window**。
5. **与 `W743` 的「长上下文解码 36-38 tok/s vs 短 43-60」不一致**：本次两档 decode 速度相近（**38.5 vs 39.4 tok/s**，`128 generated`）。**须记限定**：本次带 `STRATA_VERIFY_PROFILE=1`，文档逐字说它 *"slows the decode a little: use it to compare, not to measure speed"* => **只做相对对比，绝对速度不作数**。

## 1 配置与安全性（本次合规要点）

| 项 | 做法 | 验证 |
|---|---|---|
| 生产 config | **未改动** | `md5 ff8cb97379f0bdbe76ee555da6d8729c` 前后一致 |
| 生产日志 | **未覆盖** | 副本把 `log` 指向 `/data/_w4_measure.log` |
| 测量 env | 加在**副本的 `env` 段**（`STRATA_DECODE_TIMING=1` / `STRATA_VERIFY_PROFILE=1`） | 副本自检打印 env 五项 |
| 临时实例 | `docker run -d --name strata-w4`，devices/binds/group/security **逐项抄自 `docker inspect`**，port 8091 | `Up` + `/health` OK（40 s 就绪） |
| 恢复 | 停临时 -> 删副本 config -> `docker start strata166-407` | **PROD READY 50 s**、`/health` OK、其余 5 容器不受影响 |
| 临时件清理 | 证据拉回本机后删 166 上 `_w4_*` | `deploy/tmp/_w4_ev/` 留档 |

**注意**：生产实例在测量期间**停机 6 分钟**（VRAM 不可共存：生产 `vram_free_mib=574`）。

## 2 读数（短 5,406 tok vs 长 49,722 tok，各 2 runs）

### 2.1 `strata decode timing:`（ms/window）

| 臂 | windows | avg T | **ms/window** | verify | (GPU-reach wait) | (per-layer host [CPU]) | commit | draft | CPU experts | VRAM hits |
|---|---|---|---|---|---|---|---|---|---|---|
| SHORT r0 | 61 | 2.36 | **54.57** | 40.97 | 31.14 | 6.48 [5.92] | 0.04 | 4.70 | 1.26 | 20.91 |
| SHORT r1 | 57 | 2.49 | **48.55** | 39.38 | 33.68 | 3.76 [3.21] | 0.04 | 3.54 | 0.64 | 23.49 |
| LONG r0 | 65 | 2.29 | **50.04** | 39.14 | 33.39 | 3.92 [3.42] | 0.10 | 3.70 | 0.70 | 21.34 |
| LONG r1 | 62 | 2.45 | **48.18** | 40.54 | 35.63 | 2.99 [2.51] | 0.06 | 3.36 | 0.49 | 23.34 |

### 2.2 `strata decode GPU stages (ms/window)`：关键项

| 臂 | total | GDN `q8+qkv/q-idx gemv` / `hc-read1+router` / `VRAM hits` | QSA `q+q-idx` / **`scores+topk`** / `attention` |
|---|---|---|---|
| SHORT r0 | 39.97 | 3.05 / 4.94 / 5.01 | 1.80 / **0.87** / 1.59 |
| SHORT r1 | 39.71 | 3.14 / 4.92 / 5.42 | 1.85 / **0.87** / 1.67 |
| LONG r0 | 39.43 | 2.91 / 4.89 / 5.00 | 1.72 / **2.45** / 1.57 |
| LONG r1 | 40.82 | 3.10 / 4.91 / 5.36 | 1.82 / **2.48** / 1.65 |

### 2.3 短 vs 长（两 run 均值）

| 项 | short | long | delta |
|---|---:|---:|---:|
| `ms/window` | 51.560 | 49.110 | **-2.450** |
| `verify` | 40.175 | 39.840 | -0.335 |
| GPU-reach wait | 32.410 | 34.510 | +2.100 |
| per-layer host（含 CPU） | 5.120 | 3.455 | -1.665 |
| GPU stages `total` | 39.840 | 40.125 | +0.285 |
| **QSA `scores+topk`** | **0.870** | **2.465** | **+1.595** |
| QSA `attention` | 1.630 | 1.610 | -0.020 |

## 3 判读

- **增长项**：只有 `scores+topk`（QSA 的 attention scores + topk）**单调随上下文增长**，+1.60 ms/window => 若按 40 ms 的 verify 算约 **+4%**。
- **抵消项**：同量级的 `per-layer host`（-1.67）与 `GPU-reach wait`（+2.10）在 2 runs 内抖动很大 => **总 `ms/window` 在两档间不可分辨**。
- **主导项（与上下文无关）**：`VRAM hits`（6.6-7.2）+ `hc-read1+router`（6.6）+ `gemv`（3.0）+ `head`（1.6）=> **expert/路由/搬运**才是我们 decode 的 GPU 主体。
- **与 routeK 的差异**：routeK 在 k4 上得「full_attn 增长占 64k->120k 增长的 **87%**」；本机**不复现**该主导性（不同模型 / 不同引擎 / 不同 KV 格式 `k8v4` / 不同 attention 结构 GDN+QSA 混合）。

## 4 局限（必须随行）

1. **仅 2 runs/档**，且本项目 decode spread 惯常 16-41% => **`ms/window` 的两档差（-2.45）在噪声内**；结论只落在**单桶 `scores+topk` 的单调性**上（该桶本身 spread 小：0.87/0.87 与 2.45/2.48）。
2. **测量本身拖慢 decode**（文档逐字）=> **绝对速度不作数**，只做同条件相对对比。
3. 只做了**两档**（5.4K / 49.7K）；未做 16K / 128K 的中间点 => 增长是否线性未验。
4. 两档都是**冷请求**（每 run 换 salt）；短档的 `read_ms` 11.6-12.8 s、长档 105.7-106.0 s。
5. 三桶（mixer / ffn+router / post）在本引擎**对 native pack 不可得**（`--gpu-stages` 拒绝）；本件的桶是按引擎自己打印的 stage 名分的（GDN / QSA 各段），粒度更细但**不等价**于 R0.9 的三桶。

## 5 复现

```bash
# 1) 副本 config（改 log + 加两个测量 env）—— 绝不改生产 config
cp /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json /home/albus/strata166/data/_w4_measure.json
python3 - <<'PY'
import json; p='/home/albus/strata166/data/_w4_measure.json'; d=json.load(open(p))
d['log']='/data/_w4_measure.log'; d['env']['STRATA_DECODE_TIMING']='1'; d['env']['STRATA_VERIFY_PROFILE']='1'
json.dump(d,open(p,'w'),indent=1)
PY
# 2) 停生产、起临时（devices/binds 抄自 docker inspect）
docker stop -t 30 strata166-407
docker run -d --name strata-w4 --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable --ipc host -v /home/albus/strata166/data:/data -v /models:/models:ro \
  -e STRATA_SRC=/src -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -p 8091:8091 strata-gfx906:0.1.42 \
  /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/_w4_measure.json --port 8091"
# 3) 两档
docker exec strata-w4 python3 /data/_w773_speed.py http://127.0.0.1:8091 W4s /data/_w4_s.json 8192  2 /data/_w4_measure.log 128
docker exec strata-w4 python3 /data/_w773_speed.py http://127.0.0.1:8091 W4l /data/_w4_l.json 65536 2 /data/_w4_measure.log 128
# 4) 收行
grep -a "strata decode timing\|strata decode GPU stages" /home/albus/strata166/data/_w4_measure.log
# 5) 恢复
docker stop -t 20 strata-w4 && docker rm -f strata-w4 && rm -f /data/_w4_measure.json
docker start strata166-407
```

**本机留档**：`deploy/tmp/_w4_ev/`（`_w4_measure.keep.log` / `_w4_s.json` / `_w4_l.json`）· 解析脚本 `deploy/tmp/_w4_analyze.py`。
