/**
 * Local, opt-in telemetry collector.
 *
 * Events are redacted before they enter memory, written to bounded rotating
 * JSONL files, and never uploaded automatically. `previewUpload()` is the
 * explicit boundary for inspecting the exact redacted payload a caller may
 * choose to upload.
 */
import { randomUUID } from "node:crypto";
import * as fs from "node:fs/promises";
import type { Stats } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

const TELEMETRY_FILE_NAME = "telemetry.jsonl";
const FAILED_BATCH_PATTERN = /^telemetry\.failed\.(\d{13})\.([0-9a-f-]+)\.jsonl$/;
const DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024;
const DEFAULT_MAX_BACKUP_FILES = 3;
const DEFAULT_RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const DEFAULT_MAX_BUFFER_EVENTS = 1000;
const DEFAULT_MAX_BUFFER_BYTES = 1024 * 1024;
const DEFAULT_MAX_EVENT_BYTES = 256 * 1024;
const DEFAULT_FLUSH_INTERVAL_MS = 5000;
const DEFAULT_PREVIEW_MAX_EVENTS = 1000;
const DEFAULT_PREVIEW_MAX_BYTES = 1024 * 1024;
const REDACTED = "[REDACTED]";
const SENSITIVE_FIELD_NAMES = new Set([
	"access_token",
	"accesstoken",
	"api_key",
	"apikey",
	"authorization",
	"auth_token",
	"authtoken",
	"client_secret",
	"clientsecret",
	"credential",
	"id_token",
	"idtoken",
	"password",
	"private_key",
	"privatekey",
	"refresh_token",
	"refreshtoken",
	"secret",
	"token",
]);
const SECRET_VALUE_PATTERNS = [
	/\b(?:sk-|ghp_|github_pat_|gho_|ghu_|ghs_|ghr_|xox[baprs]-|pplx-|fal_|gsk_|xai-)[A-Za-z0-9_-]{10,}\b/g,
	/\bAIza[A-Za-z0-9_-]{30,}\b/g,
	/\bAKIA[A-Z0-9]{16}\b/g,
	/\beyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_=-]{4,}){0,2}\b/g,
];
const AUTHORIZATION_HEADER_PATTERN = /(\bAuthorization\s*:\s*Bearer\s+)\S+/gi;
const PRIVATE_KEY_PATTERN = /-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----/g;
const URL_USERINFO_PATTERN =
	/((?:https?|wss?|ftp|postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\s/:@]+:)[^\s/@]+(@)/gi;

function tryJsonStringify(value: unknown): { ok: true; text: string } | { ok: false } {
	try {
		return { ok: true, text: JSON.stringify(value) };
	} catch {
		return { ok: false };
	}
}

function normalizeSensitiveFieldName(name: string): string {
	return name.toLowerCase().replaceAll("-", "_");
}

function redactString(value: string): string {
	let redacted = value;
	for (const pattern of SECRET_VALUE_PATTERNS) {
		pattern.lastIndex = 0;
		redacted = redacted.replace(pattern, REDACTED);
	}
	redacted = redacted.replace(AUTHORIZATION_HEADER_PATTERN, `$1${REDACTED}`);
	redacted = redacted.replace(PRIVATE_KEY_PATTERN, REDACTED);
	redacted = redacted.replace(URL_USERINFO_PATTERN, `$1${REDACTED}$2`);
	try {
		const url = new URL(redacted);
		for (const key of [...url.searchParams.keys()]) {
			if (SENSITIVE_FIELD_NAMES.has(normalizeSensitiveFieldName(key))) url.searchParams.set(key, REDACTED);
		}
		redacted = url.toString();
	} catch {
		// Most telemetry strings are not URLs.
	}
	return redacted;
}

