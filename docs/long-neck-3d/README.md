# liaose 长颈雕塑泵瓶 · 3D 外观展示

基于 poster-071 效果图重建的可编辑模型，保留乳白磨砂外观、长颈宽底、细纹旋盖、左向泵嘴与现有 liaose 矢量字标。

瓶盖包含独立的按压头与泵嘴、泵杆与连接座、细纹旋盖三层，展开滑杆控制连续分离/合拢。Logo 为独立印刷网格，随展开向瓶身外移出并等比例放大，回滑后贴回原位；没有复制或改写字体。瓶口与旋盖内腔仅为展示示意。

打开 `index.html` 即可离线交互，无需安装或联网。支持鼠标/触控拖动旋转、滚轮展开、双指/滑杆缩放、自动旋转、恢复视角；聚焦模型区后，左右方向键旋转，上下方向键缩放。

- `assets/liaose-pump.glb`：自包含模型，内嵌 Logo 贴图。
- `liaose-pump.blend`：可编辑 Blender 源文件，含棚拍灯光和相机。
- `assets/studio.png`：从三维模型渲染的静态效果图。
- `source/build_model.py`：Blender 4.5 建模/导出脚本。
- `source/viewer.js`、`source/template.html`：交互和界面源码。
- `source/package.py`：检查 GLB 与打包独立 HTML。

在包材库仓库中复建：运行 Blender `--background --python docs/long-neck-3d/source/build_model.py`，使用已安装 Vite 执行 `build --config docs/long-neck-3d/source/vite.config.mjs`，最后运行 `python3 docs/long-neck-3d/source/package.py`。无需新增 npm 依赖。交互源码复用客户端已经安装的 Three.js；OrbitControls 及其 MIT 许可随源码保留。

验证：GLB 容器、组件命名、内嵌贴图与自包含性检查通过；Ego Lite 实际检查本地 HTTP 和 file:// 离线加载、桌面/393px 手机宽度、鼠标拖动、滚轮展开、键盘旋转/缩放、展开滑杆 Home/End、自动旋转/暂停和复位；正面、侧面、背面视觉检查通过。Impeccable 检测无发现，浏览器实看保留既有浅鼠尾草绿和深绿排版。

这是独立本地交互交付，尚未接入正式客户端。单张参考图没有实测尺寸，背面及未显示的结构为外观近似；未制作内部泵芯、液体模拟或量产开模结构，未在实体手机上测试。
