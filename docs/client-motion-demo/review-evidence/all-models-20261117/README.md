# 全部正式3D模型质量审查 · client1.59

审查日期：2026年11月17日。范围为当前正式32款模型，含080的全部3个finish，共34个场景。本页是当前版本的审查入口。视觉结论由主代理独立逐图检查后提供；本页整理者仅核对文件、状态和结构证据，没有追加视觉判断。

**当前并非全部模型都已按新标准完成优化。** 012v2、049v2的新版结构与半展开接影已通过本轮目检。其余产品存在旧印刷分组、材质光感、对应阴影或组件完整性方面的不同改进项；逐款情况见下表。

## 当前状态与范围

| 项目 | 当前已核实状态 |
|---|---|
| 正式版本 | client1.59；012已迁移为poster-012-v2.glb，049为poster-049-v2.glb |
| 正式模型 / 展示场景 | 32款 / 34场景；080的soap、after、baby分别核查 |
| 独立标贴、Logo、产品字三层 | 11款：012、049、067、068、072、073、080、081、082、084、085 |
| 合理原设计例外 | 071只有liaose Logo，没有产品文字，不补造文字 |
| 仍使用合并或附着印刷结构 | 20款；不等于每款都应额外增加实体纸标，需保留原直印设计 |
| 显式标贴接影配置 | 6款：012、049、067、068、071、085；配置存在不等于6款全部视觉达标 |
| 当前已记录缺管问题 | 正式072旧版没有长吸管；本地v2不计为正式修复 |
| 本轮证据 | 34份states JSON、136张主截图、061额外复拍1张、9张contact sheets |
| 当前优化队列 | **056之后084**；本次审查不调整既定顺序 |

012迁移发布事实参见[client1.59发布记录](../beach-magic/client159/publication.json)和[线上验证记录](../beach-magic/client159/online-verification.json)。本页描述当前1.59；[结构审查详表](structural-audit.md)及[结构原始数据](structural-audit.json)保留**client1.58冻结基线**，另附012升级1.59的增补。旧结构表里012的旧文件、缺分层、旧贴图预算均为历史记录，不能当成当前012的状态。

## 本轮覆盖验证

[coverage.json](coverage.json)的检查结果为通过，无缺失或多余条目：

- 32款各四态，共128张；080的after和baby各四态，再加8张，合计136张主截图。
- 061合拢复拍另计1张，共137张PNG。四态顺序为合拢、半展开、完全展开、90°旋转。
- 34份状态文件中的产品文件、组件键、展开目标/收敛进度、旋转角度和finish均与当前正式注册一致。
- 32个GLB的实际字节数及SHA256匹配当前正式manifest。137张PNG逐一通过签名、块CRC、解压、扫描行尺寸与结束标记校验；图像像素尺寸均为1557×971。
- 9张contact sheets已检查文件完整标记并记录哈希。文件完整及姿态元数据不代替视觉判断；本页视觉结论来自主代理实际检查。像素尺寸不被表述为实机验证。

## 总览图

| 页码 | Contact sheet |
|---|---|
| 01 | [打开总览 01](contact-01.jpg) |
| 02 | [打开总览 02](contact-02.jpg) |
| 03 | [打开总览 03](contact-03.jpg) |
| 04 | [打开总览 04](contact-04.jpg) |
| 05 | [打开总览 05](contact-05.jpg) |
| 06 | [打开总览 06](contact-06.jpg) |
| 07 | [打开总览 07](contact-07.jpg) |
| 08 | [打开总览 08](contact-08.jpg) |
| 09 | [打开总览 09](contact-09.jpg) |

## 逐款独立目检结论

