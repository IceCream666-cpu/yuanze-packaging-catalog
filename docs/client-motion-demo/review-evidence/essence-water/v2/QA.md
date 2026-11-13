# 21 / Essence Water v2 本地检查

2026-11-13；本地完成，未发布，待用户检查。顺序20已上线→21当前→23未动。

原海报 `docs/mobile-client-preview/assets/posters/poster-068.webp` 已目检：透明扁方玻璃、厚底、淡紫U形折面盖、银色颈圈，淡紫细边框标贴。保留原瓶型与盖形，原四个网格世界坐标逐点比较一致。无料体、不额外增加泵或吸管。

## 验证
- Blender重开源档验证通过：3个盖部件同组，合拢→50%→100%→50%→0%内部相对矩阵不变。
- Cycles真实地面/四盏面积灯，合拢、半展开、全展开、旋转成片已目检；实体标贴可投影，文字面禁投不透明矩形。
- 193/193前端测试通过，新增本款真实GLB节点与变换测试；隔离构建 `/tmp/essence-water-build-check` 成功，没有覆盖已上线发布包。
- Ego Lite本地页面合拢、半展开、完全展开、旋转90度、复位、原海报打开/返回均通过。桌面与393×852手机模拟视口已目检，无页面横溢；不等同真机验证。
- 网页50%展开、同场景只切换Label.castShadow：瓶身对应范围出现3054个差值大于2的像素，差异边界[581,514,844,872]。开关截图与x20差分留存。透明膜投影较弱，未把整块文字面当作阴影。
- 审美polish：对照原海报检查轮廓、配色、字体、分层与画面裁切；静态审美检测结果为空列表。沿用既有交互，不改页面结构。

## 文件与状态
- 截图：closed.png、half.png、expanded.png、rotated.png、mobile-simulated.png。
- 阴影：film-shadow-on.png、film-shadow-off.png、difference-x20.png、shadow-comparison.json。
- 测试/构建：frontend-tests.txt、isolated-build.txt。
- 独立预览入口：essence-water.html；正式collection-products.json、manifest及首页均未切换068。
- 实时玻璃使用0.94透射率近似接影，不等同Cycles光线追踪；本款为展示模型，不提供生产尺寸依据。
