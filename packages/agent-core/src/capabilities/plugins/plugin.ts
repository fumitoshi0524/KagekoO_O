import * as dns from "node:dns/promises";
import * as fs from "node:fs/promises";
import * as net from "node:net";
import * as path from "node:path";
import { promisify } from "node:util";
import { gunzip as gunzipCb, inflateRaw as inflateRawCb } from "node:zlib";

const gunzip = promisify(gunzipCb);
const inflateRaw = promisify(inflateRawCb);

const MAX_ARCHIVE_BYTES = 100 * 1024 * 1024;
const FETCH_TIMEOUT_MS = 30000;
const MAX_DOWNLOAD_REDIRECTS = 5;
const MAX_TAR_ENTRY_BYTES = 100 * 1024 * 1024;
const MAX_TAR_ENTRIES = 10_000;
const MAX_ZIP_ENTRIES = 10_000;
const MAX_EXTRACTED_BYTES = 100 * 1024 * 1024;

export interface InstallPluginOptions {
	/** Override the plugin id (defaults to repo name or extracted manifest name). */
	pluginId?: string;
	/** Installation root directory, supplied by the caller (the application layer owns plugin directory locations). */
	pluginsDir: string;
	/** Workspace root supplied by application for local file:// validation. */
	sourceRoot: string;
}

interface ArchiveEntry {
	name: string;
	data: Buffer;
}

interface EndOfCentralDirectory {
	totalEntries: number;
	centralDirSize: number;
	centralDirOffset: number;
}

/**
 * Install a plugin from a GitHub repo or a zip/tar URL into `<pluginsDir>/<pluginId>`.
 *
 * @param source - GitHub repo (owner/repo or github:owner/repo) or archive URL.
 * @returns Installed plugin id.
 */
export async function installPlugin(source: string, options: InstallPluginOptions): Promise<string> {
	const { pluginId, pluginsDir } = options;
	let url: string;
	let inferredId: string | undefined;

	if (source.startsWith("http://") || source.startsWith("https://")) {
		url = source;
	} else if (source.startsWith("file://")) {
		url = source;
	} else if (source.startsWith("github:")) {
		const repo = source.slice("github:".length);
		url = `https://api.github.com/repos/${repo}/tarball`;
		inferredId = repo.split("/").pop();
	} else if (source.includes("/") && !source.includes("://")) {
		url = `https://api.github.com/repos/${source}/tarball`;
		inferredId = source.split("/").pop();
	} else {
		throw new Error(`Unsupported plugin source: ${source}`);
	}

	const archiveBuffer = await downloadArchive(url, pluginsDir, options.sourceRoot);
	const targetId = sanitizePluginId(pluginId ?? inferredId ?? "plugin");
	const targetDir = resolvePluginDir(pluginsDir, targetId);
	await fs.mkdir(targetDir, { recursive: true });

	const format = detectArchiveFormat(archiveBuffer, url);
	if (format === "zip") {
		await extractZip(archiveBuffer, targetDir);
	} else {
		// GitHub tarballs and .tar/.tar.gz archives
		await extractTar(archiveBuffer, targetDir);
	}

	const manifestPath = path.join(targetDir, "kageko-plugin.json");
	if (!(await fileExists(manifestPath))) {
		throw new Error(`Installed plugin is missing kageko-plugin.json at ${targetDir}`);
	}

	const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8")) as { name?: unknown };
	if (!manifest.name || typeof manifest.name !== "string") {
		throw new Error("kageko-plugin.json is missing a valid plugin name");
	}

	const rawId = pluginId ?? manifest.name.toLowerCase();
	const finalId = sanitizePluginId(rawId);
	if (finalId !== path.basename(targetDir)) {
		const finalDir = resolvePluginDir(pluginsDir, finalId);
		await fs.rm(finalDir, { recursive: true, force: true });
		await fs.rename(targetDir, finalDir);
	}

	return finalId;
}

function sanitizePluginId(id: string): string {
	const sanitized =
		String(id)
			.toLowerCase()
			.replace(/[^a-z0-9_.-]/g, "_")
			.replace(/^_+|_+$/g, "")
			.slice(0, 64) || "plugin";
	// "." and ".." survive the character whitelist and would traverse out of
	// the plugins directory when joined as a path segment.
	if (sanitized === "." || sanitized === "..") {
		throw new Error(`Invalid plugin id: ${id}`);
	}
	return sanitized;
}

/** Resolve a plugin id under the plugins directory, asserting containment. */
function resolvePluginDir(pluginsDir: string, id: string): string {
	const root = path.resolve(pluginsDir);
	const dir = path.resolve(root, id);
	if (!isUnderRoot(root, dir)) {
		throw new Error(`Invalid plugin id: ${id} escapes the plugins directory`);
	}
	return dir;
}