function redactValue(value: unknown, seen = new WeakMap<object, unknown>()): unknown {
	if (typeof value === "string") return redactString(value);
	if (value === null || typeof value !== "object") return value;
	const cached = seen.get(value);
	if (cached !== undefined) return cached;
	if (Array.isArray(value)) {
		const output: unknown[] = [];
		seen.set(value, output);
		for (const item of value) output.push(redactValue(item, seen));
		return output;
	}
	const output: Record<string, unknown> = {};
	seen.set(value, output);
	for (const [key, item] of Object.entries(value)) {
		output[key] = SENSITIVE_FIELD_NAMES.has(normalizeSensitiveFieldName(key)) ? REDACTED : redactValue(item, seen);
	}
	return output;
}

function nonNegativeInteger(name: string, value: number): number {
	if (!Number.isSafeInteger(value) || value < 0) throw new RangeError(`${name} must be a non-negative safe integer`);
	return value;
}

function positiveInteger(name: string, value: number): number {
	if (!Number.isSafeInteger(value) || value <= 0) throw new RangeError(`${name} must be a positive safe integer`);
	return value;
}

function isMissingFile(error: unknown): boolean {
	return (error as NodeJS.ErrnoException).code === "ENOENT";
}

export interface TelemetryEvent {
	type: string;
	[key: string]: unknown;
}

export interface TelemetryCollectorOptions {
	enabled?: boolean;
	kagekoDir?: string;
	maxBufferEvents?: number;
	maxBufferBytes?: number;
	maxEventBytes?: number;
	maxFileBytes?: number;
	maxBackupFiles?: number;
	retentionMs?: number;
	flushIntervalMs?: number;
	now?: () => number;
}

export interface TelemetryUploadPreviewOptions {
	maxEvents?: number;
	maxBytes?: number;
}

export interface TelemetryUploadPreview {
	generatedAt: string;
	events: TelemetryEvent[];
	eventCount: number;
	byteLength: number;
	truncated: boolean;
	pendingEventCount: number;
	sourceFiles: string[];
}

interface SerializedEvent {
	event: TelemetryEvent;
	line: string;
	bytes: number;
}

export class TelemetryCollector {
	private enabled: boolean;
	private kagekoDir: string;
	private maxBufferEvents: number;
	private maxBufferBytes: number;
	private maxEventBytes: number;
	private maxFileBytes: number;
	private maxBackupFiles: number;
	private retentionMs: number;
	private flushIntervalMs: number;
	private now: () => number;
	private buffer: TelemetryEvent[] = [];
	private flushTimer: NodeJS.Timeout | null = null;
	private _flushPromise: Promise<void> | null = null;
	private _closed = false;

	constructor({
		enabled = false,
		kagekoDir,
		maxBufferEvents,
		maxBufferBytes,
		maxEventBytes,
		maxFileBytes,
		maxBackupFiles,
		retentionMs,
		flushIntervalMs,
		now,
	}: TelemetryCollectorOptions = {}) {
		this.enabled = enabled;
		this.kagekoDir = kagekoDir ?? path.join(os.homedir(), ".kageko");
		this.maxBufferEvents = nonNegativeInteger("maxBufferEvents", maxBufferEvents ?? DEFAULT_MAX_BUFFER_EVENTS);
		this.maxBufferBytes = nonNegativeInteger("maxBufferBytes", maxBufferBytes ?? DEFAULT_MAX_BUFFER_BYTES);
		this.maxEventBytes = positiveInteger("maxEventBytes", maxEventBytes ?? DEFAULT_MAX_EVENT_BYTES);
		this.maxFileBytes = positiveInteger("maxFileBytes", maxFileBytes ?? DEFAULT_MAX_FILE_BYTES);
		this.maxBackupFiles = nonNegativeInteger("maxBackupFiles", maxBackupFiles ?? DEFAULT_MAX_BACKUP_FILES);
		this.retentionMs = nonNegativeInteger("retentionMs", retentionMs ?? DEFAULT_RETENTION_MS);
		this.flushIntervalMs = nonNegativeInteger("flushIntervalMs", flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS);
		this.now = now ?? Date.now;
		if (this.enabled) this.scheduleFlush();
	}

	record(event: TelemetryEvent): void {
		if (!this.enabled || this._closed) return;
		this.buffer.push(
			redactValue({
				ts: new Date(this.now()).toISOString(),
				...event,
			}) as TelemetryEvent,
		);
		this._enforceBufferCap();
		this.scheduleFlush();
	}

