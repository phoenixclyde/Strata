# P0 判定：TensileLite 能不能为 gfx906 生成并汇编出 kernel

> 跑于 2026-11-01 00:5x–01:0x。**结论：BLOCK（依赖版本错配），不是 WALL。**
> 判据来自 `PLAN.md §3`：PASS = 有 `.hsaco`；WALL = 汇编器撞 `.amdhsa_accum_offset`（gfx90a+）；
> BLOCK = codegen 起不来。

## 1 这一轮真正拿到的三件事

| # | 事实 | 证据 |
|---|---|---|
| 1 | **codegen 是纯 CPU 的**，不需要 GPU、不需要碰生产 | 上游 `tensilelite/Tensile/Tests/unit/characterization/_codegen/GPU-MOCK.md`：`Codegen emit` / `TensileCreateLibrary` 都标 **No**（"A cross-compiler — host `amdclang++` for the target ISA; no device"），只有 client perf-run 与设备探测需要卡 |
| 2 | **镜像只装了 rocisa 的原生扩展，没装 Python 包** | `ls /opt/rocm/share/hipblaslt/tensilelite/rocisa/` → 只有 `_rocisa.abi3.so`、`libstinkytofu.so*`、`include/`，**没有 `__init__.py`**；`python3 -c "import Tensile"` → `ModuleNotFoundError` |
| 3 | **镜像里的 rocisa 是 10.1 的预发布快照**，既不是 `develop` 也不是 `therock-10.1` | 见 §2 的符号对撞 |

## 2 依赖对撞（逐条实跑，不是猜）

组装方式：源码里的 rocisa **Python 包** + 镜像里的 `_rocisa.abi3.so` + `LD_LIBRARY_PATH=/opt/rocm/lib`
（缺 `liborigami.so.1` 会直接 ImportError；补上后能 import）。

| 源码 ref | 报错 | 含义 |
|---|---|---|
| `develop` | `cannot import name 'VCndMaskB16' from rocisa._rocisa.instruction` | develop 的 TensorLite 期待更新的 rocisa |
| `therock-10.1`（tag，= `gpuep-releases/therock-10.1`） | `cannot import name 'SAtomicCmpswapX2' from rocisa._rocisa.instruction` | 10.1 成品 tag 需要的符号，镜像里的 rocisa **没有** |

镜像实际有的（`dir(rocisa._rocisa.instruction)` 过滤 Atomic）：`BufferAtomicCmpswapB32/B64`、`FlatAtomicCmpswapB32`…
⇒ 我们的 rocisa 比 `therock-10.1` **更早**，比 `develop` **更晚**。三者互不相等。

补充（早期踩到的坑，已记）：
- 稀疏克隆先要 `git read-tree -mu HEAD`（clone 时 index 为空，`sparse-checkout` 只写配置不落文件），
  且要删掉残留的 `.git/index.lock`。
- `pip` 在只读源码树上构建 rocisa 会失败：`scikit-build-core` 要在源码目录里建 `build/`；
  拷到可写目录后仍卡在 build-deps 安装（本轮未继续）。

## 3 结构性判断（比依赖问题更重要）

**墙不在 ISA，在 logic。** 依据：

1. `SUPPORTED_ARCHITECTURES` 里没有 gfx906（10.1 与 develop 都一样），但同一份文件里
   **gfx1100/1101/.../gfx1201 都在** —— 这些是非 MFMA 的 RDNA 目标 ⇒ 生成器**有非 MFMA 的代码路径**，
   "TensileLite 只会写 MFMA" 的说法不成立。
2. Debian 2024 年那次 `.amdhsa_accum_offset requires gfx90a+` 是给 **gfx803** 编老 `Tensile` 时的记录；
   它能证明"某些 logic 会走到 MFMA 累加器布局"，不能证明"gfx906 必然如此"。
3. TheRock-gfx906 文档的原话是 `there is no vega20 logic` —— 与上面一致：缺的是**调优逻辑**，不是 ISA 支持。

⇒ 这条支线的成本模型要改：不是"重写汇编生成器（周）"，而是"**造/移植一份 vega20 logic（天–周）**"，
外加 P1 的 API 对拍。第一步应当是**先让 codegen 跑起来**（配对 rocisa），再讨论 logic。

## 4 下一步（按性价比）

| 序 | 动作 | 判据 |
|---|---|---|
| 1 | **配对 rocisa**：在可写目录里按 `therock-10.1` 源码 `pip install ./rocisa`（先 `pip install pybind11 scikit-build-core cmake ninja`） | `import rocisa` 成功且 `from rocisa.instruction import SAtomicCmpswapX2` 不报错 |
| 2 | 用 `Tensile/Tests/unit/characterization/_codegen/data/gfx1100/{SB,HSS,DB}.yaml` 跑 `--architecture=gfx906` | 出 `.s`；再 `amdclang++ -x assembler` 汇编 |
| 3 | 若第 2 步出 `.s` 但汇编报 gfx90a+ 指令 ⇒ 换更"朴素"的 solution 参数（关 MFMA/WMMA 路径）再试 | 得到**一个** `.hsaco` 才算 PASS |
| 4 | 只有 P0 PASS 才谈 P1（`AlgoGetHeuristic>0` + 与 rocBLAS 对拍） | PLAN.md §3 |

**不要**在这一层往下堆：依赖没配对之前，任何"生成失败"都分不清是 logic 缺还是版本错。

## 5 复现

```bash
# 1) 源码（稀疏，只要 tensilelite）
git clone --filter=blob:none --sparse https://gh-proxy.com/https://github.com/ROCm/rocm-libraries.git
cd rocm-libraries && git sparse-checkout set projects/hipblaslt/tensilelite
rm -f .git/index.lock && git read-tree -mu HEAD
git checkout therock-10.1

# 2) rocisa 的 Python 包（源码）+ 原生扩展（镜像）
cp -r projects/hipblaslt/tensilelite/rocisa/rocisa /out/pylib/rocisa
cp /opt/rocm/share/hipblaslt/tensilelite/rocisa/{_rocisa.abi3.so,libstinkytofu.so*} /out/pylib/rocisa/

# 3) 跑（镜像 strata-gfx906:0.2.9-101）
export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/out/pylib:/src/projects/hipblaslt/tensilelite
python3 Tensile/bin/TensileCreateLibrary --architecture=gfx906 \
  --logic=Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml \
  --output-path=/out/gen --code-object-version=5 --library-format=yaml
```

脚本：`albus/w856/hblt_p0{,b,c}.sh`（本地）；远端日志 `166:data/w856_hblt_p0/`。
