# client1.63 · Soap Clean Duo v2 发布候选

状态：本地候选已冻结，尚未远端部署。基线源码 `8913c9b7`；主任务负责提交、发布和独立线上验收。

## 范围

仅将获批082正式配置切至 `model-source/collection/poster-082/v2/review-product.json`、模型切至 `poster-082-v2.glb`。保留原海报和首页图。六根结构为双容器、完整圆盘泵含长空心吸管、完整翻盖、直印条纹及透明印刷承载面、Logo、产品文字。蓝条纹为薄实体装饰，无纸标；透明印字面不投不透明矩形影。

GLB 2,782,400 bytes，SHA256 `21fe3328200b394c3aa873989fb8f3db35512df2ee3c1f961310cf396eff6a0b`；配置 SHA256 `625c77e753cf9c11253010c3900a4cff2a6ccf8d6aa4deda52ae914a557dffd1`。20个网格，泵组6件、翻盖3件。旧v1源文件保留，仅移除旧正式路由。

其他31模型和配置、全部海报和首页图片、共享3D代码分块、样式、动画脚本保持原摘要。正式085保持v2，085v3和072v2仍仅本地；撤下款保持。数量不变：68海报 / 31首页展示 / 32模型 / 514资源，无依赖升级。

## 新鲜基线和冻结包

先保存本机 `local-baseline-manifest.json`，再使用主任务本轮采集的 `server-before.json`，二者一致。线上基线client1.62，6820项展厅外文件、PID33772 active，可用空间 291,422,208 bytes。

- 基线manifest：`7db97fb7dc79ea20d79fec3a9f8875053ae17564831b472e0760612fb78c2adb`
- 候选manifest：`3a86a3d62db42baa50a97be43a2fe0f10816db470c74ca27f177fccd014273f8`
- 构建源码摘要：`564d03b555e9acbe738f50871b5081214a050dde7462d17090be96aef4cf83be`

精确3项变化：index.html、preview.js、poster-082-v2.glb；移除旧poster-082-v1.glb正式路由。此轮没有替换共享3D JS分块。`publication-plan.json` 列出全部31保留模型。

## 本地验证

210前端、4全库模型结构、13打包、5发布计划测试全部通过。正式Vite构建、stamp/build/check、514文件实际摘要与目录清单、32模型范围、Python语法与diff检查通过。

真实GLTF回归覆盖完整泵/长吸管及翻盖随动、实际条纹投影/容器接影、8透明印刷载体无矩形影、原UV/贴图、合拢/半开/全开、四向旋转/底视/复位、桌面及模拟窄屏投影范围。后者为模拟视口，未记作真机验证。获批本地视觉证据见 ../v2/QA.md；本候选的正式浏览器验收仍待部署后执行。

完整实际命令、cwd、参数、修改脚本和结果在 `operations.json`；完整日志在 `frontend-tests.log` 与 `build.log`，摘要在 `local-verification.json`。

```sh
python3 scripts/build_customer_showroom.py --edition client163 --check
python3 docs/client-motion-demo/review-evidence/soap-clean/client163/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/soap-clean/client163 -p test_release_plan.py -v
```

## 发布和回退

publish.py 默认仅校验本地计划；只有显式 `--publish` 才调用主任务的临时SSH helper。保持256MiB余量、上传前和部署锁内双重容量检查、新鲜current/manifest/网关/服务/展厅外摘要保护、硬链接后写前解除链接、原子切换、完整旧包回退。此准备代理未SSH、未发布、未清理服务器、未提交。

计划回退目录 `/opt/yuanze-reference/backups/client1.63-soap-clean-quality-model-20261117`，仅发布成功核验后才记为实际可用。发布后运行 verify_online.py，核验3项变化资源完整SHA、32模型Range、三角色/匿名/退出、082原图与082/085首页图、旧082v1及未发布072v2/085v3和撤下款不可读。主任务随后进行正式浏览器多状态验收。

085后续预览只使用隔离构建，不重建或覆盖此冻结release与server-reference/public/showroom包。