function detectArchiveFormat(buffer: Buffer, url: string): "zip" | "tar" {
	if (buffer.length >= 4 && buffer[0] === 0x50 && buffer[1] === 0x4b && buffer[2] === 0x03 && buffer[3] === 0x04) {
		return "zip";
	}
	if (buffer.length >= 2 && buffer[0] === 0x1f && buffer[1] === 0x8b) {
		return "tar";
	}
	if (buffer.length >= 262 && buffer.toString("utf8", 257, 263) === "ustar\0") {
		return "tar";
	}
	return url.toLowerCase().split("?")[0]?.endsWith(".zip") ? "zip" : "tar";
}

function isRedirectStatus(status: number): boolean {
	return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

function cancelResponseBody(res: Response): void {
	void (res.body?.cancel().catch(() => {}) as Promise<void> | undefined);
}

async function assertPublicHttpsUrl(urlString: string): Promise<void> {
	let parsed: URL;
	try {
		parsed = new URL(urlString);
	} catch {
		throw new Error(`Invalid plugin archive URL: ${urlString}`);
	}
	if (parsed.protocol !== "https:") {
		throw new Error(`Plugin archive URL must use HTTPS: ${urlString}`);
	}
	if (parsed.username || parsed.password) {
		throw new Error(`Plugin archive URL must not contain credentials: ${urlString}`);
	}
	const hostCheck = await isHostPrivate(parsed.hostname);
	if (hostCheck.private) {
		throw new Error(`Refusing to download plugin archive from private/reserved address: ${hostCheck.reason}`);
	}
}

async function isHostPrivate(hostname: string): Promise<{ private: boolean; reason?: string }> {
	const family = net.isIP(hostname);
	if (family === 4) {
		return { private: isPrivateIPv4(hostname), reason: hostname };
	}
	if (family === 6) {
		return { private: isPrivateIPv6(hostname), reason: hostname };
	}
	try {
		const records = await dns.lookup(hostname, { all: true });
		for (const { address } of records) {
			if (isPrivateIPv4(address) || isPrivateIPv6(address)) {
				return { private: true, reason: address };
			}
		}
	} catch {
		// Allow the fetch to proceed; the network will reject unreachable hosts.
	}
	return { private: false };
}

function isPrivateIPv4(ip: string): boolean {
	const lowered = ip.toLowerCase();
	if (lowered.startsWith("::ffff:")) {
		return isPrivateIPv4(extractMappedIPv4(lowered));
	}
	const parts = ip.split(".").map(Number);
	if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return false;
	const [a = 0, b = 0, c = 0] = parts;
	if (a === 0 || a === 10 || a === 127) return true;
	if (a === 169 && b === 254) return true;
	if (a === 172 && b >= 16 && b <= 31) return true;
	if (a === 192 && b === 168) return true;
	if (a === 100 && b >= 64 && b <= 127) return true;
	if (a >= 224 && a <= 239) return true;
	if (a === 255 && b === 255 && c === 255) return true;
	return false;
}

function extractMappedIPv4(mapped: string): string {
	if (mapped.includes(".")) return mapped;
	const groups = mapped.split(":").filter(Boolean);
	const octets: number[] = [];
	for (const group of groups) {
		const value = parseInt(group, 16);
		if (Number.isNaN(value) || value < 0 || value > 0xffff) return "";
		octets.push((value >> 8) & 0xff, value & 0xff);
	}
	if (octets.length !== 4) return "";
	return octets.join(".");
}

function isPrivateIPv6(ip: string): boolean {
	const full = ip.toLowerCase();
	if (full === "::1" || full.startsWith("fe80:") || full.startsWith("fc") || full.startsWith("fd")) return true;
	if (full.startsWith("::ffff:")) {
		return isPrivateIPv4(extractMappedIPv4(full.slice(7)));
	}
	return false;
}

async function downloadArchive(url: string, pluginsDir: string, sourceRoot: string): Promise<Buffer> {
	if (url.startsWith("file://")) {
		const filePath = path.resolve(url.slice("file://".length));
		const allowedRoots = [path.resolve(pluginsDir), path.resolve(sourceRoot)];
		if (!allowedRoots.some((root) => isUnderRoot(root, filePath))) {
			throw new Error("Local plugin source must be inside the plugins directory or current working directory.");
		}
		const stat = await fs.stat(filePath).catch(() => null);
		if (!stat || stat.size > MAX_ARCHIVE_BYTES) {
			throw new Error("Plugin archive file is missing or exceeds the maximum size.");
		}
		return fs.readFile(filePath);
	}

	let currentUrl = url;
	let redirects = 0;
	while (redirects <= MAX_DOWNLOAD_REDIRECTS) {
		await assertPublicHttpsUrl(currentUrl);
		const res = await fetch(currentUrl, {
			signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
			redirect: "manual",
			headers: {
				Accept: "application/vnd.github+json, application/octet-stream, */*",
				"User-Agent": "kageko",
			},
		});

		if (isRedirectStatus(res.status)) {
			const location = res.headers.get("location");
			cancelResponseBody(res);
			if (!location) {
				throw new Error(`Redirect response missing Location header: ${currentUrl}`);
			}
			currentUrl = new URL(location, currentUrl).toString();
			redirects += 1;
			continue;
		}

		if (!res.ok) {
			cancelResponseBody(res);
			throw new Error(`Failed to download plugin archive: ${res.status} ${await res.text()}`);
		}
		if (!res.body) {
			throw new Error("Plugin archive response has no body.");
		}

		const reader = res.body.getReader();
		const chunks: Uint8Array[] = [];
		let received = 0;
		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				received += value.length;
				if (received > MAX_ARCHIVE_BYTES) {
					void reader.cancel().catch(() => {});
					throw new Error("Plugin archive exceeds the maximum size.");
				}
				chunks.push(value);
			}
		} finally {
			reader.releaseLock();
		}
		return Buffer.concat(chunks);
	}
	throw new Error(`Too many redirects (${MAX_DOWNLOAD_REDIRECTS}) downloading plugin archive.`);
}

