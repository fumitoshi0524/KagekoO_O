import * as fs from "node:fs/promises";
import * as crypto from "node:crypto";

const DEFAULT_MAX_JSONL_BYTES = 128 * 1024 * 1024;

export function tokenize(text: unknown): string[] {
	return String(text)
		.toLowerCase()
		.replace(/[^a-z0-9_一-龥]+/g, " ")
		.split(/\s+/)
		.filter((t) => t.length > 1);
}

export function fingerprint(text: unknown): string {
	const normalized = String(text).toLowerCase().replace(/\s+/g, " ").trim().slice(0, 500);
	return crypto.createHash("sha256").update(normalized).digest("hex");
}

export interface ReadJsonlLinesOptions {
	maxBytes?: number;
	/** Called once with the number of unparseable lines that were skipped. */
	onSkippedLines?: (skipped: number, filePath: string) => void;
}

/**
 * Read a JSONL file with a size cap, skipping corrupt lines.
 */
export async function readJsonlLines<T = unknown>(
	filePath: string,
	{ maxBytes = DEFAULT_MAX_JSONL_BYTES, onSkippedLines }: ReadJsonlLinesOptions = {},
): Promise<T[]> {
	let stat;
	try {
		stat = await fs.stat(filePath);
	} catch (err) {
		if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
		throw err;
	}
	if (stat.size > maxBytes) {
		throw new Error(`JSONL file ${filePath} is ${stat.size} bytes, exceeding the ${maxBytes} byte cap`);
	}
	const data = await fs.readFile(filePath, "utf-8");
	let skipped = 0;
	const entries = data
		.split("\n")
		.map((line) => {
			if (!line.trim()) return undefined;
			try {
				return JSON.parse(line) as T;
			} catch {
				skipped += 1;
				return undefined;
			}
		})
		// `!= null` also drops a literal `null` JSONL line: `JSON.parse("null")`
		// succeeds, and a null entry would crash consumers (e.g. pending.jsonl
		// resolution reading `entry.event.id`).
		.filter((entry): entry is T => entry != null);
	if (skipped > 0) onSkippedLines?.(skipped, filePath);
	return entries;
}

export interface SafeStringifyOptions {
	pretty?: boolean;
	maxLength?: number;
}

export function safeStringify(
	value: unknown,
	{ pretty = false, maxLength = 10_000 }: SafeStringifyOptions = {},
): string {
	let text: string;
	try {
		text = JSON.stringify(value, null, pretty ? 2 : undefined);
	} catch {
		text = "[unserializable]";
	}
	if (text.length > maxLength) {
		return text.slice(0, maxLength);
	}
	return text;
}

function bigintReplacer(_key: string, value: unknown): unknown {
	if (typeof value === "bigint") return value.toString();
	return value;
}

export type JsonStringifyResult = { ok: true; text: string } | { ok: false; error: unknown };

/**
 * Serialize a value to JSON with BigInt support, returning the result or an
 * error marker. Useful for durable writes where an unserializable event should
 * be skipped rather than crashing the whole batch.
 */
export function tryJsonStringify(value: unknown): JsonStringifyResult {
	try {
		return { ok: true, text: JSON.stringify(value, bigintReplacer) };
	} catch (err) {
		return { ok: false, error: err };
	}
}

export interface EnsureJsonlSizeCapOptions {
	retainRatio?: number;
}

export async function ensureJsonlSizeCap(
	filePath: string,
	maxBytes: number,
	{ retainRatio = 0.75 }: EnsureJsonlSizeCapOptions = {},
): Promise<void> {
	let stat;
	try {
		stat = await fs.stat(filePath);
	} catch {
		return;
	}
	if (stat.size <= maxBytes) return;

	const data = await fs.readFile(filePath, "utf-8");
	const lines = data.split("\n");
	const target = Math.floor(maxBytes * retainRatio);
	const kept: string[] = [];
	let size = 0;
	// Keep the most recent lines (at the end of the file) so we do not lose
	// everything when the cap is exceeded.
	for (let i = lines.length - 1; i >= 0; i--) {
		const line = lines[i]!;
		if (line === "") continue;
		const lineBytes = Buffer.byteLength(line + "\n", "utf-8");
		if (size > 0 && size + lineBytes > target) break;
		kept.unshift(line);
		size += lineBytes;
	}
	await fs.writeFile(filePath, kept.length ? `${kept.join("\n")}\n` : "", "utf-8");
}

export async function mapConcurrent<T, R>(
	items: T[],
	concurrency: number,
	fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
	const results = new Array<R>(items.length);
	let index = 0;

	async function worker(): Promise<void> {
		while (index < items.length) {
			const i = index++;
			results[i] = await fn(items[i]!, i);
		}
	}

	await Promise.all(Array.from({ length: Math.max(1, concurrency) }, worker));
	return results;
}