| ID / 产品 | 当前正式GLB | 主代理本轮目检结论 | 四态截图 |
|---|---|---|---|
| poster-012 · Beach Magic | poster-012-v2.glb | v2新版结构与半展开接影通过。 | [合拢](screenshots/poster-012-closed.png) · [半开](screenshots/poster-012-half.png) · [全开](screenshots/poster-012-expanded.png) · [旋转](screenshots/poster-012-rotated.png) |
| poster-013 · Coral & Aqua | poster-013.glb | 印刷仍合并；盖子反射偏平。 | [合拢](screenshots/poster-013-closed.png) · [半开](screenshots/poster-013-half.png) · [全开](screenshots/poster-013-expanded.png) · [旋转](screenshots/poster-013-rotated.png) |
| poster-039 · PDRN Capsule Cream | poster-039.glb | 银盖反射过于整齐；直印文字合并。 | [合拢](screenshots/poster-039-closed.png) · [半开](screenshots/poster-039-half.png) · [全开](screenshots/poster-039-expanded.png) · [旋转](screenshots/poster-039-rotated.png) |
| poster-049 · Moisture Shampoo | poster-049-v2.glb | v2新版结构与半展开接影通过。 | [合拢](screenshots/poster-049-closed.png) · [半开](screenshots/poster-049-half.png) · [全开](screenshots/poster-049-expanded.png) · [旋转](screenshots/poster-049-rotated.png) |
| poster-042 · Woodland | poster-042.glb | 玻璃轮廓偏淡。 | [合拢](screenshots/poster-042-closed.png) · [半开](screenshots/poster-042-half.png) · [全开](screenshots/poster-042-expanded.png) · [旋转](screenshots/poster-042-rotated.png) |
| poster-051 · Pure Volume | poster-051.glb | 白色泵头层次偏弱。 | [合拢](screenshots/poster-051-closed.png) · [半开](screenshots/poster-051-half.png) · [全开](screenshots/poster-051-expanded.png) · [旋转](screenshots/poster-051-rotated.png) |
| poster-044 · Gentle Cleansing | poster-044.glb | 白色泵头层次偏弱。 | [合拢](screenshots/poster-044-closed.png) · [半开](screenshots/poster-044-half.png) · [全开](screenshots/poster-044-expanded.png) · [旋转](screenshots/poster-044-rotated.png) |
| poster-047 · Coastal | poster-047.glb | 玻璃轮廓偏淡。 | [合拢](screenshots/poster-047-closed.png) · [半开](screenshots/poster-047-half.png) · [全开](screenshots/poster-047-expanded.png) · [旋转](screenshots/poster-047-rotated.png) |
| poster-056 · Golden Face Oil | poster-056.glb | 正式旧版盖子偏平；本地v2网页验收已完成，尚未上线。 | [合拢](screenshots/poster-056-closed.png) · [半开](screenshots/poster-056-half.png) · [全开](screenshots/poster-056-expanded.png) · [旋转](screenshots/poster-056-rotated.png) |
| poster-057 · B5 Serum | poster-057.glb | 瓶底高光过强。 | [合拢](screenshots/poster-057-closed.png) · [半开](screenshots/poster-057-half.png) · [全开](screenshots/poster-057-expanded.png) · [旋转](screenshots/poster-057-rotated.png) |
| poster-058 · Luminous Face Oil | poster-058.glb | 玻璃轮廓偏淡。 | [合拢](screenshots/poster-058-closed.png) · [半开](screenshots/poster-058-half.png) · [全开](screenshots/poster-058-expanded.png) · [旋转](screenshots/poster-058-rotated.png) |
| poster-059 · Essence Oil Duo | poster-059.glb | 文字仍合并。 | [合拢](screenshots/poster-059-closed.png) · [半开](screenshots/poster-059-half.png) · [全开](screenshots/poster-059-expanded.png) · [旋转](screenshots/poster-059-rotated.png) |
| poster-060 · AHA Body Mist | poster-060.glb | 银色贴饰反射单一。 | [合拢](screenshots/poster-060-closed.png) · [半开](screenshots/poster-060-half.png) · [全开](screenshots/poster-060-expanded.png) · [旋转](screenshots/poster-060-rotated.png) |
| poster-061 · Oil-Infused Body Cream | poster-061.glb | 首次合拢帧出现黑块，半展开后复拍已消失；记为暂态待复现，不认定为永久模型缺陷。 | [合拢](screenshots/poster-061-closed.png) · [半开](screenshots/poster-061-half.png) · [全开](screenshots/poster-061-expanded.png) · [旋转](screenshots/poster-061-rotated.png) |
| poster-062 · Micro Cream | poster-062.glb | 盖子反射与玻璃质感可提升。 | [合拢](screenshots/poster-062-closed.png) · [半开](screenshots/poster-062-half.png) · [全开](screenshots/poster-062-expanded.png) · [旋转](screenshots/poster-062-rotated.png) |
| poster-063 · Moisture Cream | poster-063.glb | 盖子反射与玻璃质感可提升。 | [合拢](screenshots/poster-063-closed.png) · [半开](screenshots/poster-063-half.png) · [全开](screenshots/poster-063-expanded.png) · [旋转](screenshots/poster-063-rotated.png) |
| poster-064 · Aromatic Body Lotion | poster-064.glb | 白泵、黄瓶偏平；资产有139个网格。 | [合拢](screenshots/poster-064-closed.png) · [半开](screenshots/poster-064-half.png) · [全开](screenshots/poster-064-expanded.png) · [旋转](screenshots/poster-064-rotated.png) |
| poster-065 · Tea Tree Shampoo | poster-065.glb | 补充袋暖白底色正确；折褶偏硬。 | [合拢](screenshots/poster-065-closed.png) · [半开](screenshots/poster-065-half.png) · [全开](screenshots/poster-065-expanded.png) · [旋转](screenshots/poster-065-rotated.png) |
| poster-066 · Rose Hair Oil | poster-066.glb | 玻璃边界偏淡。 | [合拢](screenshots/poster-066-closed.png) · [半开](screenshots/poster-066-half.png) · [全开](screenshots/poster-066-expanded.png) · [旋转](screenshots/poster-066-rotated.png) |
| poster-067 · Amber Ginger Shampoo | poster-067-v2.glb | 结构正确；玻璃与白字的对比可提升。 | [合拢](screenshots/poster-067-closed.png) · [半开](screenshots/poster-067-half.png) · [全开](screenshots/poster-067-expanded.png) · [旋转](screenshots/poster-067-rotated.png) |
| poster-068 · Essence Water | poster-068-v3.glb | 结构正确；玻璃与白字的对比可提升。 | [合拢](screenshots/poster-068-closed.png) · [半开](screenshots/poster-068-half.png) · [全开](screenshots/poster-068-expanded.png) · [旋转](screenshots/poster-068-rotated.png) |
| poster-069 · Still Essential Oil | poster-069.glb | 装饰与厚底光感可提升。 | [合拢](screenshots/poster-069-closed.png) · [半开](screenshots/poster-069-half.png) · [全开](screenshots/poster-069-expanded.png) · [旋转](screenshots/poster-069-rotated.png) |
| poster-070 · Daylight Essential Oil | poster-070.glb | 装饰与厚底光感可提升。 | [合拢](screenshots/poster-070-closed.png) · [半开](screenshots/poster-070-half.png) · [全开](screenshots/poster-070-expanded.png) · [旋转](screenshots/poster-070-rotated.png) |
| poster-073 · Body Oil Collection | poster-073.glb | 单瓶展示符合此前批准的形式。 | [合拢](screenshots/poster-073-closed.png) · [半开](screenshots/poster-073-half.png) · [全开](screenshots/poster-073-expanded.png) · [旋转](screenshots/poster-073-rotated.png) |
| poster-072 · Daily Emulsion | poster-072.glb | 正式旧版缺少长吸管；v2只在本地。 | [合拢](screenshots/poster-072-closed.png) · [半开](screenshots/poster-072-half.png) · [全开](screenshots/poster-072-expanded.png) · [旋转](screenshots/poster-072-rotated.png) |
| poster-079 · Body Care Duo | poster-079-v2.glb | 包装盒Logo独立飞出正确；白色构件层次偏弱。 | [合拢](screenshots/poster-079-closed.png) · [半开](screenshots/poster-079-half.png) · [全开](screenshots/poster-079-expanded.png) · [旋转](screenshots/poster-079-rotated.png) |
| poster-080 · Bath Trio | poster-080-v2.glb | soap、after、baby三个finish均齐全；白色构件偏平。 | [合拢](screenshots/poster-080-closed.png) · [半开](screenshots/poster-080-half.png) · [全开](screenshots/poster-080-expanded.png) · [旋转](screenshots/poster-080-rotated.png) |
| poster-081 · Exfoliating Hand Gel | poster-081-v1.glb | 织物质感偏平，且对应接影缺失。 | [合拢](screenshots/poster-081-closed.png) · [半开](screenshots/poster-081-half.png) · [全开](screenshots/poster-081-expanded.png) · [旋转](screenshots/poster-081-rotated.png) |
| poster-082 · Soap Clean Duo | poster-082-v1.glb | 软管观感偏硬。 | [合拢](screenshots/poster-082-closed.png) · [半开](screenshots/poster-082-half.png) · [全开](screenshots/poster-082-expanded.png) · [旋转](screenshots/poster-082-rotated.png) |
| poster-084 · Soft Body Duo | poster-084-v2.glb | 透明瓶正确；白字辨识偏弱，玻璃接影关闭；资产有212个网格。 | [合拢](screenshots/poster-084-closed.png) · [半开](screenshots/poster-084-half.png) · [全开](screenshots/poster-084-expanded.png) · [旋转](screenshots/poster-084-rotated.png) |
| poster-085 · Daily Hair Ritual | poster-085-v2.glb | 铜色装饰层次不足。 | [合拢](screenshots/poster-085-closed.png) · [半开](screenshots/poster-085-half.png) · [全开](screenshots/poster-085-expanded.png) · [旋转](screenshots/poster-085-rotated.png) |
| poster-071 · Sculptural Pump | poster-071-v2.glb | 仅有Logo符合原设计；白色构件层次偏弱。 | [合拢](screenshots/poster-071-closed.png) · [半开](screenshots/poster-071-half.png) · [全开](screenshots/poster-071-expanded.png) · [旋转](screenshots/poster-071-rotated.png) |

