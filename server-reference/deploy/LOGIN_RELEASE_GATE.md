# 登录与反向代理发布门禁

应用负责决定匿名用户去 `/login`、业务员去 `/`、管理员去 `/admin`。Caddy 只负责 TLS、安全响应头、压缩与转发至 `127.0.0.1:4180`。不要在 Caddy 中再增加根路径到登录页的 rewrite 或 redirect。否则登录成功后，应用返回首页，网关又将首页改成登录页，会形成循环；Caddy 语法检查本身不能发现这个业务错误。

`release_gate.py` 是一次性、只读业务验证工具。只有登录/退出创建并撤销自己的临时会话，不改账号密码或产品数据，不自动定时运行。失败退出码为 `1`，成功为 `0`。JSON 报告不含密码、Cookie、CSRF Token、响应正文或重定向 Location。

## 发布前：配置语法与路由约束

在目标服务器、与 Caddy 相同的用户和环境中运行，证书文件必须可读：

```sh
python3 /usr/local/lib/yuanze/release_gate.py config \
  --caddyfile /etc/yuanze-reference/Caddyfile \
  --caddy-bin /usr/local/bin/yuanze-caddy
```

默认要求 `bmt.yuanzebeauty.com` 和 `8.134.220.216` 各有一个终止匹配的站点，只有透明反向代理、压缩和响应头处理。脚本会调用 `caddy validate`、`caddy adapt` 并检查适配后的实际 JSON 路由。它会拒绝 rewrite、redirect、file_server、路径分流、兜底拦截和错误 upstream。以后确实需要新增网关功能时，先更新规则及对应测试，不能绕过门禁直接发布。

在 systemd `ExecStartPre` 与 reload wrapper 中运行以上命令可强制阻止不符合约束的配置启动/重载。reload wrapper 应使用 `set -e`，只有门禁通过才执行原来的 Caddy reload。网关重载失败时，保留原配置并恢复磁盘上的候选文件，不能把 `systemctl is-active` 当作新配置验证通过。

## 发布后：真实账号与完整 HTTP 路由

可在本机读取已有 owner-only（`0600`）凭据文件。支持 `账号：…` / `密码：…` 格式，或 JSON `{"username":"…","password":"…"}`。密码有有意保留的首尾空格时使用 JSON。

```sh
python3 server-reference/deploy/release_gate.py \
  --report work/login-release-gate.json routes \
  --origin https://bmt.yuanzebeauty.com \
  --origin https://8.134.220.216 \
  --employee-credentials .secrets/包材库登录信息.txt \
  --admin-credentials .secrets/管理员登录信息.txt
```

每个入口只对两种账号各登录一次，依次验证：

- 匿名首页、后台及产品深链接进入正确登录页，受保护 API 返回 401。
- 登录页的脚本及递归 import 依赖无需登录即可获取，返回 200 和正确 JavaScript MIME。
- 登录成功后 `/api/session` 的账号和角色正确，Cookie 带必要保护，首页和再次访问 `/login` 均到达正确工作区。
- 带手机浏览器 User-Agent 刷新工作区、员工读取非空产品目录、员工访问管理员页面/API 返回 403、管理员 API 可读。
- 带编号的产品深链接正常打开，缺失 CSRF 的退出请求被拒绝。
- 最后退出并确认旧会话不可继续使用。即使中途失败，已获取 CSRF 的临时会话也会尽力退出。

此流程验证的是实际 HTTP 路由，不能替代浏览器 JavaScript 执行及设备实测。最多跟随 4 次同源重定向；重复路径、跨域跳转、依赖资源失败均立刻中止。不重试错误密码，不轮询服务器。

## 分开验证应用和公网路径

若服务器不能经公网访问自身域名，可在服务器运行同一个 routes 命令，加：

```sh
--connect-address 127.0.0.1
```

这只更换 TCP 连接地址，仍保留原域名的 Host、TLS SNI、证书及主机名验证；没有关闭 TLS 校验的选项。报告将明确标为 `direct_tcp_override_not_public_dns_test`，只能证明网关与应用链路通过，不能说明公网 DNS、运营商或备案拦截正常。两条网络路径的结果必须分别记录；公网失败不能被直连通过覆盖。

报告还记录两个 HTTPS 入口的证书到期时间与剩余天数，不改动自动续期机制。短期 IP 证书本来就会有较短剩余时间，不依据单一固定天数误判故障。

经 SSH 运行时可用 `--credentials-stdin` 代替两个凭据路径，输入 JSON 结构为 `{"employee":{"username":"…","password":"…"},"admin":{"username":"…","password":"…"}}`。由受信本机脚本读取文件后直接作为 `subprocess.run(..., input=...)` 传给 SSH 标准输入；不要将凭据放入命令参数、日志、脚本源码、环境变量或服务器临时文件。

## 发布流程中的失败处理

1. 备份当前发布代码、Caddy 配置和服务覆盖配置；升级不覆盖账号与产品数据库。
2. 运行本地回归测试与候选配置门禁，任一失败即停止切换。
3. 候选应用预验通过后，原子替换文件；必要时仅重启应用一次。
4. 对新域名和原 IP 运行一次 routes 门禁。应用/网关路由失败时立即恢复本次代码与配置备份，重启对应服务，并验证恢复后的路由。公网独有故障须单独诊断 DNS/TLS/接入网络，不能反复重启应用掩盖。
5. 留下脱敏报告，只有全部预定门禁通过后才标记发布完成。

本地测试（不访问生产服务器、不读取真实凭据）：

```sh
python3 -m unittest discover -s server-reference/deploy/tests -v
```

测试覆盖此次根路径循环、跨域重定向、缺失登录模块、错误 JS MIME、权限越界、账号失败脱敏、凭据权限及指定 TCP 地址仍保留 TLS 主机名。
