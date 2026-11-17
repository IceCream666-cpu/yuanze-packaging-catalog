# Soft Body Duo · poster-084 v3

本目录为本机 Blender 制作的本地质量修订稿。未在此任务中修改正式注册、旧资产或发布网站；网页视觉验证由主任务分别记录。

## 保留与修订

- 保留两个原始无色透明玻璃空瓶，瓶壁、厚底、瓶口和瓶型比例均不改；蓝/粉属于原海报的料体，本模型不添加料体。
- 玻璃瓶所有世界坐标顶点与 v2 逐项相同。
- 完整白泵、泵圈、96 条真实肋线、泵嘴、内腔接口和长空心吸管归入同一个 `Pump` 根一起展开。新增实际向下出液口、泵圈底部内腔和中空接口。
- 白色纸标为厚度 0.002 的封闭曲面实体，前后与封边均为米白色；保留原正面占位，不扩大为未经参考确认的完整圆周绕标。
- `LogoInk` 保留原小号白色 liaose 字形与字距，`NameInk` 保留原黑色竖排产品文字。三个原始 SVG 逐字节保留，输出 2048 像素宽的透明 PNG。透明文字承载面不投矩形影。
- 删除白色泵材质未使用的 UV，左右同拓扑白泵共用几何数据，保留两个对象与完整肋线。未抽稀网格、未量化顶点；共享产生的最大世界坐标差为 float32 平移舍入量 1.19e-7。

## 文件

- `poster-084-v3.blend`：已打包图片；保留闭合/半展开/全展开帧 1/31/61 与真实 Cycles 棚拍。
- `../../../../packaging-assets/poster-084-v3.glb`：只导出产品，闭合姿态，无内嵌动画。实际相对路径以工程 `docs/client-motion-demo/packaging-assets/` 为准。
- `review-product.json`：五根及网页展开配置。
- `build_v3.py`、`optimize_meshes.py`：从上一级 v2 源档复现修订；旧 v2 是生成输入，不被覆盖。
- `render_studio.py`：Metal / Cycles，96 samples，1600 × 1600，四态真实渲染与同位阴影开关控制图。
- `verify_source.py`：独立重开源文件，检查实体、孔道、纸标间距、完整泵动作、版本化 GLB 与纹理。
- `build-verification.json`、`mesh-optimization.json`、`source-verification.json`、`render-verification.json`、`visual-qa.json`：实际检查证据。

## 根与数据

| 根 | 直接子对象 | 展开语义 |
|---|---:|---|
| Body | 2 | 两个原始玻璃空瓶 |
| Pump | 4 | 两个完整白泵 + 两条长空心吸管，整组抬升 |
| Label | 2 | 两片实体白纸标 |
| LogoInk | 2 | 两个白色品牌字标 |
| NameInk | 2 | 两套黑色竖排产品字 |

共 12 个逻辑网格对象、11 个 glTF mesh 定义、14 个实际材质 primitive 实例。GLB 为 1,855,884 bytes，较旧 v2 的 2,393,772 bytes 减少 22.47%。

## 阴影与展示边界

实体纸标启用真实 Blender 投影；字标/产品字的透明载体关闭投影。控制图使用相同帧、机位、灯光、随机种子，只切换两个实体标贴的 `visible_shadow`。透明玻璃上的实际阴影较网页接影处理柔和，必须结合原图对照与量化报告判断，不能把纸标反射或物体遮挡直接当成接影验证。

双瓶的竖排字在正面展开时可能与相邻纸标产生画面上的叠位；这些层在三维空间彼此分离，旋转小角度可查看。源稿与网页配置保留同一展开坐标。

这些尺寸属于参考图驱动的展示模型，不是实测制造 CAD。

## 复现命令

在本目录下按顺序运行本机 Blender：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python build_v3.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python render_studio.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python verify_source.py
```

只重做棚拍时运行后两项，避免重新生成已冻结的 GLB/JSON。
