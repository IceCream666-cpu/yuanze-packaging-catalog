# client1.62 · Exfoliating Hand Gel v2 发布候选

状态：本地候选、回归与差量发布计划已完成，尚未远端部署。基线源码 `89c2d54`；主任务负责提交、发布及线上验收。

## 本次范围

用户已批准 081 v2。仅正式 081 改为已验收 `model-source/collection/poster-081/v2/review-product.json` 和 `poster-081-v2.glb`。保留透明玻璃瓶、完整泵头及长空心吸管；实体布纹环标和黑色侧旗投影、玻璃接影，Logo 与文字分层且透明文字承载面无矩形投影。布纹色图/法线贴图均为 512²，保留真实 UV；完整展开环标径向净距已验证。

081 GLB：2,053,332 bytes，SHA256 `ebf9e173e2cff88e67d4ea834aaafc1d6c0ec147252e0aca9c03d3cf1a16d4bf`，11 mesh / 11 primitive。比旧正式文件减少约 54.64%。配置 SHA256 `a76fbe5e1c86fdab57c5c8cd3b958f9a1f4b82c1fccf465956e281de7a5756d3`。旧 v1 源资产保留，仅从当前正式路由移除。

其他 31 款正式配置/GLB、全部海报及首页图片保持。072 v2 与制作中的 082 v2 不进入正式包；082 正式仍为 v1，084 保持已发布 v3，086 保持撤下。数量保持 68 海报 / 31 首页展示 / 32 模型、514 资源，无依赖升级。

## 新鲜基线与冻结包

`server-before.json` 为主任务本轮重新采集，和修改前 `local-baseline-manifest.json` 一致：client1.61、514 资源、6820 项展厅外文件、PID33772 active。网关、服务、展厅外摘要和 current 路径均进入发布保护。

- 基线 manifest：`23ab8089fd3bcd6c4c9cd6c14093660411a3d305e5d1682a83f4ffeb993ce080`
- 候选 manifest：`7db97fb7dc79ea20d79fec3a9f8875053ae17564831b472e0760612fb78c2adb`
- sourceStamp：`271261f50f51302a86814d883fc6667dcb222dafaf1b93b938e8e884ca427df8`，由实际源码内容生成，不使用尚未产生的自引用提交号。

变化 5 项：index.html、preview.js、PackagingDetail-Cw0m57ur.js、packaging-scene-BCRknYCL.js、poster-081-v2.glb。删除旧 PackagingDetail-BluZAaY2.js、packaging-scene-CyMuL9MP.js 和 poster-081-v1.glb 路由；精确清单见 `publication-plan.json`。

## 本地验证

208 项前端、4 项全库模型结构、13 项发布打包、5 项发布计划测试通过。正式 Vite 构建、源摘要一致性、全部 514 文件实际 SHA 与目录清单、32 模型范围检查通过，详见 `local-verification.json`。

真实 GLTFLoader 回归覆盖完整泵与长管随动、实体布纹/侧旗投影、透明字无矩形影、玻璃接影、布纹贴图/UV、合拢/半开/全开、四向旋转/底视/复位，以及桌面和模拟窄视口完整容纳产品。完全展开按实际顶点圆包络验证环标与瓶身有正净距。手机检查为模拟视口，未记作真机验证。

```sh
python3 scripts/build_customer_showroom.py --edition client162 --check
python3 docs/client-motion-demo/review-evidence/hand-gel/client162/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/hand-gel/client162 -p test_release_plan.py -v
```

## 发布与回退

`publish.py` 默认仅本地校验，`--publish` 才调用现有临时 SSH helper。发布前及部署锁内均保留 256 MiB 容量余量；新鲜基线检查、未变化资源硬链接、写入前解除链接、原子切换、完整回退校验均沿用上一版。无需服务重启或业务写入。

基线采集时空间 216,248,320 bytes 不足门槛。主任务已把 60 个旧上传暂存包共 98,308,917 bytes 逐个完整 SHA256 验证归档到本机后移除远端重复，空间恢复到 306,524,160 bytes；当前版本与全部回退保留。证据见 `staging-cleanup.json`。发布仍会复核实时容量，不降低保护线；准备代理未执行 SSH 或远端清理。

计划回退目录为 `/opt/yuanze-reference/backups/client1.62-hand-gel-quality-model-20261117`，仅发布成功并核验后才能记为实际可用。回退仅切换完整展厅目录，不回灌业务数据。

发布后运行 `verify_online.py` 验证 HTTPS 证书、5 项变化资源完整 SHA、32 模型 Range、三角色/匿名/退出、081 原图和 081/085 首页预览；旧 081 v1、072 v2、082 v2 与撤下资源应不可读。主任务随后从正式首页进入 081，复查半开接影、全开、旋转和复位，再更新发布回执。

082 后续本地制作使用隔离构建；不要重建或覆盖本次冻结 release 与 server-reference/public/showroom 包。


## 已执行结果
081v2已于2026-11-17 17:28:20发布为client1.62，17:30:58完成独立HTTPS验证，随后正式首页的合拢、半开、全开、旋转和回正已实测并逐图查看。源码提交1d94ef11。
514资源核验；5项变更资源完整HTTPS哈希、32模型Range、三角色/匿名/退出及原图/首页资源检查通过。其他31模型、6820展厅外文件、网关和服务PID保持，无服务重启或业务数据写入。
实际回退目录：/opt/yuanze-reference/backups/client1.62-hand-gel-quality-model-20261117。
第一次发布遇到SSH控制连接过期，在上传前退出；恢复已授权连接后发布成功。浏览器首次点击过快打开邻款，以及原生dialog选择器等待失败，均检查实际状态后纠正，再完成081证据采集。
082v2本地预览完成，未进入正式包；072v2继续保持本地。
