# 源泽沉浸式登录页预览

状态：2026-10-20 的独立前端 demo，未替换正式 `/login`，未发布服务器。

使用 React、Tailwind CSS、Lucide React。按本轮要求保留账号密码形式；不包含邮箱、Google、X 登录或自助注册。源泽标志复用正式包材库品牌图，不修改原登录服务、权限或其他页面。

## 启动

在本目录使用 Node.js 22+、pnpm：

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm build
pnpm preview
```

默认只监听本机 `http://127.0.0.1:8772/`。`dist/` 是可重新构建的本地输出，不进入 Git；依赖版本和锁文件进入版本库。开发可用 `pnpm dev`。

## 预览与原登录的关系

- `src/App.jsx` 是完整响应式界面。桌面 45% 视频 / 55% 表单、最大宽 1040px、最小高 650px；手机上下布局，视频高度 225px，极窄屏 200px。
- 默认只使用 `createPreviewTransport` 的内存模拟，不调用正式认证 API，不存储账号密码，不更改生产会话。下方“填入演示账号”用于体验输入、错误、加载、成功反馈。
- 演示账号 `demo.employee`、`demo.client`、`demo.admin`，统一演示密码 `YuanzeDemo2026`；它们不是正式账号，也不具备任何线上权限。
- `src/login-contract.js` 保留现有接口契约：`POST /api/login` 仅发送 username/password；成功后 `GET /api/session` 核对会话；角色由返回结果确定，分别去 `/`、`/client`、`/admin`。有效产品 code 可保留，外部跳转参数忽略。
- 本预览只展示上述目标地址，不真的进入工作区。正式集成仍需接入现有 `requestJSON`、服务端静态资源白名单/CSP，并按登录发布门禁检查三角色和并行更新；不应直接覆盖整个站点。
- 可用 `?scenario=invalid`、`offline`、`timeout`、`cookie` 验证对应错误状态。未配置管理员联系方式，帮助按钮只显示现有账号管理员联系说明，不虚构链接。

## 视频与回退

背景及左侧共用用户补充的本地 `0.mp4` 的网页副本。原外链：
`https://cdn.midjourney.com/video/71048e88-d8e6-470e-88ef-555c01eacb12/0.mp4`。

2026-10-20 原外链实测 HTTP 403 / Cloudflare challenge，随后用户提供原始 MP4。本版已接入 `assets/login-atmosphere.mp4`，页面从本机同源提供视频，构建后使用带摘要的文件名，不再向 Midjourney 发起请求。使用系统 avconvert 生成支持 Fast Start 的网页副本，原文件保留；来源摘要、体积和实际媒体参数见 `assets/manifest.json`。电脑浏览器已验证两个视频正常加载、静音循环与同步暂停。加载失败时仍显示黑色兜底，表单不等待视频。

下方“选择本地视频”可读取本机 MP4/WebM，使用 Blob URL，仅供本机预览，不上传、不写服务器。切换或关闭页面时释放地址。

视频加载不阻塞表单；静音、循环、playsInline、object-cover，背景放大 105% 并使用 10% 黑色 / 小模糊遮罩，左侧视频无暗色遮罩。减少动态效果时不自动播放、不旋转；切换浏览器标签时暂停视频并隐藏密码；播放后可手动暂停。

## 验证

- `pnpm test`：角色与深链接、接口字段、会话校验、失败不重试、输入异常提示、内存演示、React 表单、重复提交、语言切换、视频失败、焦点等。
- 正式包材库的 `scripts/verify.py` 仍独立运行；本 demo 的依赖和构建不加入正式部署目录。
- 已检查桌面、窄屏手机、英文切换、Tab / Enter、必填验证、错误及成功状态。实际截图和结果见 `verification.json`；截图保存在项目忽略目录 `outputs/login-immersive-demo-20261020/`。
