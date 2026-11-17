# poster-085 v3 — 只读调查与最小改进方案

状态：仅调查；等待 root 确认 082 上线后启动。没有保存源模型、导出 GLB、渲染或修改正式注册。

## 当前实际源与参考

- `../poster-085-v2.blend`，本机 Blender 5.4.0 Alpha 只读重新打开成功。
- `../daily-hair-ritual-poster-v1.png`：铜棕长泵瓶、玫瑰棕软管、奶白宽泵与底盖；铜面细砂高光、玫瑰面低对比斜向刷纹。logo 和文案原样保留。
- `../build_hair_duo.py`、`../render_photographic.py`、`../export_web_v2.py`：原几何、程序微纹理、网页导出链。
- `../../../../review-evidence/all-models-20261117/screenshots/poster-085-half.png`：六层可展开，但铜/玫瑰面近纯色、白部件层次偏平。
- `original-inspection.json` 与 `original-glb-inspection.json` 为本次当前文件实际读取结果；`operations.json` 含完整 Blender argv、只读检查代码及 shell 等价命令。

## 已证实问题

1. 主材程序 Noise→MapRange/Bump 在 Cycles 存在，但 GLB 没有 normalTexture、metallicRoughnessTexture，且奶白/铜棕/玫瑰棕的 roughnessFactor 缺省为 1。网页未带入源 .30/.32/.43 的粗糙度变化。这是实时材质发平的直接数据原因。
2. 90 mesh / 90 primitive、2,099,732 bytes。Body 为 75 个网格，其中 72 个是同材质 `Tube seal ridge` 小肋线，可只合并保留全部几何。
3. `Bottle copper bronze decorative wrap` 与 `Tube rose bronze decorative wrap` 均 10,465 顶点/10,240 面，无 UV，各 448 条边界边。它们是开口单面包覆曲面，不是有物理边缘的薄实体；现在投影开启。
4. 旧泵座、按压杆、连接件配方以轴心封闭；泵口是暗色封闭小块并非开口。长吸管本身为空心实体，外径 .082 / 内径 .058，应保留。
5. `Tube cap | closure sleeve` 有一个空材质槽；原上盖中心为封面，应补真实出液通孔。下盖/铰链和外部样式保留。
6. 软管主体仅十段原 profile，可按原截面平滑过渡；不夸大软化、不改变封尾宽度或原产品比例。

## 稳定分组与原比例

六根：Body75、Pump6、TubeCap3、Label2、LogoInk2、NameInk2。整体世界包围盒 `[-1.1025,-.522,0]` 到 `[1.162,.522,3.329]`。三张原印刷图内嵌：logo 1360×500、shampoo 1400×220、treatment 900×450；均保留原字形、透明 alpha、UV 与颜色。源帧1/31/61已有动画，网页 GLB 无动画。

## 建议最小 v3

- 补可导出的轻量纹理链：主材明确 PBR 常数，低分辨率细纹 normal/roughness；玫瑰装饰增加对应原海报的克制抽象斜刷色纹。铜/玫瑰/奶白主色不改，避免烘焙灯光到颜色。
- 两层装饰面增加 UV，背缝焊接，约 .0008–.001 场景单位薄壁与封边。保留包覆装饰定义，不发明厚纸标或制造工艺事实。对应实体开启阴影，4 张透明字膜关闭矩形投影。
- 完整泵六部件和长空心管整体抬起，局部补泵座/连接件孔腔和真实凹口；完整底盖三部件一起展开并补通孔/清理空材质槽。
- 原72条封尾肋线同材质合并，保持实际几何，不抽稀微细节；目标约19逻辑mesh。软管只按原轮廓做适度曲率过渡和文字贴合。
- 仍按本机 Blender 保存 v3 源/重建脚本/内嵌 GLB/JSON，原 v2 不覆盖。验证薄壁封闭/正体积、原图字节、真实孔腔射线、泵与底盖全开净距、全部姿态地台不遮挡、原字膜无矩形影。
- Cycles四态与同位仅关实体装饰影控制；root 独立网页与视觉验证，手机明确模拟。最终效果分开描述 Cycles 和 WebGL。

范围：展示包材，单位非毫米；未提供实测结构，内腔/图案只作参考推定，不是制造 CAD。下一步由 root 下发 build-go 后才建模。
