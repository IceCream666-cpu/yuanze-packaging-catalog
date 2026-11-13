# 23 / Sculptural Pump v2 — 本地待审

保持 poster-071 稳定编号。2026-11-13 使用本机 Blender 5.4 Alpha 修订，未更改正式注册，线上仍为旧 liaose-pump.glb。

- 保留原瓶外侧 13440 个顶点及泵头形态，乳白表面、长颈宽肩比例不变；补成空内腔。
- 将泵头、杆、细纹旋盖及较粗透明长吸管合为 PumpAssembly；吸管外径0.086、内径0.058，近瓶底开口，数值为展示归一化单位。
- Body、PumpAssembly、Label、LogoInk 四组。透明承印膜是印刷展示层，并不证明原产品使用贴纸；原海报只有liaose字标，没有新增产品名或容量。
- 源档含合拢/半开/全开动画与Cycles摄影场景。透明承印面投影，文字平面禁投不透明整片影。

预览：http://127.0.0.1:8785/sculptural-pump.html
源档：[poster-071-v2.blend](poster-071-v2.blend)
网页资源：[poster-071-v2.glb](../../../../packaging-assets/poster-071-v2.glb)。
依赖：原模型 work/client18/docs/long-neck-3d/liaose-pump.blend；共享 ../../tail_model_helpers.py。原档只读，旧GLB保留。

运行 revise.py 导出初始GLB/源档；再以生成的.blend运行 render_studio.py；verify_source.py重开校验。Blender使用 --python-exit-code 1。检查证据在 client-motion-demo/review-evidence/sculptural-pump/v2/。

内部泵结构、吸管尺寸和材料为合理展示方案，没有实测尺寸或生产验证。
