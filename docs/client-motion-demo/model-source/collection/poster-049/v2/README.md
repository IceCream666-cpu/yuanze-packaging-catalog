# poster-049 v2 — 本地候选

本机 Blender 5.4 Alpha 打开原 poster-049.blend 修订，保留外部瓶型与银色泵头原顶点，新增中空长吸管及连接座。真实薄纸标、字标和产品文字独立展开，原文案不变。

- revise.py：加载旧源稿，输出新 GLB 和三阶段动画源场景。
- render_studio.py：Cycles / Metal，64 采样、1200×1500，四状态和阴影控制图。
- verify_source.py：重开源稿检查泵组、管长、投影与动画。
- review-product.json：独立前端预览配置，正式注册未切换。

网页玻璃阴影为实时近似，完整光路以 Cycles 渲染为准。隐藏内部结构为展示推定，非制造 CAD。

预览：http://127.0.0.1:8785/moisture-quality.html

本款未发布；下一款 072。
