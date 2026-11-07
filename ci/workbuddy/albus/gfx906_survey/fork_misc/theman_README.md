# llama.cpp GFX906 Turbo + MTP Support (Patch Wrapper)

This repository provides a reliable, patch-based wrapper to inject **GFX906 (Radeon VII / MI50) Turbo optimizations** and **TurboQuant KV Cache Compression** into a known-stable version of the upstream [llama.cpp](https://github.com/ggml-org/llama.cpp) repository.

The current patch is based on upstream commit `6e60f35608ec6918b44a9839c0c433687165f086` and reproduces full-fork tag `gfx906-b11187` (`90338319703e9deb31ce584dd6a42ac8900c9665`).

## What is included in this patch?
1. **GFX906 Wave64 Kernels:** Highly optimized warp-cooperative kernels tailored specifically for the Radeon VII / MI50 hardware architecture, drastically improving Prompt Processing and Token Generation speed.
2. **TurboQuant:** Support for 2-bit, 3-bit (`turbo3`), and 4-bit KV cache compression to save up to 78% of Context VRAM with minimal quality loss.
3. **Shadow Cache:** A persistent FP16 shadow cache workaround to resolve the known ROCm 6.0+ instability issues on GFX906 during FlashAttention dequantization.
4. **FWHT Rotation:** A fast $O(d \log d)$ Walsh-Hadamard Transform kernel (`GGML_OP_TURBO_WHT`) to rotate the KV cache into a compression-friendly space.
5. **HIP Graphs:** Fully integrated and activated `-DGGML_HIP_GRAPHS=ON` to reduce CPU overhead during decoding.

## How to use

We provide a simple Bash script that automatically clones the upstream repository, checks out the exact commit this patch was built for, and applies the optimizations.

### 1. Run the Wrapper Script

```bash
chmod +x apply-turbo.sh
./apply-turbo.sh
```

If successful, you will see a new directory called `llama.cpp-gfx906-turbo`.

### 2. Build the Project

Move into the new directory and build using CMake. The script will output these exact commands:

```bash
cmake -S llama.cpp-gfx906-turbo -B llama.cpp-gfx906-turbo/build -G Ninja \
  -DGGML_HIP=ON -DGPU_TARGETS=gfx906 -DAMDGPU_TARGETS=gfx906 \
  -DCMAKE_HIP_ARCHITECTURES=gfx906 -DGGML_HIP_GFX906=ON \
  -DGGML_HIP_GRAPHS=ON -DGGML_HIP_MMQ_MFMA=ON -DGGML_HIP_NO_VMM=ON \
  -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp-gfx906-turbo/build --target llama-server --parallel "$(nproc)"
```

### 3. Run with Turbo3 and MTP

```bash
./bin/llama-cli -m your_model.gguf --mtp 1 --ctk turbo3 --ctv turbo3 -fa on ...
```

## Maintaining and Updating

This patch is tied to upstream commit `6e60f35608ec6918b44a9839c0c433687165f086` from September 23, 2026.

If you want to update to a newer upstream commit in the future:
1. Change the `STABLE_COMMIT` variable in `apply-turbo.sh`.
2. Regenerate the patch from the verified full fork against that exact upstream commit.
3. Run `apply-turbo.sh` against a fresh target directory.
4. Build and run the same GFX906 verification gates as the full fork.

The script uses `git apply --check` before applying anything, so an incompatible patch leaves the target working tree unchanged.

## September 2026 optimization review

- Current upstream already includes a dedicated GCN MMQ table with wide Q8_0 and MXFP4 tiles; the separately published GFX906 Q8 MMQ patch is therefore substantially duplicated here.
- Exabit's GFX906 MXFP4 repack reports large gains on Qwen3.6 MXFP4 models, but it depends on a separate repack subsystem and follow-up commits. It is intentionally not folded into this standalone patch without an isolated MI50 benchmark and compatibility pass.
- The GFX906 SOLVE_TRI safety gate is retained for GCN hardware.