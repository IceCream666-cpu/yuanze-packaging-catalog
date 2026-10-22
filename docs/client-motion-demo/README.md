# client1.4 · Care in colour

2026-10-22：按用户提供的15张海报逐项核对，新增056–070（23款精选、53张海报），保留原8款及38张海报。来源、去重和无损核对见 [product-batch-20261022.json](product-batch-20261022.json)。当前本地验收完成、待正式发布。

全屏产品展台与完整海报画廊共用稳定ID；当前及邻近项按需加载，最多2个请求；新增单行可滚动色点条和位置计数。继续client1.3的Apple字体、圆角和清晰图片加载。

素材准备先运行 `scripts/optimize_featured_media.py`，再运行本目录 `optimize-display-assets.py` 和 `prepare-assets.py`；后二者直接读取批准的canonical海报清单，不依赖旧发布目录。构建使用 `vite build --mode showroom`，然后根目录 `scripts/build_customer_showroom.py --edition client14 --stamp-client` 和 `--edition client14`。所有历史发布记录保留如下，不能据其旧数量或命令重发当前版。

# client1.2 · Care in colour

## 2026-10-21 连续滑动修复

修复连续 wheel 被锁、动画重复启动和每帧 React 重绘；改为逐帧合并位移、停止后吸附、速度连续的可中断动画及稳定图片节点。精选与海报画廊共用修复。23 项模型/素材/DOM 检查和全量验证通过，桌面连续正反滑动、390px 拖动及两项筛选已查看；尚不代表实体触控板/手机帧率测试。**已于北京时间 2026-10-21 14:01:11 发布**，源码 `438d8eb3`，线上回执见 [smooth-release.json](smooth-release.json)。仅替换脚本、样式和清单，服务未重启；登录页及 6820 个非目标文件保持。正式域名三角色、资源、原图与实际桌面/手机宽度连续输入验收通过。本次为 client1.2 同版修复。

以下保留 client1.2 首次发布记录。

