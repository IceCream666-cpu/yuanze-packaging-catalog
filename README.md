# 源泽包材库

此目录为包材库的本地 Git 工程，包含员工端、管理员端、客户展示端及测试。原工程保留在 `/Users/icecream/Documents/Codex/2026-09-22/claude-code`；本次初始化不修改线上服务。

## 目录

- `server-reference/`：当前网站的 Python 服务、前端、部署配置和后端测试。
- `site/`：国内／国外业务流程的早期演示，使用虚构数据。
- `tests/`：前端回归与版本库安全检查。
- `scripts/verify.py`：统一验证入口。
- `AGENTS.md`：每次修改的测试与提交要求。
- [后端与数据库说明](docs/后端与数据库说明.md)：模块职责、三个数据库、线上只读检查结果及备份边界。
- [Codex 与 Sites 选择说明](docs/Codex与Sites选择说明.md)：三种维护方式对比及本项目的适配限制。
- [客户目录与中英文界面](docs/客户目录与中英文界面.md)：三端切换、客户展示范围和验收边界。

只读数据库检查：`python3 scripts/database_inventory.py --state <状态目录>`，不会自动创建数据库或执行迁移。**本地 `state/` 是早期空库，不是当前线上数据备份。**

素材和本地状态已复制到 `server-reference/private/`、`server-reference/state/`，由 `.gitignore` 排除。密钥及登录信息仍保留在原工程的 `.secrets/`，未复制到新工程。旧 `work/`、`outputs/` 调查记录和导出表保留在原目录。

Git 记录代码和测试，可用于代码回滚；数据库、素材和上传图片需要单独备份，不能依靠 Git 恢复。当前没有配置远程仓库。

## 验证

使用 Python 3.11+、Node.js 22.22.2+ 或 24.15.0+（建议 24 LTS），在项目根目录执行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-test.txt
npm ci
python3 scripts/verify.py
```

测试使用临时目录、虚构账号和合成图片，不连接生产服务器或使用本地真实资料。搜图回归使用模拟向量，不下载模型。

每次修改：更新相关测试 → 执行统一验证 → 检查 `git diff` → 创建对应 commit。不要把密钥、密码、数据库或真实客户素材强制加入 Git。

## 本机预览

```sh
cd server-reference
python3 server.py --local-preview --port 4180
```

访问 `http://127.0.0.1:4180/`。此模式仅用于本机预览，不用于公网部署。

线上部署须遵循 [部署说明](server-reference/deploy/README.md) 和 [登录发布门禁](server-reference/deploy/LOGIN_RELEASE_GATE.md)。当前代码已包含客户角色隔离；存在启用的客户账号时，禁止回退至不支持客户角色的旧版本。
