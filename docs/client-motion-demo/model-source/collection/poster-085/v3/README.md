# Daily Hair Ritual · poster-085 v3

本地 Blender 优化源与交互模型，保留已批准铜棕泵瓶、玫瑰棕软管、奶白完整泵与底盖、原比例和字稿。稳定产品 ID 仍为 `poster-085`。本建模子任务未修改原海报、首页图、正式注册或线上发布。

## 实际修订

- 旧 v2 的程序 Noise/MapRange/Bump 无法随 GLB 导出，三种主材缺粗糙度纹理且 `roughnessFactor` 缺省为 1。v3 为奶白/铜棕/玫瑰棕明确嵌入粗糙度和法线图，玫瑰面另有低对比斜向刷纹色图，网页与 Blender 均使用该纹理链。
- 奶白图 256×256，铜棕/玫瑰细纹图 512×512，玫瑰色图 1024×1024。原主色保留；粗糙度中心分别 .30/.32/.43，铜棕金属度 .68。依 root 初轮网页视觉反馈，法线强度从 1 降至 .22，减弱粗糙锤纹观感，保留柔和纵向反射。
- 两个原单面装饰包覆面改为 UV 完整、封边闭合、名义厚度 .0009 场景单位的薄实体。它们独立展开并投影；仍为装饰表面示意，不新增厚纸标。四张原透明 Logo/产品名载体不投整片矩形影。
- 软管按原截面做单调平顺过渡，68 个自适应纵向截面，最大采样弦误差 0.000196812。名义壁厚 .012。原 72 条封尾压纹与封尾块合为一个网格，11096 个原顶点保留；不删除肋线，不用粗简化替代细节。
- 泵整体保持 6 件含原长空心吸管，补跟随原瓶肩/口形的套接内腔、连接孔和按压杆通孔，原宽扁泵口补真实下方凹口。完整底盖仍 3 件，补上盖出液通孔、清理旧空材质槽，下盖保持闭合。
- 原瓶体、长吸管、下盖和铰链的世界顶点误差为 0。`logo`、`shampoo`、`treatment` 三份 SVG/PNG 逐字节保持；软管文字只重贴合深度，原 X/Z、UV、字形和颜色不改。

## 分组与体积

| 网页 key | 根节点 | 实际 mesh / primitive | 全展开 Three.js 位移 |
| --- | --- | ---: | --- |
| body | Body | 3 | `[1,0,0]` |
| pump | Pump | 6 | `[1,2.95,0]` |
| cap | TubeCap | 3 | `[.85,-.5,0]` |
| label | Label | 2 | `[-.72,.08,.8]` |
| logo | LogoInk | 2 | `[-1.3,.12,1.5]` |
| print | NameInk | 2 | `[-1.5,-.1,2.05]` |

实际 GLB 共 **18 mesh 定义 / 18 mesh 实例 / 18 primitive，105198 triangles**；旧模型90个mesh。浏览器 `renderer.info.render.calls` 包含阴影等 pass，不可当作资产网格数。

GLB **4,316,472 bytes**。本轮首版6,164,800 bytes，通过去除直圆筒高度方向共线细分及按误差采样软管降约30%；这不是与旧v2的体积比较。旧v2约2.10MB且没有新材质图与实体装饰厚度。质量与加载体积均据实际资产报告，不隐瞒本次体积增加。

源帧1/31/61分别为合拢/半开/全开；GLB只导出合拢无动画，由网页控制。原动画偏移保留，完整泵/底盖子件局部矩阵不变。全开长管离瓶口 **.2765503**，完整底盖离软管口 **.3650000**。`mobilePrintSpread=1`，原白字保持。展开属于包材展示，半开时环状装饰可与容器重叠，不能当成物理拆装工艺动画。

## 本机执行

在工程根目录 `/Users/icecream/Documents/Codex/2026-10-22/gen/work/body-care-duo` 执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-085/v3/build_v3.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-085/v3/render_studio.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-085/v3/verify_source.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-085/v3/verify_shadow_rays.py
/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 docs/client-motion-demo/model-source/collection/poster-085/v3/measure_shadow.py
```

`build_v3.py` 从上一层已批准的 `poster-085-v2.blend` 重建，不覆盖原源。`poster-085-v3.blend` 已内嵌全部图片，包含本机 Cycles 棚拍灯光、相机与地台三帧关键帧。

## 验证与图片

- `source-verification.json`：实际重开源档，14 个闭合正体积实体、4 张透明字膜、原72肋线顶点一一保持、孔腔射线、薄壁、文字间隙、完整泵/底盖随动、材质 UV 与 GLB 真实 PBR 链。
- `render-verification.json`：实际 Metal GPU/Cycles、1400×1400、96samples、seed85；闭合/半开/全开及同半开对照。
- `previews/Daily-Hair-Blender-closed.png`：比例、原字稿和柔和泵轮廓。
- `previews/Daily-Hair-Blender-half.png`：六层展开及装饰层落在奶白容器上的阴影。
- `previews/Daily-Hair-Blender-expanded.png`：完整长管离瓶口、完整底盖向下分离，无地台遮挡。
- `previews/Daily-Hair-shadow-control.png`：同相机/灯光/地台/材质/seed，仅将两实体 Label 的 `visible_shadow` 关闭，四字膜始终不投影。原始 PNG 未重绘。
- `shadow-ray-verification.json`：实际裸瓶/裸管各930个接收面采样向真实主灯中心发射射线，分别755/469条被Label实体阻挡；面积光半影另由渲染对照证明。
- `shadow-verification.json`：裸瓶ROI `[910,720,1010,1110]` 有39000像素差>3/255，最大89/255；裸管ROI `[605,850,625,1110]` 有5167像素差>3/255，最大87/255；背景阴性对照0像素差>3/255、最大1/255。未将整图变化当作容器接影。
- `operations.json` 与 `operations-build.json`：本轮只读调查与实际执行命令/参数、构建轮次、冻结信息；没有秘密信息。

root 已独立查看并通过最终 Cycles 合拢/半开/全开/同位阴影对照4张图：无裁切，完整泵/长管与底盖随动，真实对应阴影通过；铜面细砂可见，网页较柔和。网页 revised-closed/half 的22%法线材质已接受。原白字在半展开与奶白容器投影重叠处局部对比偏弱，全开/旋转可区分，root明确保留原字体和颜色。实际结果记录于 `visual-qa.json`。最终网页干净画布阴影和模拟手机检查在本记录时由root继续，未标为真机或已发布。

模型/config冻结后仅补灯光源场景与验证/文档。早先报告保留其生成时的待视觉标记；当前独立验收状态以 `visual-qa.json` 为准。本子任务到此停止，不增加渲染或改变正式注册。

无实物测量或工艺图；场景单位不是毫米。隐藏内腔与装饰纹理为参考推定，这是展示模型，不是生产CAD。
