#!/usr/bin/env python3
# W1050 R114 offline gate (v3, targeted):
#   blk.N.ssm_alpha.weight / blk.N.ssm_beta.weight are F32 in GGUF; the engine converts
#   to bf16 at load ("native_bf16_projections") and gdn_ab_kernel (fused_gdn.cu:101-118)
#   reinterprets those bf16 bits to fp32 for fmaf.  The dot2 variant would instead keep
#   fp16 weights for v_dot2_f32_f16.  Gate: F32 -> engine bf16 (round-to-nearest-even)
#   -> fp16, counting losslessness.  External basis (searched): every bf16 value in
#   [6.103515625e-5, 65504] converts to fp16 EXACTLY; only the two tails lose.
import glob
import json
import sys

sys.path.insert(0, "/llama.cpp/gguf-py")
import gguf  # noqa: E402
import numpy as np  # noqa: E402

FP16_MAX = 65504.0
FP16_MIN_NORMAL = 6.103515625e-5
TARGETS = ("ssm_alpha.weight", "ssm_beta.weight")


def f32_to_bf16_bits(f32: np.ndarray) -> np.ndarray:
    """Engine-style f32 -> bf16: round-to-nearest-even on the low 16 bits."""
    bits = f32.view(np.uint32).copy()
    rounding_bias = ((bits >> 16) & 1) + 0x7FFF  # RNE
    return ((bits + rounding_bias) >> 16).astype(np.uint16)


def bf16_bits_to_f32(b16: np.ndarray) -> np.ndarray:
    return (b16.astype(np.uint32) << 16).view(np.float32)


def main():
    base = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL"
    files = sorted(glob.glob(base + "/*.gguf"))
    print("shards", len(files))
    agg = {k: {"n": 0, "over": 0, "under": 0, "bf16_exact": 0, "fp16_exact_from_bf16": 0,
               "min_abs": 1e30, "max_abs": 0.0} for k in TARGETS}
    for p in files:
        r = gguf.GGUFReader(p)
        for t in r.tensors:
            for k in TARGETS:
                if not t.name.endswith(k):
                    continue
                f32 = np.asarray(t.data, dtype=np.float32).reshape(-1)
                # engine conversion
                b16 = f32_to_bf16_bits(f32)
                w = bf16_bits_to_f32(b16)
                a = agg[k]
                mag = np.abs(w)
                nz = mag[mag > 0]
                a["n"] += int(w.size)
                a["over"] += int((mag > FP16_MAX).sum())
                a["under"] += int(((mag > 0) & (mag < FP16_MIN_NORMAL)).sum())
                a["bf16_exact"] += int((w == f32).sum())
                h = w.astype(np.float16)          # bf16 value -> fp16
                back = h.astype(np.float32)
                a["fp16_exact_from_bf16"] += int((back == w).sum())
                if nz.size:
                    a["min_abs"] = min(a["min_abs"], float(nz.min()))
                if mag.size:
                    a["max_abs"] = max(a["max_abs"], float(mag.max()))
    print("tensor n min|w| max|w| over under bf16_exact fp16_exact_from_bf16")
    verdict_ok = True
    for k, a in agg.items():
        n = max(1, a["n"])
        print("%s n=%d min|w|=%.6g max|w|=%.6g over=%d under=%d bf16_exact=%d (%.3f%%) fp16_exact=%d (%.3f%%)" %
              (k, a["n"], a["min_abs"], a["max_abs"], a["over"], a["under"],
               a["bf16_exact"], 100.0 * a["bf16_exact"] / n,
               a["fp16_exact_from_bf16"], 100.0 * a["fp16_exact_from_bf16"] / n))
        # gate: no tail loss AND bf16->fp16 must be lossless (100% of bf16 values)
        if a["over"] or a["under"] or a["fp16_exact_from_bf16"] != a["n"]:
            verdict_ok = False
    out = {"fp16_max": FP16_MAX, "fp16_min_normal": FP16_MIN_NORMAL,
           "results": agg, "verdict": "PASS" if verdict_ok else "FAIL"}
    open(sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/tmp/w1050/gdn_range.json",
         "w").write(json.dumps(out, indent=1))
    print("R114_OFFLINE_GATE:", out["verdict"])


if __name__ == "__main__":
    main()
