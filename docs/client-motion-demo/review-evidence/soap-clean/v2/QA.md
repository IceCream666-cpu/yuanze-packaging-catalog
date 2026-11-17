# 082 Soap Clean Duo v2 本地验收
状态：本地完成，Ego Lite 已打开；未发布。正式082继续使用v1。

## 模型与外观
使用本机 Blender 制作。保留奶白不透明空包材、浅蓝完整圆盘泵头与翻盖、原粗体 liaose 和产品字稿；软管为连续薄壁曲面及细压纹封尾。
六组为 Body、Pump、TubeCap、Label、LogoInk、NameInk。完整泵组包含长中空吸管；底盖三个部件整体展开。蓝条为薄实体直印装饰，Logo和产品文字进一步独立展开；本款没有新增纸标。
源档内嵌纹理，12个实体的闭合/体积/接口及完整组件随动检查通过。未提供实测尺寸，隐藏内腔是展示推定，不作为生产CAD。

## 主任务独立视觉检查
已逐图查看原海报、Cycles closed/half/expanded/rotated及同位shadow-control；网页closed/half/expanded/rotated/bottom、复位；390×844模拟手机三态，无页面横向溢出；最后查看preview-opened.png。
美观复核：原蓝白比例和粗体字风格保持，软管肩部与封尾更连续，泵头及底盖未被裁切。Cycles半开地台最初裁到下移底盖，已改为按完整组件最低点定位并重渲染全部最终图。
同位网页仅开关薄实体蓝条castShadow，在裸软管ROI[710,310,770,420]有362像素差>3/255，最大10/255。Blender薄直印影较弱，下方裸管区128像素差>3/255，最大4/255。透明印刷承载面不投整片矩形影。测试后恢复投影设置，截图未经编辑。
视觉及像素证据见visual-qa.json、web-shadow-verification.json、web-states.json、mobile-states.json。手机为模拟视口，未作真机验证。

## 回归与构建
210项前端、4项模型结构、13项打包检查通过；两个隔离构建通过。正式client1.62的514资源、8个release文件、注册表及打包清单保持。
初次测试shell使用zsh只读status变量导致包装命令失败，修正后完整重跑通过；无产品代码失败。
网页截图曾在动画未稳定时采集，已等待目标状态并替换最终旋转/底视证据。

## 产物
- Blender：../../../model-source/collection/poster-082/v2/poster-082-v2.blend
- GLB：../../../packaging-assets/poster-082-v2.glb
- 本地预览：http://127.0.0.1:8785/soap-clean-quality.html
- 最终截图：preview-opened.png
- 回归回执：frontend-test-verification.json

GLB为2,782,400bytes；本轮首稿4,140,204bytes，减少32.79%；旧正式v1为1,917,000bytes，因此不宣称比旧正式版更小。
下一步：用户查看082本地预览后，再按后续明确指令处理发布。
