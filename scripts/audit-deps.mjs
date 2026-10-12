import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const allowlistPath = path.join(repoRoot, ".github", "audit-allowlist.json");
const BLOCKED_SEVERITIES = new Set(["high", "critical"]);

function localDate() {
	const now = new Date();
	return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function auditReport() {
	// AUDIT_DEPS_FIXTURE points at a saved `npm audit --json` report, used to
	// exercise waiver matching against trees other than the installed one.
	const fixture = process.env.AUDIT_DEPS_FIXTURE;
	if (fixture) {
		return JSON.parse(readFileSync(fixture, "utf8"));
	}
	// Single static command string with shell: true — npm resolves to a batch
	// shim on Windows, which Node refuses to spawn directly. Passing the whole
	// command (no args array) keeps DEP0190 silent and injects nothing.
	const result = spawnSync("npm audit --json", {
		cwd: repoRoot,
		encoding: "utf8",
		maxBuffer: 64 * 1024 * 1024,
		shell: true,
	});
	if (result.error) {
		throw new Error(`Could not run npm audit: ${result.error.message}`);
	}
	// npm audit exits non-zero when vulnerabilities exist; that still produces a
	// valid report on stdout. A failure that prevents auditing (network error,
	// broken install) leaves stdout unparseable, which we surface distinctly.
	try {
		return JSON.parse(result.stdout);
	} catch {
		throw new Error(`npm audit did not produce a report:\n${(result.stderr ?? result.stdout ?? "").trim()}`);
	}
}

function collectAdvisories(report) {
	const byId = new Map();
	for (const vulnerability of Object.values(report.vulnerabilities ?? {})) {
		for (const via of vulnerability.via ?? []) {
			if (typeof via === "string" || !BLOCKED_SEVERITIES.has(via.severity)) {
				continue;
			}
			const id = via.url?.match(/GHSA-[\w-]+/)?.[0] ?? String(via.source ?? "");
			if (!id || byId.has(id)) {
				continue;
			}
			byId.set(id, {
				id,
				package: via.name,
				severity: via.severity,
				title: via.title,
				url: via.url,
				fixAvailable: Boolean(vulnerability.fixAvailable),
			});
		}
	}
	return [...byId.values()];
}

function loadWaivers() {
	if (!existsSync(allowlistPath)) {
		return [];
	}
	let entries;
	try {
		entries = JSON.parse(readFileSync(allowlistPath, "utf8"));
	} catch (error) {
		throw new Error(`Could not parse ${allowlistPath}: ${error.message}`);
	}
	if (!Array.isArray(entries)) {
		throw new Error(`${allowlistPath} must contain an array of waiver entries.`);
	}
	entries.forEach((entry, index) => {
		if (typeof entry?.id !== "string" || entry.id.length === 0) {
			throw new Error(`Allowlist entry #${index + 1}: missing "id".`);
		}
		if (typeof entry?.reason !== "string" || entry.reason.length === 0) {
			throw new Error(`Allowlist entry #${index + 1} (${entry.id}): missing "reason".`);
		}
		if (typeof entry?.expires !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(entry.expires)) {
			throw new Error(`Allowlist entry #${index + 1} (${entry.id}): "expires" must be YYYY-MM-DD.`);
		}
	});
	return entries;
}

const advisories = collectAdvisories(auditReport());
const waivers = loadWaivers();
const today = localDate();

const waived = [];
const unwaived = [];
for (const advisory of advisories) {
	const waiver = waivers.find((entry) => entry.id === advisory.id);
	if (!waiver) {
		unwaived.push(advisory);
	} else if (waiver.expires < today) {
		unwaived.push({ ...advisory, expiredWaiver: waiver.expires });
	} else {
		waived.push({ ...advisory, reason: waiver.reason, expires: waiver.expires });
	}
}

for (const entry of waived) {
	console.log(
		`waived: [${entry.severity}] ${entry.id} (${entry.package}) — ${entry.reason}, waiver expires ${entry.expires}`,
	);
}

if (unwaived.length > 0) {
	console.error(`\n${unwaived.length} unwaived high/critical vulnerabilit${unwaived.length === 1 ? "y" : "ies"}:\n`);
	for (const advisory of unwaived) {
		console.error(`  [${advisory.severity}] ${advisory.package}: ${advisory.title}`);
		console.error(`    ${advisory.url}`);
		console.error(
			`    fix available: ${advisory.fixAvailable ? "yes — run npm audit fix" : "no"}` +
				(advisory.expiredWaiver ? ` | waiver expired ${advisory.expiredWaiver}` : ""),
		);
	}
	console.error(
		'\nFix with "npm audit fix" where possible, or add a time-boxed entry to .github/audit-allowlist.json (see docs/dependency-security.md).',
	);
	process.exit(1);
}

console.log(
	`No unwaived high/critical vulnerabilities (${advisories.length} found at high+, ${waived.length} waived).`,
);
