# Soap Clean Duo — poster-082

2026-11-07 当前状态：**海报已上线 client1.46；3D 为本地待审查**。原八图批次第4款，稳定ID保持 poster-082。正式65张海报、29首页、29模型，本款模型尚未加入正式3D和首页。

海报采用奶白300 ml圆盘泵瓶与浅蓝条纹180 ml护发素软管、粗体liaose、2:3版式。`soap-clean-duo-v2.png` 为已批准1024×1536原稿，内置 image_gen 生成；v2修正泵顶中央误生成小柱为后缘低矮片状出液口。海报上线回执为 `../../../client146-soap-clean-duo-poster-release.json`。

3D实际使用本机 Blender 5.4.0 Alpha 构建：`poster-082-v1.blend` 为可编辑源，`../../../packaging-assets/poster-082-v1.glb` 为1.92MB内嵌纹理模型。保持空的乳白塑料容器与浅蓝配件，完整圆盘泵头连粗透明中空长吸管、完整软管翻盖、条纹印刷承载、粗体Logo、产品名容量共六组；文字比印刷层更向外展开。

本地入口：http://127.0.0.1:8794/soap-duo.html 。支持合拢、半开、完全展开、拖拽、90度旋转、底部与正面视图、原海报查看。网页复用原查看器，未新增共享渲染分支。灰色承载投影已修复，侧面字层避开说明区，手机印刷层保留完整横向间距。

验证：181项前端测试通过；最终手机间距微调后重跑两项姿态测试通过；独立入口构建、实际GLB组/材质/管长验证通过。主审和独立复查确认桌面及393×852模拟手机画面；手机为CDP模拟与DOM阶段按钮激活，非真机测试。全展开手机容量字较小，可在合拢视图或海报查看细字。

文件：`build_soap_duo.py`、`render_review.py`、`verify_model.py`、`review-product.json`、`model-design.md`、`model-verification.json`、`browser-verification.json`、`previews/`。重建命令见model-design.md。原始参考与便于查看的输出另存于 gen/outputs/20261107-Soap-Clean-Duo。

参考未提供实测尺寸，比例和隐藏内部结构为展示推定，不作为生产CAD。
