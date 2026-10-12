# 依赖漏洞防护策略

[English](./dependency-security.md)

Kageko 通过三层防护避免把已知漏洞的依赖发布出去：

1. **Dependabot**（`.github/dependabot.yml`）在新漏洞披露时自动开修复
   PR。npm workspaces 共享根 lockfile，因此一条 `directory: /` 配置即覆盖
   所有子包。需要在 GitHub 仓库 Settings → Code security 中开启
   Dependabot alerts 和 security updates。
2. **CI 门禁**（`.github/workflows/ci.yml`）在 `npm ci` 之后运行
   `npm run audit:deps`；只要树中存在未豁免的 high/critical 漏洞，
   PR 和 push 都会失败。
3. **本地发布门禁**：`npm run install:global` 在 `npm install` 与构建之间
   执行同一检查，带漏洞的依赖树不会进入全局 npm 目录。

拦截阈值为 **high 和 critical**。moderate/low 仍会出现在
`npm audit` 输出中，但不拦截。

## 豁免一个漏洞

当某个 high/critical 漏洞的上游尚未发布修复版本时，向
`.github/audit-allowlist.json` 添加一条**有时限的**豁免：

```json
[
	{
		"id": "GHSA-xxxx-yyyy-zzzz",
		"package": "qs",
		"reason": "No fixed release published upstream yet",
		"expires": "2026-11-12"
	}
]
```

- `id` 是漏洞通告 URL 中的 GHSA 编号；匹配只看 `id`（`package` 字段
  仅供阅读）。
- `reason` 必须说明为什么带着该漏洞发布是可接受的。
- `expires`（YYYY-MM-DD）为必填。日期一过，豁免自动失效、门禁重新
  拦截——豁免是刻意的、可评审的、会过期的决定，绝不是永久漏洞。
- 豁免文件不存在表示无任何豁免；格式错误的条目会使检查以校验错误
  失败。

## 排查检查失败

`scripts/audit-deps.mjs` 会区分"审计本身失败"（网络/registry 故障、
报告无法解析）和"策略不通过"。如需对着一份保存的审计报告（而非当前
安装的依赖树）验证豁免逻辑：

```sh
AUDIT_DEPS_FIXTURE=path/to/audit-report.json npm run audit:deps
```
