# poster-056 / Golden Face Oil v2

状态：本机 Blender 制作及源档验证；交付主代理进行网页检查。未修改旧资产或正式产品注册，未上线。

## 参考与保留范围

- 基础源档：`../poster-056.blend`；原配方：`../../build_golden_face_oil.py`。
- 原海报：`../../../../public/assets/poster-056-original.webp`。同时沿用原源档中已按实物修订的磨砂空玻璃瓶与前后匹配 U 形保护盖；不将海报的黄色料体加入空包材。
- 瓶型高宽比、宽深比、原文字字号/字距/手写 Logo、橄榄绿油墨及整体颜色体系保留。
- 原图没有实纸标边界。三层展示中的底层是透明薄膜示意，并非声称实物使用纸标。合拢时接近不可见，展开时适度显现，帮助理解印刷分层。

## 本次改善

- 保留原空瓶完整几何，外壁保持磨砂，内壁与厚底采用更清透的玻璃材质，描述真实厚度和底缘。
- 保留原保护盖全部网格与小倒角，精修同色系半透材质。没有在原薄壁接合处叠加不稳定的大倒角。
- 完整泵组包含圆柱按压头、双圈泵座、空心连接段和原长空心吸管；整组一起展开，外保护盖单独先抬起。
- 连接段具有通孔与管口容纳空间。按压柱增加小型内凹侧出液口，没有增加参考中不存在的长嘴；这些隐藏细节是展示推定，不是制造尺寸。
- 原 `print.svg` 拆为 Logo 和 `GOLDEN FACE OIL` 两层，矢量子树原样保留。各自使用 2048×1156 嵌入贴图，透明承载面关闭投影。
- 透明圆角薄膜有真实厚度和封闭边缘，保持柔和投影；其 Alpha 与前端预览同步。

## 文件与根组

- `poster-056-v2.blend`：包含打包贴图和 1/31/61 帧检查姿态；完成棚拍后也保存 Cycles 灯光、相机及地面。
- `../../../../packaging-assets/poster-056-v2.glb`：合拢状态导出，无动画，全部资源内嵌。
- `review-product.json`：仅用于新版本预览的部件、展开与材质控制。
- `prepare_artwork.py` / `rasterize.mjs` / `revise.py` / `verify_source.py` / `render_studio.py`：可复现制作与检查。
- `artwork-verification.json` / `build-verification.json` / `source-verification.json` / `render-verification.json`：实际检查记录；以最新生成的数据为准。
- `previews/`：闭合、半展开、完全展开、旋转四态及关闭薄膜阴影的对照渲染。

| key | 根组 | Three.js 完全展开偏移 |
| --- | --- | --- |
| overcap | Overcap | `[0.4, 4.15, 0]` |
| pump | PumpAssembly | `[0.4, 2.05, 0]` |
| body | Body | `[0.4, 0, 0]` |
| label | PaperLabel | `[-0.45, 0, 0.65]` |
| print | LogoPrint | `[-1.45, 0.20, 1.25]` |
| name | ProductPrint | `[-1.45, -0.16, 1.35]` |

前端 Three 位移 `(x,y,z)` 对应 Blender `(x,-z,y)`。保护盖使用 `[0,.72]` 的 smoothstep 时间区间，半展开时已经离开按压柱。所有模型物体在合拢时 scale=1；两层印字在完全展开时放大到 1.12。

## 验证重点

- 原瓶体、原保护盖、双圈座、长吸管和按压柱顶部嵌面保留顶点/面数量，并比对原世界坐标。
- 所有实体部件封闭流形且为正体积。射线检查吸管中心孔、连接段中心孔和按压柱侧孔通畅。
- 薄膜厚 0.0009，背面距瓶身约 0.001979；吸管底距内底约 0.08227，完全展开后吸管底距瓶口约 0.52801。
- 玻璃名义侧壁厚约 0.06582、厚底约 0.28794；这些都是展示坐标，并非实测毫米。
- 展开过程中泵组所有子件相对变换保持一致；印字与底材分层，印字平面不投整块阴影。
- 棚拍采用真实 Cycles、Metal、64 samples、1200×1500。透明薄膜的瓶身投影很弱：开启/关闭薄膜投影的整瓶区域差值最大为 3/255；不能描述为醒目的实纸标阴影。网页应独立检查其柔和对应投影。渲染通过不能代替网页中的展开、旋转和投影检查。

## 重建顺序

在工程根目录依次运行：

```sh
python3 docs/client-motion-demo/model-source/collection/poster-056/v2/prepare_artwork.py
/Users/icecream/.local/bin/node docs/client-motion-demo/model-source/collection/poster-056/v2/rasterize.mjs
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-056/v2/revise.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-056/v2/render_studio.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-056/v2/verify_source.py
```

`revise.py` 会重新生成本版本基础源档和 GLB，应在渲染之前运行。不要与主代理编辑本版本源档同时执行。正式注册、网页验收、提交与上线由主代理统一处理。
