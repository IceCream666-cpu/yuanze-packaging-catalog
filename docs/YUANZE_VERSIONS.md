# 源泽版本记录

用户于北京时间 2026-10-20 确认：从本轮首页更新开始使用 `yuanze2.0` 系列，后续每次更新依次为 `yuanze2.0.1`、`yuanze2.0.2`……

| 版本 | 日期（北京时间） | 内容 | 状态 | 源码依据 |
| --- | --- | --- | --- | --- |
| yuanze2.0 | 2026-10-20 | 本轮入口页面 / 登录视觉基线：原源泽标志、账号密码、双层橙粉光晕动画及手机布局；内部选型已有本地风格预览 | 本地预览；不代表整站已上线 2.0 | `35e190a41d20d2932079e02042740c30e485c217` |
| yuanze2.0.1 | 2026-10-20 | Apple 风格客户端灵感选型 demo：38 张海报、画廊/总览、筛选、收藏、高清查看和选型条件面板 | 本地预览，未上线；包材匹配待接入 | 实现 `adc8d34e`；后续同版本修复用 `git log -- docs/client-apple-demo` 追溯，说明见 `client-apple-demo/README.md` |
| yuanze2.0.2 | 2026-10-20 | 海报跟手拖动、松手切换/回弹、触控板横滑和防误触 | 本地预览，未上线 | 初版 `f978c251`；同版本修复 Mac 连续横滑锁定，见 `client-apple-demo/swipe-verification.json` 与对应文件 Git 历史 |

后续递增到 `yuanze2.0.3`，以此类推。相同更新中的构建、测试、修复和文档提交归属于同一版本；一次方案讨论不伪装成已完成的产品更新。上线时补充实际时间、部署 release ID 和验证结果，保留本地预览记录。

## 客户展厅 client 系列

用户于 2026-10-20 指定：当前客户端先按纯海报展示上线，正式版本命名 `client1.0`。此命名独立于历史 `yuanze2.0.*` 预览；其他页面的版本规则保持原记录。

| 版本 | 发布时间（北京时间） | 范围 | 状态 | 源码与回执 |
| --- | --- | --- | --- | --- |
| client1.0 | 2026-10-20 20:02:32 | 38 张海报；Apple 风格画廊/总览；搜索/筛选/本机收藏；拖动、触控板横滑；高清查看、下载及退出；收起未接通的选型演示 | 已上线 `/client`；账号密码和服务端权限保持 | 本条同次提交可由 `git log -- docs/client-apple-demo/client1-release.json` 定位；实际回执见该文件 |
| client1.1 | 2026-10-21（设计预览） | 38 张既有海报的立体滑动展台、跟手拖动与吸附、背景随海报换色；保留筛选、收藏、高清和下载；桌面与手机适配 | 本地预览，未替换线上 client1.0 | `docs/client-motion-demo/`；同次实现提交可由 `git log -- docs/client-motion-demo` 定位；测试回执 `verification.json` |
| client1.2 | 2026-10-21（设计预览） | 沿用用户指定粉色大标题与透明悬浮产品设计；8 款精选、全屏换色、双色圆点和自动轮播；完整 38 张海报库保留筛选/收藏/高清/下载 | 本地预览，未替换线上 client1.0 | `docs/client-motion-demo/`，本条同次提交为实现依据；衍生素材清单 `featured-manifest.json`，测试回执 `verification.json` |
| client1.2（同版正式发布） | 2026-10-21 12:00:00 | 按用户批准发布上述完整设计；8 张透明图进入正式资源清单；38 张原海报及 115 个原资源保持；接入既有登录 session 与退出 | 已上线 `/client`；203 项服务器资源、126 项 HTTPS 资源、三角色权限与真实桌面/手机浏览器验收通过 | `6fd065a7ef20255ae52f0fc5c2f0fd3fadfa33cb`；`docs/client-motion-demo/client12-release.json` |

当前 client1.2 发布使用现有 `20261013-client-hd-v1` release，在 `/client` 原子替换展厅静态目录；服务 PID 18809 未变、数据库写入为 0。manifest SHA-256 `7e35c629ca90e2ff8f062d78b92124b9f2fa66b8c7d2a15b1342ae0e8c04f993`，备份 `/opt/yuanze-reference/backups/client1.2-20261021-colour-showroom`。新增图通过 `/showroom/assets/featured/` 登录保护路径提供，未替换完整原海报。

历史 client1.0 部署标识为 `client1.0-20261020`，同样在 `20261013-client-hd-v1` release 内原子替换展厅静态文件。不得把服务 release 目录日期误作各次发布时间；同版预览与正式发布记录分别保留。
