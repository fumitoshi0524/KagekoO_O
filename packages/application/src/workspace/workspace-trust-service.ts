import * as crypto from "node:crypto";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import { kagekoHomeDir } from "@kageko/oauth";
import { replaceAtomically, retryTransientFileOperation } from "@kageko/session-store";

const TRUST_VERSION = 1;
const SECURITY_PATHS = ["plugins", "skills", path.join("tools", "auto"), path.join("mcp", "auto")];
const SECURITY_CONFIG_KEYS = ["permission", "interaction", "shell", "mcp", "hooks", "learning"] as const;

interface TrustEntry {
	workspace: string;
	manifest: string;
	trustedAt: string;
}

interface TrustDocument {
	version: typeof TRUST_VERSION;
	entries: TrustEntry[];
}

export interface WorkspaceTrustStatus {
	workspace: string;
	hasSecurityConfiguration: boolean;
	trusted: boolean;
	findings?: readonly string[];
	manifest?: string;
	reason?: "not_trusted" | "configuration_changed";
}

export class WorkspaceTrustError extends Error {
	readonly status: WorkspaceTrustStatus;

	constructor(status: WorkspaceTrustStatus) {
		const detail =
			status.reason === "configuration_changed" ? "security configuration changed" : "workspace is not trusted";
		super(
			`Refusing to load security-sensitive project configuration from ${status.workspace}: ${detail}. ` +
				"Review the workspace and grant trust explicitly before starting Kageko.",
		);
		this.name = "WorkspaceTrustError";
		this.status = status;
	}
}

/** Device-private trust decisions for security-sensitive project configuration. */
export class WorkspaceTrustService {
	readonly trustFilePath: string;

	constructor(trustFilePath = path.join(kagekoHomeDir(), ".kageko", "workspace-trust.json")) {
		this.trustFilePath = path.resolve(trustFilePath);
	}

	async inspect(cwd: string): Promise<WorkspaceTrustStatus> {
		const workspace = await canonicalWorkspace(cwd);
		const scanned = await scanSecurityConfiguration(workspace);
		if (!scanned.hasSecurityConfiguration) return { workspace, hasSecurityConfiguration: false, trusted: true };
		const document = await this.readDocument();
		const entry = document.entries.find((candidate) => samePath(candidate.workspace, workspace));
		if (!entry) {
			return {
				workspace,
				hasSecurityConfiguration: true,
				trusted: false,
				findings: scanned.findings,
				manifest: scanned.manifest,
				reason: "not_trusted",
			};
		}
		const existingManifest = typeof entry.manifest === "string" ? Buffer.from(entry.manifest) : undefined;
		const scannedManifest = typeof scanned.manifest === "string" ? Buffer.from(scanned.manifest) : undefined;
		if (
			!existingManifest ||
			!scannedManifest ||
			existingManifest.length !== scannedManifest.length ||
			!crypto.timingSafeEqual(existingManifest, scannedManifest)
		) {
			return {
				workspace,
				hasSecurityConfiguration: true,
				trusted: false,
				findings: scanned.findings,
				manifest: scanned.manifest,
				reason: "configuration_changed",
			};
		}
		return {
			workspace,
			hasSecurityConfiguration: true,
			trusted: true,
			findings: scanned.findings,
			manifest: scanned.manifest,
		};
	}

	async assertTrusted(cwd: string): Promise<WorkspaceTrustStatus> {
		const status = await this.inspect(cwd);
		if (!status.trusted) throw new WorkspaceTrustError(status);
		return status;
	}

	/** Persist trust only after the caller has obtained explicit user consent. */
	async grant(cwd: string): Promise<WorkspaceTrustStatus> {
		const status = await this.inspect(cwd);
		if (!status.hasSecurityConfiguration || !status.manifest) return status;
		const document = await this.readDocument();
		const entries = document.entries.filter((entry) => !samePath(entry.workspace, status.workspace));
		entries.push({ workspace: status.workspace, manifest: status.manifest, trustedAt: new Date().toISOString() });
		await writeDocumentAtomic(this.trustFilePath, { version: TRUST_VERSION, entries });
		return { ...status, trusted: true, reason: undefined };
	}

