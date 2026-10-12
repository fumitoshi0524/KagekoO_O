# Dependency Vulnerability Policy

[中文版](./dependency-security.zh-CN.md)

Kageko guards against shipping known-vulnerable dependencies with three
layers:

1. **Dependabot** (`.github/dependabot.yml`) opens fix PRs when new
   advisories affect the tree. The npm workspaces share the root lockfile, so
   the single `directory: /` entry covers every workspace. Requires Dependabot
   alerts and security updates to be enabled under the GitHub repo's
   Settings → Code security.
2. **CI gate** (`.github/workflows/ci.yml`) runs `npm run audit:deps` after
   `npm ci`; pull requests and pushes fail while the tree contains unwaived
   high/critical vulnerabilities.
3. **Local publish gate**: `npm run install:global` runs the same check
   between `npm install` and the build, so a vulnerable tree never reaches
   the global npm prefix.

The blocking threshold is **high and critical**. Moderate and low findings
still appear in `npm audit` output but do not block.

## Waiving a vulnerability

When a high/critical advisory has no fixed release yet, add a **time-boxed**
entry to `.github/audit-allowlist.json`:

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

- `id` is the GHSA identifier from the advisory URL; matching is by `id`
  alone (`package` is informational).
- `reason` must explain why shipping despite the advisory is acceptable.
- `expires` (YYYY-MM-DD) is mandatory. Once the date passes, the waiver stops
  applying and the gate fails again — waivers are deliberate, reviewable,
  self-expiring decisions, never permanent holes.
- A missing allowlist file means no waivers; malformed entries fail the check
  with a validation error.

## Debugging the check

`scripts/audit-deps.mjs` distinguishes a broken audit (network/registry
failure, unparseable report) from a policy failure. To exercise waiver logic
against a saved report instead of the installed tree:

```sh
AUDIT_DEPS_FIXTURE=path/to/audit-report.json npm run audit:deps
```
