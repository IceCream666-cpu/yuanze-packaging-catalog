# Soap Clean Duo — Blender v2

本地版本，稳定产品 ID 为 `poster-082`。主代理已独立通过最终 Cycles 四态、阴影控制与网页桌面视觉验收；本子任务未发布。保留已批准海报中的 180 ml 浅蓝条纹软管与 300 ml 乳白圆盘泵瓶、粗体 liaose 和全部原文。本建模任务未改海报、首页图、正式注册或部署。

## 结构修订

- 软管由稀疏线性截面改为形状保持的连续曲率截面；肩颈无同高半径跳台，外壳与细压纹封尾属于同一连通薄壁实体。主体名义壁厚 0.013 场景单位；轻微弯曲保持新品外形，不添加夸张挤压凹痕。
- 131 个自适应纵向截面，采样弦误差不超过 0.0002；主要圆周 128 段，封尾局部细分以保留细压纹。只对几乎透明的两张概念印刷载体减少冗余分段，不降字图分辨率。
- 右侧乳白塑料瓶全部世界顶点保持；未改成玻璃，不加料体。原长中空吸管、蓝色翻盖下半部与后铰链的世界顶点也保持一致。
- 完整圆盘泵保持六个机械网格，补开闭合座、内部插孔和按压杆内腔；在原后缘低矮出液片开真实凹口，没有新增顶柱。长中空吸管随完整泵抬起。
- 完整翻盖保持三网格，补上盖出液通孔，并将旧布尔指扣的空材质槽归为原浅蓝塑料。闭合底盖仍保持封口状态。
- 蓝色条纹是 **0.0006 场景单位的薄实体直印装饰**，28 段原间断条纹与文字避让区保留。它是本款唯一印刷层投影实体；两张透明概念承载面和六张文字载体均不投矩形影。没有新增纸标。
- 四份原 SVG/PNG（logo、soap-clean-soap、spec-tube、spec-bottle）逐字节保留。软管文字重新贴合连续曲面，UV/字形/位置大小保持。

## 根节点与展开

| 网页 key | 根节点 | 网格数 | Three.js 全展开位移 |
| --- | --- | ---: | --- |
| body | Body | 2 | `[1, 0, 0]` |
| pump | Pump | 6 | `[1, 2.1, 0]` |
| cap | TubeCap | 3 | `[0.75, -0.7, 0.15]` |
| label | Label | 3 | `[-0.85, 0.05, 0.75]` |
| logo | LogoInk | 2 | `[-1.55, 0.25, 1.35]` |
| print | NameInk | 4 | `[-1.6, -0.05, 1.85]` |

沿用原动作与 `mobilePrintSpread=1`，Logo/产品文字的全展开缩放为 1.08。源帧 1/31/61 对应闭合/半开/全开；GLB 为闭合、无动画，由网页控制展开。Blender 前 −Y、上 Z；网页位移 `(x,y,z)` 对应 Blender `(x,-z,y)`。

源文件实际射线、顶点与动作检查确认：全开长管末端高于瓶口 **0.04155**，完整软管盖低于软管口 **0.554**。三种源姿态的地台均低于最低部件，向下展开的盖组不会被地台遮住。局部文字与条纹可在正面投影中交叠，旋转后可辨认独立深度。

GLB 为 **2,782,400 bytes**、20 个 mesh/primitive。修订首版为 4,140,204 bytes，通过控制采样误差与透明载体采样减少约 32.79%；这个数字是与本轮首版比较，不能说比原 v1 更小。

## 本机重建和验证

在 `docs/client-motion-demo` 目录按顺序执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-082/v2/build_v2.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-082/v2/render_studio.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-082/v2/verify_source.py
/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 model-source/collection/poster-082/v2/measure_shadow.py
```

构建读取上一层 `poster-082-v1.blend` 与原图；完成的 `poster-082-v2.blend` 已内嵌所用图片，可独立打开，包含 Cycles 棚拍灯光、相机和对应地台关键帧。

- `original-inspection.json`：修改前真实源结构和材质记录。
- `build-verification.json`：构建信息、采样误差与原字稿哈希。
- `source-verification.json`：独立重开源档；12 个实体闭合/正体积，封尾与管体单一连通，薄壁和接口射线、完整泵/盖随动、字膜间隙、原图保持、GLB 结构等检查。
- `render-verification.json`：本机 Cycles Metal、96 samples、1600×1600 四态及同位控制。
- `previews/Soap-Duo-Blender-{closed,half,expanded,rotated}.png`：最终四态，未经重绘。
- `previews/Soap-Duo-shadow-control.png`：同半开姿态、同相机、同灯光、同地台、同 seed82，仅关闭薄实体蓝条的 `visible_shadow`。
- `shadow-verification.json`：未印刷管壁 ROI 与右瓶阴性对照。下方裸管区有 128 像素差 >3/255、最大 4/255；上方管壁最大 3/255，右瓶最大 1/255。薄直印装饰的物理阴影较弱；不把整图差异、蓝线本身或地面阴影说成强烈瓶身影。
- `visual-qa.json`：主代理 `/root` 已独立查看原海报、最终 Cycles 四态/同位控制以及网页闭合/半开/全开/90° 旋转，视觉通过。网页仅切换实体蓝条 `castShadow` 的同位比较，在裸软管 ROI `[710,310,770,420]` 有 362 像素差 >3/255、最大 10/255，平均最大通道差 0.390606；两透明载体无矩形影。网页证据位于 `review-evidence/soap-clean/v2/`。390×844 模拟手机闭合、半开、全开已由主任务逐图查看通过，无页面横向溢出；仍未作真机验证。

最终收尾仅补本文和 `visual-qa.json`；GLB、配置及 Blender 源档保持冻结。早先生成的各验证报告保留生成时的待视觉复核标记，最终独立验收状态以 `visual-qa.json` 为准。

真实工厂尺寸和隐藏结构未提供；这是空包材展示模型，场景单位不是毫米，后部/内腔是合理展示推定，不作为生产 CAD。