async function extractTar(buffer: Buffer, targetDir: string): Promise<void> {
	// GitHub tarballs are gzip compressed.
	const isGzipped = buffer[0] === 0x1f && buffer[1] === 0x8b;
	const tarBuffer = isGzipped ? await gunzip(buffer, { maxOutputLength: MAX_ARCHIVE_BYTES }) : buffer;

	const entries = parseTar(tarBuffer);
	const strip = commonPrefix(entries.map((e) => e.name).filter((n) => !n.endsWith("/")));

	let extractedBytes = 0;
	for (const entry of entries) {
		const relative = strip ? path.relative(strip, entry.name) : entry.name;
		const outPath = safeArchivePath(targetDir, relative);
		if (!outPath) continue;

		if (entry.name.endsWith("/")) {
			await fs.mkdir(outPath, { recursive: true });
		} else {
			extractedBytes += entry.data.length;
			if (extractedBytes > MAX_EXTRACTED_BYTES) {
				throw new Error("Extracted plugin exceeds the maximum allowed size.");
			}
			await fs.mkdir(path.dirname(outPath), { recursive: true });
			await fs.writeFile(outPath, entry.data);
		}
	}
}

function parseTar(buffer: Buffer): ArchiveEntry[] {
	const entries: ArchiveEntry[] = [];
	const BLOCK_SIZE = 512;
	let offset = 0;

	while (offset + BLOCK_SIZE <= buffer.length) {
		const header = buffer.subarray(offset, offset + BLOCK_SIZE);
		const name = readTarString(header, 0, 100);
		if (!name) break;

		const sizeOctal = readTarString(header, 124, 12).trim();
		const size = parseInt(sizeOctal, 8) || 0;
		if (size < 0 || size > MAX_TAR_ENTRY_BYTES || offset + BLOCK_SIZE + size > buffer.length) {
			break;
		}
		const typeFlag = header[156];
		const isDirectory = typeFlag === 0x35 || name.endsWith("/");
		const isRegularFile = typeFlag === 0x30 || typeFlag === 0 || typeFlag === 0x00;

		offset += BLOCK_SIZE;
		if (entries.length >= MAX_TAR_ENTRIES) {
			throw new Error("Plugin archive contains too many entries.");
		}
		if (size > 0) {
			if (!isRegularFile && !isDirectory) {
				offset += Math.ceil(size / BLOCK_SIZE) * BLOCK_SIZE;
				continue;
			}
			const data = buffer.subarray(offset, offset + size);
			entries.push({ name: isDirectory ? ensureTrailingSlash(name) : name, data: Buffer.from(data) });
			offset += Math.ceil(size / BLOCK_SIZE) * BLOCK_SIZE;
		} else if (isDirectory) {
			entries.push({ name: ensureTrailingSlash(name), data: Buffer.alloc(0) });
		}
	}

	return entries;
}

function readTarString(buffer: Buffer, start: number, length: number): string {
	return buffer
		.toString("utf8", start, start + length)
		.replace(/\0/g, "")
		.trim();
}

function ensureTrailingSlash(name: string): string {
	return name.endsWith("/") ? name : `${name}/`;
}

function safeArchivePath(targetDir: string, relative: string): string | undefined {
	if (!relative) return undefined;
	// Normalize separators and strip any leading slash/traversal before joining.
	const normalized = relative.replace(/\\/g, "/").replace(/^\/+/, "");
	if (!normalized || normalized.startsWith("..")) return undefined;
	const joined = path.resolve(targetDir, normalized);
	const rel = path.relative(targetDir, joined);
	if (rel.startsWith("..") || path.isAbsolute(rel)) return undefined;
	return joined;
}

