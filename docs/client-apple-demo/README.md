# 源泽灵感选型 · yuanze2.0.1

**本地交互 demo，未上线。** 原生产 `/client`、登录、包材检索和后台均未修改。

## 设计方向

以 Apple 应用的系统排版、细边框、圆角窗口和侧边栏组织 38 张既有客户海报。玻璃材质用于工具栏与弹出面板，海报完整显示。保留源泽原标志。

参考用户 Chrome 中的 Figma「iOS and iPadOS 27 (Community)」Materials 面板、Apple HIG Typography/Materials，以及 React Bits Circular Gallery / Accordion Gallery 的浏览方式。当前交互为独立 React/CSS 实现，没有安装 React Bits，也未复制 Figma 组件或字体文件。

## 可操作内容

- 中英文、用途分类、风格筛选、标题搜索与无结果恢复。
- 画廊与总览；左右按钮、键盘左右键、横向拖动和缩略图切换。
- 收藏及选型条件保存到本机浏览器，刷新保留；可以移除。
- 大图、按需读取原图、加载状态/失败重试、200% 缩放与原图下载。
- 桌面右侧选型面板、手机底部面板、Escape 关闭与焦点返回。
- 小屏菜单、清晰键盘焦点和减少动态效果适配。

「找相似包材」在本版打开条件面板，让用户选择整体风格或瓶型轮廓并补充备注。**没有连接真实包材匹配，不产生真实询价，不发送给业务员。** 海报风格标签只是编辑建议，不代表材质、库存、价格或配方适配。

## 运行

使用 Node.js 与 Python 3；先在本目录安装 package.json 中的依赖，再运行：

```sh
python3 prepare-assets.py
npm test
npm run build
npm run dev
```

默认地址：`http://127.0.0.1:8773/`，只监听本机。可用 `npx vite preview --host 127.0.0.1 --port 8773 --strictPort` 预览构建结果。

本机验证复用了相邻 `login-immersive-demo/node_modules` 中的相同 React/Lucide/Vite 版本；软链接、素材副本与构建目录不入库。脚本从现有已批准海报目录复制素材，不读取业务数据库或私有图册。`assets-manifest.json` 记录 115 个资源的来源摘要，`src/posters.json` 仅含客户海报展示字段。

## 验证与记录

- 六项 Node 测试：组合筛选、双语搜索、本地异常/过期状态、循环翻页、资源摘要与数据字段白名单、少量结果时的轮播身份唯一性。
- Vite 构建成功；主项目 `scripts/verify.py` 全套通过。
- TasteSkill 源码 lint：0 FAIL / 0 WARN。
- 浏览器检查通过 CUA 执行，未运行需要独立浏览器自动化的 `inspect.mjs`。已核对桌面、平板与手机断点、无横向溢出、选择/收藏/刷新、空结果、高清尺寸、弹窗、语言、键盘与拖动。
- 原图样本 poster-051 加载后真实尺寸为 1448×1086；不放大或重绘海报。
- 本轮测试记录已从 demo 本机存储中清理。

具体检查结果见 `verification.json`。截图位于仓库忽略的 `outputs/client-apple-20261020/`。后续真实接入需继续遵守客户安全目录和现有接口权限，保留另一台电脑的并行工作。
