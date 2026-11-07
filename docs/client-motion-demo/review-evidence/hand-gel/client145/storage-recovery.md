# client1.45 发布时磁盘恢复

2026-11-07 本次复制约193MiB展厅时，根盘可供非root服务用户使用的空间耗尽，现有会话查询返回503 `AUTH_STORAGE_UNAVAILABLE`。17:13:53展厅原子切换成功，但此时尚不能视为用户验收完成。

17:17:31清理了 `/opt/yuanze-reference/staging/product-type-views-20261010-v1` 中1114个已证明重复的临时文件：177个分片拼接的SHA等于保留的完整 `payload.tar`，937个解包文件与当前正式release相同路径内容SHA一致。删除前逐文件路径/大小/SHA与保留位置见 `storage-recovery-plan.json`。完整旧tar及发布元数据、当前release、全部历史回滚备份保持。

回收817,990,118字节，服务用户实际可用空间恢复670,568,448字节；PID33772保持，未重启，未写业务数据。当前client1.45与client1.44回滚清单SHA均复核一致，结果见 `storage-recovery.json`。恢复后的真实登录写入/退出和原浏览器会话另由HTTPS与浏览器证据记录。

本发布脚本补上上传前和复制前空间预检，复制后至少保留256MiB；不足即拒绝发布。对应回归测试在 `test_release_plan.py`。此预检为未来执行保护，不改变已发布页面或模型。