状态：**已于北京时间 2026-10-21 12:00:00 发布到 [正式客户端](https://bmt.yuanzebeauty.com/client)**，继续原账号密码登录。发布源码 `6fd065a7ef20255ae52f0fc5c2f0fd3fadfa33cb`，公开回执见 [client12-release.json](client12-release.json)。203 项服务器资源、126 项严格 HTTPS 页面与素材校验、三角色权限及真实浏览器验收均已通过。

本版先以 deb02b2 的 client1.0 为业务基线，在 client1.1 预览分支实现用户指定的 LIAOSE 粉色悬浮产品整体设计。2026-10-21 的初次交付为本地设计预览，随后用户明确要求“先上线这个版本”，本次发布沿用该获批视觉。此前预览测试记录 [verification.json](verification.json) 保留为历史证据，不改写成线上验收。

## 体验

首页保留指定参考的大面积粉色、Bodoni / Didot 衬线大标题、中央悬浮产品与倾斜相邻产品、简洁导航、产品说明、圆角查看按钮、前后切换、8 个双色圆点。切换产品时整页色彩随之过渡。原源泽图标保留，并配源泽英文名称。桌面、平板、手机分别排版。

8 款精选按稳定海报 ID 对应当前原海报：012 黄粉磨砂、013 珊瑚青磨砂、039 面部护理系列中的 PDRN 面霜、049 滋润洗发水、042 Woodland、051 蓬松洗发水、044 洁面泡沫、047 Coastal。标题、背景、圆点、收藏和查看原海报始终使用同一 ID。未将原演示中当前库内不存在的精华水、玫瑰护发油或花香护发油冒充当前海报。

鼠标拖动、手机横滑、横向 wheel、方向键、前后按钮与圆点均可切换；释放后吸附，首尾循环，纵向滚动不被阻断。自动轮播默认关闭，开启后每 4.2 秒推进；悬停展台、键盘聚焦展台、打开海报、隐藏页面和离开首页时暂停。系统减少动态效果会停止自动轮播和浮动，并立即对齐选中产品。

“浏览全系列”进入现有 38 张海报库，保留六类用途、视觉风格、中英文搜索、总览/画廊、本机收藏、高清原图/失败重试/缩放/下载。首页与库内收藏共用原存储键 yuanze2.0.1.demo.favorites.v1；不同端口或域名仍不共享本机收藏。往返首页会保留精选位置与库筛选状态。

## 素材边界

原 38 张海报、公开标题/类别/尺寸及源泽 logo 来自当前批准的 server-reference/public/showroom/product-posters.js 和 bundle-manifest.json。38 份预览、38 份缩略图、38 份原图和 logo 共 115 个资源；assets-manifest.json 逐项保留 SHA-256 与字节大小。**这些原始资源完全未修改。**

featured-assets/ 中的 8 张透明 PNG 是首页展示衍生图，使用官方内置 imagegen 提取产品。4 张复用用户所选视觉演示中经核对的同款素材，另 4 张从当前海报重新提取；featured-manifest.json 单独记录来源、匹配说明、输出摘要及范围。它们在设计阶段仅用于本地预览，本次随用户明确批准发布 client1.2 获得展示授权，正式路径为 `/showroom/assets/featured/poster-xxx.png`，纳入登录保护的 bundle-manifest.json。生成的展示图不作为精确包装文字依据，点击查看原海报保留批准原图。

风格与描述为视觉表达，不新增 SKU、供应商、库存、价格、功效或选型/询价功能。

## 运行与检查

```sh
python3 prepare-assets.py
npm run dev
npm test
node tests/browser-featured.cjs
node tests/browser-interruptions.cjs
npm run build
```

开发预览 http://127.0.0.1:8784/；构建输出 dist/，资源路径相对，需本地 HTTP 静态服务。浏览器脚本需要 Playwright 与 Chrome，可通过 QA_URL、QA_CHROME、QA_OUTPUT 指定环境。

设计预览验证记录见 verification.json。浏览器触摸与 wheel 为 Chrome 模拟，不替代实体 iPhone Safari 和物理触控板验收。本地预览模式不请求业务 API；正式 `showroom` 模式读取现有 session 并通过 CSRF 退出，不把本地模拟响应当成线上鉴权验收。

## 正式构建与发布

设计依据与合理例外见 DESIGN.md。从仓库根目录执行：

```sh
(cd docs/client-motion-demo && npm run build:release)
.venv/bin/python scripts/build_customer_showroom.py --edition client12 --stamp-client
.venv/bin/python scripts/build_customer_showroom.py --edition client12
.venv/bin/python scripts/build_customer_showroom.py --check
```

CLI 默认 `client12`；`--edition client1` 与 `--edition legacy` 保留历史构建。正式 Vite 构建禁用 public 目录直接复制，仅生成 `release/index.html`、`preview.js`、`preview.css`；build.json 保存源码和构建摘要。清单接入逐项校验 115 个原资源与 8 个衍生图，拒绝过期源码、构建篡改、路径越界和覆盖原图。

本次安装在既有 `/opt/yuanze-reference/releases/20261013-client-hd-v1` 内完成，203 项静态资源全部核对；只改变三个页面入口及清单，新增 8 张透明图。manifest SHA-256 为 `7e35c629ca90e2ff8f062d78b92124b9f2fa66b8c7d2a15b1342ae0e8c04f993`。展厅之外 6814 个文件摘要保持，服务 PID 18809 未变，无服务重启、release 切换或数据库写入。备份为 `/opt/yuanze-reference/backups/client1.2-20261021-colour-showroom`。

发布前全量验证通过：160 项根测试（3 项既有条件跳过）、249 项后端、32 项部署、全部原前端、18 项旧客户端及 15 项新版测试；生产构建浏览器模拟 session/退出等 13 项检查通过。正式域名另完成 126 项页面与素材摘要核验、客户/员工/管理员权限、匿名拒绝、原图下载及退出失效；真实客户登录的桌面与 390px 手机浏览器 8 项检查通过，JS/网络/意外 HTTP 错误均为 0。首次素材检查遇 TLS EOF 中止，完整重跑全部通过；证据见 client12-release.json。

## 2026-10-21 mobile audit patch

Client1.2 same-version fix: 320px swatch clipping and navigation compression, 44px mobile controls, 16px search inputs, in-flow filters, scroll-contained landscape dialogs, reversible page scroll lock and native pinch-zoom allowance. See `mobile-verification.json` for observed viewport coverage, checks and physical-device limitations. Login is audited without source changes. Published at 2026-10-21 17:24:47 +08:00; live verification and selective no-restart deployment evidence: `mobile-release.json`.
