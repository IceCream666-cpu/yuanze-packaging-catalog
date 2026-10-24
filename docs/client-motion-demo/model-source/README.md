# 首页精选 24 款包材结构预览

状态：2026-10-24 本地评审，未上线。用户要求每完成一款就在浏览器打开预览，然后继续下一款，等待统一梳理。

启动既有 Vite 客户端后打开 `/model-review.html`，每款通过 `/?model=poster-XXX` 直达；深链仅在本地模式生效。24 个模型按需加载，海报/收藏/旋转/看瓶底和滚动展开沿用客户端组件。Logo 为独立移动组，固定标签中不再留第二个 Logo。

- `beach-magic/`：原模型保留几何，SVG标签拆为固定文字与独立Logo；可编辑 Blender 场景含拆分后的印刷层。
- `collection/`：22款独立GLB及Blender源文件。`products.json` 保存参考外观参数，`prepare-artwork.mjs` 栅格化可编辑SVG印刷稿，`build_product.py` 逐款生成结构；`make_review.py` 生成本地预览目录。
- 长颈泵瓶沿用 `docs/long-neck-3d/` 的已确认模型与五个独立根组。

生成：`Blender --background --python model-source/collection/build_product.py -- poster-XXX`。使用 Blender 4.5.9；SVG栅格化使用本机已有 Sharp，脚本中的路径对应本机工具运行时。

所有尺寸、壁厚、内盖与非可见结构为外观示意，没有实测供应商尺寸。不含配方料体。部分标签排版重建；玫瑰瓶保留原图花卉边饰的UV映射，Logo独立。外盒与补充袋为外观结构，不代表已校准的印刷刀模。正式定稿需在用户集中梳理后继续校准。

`packaging-manifest.json` 标记 `publicationApproved: false`。本轮没有服务器发布、业务数据写入或线上替换。
