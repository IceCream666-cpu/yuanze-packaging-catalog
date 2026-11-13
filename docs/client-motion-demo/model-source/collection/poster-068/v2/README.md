# Essence Water / 旧款21 / poster-068 v2

状态：本地待用户审查，未发布。正式注册仍使用旧版068；23/071尚未修改。

本机 Blender 5.4 Alpha 修改原 .blend，保留四个原网格的世界坐标、透明扁方玻璃瓶与厚底、淡紫折面外盖。外盖、银色颈圈、内封口组成 CapAssembly，整体抬起；本款没有泵头，不新增吸管。空瓶，无料体。

五组：Body、CapAssembly、Label、LogoInk、NameInk。淡紫标贴含细边框，向外第一层；liaose字形第二层；ESSENCE WATER、分隔线、200 ml第三层。文字不投整块矩形阴影，实体标贴投影保留。

- 源档：`poster-068-v2.blend`（纹理已打包）
- 模型：`../../../../packaging-assets/poster-068-v2.glb`
- 本地页面：http://127.0.0.1:8785/essence-water.html
- 生成/核验：`revise.py`、`render_studio.py`、`verify_source.py`，运行 Blender 时使用 `--python-exit-code 1`。
- Cycles Metal 64 samples，1200×1500，四盏面积灯与真实接影地面；`previews/`包含合拢、半展开、完全展开、旋转及阴影关闭对照。
- 详见 `../../../../review-evidence/essence-water/v2/QA.md`。

网页使用实时WebGL，玻璃透射率0.94保留少量接影表面响应；与Cycles离线光线追踪不完全相同。尺寸为原模型展示比例，并非制造尺寸。
