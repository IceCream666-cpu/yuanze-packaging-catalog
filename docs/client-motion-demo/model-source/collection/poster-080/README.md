# Bath Trio — 本地模型审查

2026-11-06 更新白色款默认预览，尚未发布。打开 `http://127.0.0.1:8794/bath-trio.html`；本页单独注册 poster-080，正式海报和首页清单未加入本款。

本机 Blender 建模，`poster-080-v2.blend` 默认打开奶白色 Soap Clean Soap，含 soap / after / baby 三场景；第 1、31、61 帧分别为合拢、半展开、完全展开。三种款式共享瓶型，完整泵组含长中空吸管，不含料体。Logo、品名及容量位于独立印刷层。尺寸和隐藏内部结构为展示示意。

网页 GLB：`../../../packaging-assets/poster-080-v2.glb`。重建配方 `../build_bath_trio.py`；原海报 `bath-trio.webp`，审查配置 `review-product.json`，新版验证记录 `review-verification-v2.json`（v1 记录保留）。

前端截图保存在工作区 outputs/20261103-Bath-Trio。网页与 Blender 材质存在实时渲染差异，最终网页验收以浏览器为准。

白色款前端截图保存在工作区 `outputs/20261106-Bath-Trio-White`。v1 GLB 和 `poster-080.blend` 保留供回退。白色版保留完整泵组、长吸管以及透明底层 / 字标 / 品名的独立展开。
