# client1.2 设计依据

用户指定的视觉基准：本聊天中的 liaose-slider-preview.png，1440 × 900，粉色首屏、Care in colour.、透明悬浮产品、大衬线字、双色圆点及右侧操作。此明确参考优先于旧客户端 Apple 风格记录；本轮不抽取新的随机风格。

核心构图：把已批准海报中的产品带到纯色舞台，让客户通过色彩与轮廓探索，再打开完整海报。首页仅突出这条路径；搜索、类别和全部 38 张海报放在“浏览全系列”。

- 首屏背景 #f4c8d6，文字 #3c1927；其余 7 种颜色对应当前精选产品，见 src/featured.json。
- 大标题 Bodoni 72 / Didot / Times New Roman；正文 Helvetica Neue / PingFang SC。系统字体依赖与原参考一致，不宣称跨系统字形完全一致。
- 桌面边距 4.3vw，标题 6.8vw，产品舞台 46svh；手机 22px 边距、单列文案和独立操作行。
- 主体与相邻产品以位移、轻微旋转和缩放表达深度；没有给透明图加卡片、方框或台面。浮动 5.5 秒，手动切换吸附约 0.36–0.66 秒。
- 减少动态效果关闭浮动、过渡和自动播放，维持完整内容与手动切换。

独立视觉核验：审阅者实际检查 1440×900 与 390×844 的全部 8 个居中状态，以及手机英文导航。主体完整，无透明黑底、裁切或明显残留；首页构图与指定参考一致。051 束口泵瓶和 044 细长洁面瓶按自然比例显示，不为了填满同样宽度而拉伸。

规则扫描的合理保留：这是用户指定的单屏交互展台，无需添加无关背景视频或额外滚动章节。标题使用用户选定文案，右侧中文说明护理品类；页脚与辅助元信息沿用参考较小字号。海报库中的顺序计数和海报投影用于原有画廊操作，不套用营销页面装饰规则。

最终视觉评估：构图与参考一致、产品辨识清晰、交互入口完整；局限是用户提供海报生成的透明展示图并非精确三维模型。完整批准海报仍是包装细节的依据。本轮交付是本地可交互设计预览。

## Final visual critique

ROUND 1
Seen in one second: A colourful product collection with an immediately draggable hero.
Idea (one sentence): Explore approved care-product packaging through colour and silhouette, then open its original poster.
Live thing: Eight-product circular carousel with theme, content and poster identity linked.
Layout words by section: hero=oversized type plus floating cutouts / controls=copy left and actions right / library=searchable poster grid.
Scores: design 7 · usability 9 · creativity 7 · content 9 → overall 7.7
Caps applied: Strict generic still-page warning caps design at 7; user-pinned single-screen motion takes precedence over adding unrelated effects.
Top three problems: No blocking visual defects found in desktop, tablet or phone screenshots. Non-blocking limits are system-font differences across platforms, small auxiliary footer text retained from the reference, and generated display cutouts whose fine print should be checked in the original poster.
