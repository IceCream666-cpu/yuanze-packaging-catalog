# poster-012 / Beach Magic v2

状态：Blender 源档、GLB、Cycles渲染及网页视觉/阴影验收均已完成；仅本地预览，未正式注册或上线。最终结果见 [QA](../../../../review-evidence/beach-magic/v2/QA.md)。

## 本次修改

- 以 `model-source/beach-magic/beach-magic.blend` 为基础，8 个原机械 Mesh 的顶点及面数量全部保留，包括完整外盖、盖内螺纹/顶面、带短舌内盖、罐身及颈部螺纹。
- 原世界坐标统一乘 30，物体缩放均为 1；Blender 前方为 −Y、上方为 +Z，GLB 导出为 +Y 向上。
- 纸标、liaose Logo 和产品文字成为三个独立层，产品文字包含原标题、说明和彩色线条。SVG 路径和颜色从原稿直接分离，未重新绘制字体。
- 纸标采用真实封闭的圆角曲面，前面保留原金边，背面和封边为无印刷米白材质。纸标有真实投影；Logo/产品文字透明承载面关闭投影，避免矩形阴影。
- 罐体保持空包材；没有添加料体或不属于该罐的泵头。透明材质微调为中性清透，需结合网页和离线灯光独立验收。

## 文件

- `poster-012-v2.blend`：已打包贴图，保存 1/31/61 帧合拢、半展开、完全展开。
- `../../../../packaging-assets/poster-012-v2.glb`：合拢导出，无动画；3,626,268 bytes。
- `review-product.json`：六个部件根与前端 Three.js 展开偏移/旋转建议；此配置仅供预览接入。
- `front-original.svg`、`paper.svg`、`logo.svg`、`product.svg`：原图及分层矢量；各 PNG 均为 2048×1280。
- `prepare_artwork.py`、`rasterize.mjs`、`revise.py`、`verify_source.py`：分层、贴图、重建及独立重开验证脚本。
- `artwork-verification.json`、`build-verification.json`、`source-verification.json`：路径原样保留、几何保留、实体间距、根组、GLB 验证结果。
- `render_studio.py`：Cycles Metal棚拍渲染脚本，已执行四姿态及无纸标投影对照。

## 根与展开偏移

| 前端 key | Blender / GLB 根 | Three.js 完全展开偏移 |
| --- | --- | --- |
| cap | OuterCap | `[0.45, 2.8, 0]` |
| liner | InnerLid | `[0.45, 1.4, 0]` |
| body | Jar | `[0.45, 0, 0]` |
| label | PaperLabel | `[-0.55, 0, 0.75]` |
| print | LogoPrint | `[-1.6, 0.20, 1.35]` |
| name | ProductPrint | `[-1.6, -0.16, 1.45]` |

Blender 对应位移为 `(x, -z, y)`。LogoPrint 与 ProductPrint 是 Mesh 根，其余根是 Empty 组；前端应包含根本身进行遍历。

## 已通过的结构检查

- 机械网格数值保留：归一化前后最大世界坐标误差 0.0000002384。
- 合拢全体尺寸约为 2.790 × 2.796 × 2.298（Blender XYZ）。
- 纸厚约 0.0012，纸背距整个罐体最大半径的保守间隙为 0.00329985。
- 纸标所有长边也已细分：476 个边界点、24 圈，封闭流形且正体积。最坏三角跨角 0.044159 rad，对应弦下沉上界 0.00034112；前背仍至少留 0.00085888，避免曲面三角弦穿透薄背面。
- Logo 与产品文字距纸前的最小径向间隙分别约 0.00051179 / 0.00102378。
- 六根可见；Logo/产品文字有 UV 且关闭投影；纸标两个材质均 OPAQUE，印刷材质为 BLEND。
- 贴图嵌入 GLB，动画数为 0；源档保留 3 个检查帧。

GLB SHA-256：`1181aa8d8738901d12c6cee3790007fd09143f4007e3124cea8a0b398deda643`。

## 重建与验证

在工程根目录依次运行：

```sh
python3 docs/client-motion-demo/model-source/collection/poster-012/v2/prepare_artwork.py
/Users/icecream/.local/bin/node docs/client-motion-demo/model-source/collection/poster-012/v2/rasterize.mjs
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-012/v2/revise.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python docs/client-motion-demo/model-source/collection/poster-012/v2/verify_source.py
```

`revise.py` 重新生成无灯光/相机的基础打包源档；不得在主代理正在编辑或渲染源档时并行运行。几何验证不代替合拢、半展开、完全展开、旋转以及标贴对应阴影的视觉验收。