	log(message: string, details: Record<string, unknown> = {}): void {
		this.record({ type: "log", message, ...details });
	}

	count(name: string, value = 1, details: Record<string, unknown> = {}): void {
		this.record({ type: "count", name, value, ...details });
	}

	timing(name: string, durationMs: number, details: Record<string, unknown> = {}): void {
		this.record({ type: "timing", name, durationMs, ...details });
	}

	scheduleFlush(): void {
		if (this._closed || this.flushTimer) return;
		this.flushTimer = setTimeout(() => {
			this.flushTimer = null;
			void this.flush();
		}, this.flushIntervalMs);
		this.flushTimer.unref?.();
	}

	private _enforceBufferCap(): void {
		while (this.buffer.length > this.maxBufferEvents) {
			this.buffer.shift();
		}
		let bytes = 0;
		let i = 0;
		while (i < this.buffer.length) {
			const serialized = tryJsonStringify(this.buffer[i]);
			if (!serialized.ok) {
				console.warn("TelemetryCollector: dropping unserializable event");
				this.buffer.splice(i, 1);
				continue;
			}
			bytes += Buffer.byteLength(serialized.text, "utf-8");
			i++;
		}
		while (this.buffer.length > 0 && bytes > this.maxBufferBytes) {
			const removed = this.buffer.shift();
			const serialized = tryJsonStringify(removed);
			if (serialized.ok) bytes -= Buffer.byteLength(serialized.text, "utf-8");
		}
	}

	async flush(): Promise<void> {
		if (this._flushPromise) return this._flushPromise;
		const promise = this._flush();
		this._flushPromise = promise;
		try {
			await promise;
		} finally {
			this._flushPromise = null;
			if (this.enabled && !this._closed) this.scheduleFlush();
		}
	}

	private async _flush(): Promise<void> {
		if (!this.enabled) return;
		await this._applyRetention();
		if (!(await this._retryFailedBatches())) {
			this.scheduleFlush();
			return;
		}
		if (this.buffer.length === 0) return;
		while (this.buffer.length > 0) {
			const events = this.buffer.splice(0);
			const serialized = this._serializeEvents(events);
			if (serialized.length === 0) continue;
			const chunks = this._chunkEvents(serialized);
			for (let index = 0; index < chunks.length; index++) {
				const chunk = chunks[index]!;
				try {
					await this._writeChunk(chunk);
				} catch {
					const retry = chunks.slice(index).flatMap((remaining) => remaining.map((item) => item.event));
					if (!(await this._spoolFailedBatch(retry))) {
						this.buffer.unshift(...retry);
						this._enforceBufferCap();
					}
					this.scheduleFlush();
					return;
				}
			}
		}
	}

	private _serializeEvents(events: TelemetryEvent[]): SerializedEvent[] {
		const serialized: SerializedEvent[] = [];
		for (const event of events) {
			const result = tryJsonStringify(event);
			if (!result.ok) {
				console.warn("TelemetryCollector: skipping unserializable event");
				continue;
			}
			const line = `${result.text}\n`;
			const bytes = Buffer.byteLength(line, "utf-8");
			if (bytes > this.maxEventBytes || bytes > this.maxFileBytes) {
				console.warn("TelemetryCollector: skipping oversized event");
				continue;
			}
			serialized.push({ event, line, bytes });
		}
		return serialized;
	}

	private _chunkEvents(events: SerializedEvent[]): SerializedEvent[][] {
		const chunks: SerializedEvent[][] = [];
		let chunk: SerializedEvent[] = [];
		let bytes = 0;
		for (const event of events) {
			if (chunk.length > 0 && bytes + event.bytes > this.maxFileBytes) {
				chunks.push(chunk);
				chunk = [];
				bytes = 0;
			}
			chunk.push(event);
			bytes += event.bytes;
		}
		if (chunk.length > 0) chunks.push(chunk);
		return chunks;
	}

