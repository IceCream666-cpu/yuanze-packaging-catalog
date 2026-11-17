# client1.58 本地发布候选

本目录于 2026-11-17 为用户已批准的加载优化准备。准备脚本本身不代表已发布；远端发布和实际浏览器验收由主任务执行，最终状态以 `publication.json`、`online-verification.json` 及浏览器证据为准。

## 范围与基线

- `server-before.json` 由主任务从服务器只读采集，实际版本 client1.57、514 项资源、6820 项展厅外文件。`local-baseline-manifest.json` 是构建前本机正式目录的原始清单，独立保留，不冒充服务器采集。
- 旧清单 SHA256：`3be5fa41c17d98ae8df327532848d82bf47160036292d0eb3a88cefb0a0fbb8d`。
- 新清单 SHA256：`c30552e997b0009d625985d1815627248fcb21c7654f17054ff38e6e3542c65f`。
- 资源差异仅 `index.html` 与 `preview.js`，另更新清单本身；没有新增或移除资源。
- 32 个 GLB、68 张海报、31 款首页、所有样式、3D 场景/详情分块和动画脚本保持原字节。072 仍是正式 `poster-072.glb`；本地 `poster-072-v2.glb` 及 086 不纳入发布。
- 模型批准清单继续使用原 `approved-client1.57-collection-packaging`，未重新声称批准模型。客户端 package/title/中英页脚与关于入口统一为 client1.58。

## 本地复核

在工程根目录运行：

```sh
python3 scripts/build_customer_showroom.py --edition client158 --check
python3 docs/client-motion-demo/review-evidence/loading-20261117/client158/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/loading-20261117/client158 -p test_release_plan.py -v
python3 -m unittest discover -s tests -p test_packaging_release.py -v
```

本地 plan 每次重新计算所有 514 文件大小及摘要，并拒绝模型、图片、样式或分块变化。发布测试覆盖错误版本、未批准资源、样式/模型变动、空间不足和硬链接旧版保护。

## 主任务发布与线上检查

`publish.py --publish` 使用临时授权 SSH helper `/private/tmp/yuanze-1117-ssh.py`，脚本中不含凭据。执行前再次检查已采集基线、current 路径、网关摘要、服务身份、展厅外文件摘要及磁盘余量；差量归档包含两项变化资源和新清单。在部署锁内构建同文件系统硬链接候选，替换文件前先解除候选硬链接，再原子交换；不重启服务、不写业务数据。

成功发布后运行同目录 `verify_online.py`。它使用已有专用测试账号，登录/退出三个角色，通过验证证书的 HTTPS 检查两个变化资源完整 SHA、32 个 GLB Range、海报原图下载、首页缩略图、员工与匿名拦截、退出会话、旧撤下资源以及本地 072 v2/086 不可读。报告不保存密码、令牌或 Cookie。此脚本不替代浏览器中预取/取消/键盘/模拟触屏与模型展开阴影检查。

回退目录预留为 `/opt/yuanze-reference/backups/client1.58-loading-optimization-20261117`。仅在发布成功并校验旧版完整后才能称为可用远端回退；不要根据该目录名推定它已经存在。

本地准备未操作远端，未创建 Git commit；由主任务统一完成提交与发布状态记录。
