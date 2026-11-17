# client1.59 · Beach Magic v2 发布与验证

状态：2026-11-17 11:58:53 已原子发布，12:00:53 已完成独立 HTTPS 验证。发布源码提交 `c5fe6795`，主任务已确认自动推送成功。主任务随后完成正式浏览器展开与接影验收，证据与 HTTPS 校验分别保存。

## 范围

- 012 替换为已批准 `poster-012-v2.glb`：完整外盖、带短舌内盖、透明罐、实体圆角纸标、Logo 与产品文字六层；纸标在玻璃上的对应阴影沿用已验收的逐款处理。
- 012 配置纳入现有 collection 注册，稳定 ID 保持。68 海报 / 31 首页 / 32 模型。
- 514 项发布资源；仅替换 index、preview、两个相关 3D 分块和 012 版本化 GLB。其余 31 模型、所有海报和首页图片、样式及动画脚本保持旧摘要。
- 072v2 和 056v2 仍为本地资源，不进入正式包；086 保持撤下。旧 012 源 GLB、源档和历史配置保留；正式包不再引用旧文件。

## 基线与冻结包

`server-before.json` 由主任务于本轮从服务器重新采集，是实际 client1.58 / 514 项资源 / 6820 项展厅外文件基线。`local-baseline-manifest.json` 是发布构建前本机清单，单独留存，不冒充线上证据。

- 基线 manifest SHA256：`c30552e997b0009d625985d1815627248fcb21c7654f17054ff38e6e3542c65f`
- 候选 manifest SHA256：`e31ee750721a42b1405ca06df3e3d0bca8a8cae0464df1321b6ce48a1ffd0a09`
- 新 012 GLB SHA256：`1181aa8d8738901d12c6cee3790007fd09143f4007e3124cea8a0b398deda643`

本轮完成 202 前端测试、13 包材发布测试、4 全库 GLB 结构测试、5 发布计划测试和正式模式构建。测试覆盖新的独立根 Mesh 文字层、实体纸标投影、完整盖子随动、分层位移与复位，及迟到解析后的资源释放。旧测试中的 `children` 假设修正为真实 Mesh 根也合法。

## 执行与回退

```sh
python3 scripts/build_customer_showroom.py --edition client159 --check
python3 docs/client-motion-demo/review-evidence/beach-magic/client159/publish.py
python3 -m unittest discover -s docs/client-motion-demo/review-evidence/beach-magic/client159 -p test_release_plan.py -v
```

以上只读校验本地候选。`publish.py --publish` 才使用主任务的临时授权 SSH helper 执行远端写入。脚本不含凭据。它核对 current、manifest、服务 PID/active、网关与展厅外文件摘要，上传前和落盘前均保留 256MiB 磁盘余量；在部署锁中用硬链接暂存，写前先解除候选链接，再原子交换，完整校验旧版回退。不重启服务、不写业务数据。

成功后运行同目录 `verify_online.py`，通过验证证书的 HTTPS 检查五项变化资源完整 SHA、32 个模型 Range、012 原图下载与首页缩略图、客户/员工/管理员权限、匿名和退出、旧012/撤下资源/本地072v2与056v2不可读。再在浏览器从首页进入012，核验实际闭合、半展接影、全展及旋转。

已验证回退目录：`/opt/yuanze-reference/backups/client1.59-beach-magic-quality-model-20261117`；发布后已逐文件核对其存在及完整性。回退只切回展厅，不能回灌业务数据库。

056 的后续预览代码变化会使工作区源摘要变化，但不会改变已冻结的 `server-reference/public/showroom` 包；请使用隔离构建检查新产品，不重建本次发布包。发布前应完成对应源码提交，便于准确追溯。

## 本次远端结果

- `publication.json` 确认候选 manifest 摘要一致、514 项资源、6820 项展厅外文件保持，服务 PID 33772/active 不变；没有服务重启或业务数据写入。旧版完整回退目录已生成并通过逐文件校验。
- `online-verification.json` 于 12:00:53 完成：5 项变更资源完整 SHA、全部32模型 Range、012/085 海报缩略图与首页预览、012 原图下载、客户/员工/管理员权限、匿名拒绝、退出会话、登录脚本不变均通过。旧012及未批准/撤下资源共41条拒绝访问。
- 首次容量预检在上传前阻止了发布。主任务执行 `dnf clean all` 清理19个包管理缓存文件，可用空间约310MB；全部既有版本和备份保留，原256MiB余量保护未降低。之后重试通过容量保护并成功发布。该清理过程为主任务执行报告，发布脚本中的容量检查及成功结果另有回执。
- 浏览器交互已验收：首页进入、合拢、半展开接影、全展开和90°旋转；详见下方独立浏览器证据。

主代理已完成正式浏览器验收：首页进入012实际请求poster-012-v2.glb；合拢、半展接影、全展及90°旋转通过。证据见browser-verification.json及live-*.png。
