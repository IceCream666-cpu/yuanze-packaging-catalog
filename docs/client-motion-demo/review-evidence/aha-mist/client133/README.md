# AHA Body Mist / client1.33 正式验收

2026-10-30 14:20:39 +08:00 原子发布，14:26:23 +08:00 HTTPS 验收通过。仅发布批准的 poster-060；client1.31 性能预览及下一款 poster-061 不包含。

- `desktop-closed/half/open/rotated.png`：正式 Ego 1622×865 桌面，旋转等待 yaw 接近 π/2 后记录。
- `mobile-closed/open.png`：393×852 模拟视口，scrollWidth=393；未测试实体手机或原生触摸。
- 六张图片已由发布代理及独立审查代理 aha_release_review 逐张审阅，通过。
- `poster-roundtrip.json`：1280×960 原海报加载成功，并返回四部件结构展示。
- `online-verification.json`：060 完整 GLB 大小/SHA、旧缓存更新、26 模型 Range、三角色权限、匿名拒绝、原图下载及登录退出。
- `publication-plan.json`：458 资源中仅 060 GLB、index.html、preview.js 改动，其余455项保持；manifest 另更新。
- `publication.json`：6820 项展厅外文件、网关与服务 PID 保持，没有重启和业务数据写入。
- Python 发布脚本为归档副本；可执行原件在工作树 `work/aha-mist-release/`。回滚默认只输出计划，且拒绝覆盖后续版本。生产备份在 `/opt/yuanze-reference/backups/client1.33-aha-complete-sprayer-20261030`。

已批准局限：窄屏文字偏小，标贴与瓶身投影轻微叠合；透明弯吸管在动画中作为刚体整体提起，中间过程不代表经过验证的柔性软管真实装配路径。隐藏尺寸、壁厚和接口保持展示示意。
