import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

# ---- §0.1: W1021 只改了主线行，前三行还停在 0.2.10 —— "唯一来源"过期就等于没有来源
PAIRS = [
 ("| 生产容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101` |",
  "| 生产容器 / 镜像 | `7f375aff168a` / `strata-gfx906:0.2.11-101`（image `92689ea54d11`） |"),
 ("| 引擎 md5 / 大小 | `eea5ea3749ad54b124330386605a18bc` / 44,908,992 B（`strata-0.1.56-090`） |",
  "| 引擎 md5 / 大小 | `5e63174dbd7cc04e5fa1b5fc455b2a73` / 42,947,088 B（`strata-0.1.57-001`） |"),
 ("| config md5 / args / env | `e62685e6ff21d9e2b60c1cd622fd5a67` / 37 / 9 |",
  "| config md5 / args / env | `53ac61e0c663a6a46b7a5aa2e610bf43` / 37 / 9 |"),
 ("树 = `mi50-0.2.11-r33-3`（v0.2.11 + 两处 API 移植，线性）；**镜像 `strata-gfx906:0.2.11-101`（`/src` = v0.2.11）**；引擎 `strata-0.1.57-001`（md5 `5e63174d…`，`--version` = 0.1.57）；容器 `4f9d5c5b` 跑 `0.2.11-101`",
  "树 = `mi50-0.2.11-r33-7` @ `56fd43a0`（v0.2.11 + API 移植 + 发布门，线性，behind 0 / ahead 70 / merges 0）；**镜像 `strata-gfx906:0.2.11-101`（`/src` = 该 tag 的树）**；引擎 `strata-0.1.57-001`（md5 `5e63174d…`）；容器 `7f375aff168a` 跑 `0.2.11-101`"),
 ("| 进度分母 | **279 条 / 已结 199 / 71.3%** |",
  "| 进度分母 | **281 条 / 已结 201 / 71.5%** |"),
]
for a, b in PAIRS:
    assert a in s, a[:50]
    s = s.replace(a, b, 1)

# ---- §0.1: 新的第七行 —— 依赖 pin。之前"版本"只算自家五处，把 llama.cpp 排除在外
ROW = ("| **依赖 pin（llama.cpp）** | **`b11062` = `3cf03257f219afbe7334045ff7c6a06ac68c627d`**（2026-09-20）；"
       "整树 hash `6feee58927d5f1efd38e72bbc1db061d`；镜像 `/src/third_party/llama.cpp`、构建挂载 `ref/llama_3cf0325`、"
       "引擎 `/llama.cpp/…`×93 三处同 hash；自 0.2.8p2 起未变 | `ci/release_check.py` 三行（pin / tree / build refs）；"
       "上游钉法 `.github/workflows/metal-build.yml:29` |\n")
anchor = "| **唯一队列** |"
if "依赖 pin（llama.cpp）" not in s:
    assert anchor in s
    s = s.replace(anchor, ROW + anchor, 1)