### 080全部finish

| finish | 本轮覆盖 | 四态截图 | 状态记录 |
|---|---|---|---|
| soap | 四态齐全；主代理已独立目检 | [合拢](screenshots/poster-080-closed.png) · [半开](screenshots/poster-080-half.png) · [全开](screenshots/poster-080-expanded.png) · [旋转](screenshots/poster-080-rotated.png) | [states](screenshots/poster-080-states.json) |
| after | 四态齐全；主代理已独立目检 | [合拢](screenshots/poster-080-after-closed.png) · [半开](screenshots/poster-080-after-half.png) · [全开](screenshots/poster-080-after-expanded.png) · [旋转](screenshots/poster-080-after-rotated.png) | [states](screenshots/poster-080-after-states.json) |
| baby | 四态齐全；主代理已独立目检 | [合拢](screenshots/poster-080-baby-closed.png) · [半开](screenshots/poster-080-baby-half.png) · [全开](screenshots/poster-080-baby-expanded.png) · [旋转](screenshots/poster-080-baby-rotated.png) | [states](screenshots/poster-080-baby-states.json) |

11月13日历史统一审查只记录soap；本轮after、baby均已补齐并检查，不再列为“本轮未截图”。

## 本地候选与当前队列

| 产品 | 正式状态 | 本地状态 | 下一步边界 |
|---|---|---|---|
| 056 Golden Face Oil | 正式仍为poster-056.glb | v2本地网页验收已完成，尚未上线 | 先完成056既定交付，再继续084 |
| 072 Daily Emulsion | 正式仍为poster-072.glb，缺长吸管 | poster-072-v2.glb仅本地 | 不将本地优化算作已上线，也不插入当前056→084队列 |

