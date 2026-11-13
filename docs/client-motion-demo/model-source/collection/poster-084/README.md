# Soft Body Duo · poster-084

## 当前状态（2026-11-13）
海报已于2026-11-12发布并验证。3D v2 本地待审，未发布。

用户纠正：透明玻璃瓶；蓝色与粉色来自料体。本模型沿用空包材展示，不含料体。
本机 Blender 从保留的 v1 场景修正双瓶材质，另存 `poster-084-v2.blend` 并导出 `poster-084-v2.glb`。瓶体使用中空内外壁及厚底；完整泵组、长透明吸管、白色标贴、独立Logo和产品文字保持原结构。

- 当前入口：http://127.0.0.1:8785/soft-body-duo.html
- 构建：`build_glass_v2.py`（本机Blender执行）
- 结构与材质检查：`python3 verify_model.py`
- 回退：v1 Blender/GLB和`review-product-v1.json`保留。
- 来源：主工程`outputs/20261111-Soft-Body-Duo/reference-06.jpg`；海报保留蓝粉料体视觉。

## 验证
GLB校验确认双瓶透射材质为无色玻璃，未添加料体；前端183项测试通过。目检合拢、半展开、完全展开、侧面、瓶底及393×852模拟视口；081玻璃模型回归目检通过。截图见`../../../review-evidence/soft-body/glass-v2/`。
审美工具静态检测未发现问题，并已目检。网页吸管使用现有透明合成方式，属于展示级近似，不是精确多层折射。
