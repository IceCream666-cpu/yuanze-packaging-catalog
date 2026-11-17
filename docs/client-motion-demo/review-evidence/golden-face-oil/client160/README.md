# client1.60 · Golden Face Oil v2 已发布

状态：2026-11-17 13:46:59（北京）已发布，13:48:59 完成独立 HTTPS 验证，随后完成正式网站首页进入056的交互视觉复查。发布源码 `5717bc39`，基线源码 `0a8d937`。

## 范围与依据

- 用户已批准056v2。正式配置与已验收 `model-source/collection/poster-056/v2/review-product.json` 完全一致：U形保护盖、含长中空吸管的完整泵组、磨砂空瓶、透明承印层示意、Logo、产品名称六层。原图直印的限制保持说明；没有把透明示意层改成实体纸标。
- 056新GLB SHA256：`dbb0a3ab019d78fe74ae6639b6809d5b4ec982c5919f2a8b2f4e65e0926d5a81`，609,256 bytes。旧GLB和源档留存；客户端正式路由改用新版本文件。
- 514项资源，68海报 / 31首页 / 32模型；其他31模型及所有海报、首页图片、样式和动画脚本保持旧摘要。072v2仍本地；084下一新版不纳入此次包，086保持撤下。
- 候选差异为index、preview、两个相关3D分块和056v2 GLB。具体新增/移除列表见publication-plan.json。未升级任何依赖。

## 基线和冻结包

`server-before.json` 由主任务本轮重新采集：client1.59，514项资源，6820项展厅外文件，PID33772 active。`local-baseline-manifest.json` 是构建前本机清单，单独保留。

- 基线manifest：`e31ee750721a42b1405ca06df3e3d0bca8a8cae0464df1321b6ce48a1ffd0a09`
- 候选manifest：`296e5f53a1f2e02f2bc756de244d2e218b176e7f3e1011f4ea46efb17cbfcd82`

主任务采集基线时服务器可用225,927,168 bytes，低于256MiB安全余量；随后主任务报告仅清理dnf缓存后约296MB。当前版本和所有回退保持留存。最终容量以发布时重新读取的精确值为准；发布脚本保留256MiB保护线，容量不满足时停止于上传前。

## 本地验证

203项前端、13项发布打包、4项全库GLB结构、5项发布计划测试通过；正式构建及源摘要一致性检查通过。056测试已切到实际v2资产，覆盖整泵所有零件随动、中空管与瓶口净空、U形保护盖先行展开、七个展开/收拢进度完整入框、透明底材/Logo/产品文字各自位移与复位、真实薄膜投影与文字无整片矩形影。072测试继续要求旧正式文件不变。

```sh
python3 scripts/build_customer_showroom.py --edition client160 --check
python3 docs/client-motion-demo/review-evidence/golden-face-oil/client160/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/golden-face-oil/client160 -p test_release_plan.py -v
```

## 主任务发布与验收

默认publish.py只校验本地计划；`--publish`才使用现有临时授权SSH helper远端写入。上传前容量检查和部署锁内容量检查均保留256MiB余量；检查current、manifest、网关、服务及展厅外摘要，在同文件系统用硬链接候选，写前解除链接后替换，原子切换并校验完整回退。不重启服务、不写业务数据。

发布成功后运行verify_online.py：通过验证证书的HTTPS检查5项变化资源完整SHA、32模型Range、056原图与056/085海报缩略图/首页预览、三角色、匿名/退出、旧056以及本地072v2/084v3不可读。之后从正式首页打开056，复查半展开接影、全展开、旋转和复位。

计划回退目录：`/opt/yuanze-reference/backups/client1.60-golden-face-oil-quality-model-20261117`。仅成功切换并校验后才记为存在和可用。仅回退展厅，不回灌业务数据库。

084后续预览源代码可能改变工作区源摘要；请使用隔离构建，不覆盖这次已冻结的release与server-reference/public/showroom包。

## 本轮实际发布与线上验证

- publication.json：514项文件完整校验；6820项展厅外文件摘要不变；其他31款模型不变；服务PID33772持续active；未重启服务，业务数据写入为0。
- online-verification.json：校验证书的HTTPS完整核对5项变化资源，32/32模型Range；客户、员工、管理员三角色边界，匿名与退出，原图下载、首页缩略图通过。
- browser-verification.json与online-*.png：从正式首页选择Golden Face Oil进入结构页，实际请求056v2；合拢、半/全展开、90度旋转、复位通过。主任务逐张检查无裁切，标贴薄影保留。手机本轮未重测，前次模拟视口证据保留于v2/QA.md，非真机。
- 回退目录现已创建并逐文件验证，路径同上。正式包维持冻结，084v3接下来仅本地预览。