function isUnderRoot(root: string, target: string): boolean {
	const rel = path.relative(root, target);
	return Boolean(rel) && !rel.startsWith("..") && !path.isAbsolute(rel);
}

function commonPrefix(paths: string[]): string {
	if (paths.length === 0) return "";
	const dirParts = paths.map((p) => {
		const dir = p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "";
		return dir.split("/").filter(Boolean);
	});
	const first = dirParts[0]!;
	if (first.length === 0) return "";

	let prefixLen = 0;
	for (let i = 0; i < first.length; i++) {
		if (dirParts.every((p) => p[i] === first[i])) {
			prefixLen = i + 1;
		} else {
			break;
		}
	}
	return prefixLen > 0 ? first.slice(0, prefixLen).join("/") : "";
}

async function extractZip(buffer: Buffer, targetDir: string): Promise<void> {
	const entries = await parseZip(buffer);
	const strip = commonPrefix(entries.map((e) => e.name).filter((n) => !n.endsWith("/")));

	let extractedBytes = 0;
	for (const entry of entries) {
		const relative = strip ? path.relative(strip, entry.name) : entry.name;
		const outPath = safeArchivePath(targetDir, relative);
		if (!outPath) continue;

		if (entry.name.endsWith("/")) {
			await fs.mkdir(outPath, { recursive: true });
		} else {
			extractedBytes += entry.data.length;
			if (extractedBytes > MAX_EXTRACTED_BYTES) {
				throw new Error("Extracted plugin exceeds the maximum allowed size.");
			}
			await fs.mkdir(path.dirname(outPath), { recursive: true });
			await fs.writeFile(outPath, entry.data);
		}
	}
}

async function parseZip(buffer: Buffer): Promise<ArchiveEntry[]> {
	const entries: ArchiveEntry[] = [];
	const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
	const eocd = findEndOfCentralDirectory(buffer, view);
	if (!eocd) throw new Error("Invalid zip file: missing end of central directory");
	if (eocd.totalEntries > MAX_ZIP_ENTRIES) {
		throw new Error("Plugin archive contains too many entries.");
	}

	let offset = eocd.centralDirOffset;
	for (let i = 0; i < eocd.totalEntries; i++) {
		const signature = view.getUint32(offset, true);
		if (signature !== 0x02014b50) throw new Error("Invalid zip central directory signature");

		const compression = view.getUint16(offset + 10, true);
		const compressedSize = view.getUint32(offset + 20, true);
		const nameLength = view.getUint16(offset + 28, true);
		const extraLength = view.getUint16(offset + 30, true);
		const commentLength = view.getUint16(offset + 32, true);
		const localHeaderOffset = view.getUint32(offset + 42, true);

		if (localHeaderOffset + 30 > buffer.length) {
			throw new Error("Invalid zip local header offset.");
		}
		const localSignature = view.getUint32(localHeaderOffset, true);
		if (localSignature !== 0x04034b50) {
			throw new Error("Invalid zip local file header signature");
		}

		const name = buffer.toString("utf8", offset + 46, offset + 46 + nameLength);
		const localNameLength = view.getUint16(localHeaderOffset + 26, true);
		const localExtraLength = view.getUint16(localHeaderOffset + 28, true);
		const dataOffset = localHeaderOffset + 30 + localNameLength + localExtraLength;

		if (compressedSize > MAX_ARCHIVE_BYTES || dataOffset + compressedSize > buffer.length) {
			throw new Error("Invalid or oversized zip entry.");
		}

		const compressed = buffer.subarray(dataOffset, dataOffset + compressedSize);
		let data: Buffer;
		if (compression === 0) {
			data = Buffer.from(compressed);
		} else if (compression === 8) {
			// Zip method 8 is raw DEFLATE (no gzip/zlib wrapper).
			data = await inflateRaw(compressed, { maxOutputLength: MAX_ARCHIVE_BYTES });
		} else {
			throw new Error(`Unsupported zip compression method: ${compression}`);
		}

		entries.push({ name, data: Buffer.from(data) });
		offset += 46 + nameLength + extraLength + commentLength;
	}

	return entries;
}

function findEndOfCentralDirectory(buffer: Buffer, view: DataView): EndOfCentralDirectory | null {
	for (let i = buffer.length - 22; i >= 0; i--) {
		if (view.getUint32(i, true) === 0x06054b50) {
			return {
				totalEntries: view.getUint16(i + 10, true),
				centralDirSize: view.getUint32(i + 12, true),
				centralDirOffset: view.getUint32(i + 16, true),
			};
		}
	}
	return null;
}

async function fileExists(filePath: string): Promise<boolean> {
	try {
		await fs.access(filePath);
		return true;
	} catch {
		return false;
	}
}
