# Exfoliating Hand Gel — Blender v2

本地 Blender 建模与源档版本；正式产品身份仍为 `poster-081`。本建模任务未改注册、海报或部署。浏览器验收与是否发布由主代理单独记录。

## 保留与修改

- 原透明厚底玻璃瓶、96 齿黑色旋盖、弧形泵嘴、活塞/按压杆和长中空吸管的全部世界顶点保持一致。空瓶不加绿色料体，也不把玻璃染绿。
- 完整泵保持 `Pump` 一个展开根节点、五个机械网格；补通原泵底接口内腔与吸管插孔，保留原出口凹腔。射线验证接口、出口凹腔、中空管轴线及斜口开放。
- 米白织物环标改为有内外面和薄卷边的闭合实体，厚度 0.010，闭合时与瓶身的最小三角面采样间隙 0.002097。经纬纱线采用同物理间距的 512×512 平铺颜色/法线图；两款布材质为不透明实体。
- 黑色侧旗减薄至 0.008，轻微弯曲；保留原可见外边缘和其上的白色 `liaose` 字标。侧旗、侧旗白字跟随环标展开。
- 主 Logo、产品名仍为各自独立图层。三份原 SVG/PNG 逐字节保留；三层透明字膜不投矩形影，只有真实布层参与投影。

## 根节点与网页配置

| 网页 key | Blender / GLB 根节点 | Three.js 全展开位移 |
| --- | --- | --- |
| body | Body | `[0, 0, 0]` |
| pump | Pump | `[0, 2.3, 0]` |
| label | Label | `[-1.45, 0.02, 0.9]` |
| logo | LogoInk | `[-2.45, 0.24, 1.62]` |
| print | NameInk | `[-2.45, -0.08, 2.04]` |

布标/Logo/产品字全展开缩放分别为 1.03 / 1.18 / 1.18；本款 `mobilePrintSpread=1`，避免窄屏缩短位移后重新穿入瓶身。Blender 坐标为前 −Y、上 Z，对应位移变换 `(x, -z, y)`。

源档保存闭合/半开/全开帧 1 / 31 / 61。全展开实体环标与玻璃的径向包络净距为 **0.104977**，泵管最低点高于瓶口 **0.272900**。环形布标的中间动画是分层比较示意，并非物理脱套路径；不宣称中间状态无碰撞。

GLB 导出闭合装配、五个根节点、11 个 mesh / primitive、六张内嵌图像、无动画。原 4,527,020 bytes 降为 **2,053,332 bytes**（减少 **54.64%**），主要通过平铺织纹代替高熵宽幅图，不抽稀泵头与玻璃。

## 本机重建

从客户端工程目录运行，顺序如下；前两个命令需要本机 Blender，最后一个需要 Pillow。

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-081/v2/build_v2.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-081/v2/render_studio.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python model-source/collection/poster-081/v2/verify_source.py
/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 model-source/collection/poster-081/v2/measure_shadow.py
```

`build_v2.py` 读取上一层原 `poster-081-v1.blend` 和原 SVG/PNG。完成的 `poster-081-v2.blend` 已内嵌图片，可单独打开；包括真实 Cycles 棚拍灯光和相机。GLB 位于客户端 `packaging-assets/poster-081-v2.glb`。

## 验证和影像

- `build-verification.json`：构建输出、原图哈希和机械顶点保持证据。
- `source-verification.json`：独立重开源档，验证八个实体网格闭合/正体积，三层字膜不投影，泵管与接口射线、动作、几何间隙、GLB 结构与大小。
- `render-verification.json`：本机 Cycles Metal、96 samples、1600×1600 四态及相机记录。
- `previews/Hand-Gel-Blender-closed.png`、`-half.png`、`-expanded.png`、`-rotated.png`：未经重绘的 Cycles 输出。
- `previews/Hand-Gel-shadow-control.png`：和半展开完全同位同光同 seed，仅关闭两层实体织物的 `visible_shadow`；透明侧旗白字仍不投影。
- `shadow-verification.json`：同位差异与不含前景布标的露出玻璃 ROI。下方玻璃区 2,745 像素差值大于 3/255，最大 8/255；右方/上方区最大仅 3/255、2/255。透明玻璃的物理接影较弱，不能把布标自身、反射或地面阴影当作强烈瓶身阴影；网页专门接影另行验证。

正式独立视觉验收详见 `visual-qa.json`。这是一份展示级包材资产，单位是统一场景单位，不是制造尺寸图。
