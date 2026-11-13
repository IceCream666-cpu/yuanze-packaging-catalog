# Daily Hair Ritual · poster-085

2026-11-13：本机 Blender 5.4 Alpha 制作，本地交互预览完成，待用户审查，未发布。

- 参考：daily-hair-ritual-poster-v1.png（原八图第7张）。铜棕长圆柱泵瓶 + 玫瑰棕软管，一瓶一管、空包材。
- 预览：http://127.0.0.1:8785/daily-hair-ritual.html
- 源文件：poster-085-v1.blend；时间轴1合拢、31半展开、61完全展开。
- 网页模型：../../../packaging-assets/poster-085-v1.glb，约2.05MB；3张文字纹理内嵌。
- 制作脚本：build_hair_duo.py；渲染脚本：render_review.py；结构校验：verify_model.py。
- 六组：容器、完整泵头与长吸管、完整软管底盖、装饰面、Logo、产品名。泵头内部不碎拆；无料体。
- 泵管外径0.082、内径0.058，贴近容器内底；比例单位，非毫米。完全展开后管尖离开瓶口。
- 暖灰棕背景用于提高白色独立印刷层的可见度；源海报保持不变。
- 验证：185项前端测试、实际GLB结构断言、独立预览构建通过。Blender正面/侧面/展开及浏览器闭合/半展开/完全展开/旋转目检通过。
- 手机仅393×852模拟视口，未做真机验证。材质、内部结构与尺寸为展示推定，不是生产CAD。

详见 model-verification.json、visual-review.json 和 previews/。正式海报/模型注册、首页列表与client1.50发布资源未修改。

## 2026-11-13 · Cycles 写实场景 v2

新增独立 [photographic-v2 摄影场景](photographic-v2/README.md)，保留 v1 网页模型与原有分组。真实接影地面、无缝背景、四盏面积灯、85mm透视相机、微观材质纹理；源文件已重新打开并验证。2400×3000、16位合拢与完全展开图均已完成并目检；实际源文件及图片校验通过，详见photographic-v2/verification.json及visual-review.json。未发布，未替换网页GLB。

## client1.51 网页 v2
由摄影源场景导出 poster-085-v2.blend 与 GLB，保留6组及物理PBR基础材质、平滑泵嘴。实体装饰面在Blender开启投影，网页开启labelShadows；透明字标承载面不投整片矩形阴影。首页1600×2000透明Cycles渲染。离线程序微纹理与光线追踪不等同实时WebGL。188项基础前端测试及后续新款投影约束检查、GLB断言、发布范围和资源权限检查。