	private async _writeChunk(events: SerializedEvent[]): Promise<void> {
		await fs.mkdir(this.kagekoDir, { recursive: true });
		const logPath = path.join(this.kagekoDir, TELEMETRY_FILE_NAME);
		const chunk = events.map((event) => event.line).join("");
		const chunkBytes = Buffer.byteLength(chunk, "utf-8");
		await this._rotateIfNeeded(logPath, chunkBytes);

		// O_APPEND makes concurrent collectors' chunks atomic with respect to the
		// file offset and avoids the read-modify-rename lost-update race.
		await fs.appendFile(logPath, chunk, { encoding: "utf-8", mode: 0o600 });
	}

	private async _spoolFailedBatch(events: TelemetryEvent[]): Promise<boolean> {
		const serialized = this._serializeEvents(events);
		if (serialized.length === 0) return true;
		try {
			await fs.mkdir(this.kagekoDir, { recursive: true });
			const timestamp = String(this.now()).padStart(13, "0");
			const fileName = `telemetry.failed.${timestamp}.${randomUUID()}.jsonl`;
			await fs.writeFile(path.join(this.kagekoDir, fileName), serialized.map((item) => item.line).join(""), {
				encoding: "utf-8",
				mode: 0o600,
				flag: "wx",
			});
			return true;
		} catch {
			return false;
		}
	}

	private async _retryFailedBatches(): Promise<boolean> {
		let entries: string[];
		try {
			entries = await fs.readdir(this.kagekoDir);
		} catch (error) {
			return isMissingFile(error);
		}
		const failed = entries.filter((entry) => FAILED_BATCH_PATTERN.test(entry)).sort();
		for (const entry of failed) {
			const filePath = path.join(this.kagekoDir, entry);
			let stat: Stats;
			try {
				stat = await fs.stat(filePath);
				if (this.now() - stat.mtimeMs > this.retentionMs) {
					await fs.unlink(filePath);
					continue;
				}
			} catch (error) {
				if (isMissingFile(error)) continue;
				return false;
			}
			let events: TelemetryEvent[];
			try {
				events = await this._readJsonl(filePath);
			} catch {
				await fs.unlink(filePath).catch(() => undefined);
				continue;
			}
			if (events.length === 0) {
				await fs.unlink(filePath).catch(() => undefined);
				continue;
			}
			try {
				await this._writeChunk(this._serializeEvents(events));
				await fs.unlink(filePath);
			} catch {
				return false;
			}
		}
		return true;
	}

	private async _rotateIfNeeded(logPath: string, incomingBytes: number): Promise<void> {
		let stat: Stats;
		try {
			stat = await fs.stat(logPath);
		} catch (error) {
			if (isMissingFile(error)) return;
			throw error;
		}
		if (stat.size === 0 || stat.size + incomingBytes <= this.maxFileBytes) return;
		if (this.maxBackupFiles === 0) {
			await fs.unlink(logPath);
			return;
		}
		await fs.unlink(`${logPath}.${String(this.maxBackupFiles)}`).catch((error: unknown) => {
			if (!isMissingFile(error)) throw error;
		});
		for (let index = this.maxBackupFiles - 1; index >= 1; index--) {
			const source = `${logPath}.${String(index)}`;
			const destination = `${logPath}.${String(index + 1)}`;
			try {
				await fs.rename(source, destination);
			} catch (error) {
				if (!isMissingFile(error)) throw error;
			}
		}
		await fs.rename(logPath, `${logPath}.1`);
	}

	private async _applyRetention(): Promise<void> {
		let entries: string[];
		try {
			entries = await fs.readdir(this.kagekoDir);
		} catch (error) {
			if (isMissingFile(error) || (error as NodeJS.ErrnoException).code === "ENOTDIR") return;
			throw error;
		}
		const now = this.now();
		for (const entry of entries) {
			const backup = this._backupIndex(entry);
			const failedBatch = FAILED_BATCH_PATTERN.test(entry);
			if (entry !== TELEMETRY_FILE_NAME && backup === null && !failedBatch) continue;
			const filePath = path.join(this.kagekoDir, entry);
			if (backup !== null && backup > this.maxBackupFiles) {
				await fs.unlink(filePath).catch(() => {});
				continue;
			}
			try {
				const stat = await fs.stat(filePath);
				if (now - stat.mtimeMs > this.retentionMs) await fs.unlink(filePath);
			} catch (error) {
				if (!isMissingFile(error)) throw error;
			}
		}
	}

