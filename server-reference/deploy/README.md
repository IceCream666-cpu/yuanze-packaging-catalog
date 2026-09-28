# 部署说明

每次更新都必须执行[登录与反向代理发布门禁](LOGIN_RELEASE_GATE.md)：加载前校验候选 Caddy 配置及透明代理规则，加载后用临时员工/管理员会话验证新域名与原 IP。HTTP 200、服务 active 或 Caddy 语法通过，均不能单独作为发布完成依据。

目标：8.134.220.216。源目录不含任何SSH私钥或站点密码。仅在确认服务器身份后操作。

1. 服务器准备 Python 3.11+、systemd，以及从 Caddy 官方发布页获取且校验的 Caddy 2.11.4 Linux amd64。图片检索依赖安装在独立虚拟环境，安装与重建说明见 ../IMAGE_SEARCH.md。
2. 本项目代码和 private 内的数据、图片部署至 /opt/yuanze-reference/releases/<release>，current 符号链接指向对应发布目录。后续更新保留上一版本用于回退。
3. 使用专用非登录用户 yuanze 运行 Python 服务，状态数据库、上传图片、动态搜图索引及认证初始化文件位于 /var/lib/yuanze-reference，权限仅该服务用户可读写。
4. 使用独立非登录用户 yuanze-web 运行 HTTPS 网关，证书持久化于 /var/lib/yuanze-web。Python 服务仅监听 127.0.0.1:4180。
5. 加载两个服务文件。Caddyfile 为指定IP申请并自动续期公开可信的短期证书。签发成功前不能称为部署完成，也不要通过关闭证书校验来掩盖错误。
6. 验证 HTTPS 证书、未登录API和图片返回401、登录后目录可读、记录写入及重启后的持久化。

无现成私钥时，通过服务器控制台由用户登记新的SSH公钥。本机 .secrets 不应上传、加入归档或暴露到网站。

此次参考网站包含真实历史询价资料；未确认币种、单位、数量条件或价格有效性时展示原文。原业务系统位于 /business/index.html，保留原有虚构数据和刷新重置规则；包材库的收藏、方案和实物借还为独立持久化记录。

状态目录中的 `catalog.sqlite` 保存后台资料、账号、审计和业务记录；`admin_uploads.sqlite` 保存上传登记，另有 `uploads/` 图片和 `image-search/` 动态索引。备份两个数据库和图片时应暂停应用写入，分别使用 sqlite3 backup API，再复制相关目录，保证跨库与文件处于同一时间点。不要运行中只复制主库而遗漏 WAL。升级不覆盖 `/var/lib/yuanze-reference`。

后台入口 `/admin` 使用独立管理员账号。旧账号保持员工权限，可查询、收藏和保存自己的方案；产品、报价、样品、设置和账号维护仅管理员可用。后台支持预览后批量导入与操作审计，详见 `../ADMIN_GUIDE.md`。

2026-09-24 已发布管理员后台 `20260924-admin-v1`。当前虚拟环境为 `/opt/yuanze-reference/venvs/admin-20260924`，systemd 的 `image-search.conf` 覆盖 ExecStart 并限制计算线程。当前版本和回退说明见 DEPLOYED.md。`install.sh` 是首次部署脚本，不用于现有服务器升级；升级先建立新 release，验证索引与内存，再切换符号链接并重启应用。

本次升级前备份位于 `/opt/yuanze-reference/backups/20260924-before-admin`，含上一服务覆盖配置 `previous-service-override.conf` 和记录前后 release 的 `deployment.json`。上一代码版本为 `20260924-image-search-v1`，回退流程及权限差异见 `DEPLOYED.md`。


2026-09-29 当前运行 `20260929-login-reliability-v1`。强制网关检查位于服务 drop-in：`/etc/systemd/system/yuanze-web.service.d/login-routing-guard.conf`，对应本目录模板 `yuanze-web-routing-guard.conf` 与 `yuanze-safe-reload`；检查脚本安装到 `/usr/local/lib/yuanze/release_gate.py`。后续不要以首次安装脚本覆盖这些配置。新会话库位于状态目录 `auth-sessions/`，发布不能覆盖或清空。代码切换流程与自动回退示例见 `work/login-root-cause-20260929/deploy.py`。公网域名备案拦截仍待核对，详见本轮故障报告。
