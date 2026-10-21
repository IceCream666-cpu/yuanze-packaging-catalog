# 源泽版本记录

用户于北京时间 2026-10-20 确认：从本轮首页更新开始使用 `yuanze2.0` 系列，后续每次更新依次为 `yuanze2.0.1`、`yuanze2.0.2`……

| 版本 | 日期（北京时间） | 内容 | 状态 | 源码依据 |
| --- | --- | --- | --- | --- |
| yuanze2.0 | 2026-10-20 | 本轮入口页面 / 登录视觉基线：原源泽标志、账号密码、双层橙粉光晕动画及手机布局；内部选型已有本地风格预览 | 本地预览；不代表整站已上线 2.0 | `35e190a41d20d2932079e02042740c30e485c217` |
| yuanze2.0.1 | 2026-10-20 | Apple 风格客户端灵感选型 demo：38 张海报、画廊/总览、筛选、收藏、高清查看和选型条件面板 | 本地预览，未上线；包材匹配待接入 | 实现 `adc8d34e`；后续同版本修复用 `git log -- docs/client-apple-demo` 追溯，说明见 `client-apple-demo/README.md` |
| yuanze2.0.2 | 2026-10-20 | 海报跟手拖动、松手切换/回弹、触控板横滑和防误触 | 本地预览，未上线 | 初版 `f978c251`；同版本修复 Mac 连续横滑锁定，见 `client-apple-demo/swipe-verification.json` 与对应文件 Git 历史 |
| yuanze2.0.3 | 2026-10-21 13:09:38 | 双层橙粉光晕登录；真实账号密码、原 LOGO、三角色跳转；视频 Range、缓存和用户手势播放兼容 | 已上线 `/login`；正式 HTTPS、真实登录与桌面/手机布局验收通过 | `992f5407`、`033c42ff`；`docs/login-immersive-demo/login-release.json` |

后续递增到 `yuanze2.0.4`，以此类推。相同更新中的构建、测试、修复和文档提交归属于同一版本；一次方案讨论不伪装成已完成的产品更新。上线时补充实际时间、部署 release ID 和验证结果，保留本地预览记录。

## 客户展厅 client 系列

用户于 2026-10-20 指定：当前客户端先按纯海报展示上线，正式版本命名 `client1.0`。此命名独立于历史 `yuanze2.0.*` 预览；其他页面的版本规则保持原记录。

| 版本 | 发布时间（北京时间） | 范围 | 状态 | 源码与回执 |
| --- | --- | --- | --- | --- |
| client1.0 | 2026-10-20 20:02:32 | 38 张海报；Apple 风格画廊/总览；搜索/筛选/本机收藏；拖动、触控板横滑；高清查看、下载及退出；收起未接通的选型演示 | 已上线 `/client`；账号密码和服务端权限保持 | 本条同次提交可由 `git log -- docs/client-apple-demo/client1-release.json` 定位；实际回执见该文件 |
| client1.1 | 2026-10-21（设计预览） | 38 张既有海报的立体滑动展台、跟手拖动与吸附、背景随海报换色；保留筛选、收藏、高清和下载；桌面与手机适配 | 本地预览，未替换线上 client1.0 | `docs/client-motion-demo/`；同次实现提交可由 `git log -- docs/client-motion-demo` 定位；测试回执 `verification.json` |
| client1.2 | 2026-10-21（设计预览） | 沿用用户指定粉色大标题与透明悬浮产品设计；8 款精选、全屏换色、双色圆点和自动轮播；完整 38 张海报库保留筛选/收藏/高清/下载 | 本地预览，未替换线上 client1.0 | `docs/client-motion-demo/`，本条同次提交为实现依据；衍生素材清单 `featured-manifest.json`，测试回执 `verification.json` |
| client1.2（同版正式发布） | 2026-10-21 12:00:00 | 按用户批准发布上述完整设计；8 张透明图进入正式资源清单；38 张原海报及 115 个原资源保持；接入既有登录 session 与退出 | 已上线 `/client`；203 项服务器资源、126 项 HTTPS 资源、三角色权限与真实桌面/手机浏览器验收通过 | `6fd065a7ef20255ae52f0fc5c2f0fd3fadfa33cb`；`docs/client-motion-demo/client12-release.json` |

| client1.2（连续滑动修复） | 2026-10-21 14:01:11 | 连续横滑与反向接续、减少每帧重绘、固定精选图片节点 | 已上线；同版修复不另占版本号，无服务重启 | `438d8eb3`；`docs/client-motion-demo/smooth-release.json` |

client1.2 当前最新修复清单为 `c1d8e58f024d4221f17aead99c1e514e66499212709f1fdb9d94cd2b67faad53`；本次同时修复登录媒体加载，其清单为 `5add53fc3a2fa81bffaf4ff1cd8ac9ab03289d803053540c8f4316e835c5bf42`；静态更新时服务 PID 2564528 保持。此前首发证据保留如下。

client1.2 首次发布使用现有 `20261013-client-hd-v1` release，在 `/client` 原子替换展厅静态目录；服务 PID 18809 未变、数据库写入为 0。manifest SHA-256 `7e35c629ca90e2ff8f062d78b92124b9f2fa66b8c7d2a15b1342ae0e8c04f993`，备份 `/opt/yuanze-reference/backups/client1.2-20261021-colour-showroom`。新增图通过 `/showroom/assets/featured/` 登录保护路径提供，未替换完整原海报。

历史 client1.0 部署标识为 `client1.0-20261020`，同样在 `20261013-client-hd-v1` release 内原子替换展厅静态文件。不得把服务 release 目录日期误作各次发布时间；同版预览与正式发布记录分别保留。

client1.2 手机适配修复（2026-10-21 17:24:47）：已上线并完成正式 HTTPS 与手机宽度浏览器验收。包含小屏导航/色点、触控区、搜索字号、横屏弹窗与背景滚动；同版修复不新增版本号。源码 `eea40c9b`，回执 `docs/client-motion-demo/mobile-release.json`。

client1.2 / yuanze2.0.3 同版媒体加载修复：2026-10-21 23:28:55 已上线；首图优先、响应式 WebP、完整占位、单视频双层显示、去掉登录暂停按钮。源码 `76e25ab6`；完整回执见 `docs/client-motion-demo/media-loading-release.json` 和 `docs/login-immersive-demo/media-loading-release.json`；同版问题修复不另占版本号。

| client1.3 | 2026-10-22 00:08:28 | 统一 Apple 风格无衬线字体与文字层级；放大返回/说明/类别/名称；圆角玻璃导航、海报卡片、画廊和弹窗；手机单列与持续可见的返回按钮 | 已上线 `/client`；桌面/手机浏览器、三角色权限、资源摘要与全套检查通过；无重启 | `9a83cc94`；`docs/client-motion-demo/client13-release.json` |