当前顺序保持**056 → 084**。下述问题作为后续优化依据，不构成自动改序或批量发布安排：

- **结构与分层：** 剩余20款旧印刷结构按原稿逐款拆分；039、079等直印设计不凭空增加纸标，071不新增不存在的产品字。
- **对应阴影：** 084白标能够投影，但透明玻璃接影关闭；081实体织物标目前没有建立对应投影链。必须同时检查投影层、接收面及半展开实际结果，不能仅加配置标记。
- **材质与光感：** 本轮所列的白件层次、玻璃边界、金属反射、织物和软管观感分别处理；保留065暖白袋底、084透明瓶、073单瓶、079盒盖Logo独立展开等已确认形式。
- **资源成本：** 084的212个网格、064的139个网格，以及051/067较高面数有结构性优化空间；静态网格数与浏览器绘制调用数区分统计，不能用一个数字代替另一个。

## 061首帧暂态记录

首次合拢截图中出现纯黑方块。主代理执行半展开再收回后，[合拢复拍](screenshots/poster-061-closed-recheck.png)中的黑块消失。结构及嵌入贴图检查未找到新增黑色quad或整片黑色标贴。**当前记为首次帧暂态、待复现；不认定为模型常驻缺陷，也不据单次异常改动资产。**

## 交付文件与判断边界

- [当前根报告](README.md)：当前1.59状态、主代理视觉结论和既定队列。
- [覆盖校验](coverage.json)：34份状态、137张PNG、9张contact sheets及正式模型哈希的机器可读结果。
- [结构详表](structural-audit.md) / [结构数据](structural-audit.json)：1.58冻结基线及1.59迁移增补，供逐组件、贴图、材质和源文件追溯。
- .blend存在、命名齐全、标记开启和文件完整均不足以证明最终质感。这里没有声称制造级尺寸、实测壁厚、真实设备性能或与肉眼完全一致。

056本地补充：主代理已完成网页阴影开关与手机模拟视口验收，203＋4＋13项检查通过；当前正式056仍旧版。详见[056v2本地QA](../golden-face-oil/v2/QA.md)。
