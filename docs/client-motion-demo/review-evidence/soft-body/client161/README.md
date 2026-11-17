# client1.61 · Soft Body Duo v3 发布候选

状态：本地候选、回归与差量发布计划已完成，尚未远端部署。基线源码 `1776425`；主任务负责提交、发布及线上验收。

## 本次范围

用户已批准084v3。仅正式084改为已验收 `model-source/collection/poster-084/v3/review-product.json` 和 `poster-084-v3.glb`；五根结构为双玻璃空瓶、含两长空心吸管的完整双泵、实体白色环标、Logo与产品文字。保留原海报及首页图；蓝粉色仍归属原海报的料体，模型为空包材。

084 GLB：1,855,884 bytes，SHA256 `764838f83f33676785fe70488957d992f5bd481a5c96a0b6ad1d5edfdf1bf164`。11个共享mesh定义、12个逻辑mesh实例、14个渲染primitive。旧v2源资产保留；仅从当前正式路由移除。072v2保持本地，081正式仍v1；086保持撤下。

正式数量保持68海报 / 31首页展示 / 32模型、514资源。其他31个模型和所有海报、首页图片、样式、动画脚本摘要未变化。没有依赖升级。

## 新鲜基线与冻结包

`server-before.json` 由主任务本轮重新采集；`local-baseline-manifest.json` 是修改前本机清单，两者一致。基线client1.60为514资源，6820项展厅外文件、PID33772 active，采集时可用293,081,088 bytes。网关、服务、展厅外摘要和current路径均进入发布保护。

- 基线manifest：`296e5f53a1f2e02f2bc756de244d2e218b176e7f3e1011f4ea46efb17cbfcd82`
- 候选manifest：`23ab8089fd3bcd6c4c9cd6c14093660411a3d305e5d1682a83f4ffeb993ce080`

变化5项：index.html、preview.js、PackagingDetail-BluZAaY2.js、packaging-scene-CyMuL9MP.js和poster-084-v3.glb。替换旧两个JS分块及poster-084-v2.glb；精确清单见publication-plan.json。

## 本地验证

206项前端、4项全库模型结构、13项发布打包和5项发布计划测试通过。正式Vite构建、源摘要一致性、全部514文件实际SHA与目录清单、32模型范围检查通过；详见local-verification.json。

前端使用实际GLTFLoader和真实几何，覆盖两完整泵与两长管装配、两实体标签投影、玻璃接影、Logo/文字纹理及无矩形影、合拢/半开/全开/四向旋转/底视/复位和桌面/模拟窄视口不裁切。原图源档验证更新为084的v3目录；072和081正式引用守卫保持。

```sh
python3 scripts/build_customer_showroom.py --edition client161 --check
python3 docs/client-motion-demo/review-evidence/soft-body/client161/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/soft-body/client161 -p test_release_plan.py -v
```

## 发布与回退

publish.py默认仅本地校验；`--publish`才调用现有临时SSH helper。发布前和部署锁内均保留256MiB容量安全余量；先校验新鲜基线，再硬链接未变化资源、写前解除链接，原子切换并验证完整回退。没有服务重启或业务数据写入。准备阶段未SSH或清理服务器。

计划回退目录：`/opt/yuanze-reference/backups/client1.61-soft-body-quality-model-20261117`，仅发布成功并核验后才能记为实际可用。回退仅切换完整展厅目录，不回灌业务数据。

发布后运行verify_online.py验证HTTPS证书、5项变化资源完整SHA、32模型Range、三角色与匿名/退出、084原图和084/085首页预览；旧084v2、072v2、081v2以及撤下资源应不可读。主任务随后打开正式084复查半开接影、全开、旋转和复位，再更新发布回执。

081后续本地制作使用隔离构建；不要重建或覆盖本次冻结release与server-reference/public/showroom包。

## 正式发布与验收

2026-11-17 14:12:12 已发布client1.61，14:14:06完成独立HTTPS验证。源提交4ba62ffe；5项变化资源完整摘要、32模型Range、三角色权限/匿名/退出通过；从正式首页Soft Body Duo进入084，合拢、半开、全开、90度旋转、复位及实际084v3请求通过，主任务逐图目检。其他31模型、6820项展厅外文件保持，服务未重启，业务写入0，回退完整。见publication.json、online-verification.json、browser-verification.json和online-*.png。
