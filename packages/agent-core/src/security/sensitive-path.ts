import * as path from "node:path";

export type SensitivePathKind = "environment" | "private_key" | "credential_file" | "credential_directory";

export interface SensitivePathClassification {
	sensitive: boolean;
	kind?: SensitivePathKind;
	hideName: boolean;
}

const CREDENTIAL_DIRECTORIES = new Set([".ssh", ".aws", ".kube", ".docker"]);
const CREDENTIAL_FILES = new Set([".git-credentials", ".netrc", ".pgpass", ".npmrc", ".pypirc"]);

/** Shared classifier used before reading, indexing, summarizing, or approving a path. */
export function classifySensitivePath(inputPath: string): SensitivePathClassification {
	const normalized = path.normalize(inputPath);
	const segments = normalized
		.split(/[\\/]+/)
		.filter(Boolean)
		.map((segment) => segment.toLowerCase());
	const base = segments.at(-1) ?? "";
	const parent = segments.at(-2) ?? "";
	if (segments.some((segment) => CREDENTIAL_DIRECTORIES.has(segment))) {
		return { sensitive: true, kind: "credential_directory", hideName: true };
	}
	if (base === ".env" || base.startsWith(".env.")) {
		return { sensitive: true, kind: "environment", hideName: false };
	}
	if (
		(parent === ".kageko" && ["auth.json", "mcp-tokens.json", "config.json"].includes(base)) ||
		(parent === ".codex" && base === "auth.json")
	) {
		return { sensitive: true, kind: "credential_file", hideName: true };
	}
	if (
		base.startsWith("id_rsa") ||
		base.startsWith("id_dsa") ||
		base.startsWith("id_ecdsa") ||
		base.startsWith("id_ed25519") ||
		base.endsWith(".pem") ||
		base.endsWith(".key")
	) {
		return { sensitive: true, kind: "private_key", hideName: true };
	}
	if (CREDENTIAL_FILES.has(base)) {
		return { sensitive: true, kind: "credential_file", hideName: true };
	}
	return { sensitive: false, hideName: false };
}

export function isSensitiveContentPath(inputPath: string): boolean {
	return classifySensitivePath(inputPath).sensitive;
}

export function shouldHideSensitiveName(inputPath: string): boolean {
	return classifySensitivePath(inputPath).hideName;
}
