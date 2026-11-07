# 记 W715：切 huihui abliterated 权重（主模型/MTP/vision/n-gram 四面）
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W715 切 huihui abliterated 权重（2026-10-09 01:4x-02:1x）
- **动作**：现役从 base 切到 huihui abliterated。链路：iq_pack 重生成 pack -> 改 register(P00/P01/P20 + 新增 P99/V00-V02)
  -> gen_config --write -> 推 166 -> 建 -407 -> 停 -406 -> 复验 PASS=17 FAIL=0。
- **pack**：/data/packs/huihui-ud-iq4_xs（tools/iq_pack.py --gguf huihui分片1 --out ... --compat-bf16）。
  **本次最有价值的机理结论**：与 base pack 逐字节对比，dense.bin / index.txt / native_experts.txt / conversions.json **全同**，
  仅 compat-bf16.json 差 4 行 => **abliteration 的差异只落在 experts（IQ4_XS 量化权重，由 --native 直读生效）**，
  float 张量（norm/router 等，即 dense.bin）**一个字节都没动**。
- **容器**：strata166-407（huihui）Up；strata166-406（base）Exited(0) **保留作回滚**。
  注意：日志出现 "session is up" 只代表引擎就绪；serve 可服务还要等 33.45 GiB page-locked 建完
  （实测首次请求打过去会 Connection refused，需轮询 /v1/models 才算真就绪）。
- **vision**：tools/vision 编译 => **/data/vision/strata-vision**（7754632 B，静态单文件；
  cmake -S tools/vision -B /data/vision-build -G Ninja -DLLAMA_DIR=third_party/llama.cpp；PORTABLE=ON/AVX2 基线，
  本机 Xeon E5-2696 v4 无 AVX-512）。config 新增 --vision + vision 段（exe/mmproj/model）。
  **实测**：448x448 测试图（黑框+红圆+蓝矩形）被准确描述；/v1/models 报 input_modalities ["text","image"]；
  CPU 22 线程编码，model files loaded in 1.0 s。产物放 /data/vision 而非镜像层（**新容器不会继承镜像内改动**）。
- **n-gram**：PLE 表 per_layer_token_embd.weight 在**分片2**；3 分片模型**不需要 --ple-gguf**（setup.py:5351 逻辑
  `if len(shards) <= 2` 才加），引擎按名字自找。启动行 `PLE on, table 320001536 rows of huihui分片2`。
  --ple-io 保持默认 direct（register **P91 已测 =ram 为 REJECTED，-45%**）。suffix draft 实测 4 次触发：5/8、3/3、7/11、20/20。
- **MTP**：复用 /data/mtp/rt（huihui 仓不带 MTP；其源是官方 Qwen/Qwen3.8-Flash-Next BF16 checkpoint 的 31 个 mtp.* 张量）。
  `draft layer loaded, 1098 MiB of VRAM (experts 675, dense 111)`。
  **接受率实测**（5 次）：33/40、29/33、162/233、66/104、80/91 = **370/501 (73.9%)**；
  base 历史同口径 5 次：11/13、29/41、30/34、30/39、281/440 = 381/567 (67.2%) => 同量级、**无退化**。
- **权威件改动**（两侧 md5 已对齐）：PARAM_REGISTER.tsv（40 行 / ADOPTED 20 / REJECTED 13 / CANDIDATE 7；
  本机 md5 88f3529d6ed9a2208c0bed307543815e）· gen_config.py（支持 scope=CFG -> cfg[段][键]；META/OUT 改 huihui）·
  verify_config.py（LIVE/LOG 改新名 strata-huihui-ud-iq4_xs.{json,log}）。config 本机 md5 ce7aa95e936a9199928487c2a8606951。
- **待查**：expert cache 槽 10289 -> 9757（-1.21 GiB，与 free VRAM 24.09 -> 22.88 GiB 同步）是否与 --vision 预留有关，未证。
- **回滚**：docker stop strata166-407 && docker start strata166-406（config 与 register 的 .bak_w715_* 均在）。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
back = io.open(LOG, encoding="utf-8").read()
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
bad = [hex(ord(c)) for c in note if ord(c) in BAN]
print("追加 %d 字符；文件现 %d 字符；CR=%d；禁用码位=%d" % (len(note), len(back), back.count("\r"), len(bad)))
for k in ["W715", "abliteration 的差异只落在 experts", "strata-vision", "370/501", "P91"]:
    print("  自证 %-34s %s" % (k, "OK" if k in back else "**缺失**"))
