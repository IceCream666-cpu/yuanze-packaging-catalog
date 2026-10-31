# 包材库离线作品集

2026-10-31 文件交付，源为正式 client1.40（归档提交 d736a61754579c03846835d2b8b9dc56d6916240）。这不是新的网站发布版本。

交付保留全部 26 款正式交互模型和 61 张海报。Windows / Mac 用户解压 ZIP 后用支持 WebGL 2 的桌面浏览器双击 `打开作品.html`，不需要启动服务器或安装开发环境。HTML 内嵌模型、预览图、品牌标志、React、Three 和 GSAP；61 张高清原图为同目录下的相对文件。原图按钮打开独立图片页，避免本地 file:// 对 download 属性的兼容差异。

模型直接复用原 `PackagingDetail`、`mountPackagingScene`、`PACKAGING_PRODUCTS` 与原材质/分层配置，均未修改。离线适配只在 `assets.js` 中将当前选中的内嵌 GLB 解码为 ArrayBuffer。原 viewer 在退出时释放显存资源；无需同时解码 26 个模型。新增作品总览可搜索中英文名称、切换模型/海报，原图弹窗不会卸载正在查看的模型。

## 构建与检查

开发侧使用原工程已安装的 Node/Vite 与 Python；接收方无需这些工具。

```sh
cd docs/client-motion-demo
node offline/build.mjs /absolute/delivery-directory
node --import tsx --test tests/offline.test.mjs
```

独立检查脚本使用带 Pillow 的 Python 环境：

```sh
python3 scripts/check_offline_portfolio.py --self-test
python3 scripts/check_offline_portfolio.py /absolute/delivery-directory/YUANZE_Portfolio --formal /absolute/rose-live --zip /absolute/delivery-directory/源泽包材库作品集_含26款交互3D_Windows与Mac.zip --report /absolute/verification.json
```

构建仅按白名单提取公开作品，不包含账户、客户信息、业务数据库、部署配置或服务端代码。HTML 用 CSP 限制外网请求。生成包保留第三方许可；ZIP 与解压目录均由构建和独立检查双重限制为小于 300,000,000 字节。

## 本次验证

- 167 项既有前端测试与 1 项新增离线二进制/取消/缺失模型测试通过。隔离 worktree 首次缺少本地预览素材，补入正式同源测试素材后既有测试全部通过。
- 独立交付检查 537 项通过，0 失败、0 警告。26 个模型、61 张高清原图与正式资源逐字节 SHA256 一致；149 个唯一内嵌图片解码通过；ZIP CRC、文件白名单、路径安全与双重体积限制通过。
- macOS Ego Lite 实际 file:// 路径下，26 款逐个在模拟断网状态载入，合拢/半展开/完全展开全部通过；每次仅保留 1 个 canvas。原版旋转、原图往返保持展开状态通过。
- 桌面 1622×865、海报页 1366×768、393×852 模拟手机首页与 Rose 全开检查。Impeccable detector 无发现，独立截图审查未发现严重裁切、缺层或控制遮挡。
- Windows 实机、Safari 与实体手机未测。结构图的隐藏尺寸仍以实物为准。未修改正式站，也没有增加新的模型修订。

最终校验摘要见 `verification.json`。作品文件输出在工程外的 `outputs/包材库作品集-20261031`，不提交大体积交付 ZIP 到源代码仓库。
