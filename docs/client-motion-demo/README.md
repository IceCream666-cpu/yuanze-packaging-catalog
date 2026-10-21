# client1.2 · Care in colour

状态：本地设计预览，尚未替换线上 /client。用户明确指定最初 LIAOSE 粉色悬浮产品版的整体设计；本版把完整视觉与交互用于包材库客户端。以 deb02b2 的 client1.0 为业务基线，在 client1.1 预览分支继续实现。

## 体验

首页保留指定参考的大面积粉色、Bodoni / Didot 衬线大标题、中央悬浮产品与倾斜相邻产品、简洁导航、产品说明、圆角查看按钮、前后切换、8 个双色圆点。切换产品时整页色彩随之过渡。原源泽图标保留，并配源泽英文名称。桌面、平板、手机分别排版。

8 款精选按稳定海报 ID 对应当前原海报：012 黄粉磨砂、013 珊瑚青磨砂、039 面部护理系列中的 PDRN 面霜、049 滋润洗发水、042 Woodland、051 蓬松洗发水、044 洁面泡沫、047 Coastal。标题、背景、圆点、收藏和查看原海报始终使用同一 ID。未将原演示中当前库内不存在的精华水、玫瑰护发油或花香护发油冒充当前海报。

鼠标拖动、手机横滑、横向 wheel、方向键、前后按钮与圆点均可切换；释放后吸附，首尾循环，纵向滚动不被阻断。自动轮播默认关闭，开启后每 4.2 秒推进；悬停展台、键盘聚焦展台、打开海报、隐藏页面和离开首页时暂停。系统减少动态效果会停止自动轮播和浮动，并立即对齐选中产品。

“浏览全系列”进入现有 38 张海报库，保留六类用途、视觉风格、中英文搜索、总览/画廊、本机收藏、高清原图/失败重试/缩放/下载。首页与库内收藏共用原存储键 yuanze2.0.1.demo.favorites.v1；不同端口或域名仍不共享本机收藏。往返首页会保留精选位置与库筛选状态。

## 素材边界

原 38 张海报、公开标题/类别/尺寸及源泽 logo 来自当前批准的 server-reference/public/showroom/product-posters.js 和 bundle-manifest.json。38 份预览、38 份缩略图、38 份原图和 logo 共 115 个资源；assets-manifest.json 逐项保留 SHA-256 与字节大小。**这些原始资源完全未修改。**

featured-assets/ 中的 8 张透明 PNG 是首页展示衍生图，使用官方内置 imagegen 提取产品。4 张复用用户所选视觉演示中经核对的同款素材，另 4 张从当前海报重新提取；featured-manifest.json 单独记录来源、匹配说明、输出摘要及范围，不把派生图当成已获正式部署批准的原素材。生成的展示图不作为精确包装文字依据，点击查看原海报保留批准原图。

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

本轮验证记录见 verification.json。浏览器触摸与 wheel 为 Chrome 模拟，不替代实体 iPhone Safari 和物理触控板验收。页面没有业务 API 请求；现有 session/CSRF 适配保留供后续整合，不把本地预览当成线上鉴权验收。

设计依据与合理例外见 DESIGN.md。正式发布脚本仍采用 client1.0；后续整合此版本需把派生资源接入正式资产路径与清单流程，并重新核验访问权限和线上发布结果。
