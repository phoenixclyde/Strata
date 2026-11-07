### 6.17 Web 控制台两处：monitor 页被上游封顶 1920，以及 WEB-UI 补丁的真实存留

起因：2560 宽窗口下 Monitor 页内容只占 **1920px**，两侧各空 ~320px，而 About/Chat 看起来「还是原来的」。

**（1）宽度：上游改的，我们一个字节没动**

- 三棵树的 `serve/web/app.css` md5 全等（`cf027c74…`）：`src0271`(0.1.53) = `src027` = `src028`(0.1.54)；容器 `/src/serve/web/app.css` 同 md5；
  HTTP 直取 `/web/app.css`（24171 B）也同 md5 ⇒ **不是我们的改动，也不是这次重建镜像引入的**。
- 按上游 tag 逐版追 `max-width`：

  | 上游版本 | 规则 |
  |---|---|
  | v0.2.2 ~ v0.2.6 | `.monitor, .about { max-width: 1240px }` |
  | **v0.2.7.1 / v0.2.8** | `.monitor, .about { max-width: min(100%, 1920px) }` |

- 另两条一直是上游设定，与我们无关：`.about { min(100%, 1100px) }`、`.chat { min(100%, 1100px) }`。
- **为什么这次才显形**：截图反算视口 = 2560。用三处尺寸互校（卡片 gap 14px→5.9px、`ctx-gauge` 150px、容器 1968px→829px），
  缩放因子 0.4219，即 1080×452 是 **2560×1073** 等比缩放 ⇒ 1920 的盖子第一次真正咬到，此前（1240 或窄窗口）不咬。
  ⇒ 结论：**上游改的，我跟着带进来了**，不是改错也不是漏改。

**（2）处置：一条 CSS 覆盖，作用域仅 monitor**

`serve/web/app.css` 末尾追加（幂等、带标记，`about`/`chat` 不动）：

```css
/* --- ALBUS-W831 (local patch; registry: deploy/patches/LOCAL_PATCHES.tsv) -------------
   Upstream v0.2.7.1 capped the dashboard at min(100%, 1920px). On a 2560-wide window that
   leaves ~320px dead on each side. Restore the pre-0.2.7.1 behaviour: fill the window.
   Scoped to .monitor only -- .about / .chat keep their upstream caps. */
.monitor { max-width: none; }
```

验证（本机无头 Chrome，`/#monitor` 前端支持 hash 直链）：**2560×1080 实图**下 8 张指标卡一行、Context/Recent requests/Conversation cache 全部通栏；
**1280×900** 下自动回落 4 卡一行，无横向滚动（全局 `box-sizing: border-box`，`width:100%` 不吃 padding）。

**（3）顺带查出的第二个问题：WEB-UI 补丁没在，而门禁给了假绿**

- 部署的 `app.js` 与上游 **v0.2.8 / v0.2.7.1 字节完全相同**（md5 `9fed14d1…`，92101 B）⇒ 我们的 WEB-UI 补丁**不在**里面。
- 把「我们的 patched(63395 B) − 它的 base orig(59958 B)」算出真实增量 **78 行**，逐行比对上游 v0.2.8：
  **74 行上游已原生具备**（`images` 页、`saveApiKey`、prefill 速率、采样默认值、火花线顶值 `Math.max(max||0,…,1)` 全都是官方功能），
  **只有 4 行是我们的**：PCIe 卡子行的 `· peak NN MB/s` 峰值后缀。
- **门禁为什么没报**：`WEB-UI` 那条用的标记是 `saveApiKey`，而上游自己就有这个词 ⇒ 假绿。已把标记换成真正只属于我们的 `pciePk`。
- 处置：按 `ALBUS-W831` 标记把 4 行精确补回（92101 → 92306 B），并保留上游新增的 `· idle GenN` 分支；实测
  `to GPU 0.0 MB/s · peak 162 MB/s`（发一条 24-token 请求后 `history/gpu_pcie_rx_mb` 出现 162.3 的采样）。
  空载时 `pciePk < 1` 不显示，避免 "peak 0.0" 噪声。

**（4）落地与一致性**

镜像 `strata-gfx906:0.2.8p2`（在 p1 基础上改 `serve/` 两层）。`app.css` / `app.js` 的 md5 **四处一致**：
`tree = image = container = 实际下发`（css `4c0a3b6b…`、js `6a968eaf…`）。
为避免二次停服（引擎加载 ~240 s），`app.js` 用 `docker cp` 热更新到运行容器，同时重建镜像；镜像内容与容器逐字节相同，
因此「重启」与「重建容器」都会得到同一份文件，不产生漂移。回滚件齐备：`0.2.8p1`/`0.2.8` 镜像、`app.css.bak-w831`、`app.js.bak-w831b`。

补丁门禁扩到 **13 项**（新增 W831 三条、WEB-UI 三条），当前 **13/13 PASS**。