	async revoke(cwd: string): Promise<void> {
		const workspace = await canonicalWorkspace(cwd);
		const document = await this.readDocument();
		const entries = document.entries.filter((entry) => !samePath(entry.workspace, workspace));
		if (entries.length !== document.entries.length) {
			await writeDocumentAtomic(this.trustFilePath, { version: TRUST_VERSION, entries });
		}
	}

	private async readDocument(): Promise<TrustDocument> {
		try {
			const value = JSON.parse(await fs.readFile(this.trustFilePath, "utf8")) as unknown;
			if (!isTrustDocument(value)) throw new Error("unsupported or malformed trust document");
			return value;
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return { version: TRUST_VERSION, entries: [] };
			throw new Error(`Could not read workspace trust store ${this.trustFilePath}: ${(error as Error).message}`, {
				cause: error,
			});
		}
	}
}

async function canonicalWorkspace(cwd: string): Promise<string> {
	return path.normalize(await fs.realpath(path.resolve(cwd)));
}

async function scanSecurityConfiguration(
	workspace: string,
): Promise<{ hasSecurityConfiguration: boolean; manifest?: string; findings: readonly string[] }> {
	const root = path.join(workspace, ".kageko");
	try {
		const rootStat = await fs.lstat(root);
		if (rootStat.isSymbolicLink()) {
			throw new Error(`Project state directory must not be a symbolic link or junction: ${root}`);
		}
		if (!rootStat.isDirectory()) throw new Error(`Project state path is not a directory: ${root}`);
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return { hasSecurityConfiguration: false, findings: [] };
		throw error;
	}
	const records: string[] = [];
	const findings: string[] = [];
	await scanSecurityConfigFile(root, records, findings);
	for (const relativePath of SECURITY_PATHS) {
		await scanPath(root, relativePath, records, findings);
	}
	if (records.length === 0) return { hasSecurityConfiguration: false, findings: [] };
	return {
		hasSecurityConfiguration: true,
		findings,
		manifest: crypto.createHash("sha256").update(records.sort().join("\n")).digest("hex"),
	};
}

/**
 * Project config contains both presentation/preferences and executable policy.
 * Only the latter participates in trust, so changing a model or theme does not
 * unexpectedly block an otherwise harmless workspace.
 */
async function scanSecurityConfigFile(root: string, records: string[], findings: string[]): Promise<void> {
	const absolutePath = path.join(root, "config.json");
	let stat;
	try {
		stat = await fs.lstat(absolutePath);
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
		throw error;
	}
	if (stat.isSymbolicLink()) {
		throw new Error(`Security-sensitive project path must not be a symbolic link or junction: ${absolutePath}`);
	}
	if (!stat.isFile()) throw new Error(`Unsupported security-sensitive project entry: ${absolutePath}`);
	const content = await fs.readFile(absolutePath, "utf8");
	let parsed: unknown;
	try {
		parsed = JSON.parse(content);
	} catch {
		const digest = crypto.createHash("sha256").update(content).digest("hex");
		records.push(`c:config:invalid:${digest}`);
		findings.push("config.json (unparseable)");
		return;
	}
	if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return;
	const security = Object.fromEntries(
		SECURITY_CONFIG_KEYS.filter((key) => {
			if (!Object.hasOwn(parsed, key)) return false;
			// Configuration deletion uses null tombstones so layered settings can
			// deep-merge safely. A mcp.servers map containing only tombstones has
			// no executable server and must not keep a removed MCP capability behind
			// a stale trust manifest.
			return key !== "mcp" || hasActiveMcpServer((parsed as Record<string, unknown>)[key]);
		}).map((key) => [key, (parsed as Record<string, unknown>)[key]]),
	);
	const model = (parsed as Record<string, unknown>)["model"];
	if (model && typeof model === "object" && !Array.isArray(model)) {
		const modelRecord = model as Record<string, unknown>;
		const modelSecurity = Object.fromEntries(
			["apiKey", "baseUrl"].filter((key) => Object.hasOwn(modelRecord, key)).map((key) => [key, modelRecord[key]]),
		);
		if (Object.keys(modelSecurity).length > 0) security["model"] = modelSecurity;
	}
	if (Object.keys(security).length === 0) return;
	records.push(`c:config:${stableSerialize(security)}`);
	findings.push(`config.json (${Object.keys(security).sort().join(", ")})`);
}