	private _backupIndex(fileName: string): number | null {
		const match = /^telemetry\.jsonl\.(\d+)$/.exec(fileName);
		if (!match) return null;
		const value = Number(match[1]);
		return Number.isSafeInteger(value) && value > 0 ? value : null;
	}

	async previewUpload({
		maxEvents = DEFAULT_PREVIEW_MAX_EVENTS,
		maxBytes = DEFAULT_PREVIEW_MAX_BYTES,
	}: TelemetryUploadPreviewOptions = {}): Promise<TelemetryUploadPreview> {
		const eventLimit = nonNegativeInteger("maxEvents", maxEvents);
		const byteLimit = nonNegativeInteger("maxBytes", maxBytes);
		await this.flush();
		const persisted = await this._readRetainedEvents();
		const pending = this.buffer.map((event) => ({ event: redactValue(event) as TelemetryEvent, source: null }));
		const available = [...persisted, ...pending];
		const events: TelemetryEvent[] = [];
		const sourceFiles = new Set<string>();
		let byteLength = 0;
		let truncated = false;
		for (const item of available) {
			const serialized = tryJsonStringify(item.event);
			if (!serialized.ok) continue;
			const bytes = Buffer.byteLength(serialized.text, "utf-8");
			if (events.length >= eventLimit || byteLength + bytes > byteLimit) {
				truncated = true;
				break;
			}
			events.push(item.event);
			byteLength += bytes;
			if (item.source !== null) sourceFiles.add(item.source);
		}
		return {
			generatedAt: new Date(this.now()).toISOString(),
			events,
			eventCount: events.length,
			byteLength,
			truncated,
			pendingEventCount: this.buffer.length,
			sourceFiles: [...sourceFiles],
		};
	}

	private async _readRetainedEvents(): Promise<Array<{ event: TelemetryEvent; source: string }>> {
		const logPath = path.join(this.kagekoDir, TELEMETRY_FILE_NAME);
		try {
			await this._applyRetention();
		} catch {
			return [];
		}
		let entries: string[];
		try {
			entries = await fs.readdir(this.kagekoDir);
		} catch {
			return [];
		}
		const backups = entries
			.map((entry) => ({ entry, index: this._backupIndex(entry) }))
			.filter((item): item is { entry: string; index: number } => item.index !== null)
			.sort((left, right) => right.index - left.index)
			.map((item) => item.entry);
		const failed = entries.filter((entry) => FAILED_BATCH_PATTERN.test(entry)).sort();
		const ordered = [...backups, ...(entries.includes(TELEMETRY_FILE_NAME) ? [TELEMETRY_FILE_NAME] : []), ...failed];
		const events: Array<{ event: TelemetryEvent; source: string }> = [];
		for (const entry of ordered) {
			try {
				for (const event of await this._readJsonl(path.join(this.kagekoDir, entry))) {
					events.push({ event, source: entry });
				}
			} catch {
				continue;
			}
		}
		return events;
	}

	private async _readJsonl(filePath: string): Promise<TelemetryEvent[]> {
		const text = await fs.readFile(filePath, "utf-8");
		const events: TelemetryEvent[] = [];
		for (const line of text.split("\n")) {
			if (line.trim().length === 0) continue;
			const parsed = JSON.parse(line) as unknown;
			if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
				throw new TypeError("telemetry JSONL event must be an object");
			}
			events.push(redactValue(parsed) as TelemetryEvent);
		}
		return events;
	}

	async close(): Promise<void> {
		if (this._closed && this.buffer.length === 0 && this._flushPromise === null) return;
		this._closed = true;
		if (this.flushTimer) {
			clearTimeout(this.flushTimer);
			this.flushTimer = null;
		}
		await this.flush();
	}
}