BLOCK = '''
### 回写 · W1022（生产用的 llama.cpp 是哪一个：查出来，并且从此可校验）

机主问「目前生产的 llama.cpp 的版本你没写」。查了，答案是**一个具体 commit，而且从 0.2.8 起就没动过**；
更要紧的是**发布记录里那一位是残的**（只有 7 位前缀，没有任何可校验的内容），这轮把它改成第五个指针。

**一、事实（三种独立取证，互不依赖）**

| 取证角度 | 看到的东西 |
|---|---|
| 上游钉法 | `.github/workflows/metal-build.yml:29` → `LLAMA_CPP_COMMIT: 3cf03257f219afbe7334045ff7c6a06ac68c627d` |
| 这是什么版本 | GitHub API：2026-09-20，`am17an`，"CUDA: enable sparse fa for qwen4 (#28770)"；`git ls-remote` 显示 `refs/tags/b11062` 正指向它 ⇒ **b11062** |
| 镜像里是哪份 | `/src/third_party/llama.cpp` 整树 hash **`6feee58927d5f1efd38e72bbc1db061d`**（2824 文件 / 166,037,690 B） |
| 编进引擎的是哪份 | 构建挂载 `ref/llama_3cf0325` 同 hash；`_ci_all.txt` 里 `/llama.cpp/` 引用 **93 处**、链接 `libggml-cpu.a`/`libggml-base.a`；二进制里留着 `/llama.cpp/ggml/src/...` 的 debug 路径 |
| 变了没有 | `0.2.8p2 / 0.2.9-101 / 0.2.10-101 / 0.2.11-101` 四个镜像的整树 hash **全等** ⇒ 跟上游 v0.2.11 **没有**动 llama.cpp |

**二、发布记录的两个缺陷（这才是问题本身）**

1. `BUILD-IMAGE.json` 写的是 `"llama_cpp": "3cf0325"` —— **7 位前缀**。任何东西都不能拿它校验：
   前缀可以碰撞，也不告诉你树里是什么。
2. **没有任何树指纹**。镜像可以整棵换掉 vendored llama.cpp 而**不动一个版本字符串**，四指针全绿。

**三、改法（第五个指针，按内容而不是按标签）**

`ci/release_check.py` 从 6 项扩到 **10 项**，新增四行：

| 行 | 判据 |
|---|---|
| `llama.cpp pin (upstream)` | 从仓内 workflow 读出 40 位 sha（缺失即 FAIL——没有 pin 就没有可校验的东西） |
| `llama.cpp pin (release)` | `BUILD-IMAGE.json` 的 `llama_cpp` 必须是 **完整 40 位**且等于上游 pin |
| `llama.cpp tree (image)` | 构建时写入 `llama_cpp_tree`，运行时在镜像内**重算整树 hash** 比对 |
| `llama.cpp in engine build` | `_ci_all.txt` 必须存在 `/llama.cpp/` 引用（0 次 = 引擎是从别处编的） |

`ci/selftest_pin.py` 用四个临时 repo 证明它会红：错 pin / 无 pin / 引擎没引用 / 正例；**4/4**，
已接进 `round_gate --ci`（无 docker 的 runner 打印 `SKIP(no docker)` 而不是假绿）。

**四、镜像与容器（这一轮真正改了生产的地方）**

- `ci/docker/Dockerfile-gfx906-0.2.11` 纳入仓库（此前只在 `build-ctx-211` 里，等于不可重现）；
- 构建时 `ENV LLAMA_CPP_SHA/BUILD/TREE` + `test "$TH" = "$LLAMA_CPP_TREE"`：**tar 被换则构建失败**；
- `commits_on_top` / `tag` 改成 `--build-arg` 注入（字面量 66 在写完后十分钟就错了，这是本项目的老毛病）；
- 镜像 `92689ea54d11`、容器 `7f375aff168a`、`restarts=0`、`/health` ok（60 s）；`RELEASE_CHECK: PASS`（10/10）；
- 性能未退化：prefill@2K **528.94**（CV 0.62%）、@8K **714.10**（CV 0.06%）、decode 35.49、TTFT 3.93 s。

**五、教训**

「版本」这个词在本项目一直只覆盖自家五处（tag / 镜像 json / binary / 编译宏 / 配置 exe），
**依赖的版本从来没进过发布记录**。而依赖一旦是 vendored 源码树，它就不是一个字符串而是一棵树——
字符串能改对、树能被换掉。凡是 vendored 的东西，记录单位必须是 **hash**。
'''
if "回写 · W1022" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P350",
  "生产 llama.cpp = b11062 / 3cf03257（2026-09-20），自 0.2.8p2 起四个镜像整树同 hash 未变",
  "W1022", "DONE",
  "**W1022 立**：三种独立取证——上游钉法 `.github/workflows/metal-build.yml:29`；"
  "`git ls-remote` 显示 refs/tags/b11062 = 3cf03257f219afbe7334045ff7c6a06ac68c627d；"
  "镜像 `/src/third_party/llama.cpp` 整树 hash `6feee58927d5f1efd38e72bbc1db061d`（2824 文件 / 166,037,690 B），"
  "与构建挂载 `ref/llama_3cf0325`、引擎 `/llama.cpp/`×93 完全一致。0.2.8p2/0.2.9/0.2.10/0.2.11 四个镜像同 hash ⇒ 跟上游没有动它。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1022"),
 ("B8工程", "P351",
  "第五个指针：依赖 pin 按**内容**校验（40 位 sha + 整树 hash + 构建引用数），并证明它会红",
  "W1022", "DONE",
  "**W1022 立**：旧 `BUILD-IMAGE.json` 只有 `llama_cpp: \"3cf0325\"`（7 位前缀，不可校验）且无树指纹 ⇒ 镜像可整棵换树而四指针全绿。"
  "`ci/release_check.py` 6→10 项；`ci/selftest_pin.py` 4/4（错 pin / 无 pin / 引擎未引用 / 正例）已进 `round_gate --ci`，"
  "无 docker 时打印 `SKIP(no docker)`。Dockerfile 构建期断言树 hash，`commits_on_top`/`tag` 改 `--build-arg` 注入。"
  "本轮 `RELEASE_CHECK: PASS`。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1022"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