function hasActiveMcpServer(value: unknown): boolean {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const servers = (value as Record<string, unknown>)["servers"];
	if (!servers || typeof servers !== "object" || Array.isArray(servers)) return false;
	return Object.values(servers as Record<string, unknown>).some((server) => server !== null && server !== undefined);
}

function stableSerialize(value: unknown): string {
	if (Array.isArray(value)) return `[${value.map((item) => stableSerialize(item)).join(",")}]`;
	if (value && typeof value === "object") {
		return `{${Object.keys(value as Record<string, unknown>)
			.sort()
			.map((key) => `${JSON.stringify(key)}:${stableSerialize((value as Record<string, unknown>)[key])}`)
			.join(",")}}`;
	}
	return JSON.stringify(value) ?? "null";
}

async function scanPath(root: string, relativePath: string, records: string[], findings: string[]): Promise<void> {
	const absolutePath = path.join(root, relativePath);
	let stat;
	try {
		stat = await fs.lstat(absolutePath);
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
		throw error;
	}
	if (stat.isSymbolicLink()) {
		throw new Error(`Security-sensitive project path must not be a symbolic link or junction: ${absolutePath}`);
	}
	const normalized = relativePath.split(path.sep).join("/");
	if (stat.isDirectory()) {
		records.push(`d:${normalized}`);
		findings.push(`${normalized}/`);
		for (const entry of await fs.readdir(absolutePath)) {
			await scanPath(root, path.join(relativePath, entry), records, findings);
		}
		return;
	}
	if (!stat.isFile()) throw new Error(`Unsupported security-sensitive project entry: ${absolutePath}`);
	const digest = crypto
		.createHash("sha256")
		.update(await fs.readFile(absolutePath))
		.digest("hex");
	records.push(`f:${normalized}:${stat.size}:${digest}`);
	findings.push(normalized);
}

function samePath(left: string, right: string): boolean {
	return process.platform === "win32" ? left.toLowerCase() === right.toLowerCase() : left === right;
}

function isTrustDocument(value: unknown): value is TrustDocument {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const candidate = value as Record<string, unknown>;
	if (candidate["version"] !== TRUST_VERSION || !Array.isArray(candidate["entries"])) return false;
	return candidate["entries"].every((entry) => {
		if (!entry || typeof entry !== "object" || Array.isArray(entry)) return false;
		const item = entry as Record<string, unknown>;
		return (
			typeof item["workspace"] === "string" &&
			typeof item["manifest"] === "string" &&
			/^[a-f0-9]{64}$/.test(item["manifest"]) &&
			typeof item["trustedAt"] === "string"
		);
	});
}

async function writeDocumentAtomic(filePath: string, document: TrustDocument): Promise<void> {
	await fs.mkdir(path.dirname(filePath), { recursive: true, mode: 0o700 });
	const tempPath = `${filePath}.${process.pid}.${Date.now().toString(36)}.tmp`;
	try {
		await retryTransientFileOperation(() =>
			fs.writeFile(tempPath, `${JSON.stringify(document, null, 2)}\n`, { encoding: "utf8", mode: 0o600 }),
		);
		await replaceAtomically(tempPath, filePath);
		await fs.chmod(filePath, 0o600).catch(() => {});
	} catch (error) {
		await fs.unlink(tempPath).catch(() => {});
		throw error;
	}
}
