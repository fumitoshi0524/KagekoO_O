import { randomUUID } from "node:crypto";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import {
	EVENT_SCHEMA_VERSION,
	isDurableEvent,
	type DurableEvent,
	type DurableEventContext,
	type DurableEventDataMap,
	type DurableEventInput,
	type DurableEventType,
} from "@kageko/protocol";
import {
	JOURNAL_FORMAT_VERSION,
	JOURNAL_HEADER_TYPE,
	MAX_JOURNAL_BYTES,
	JournalCorruptionError,
	JournalFaultedError,
	JournalIncompatibleError,
} from "./journal-format.js";

export interface JournalHeader {
	readonly type: typeof JOURNAL_HEADER_TYPE;
	readonly formatVersion: typeof JOURNAL_FORMAT_VERSION;
	readonly eventSchemaVersion: typeof EVENT_SCHEMA_VERSION;
	readonly sessionId: string;
	readonly createdAt: number;
}

export interface JournalWriterOptions {
	readonly sessionId: string;
	readonly onAppend?: (event: DurableEvent) => void | Promise<void>;
	readonly assertOwnership?: () => void;
	readonly now?: () => number;
	readonly createId?: () => string;
}

export class JournalError extends Error {
	constructor(message: string, options?: ErrorOptions) {
		super(message, options);
		this.name = new.target.name;
	}
}

interface JournalState {
	readonly header: JournalHeader;
	readonly events: DurableEvent[];
	readonly byteSize: number;
}

/**
 * Durable, append-only event journal for one session.
 *
 * Invariants:
 * - the store, header, and every event belong to the same session;
 * - sequences are contiguous and start at one;
 * - an event is published to `onAppend` only after its line is fsynced;
 * - storage and corruption failures fault the instance and prevent further writes;
 * - caller validation failures leave the writer usable for a corrected append.
 */
export class JournalWriter {
	private static readonly pathLocks = new Map<string, Promise<unknown>>();

	readonly sessionDir: string;
	readonly journalPath: string;
	readonly sessionId: string;
	readonly onAppend?: (event: DurableEvent) => void | Promise<void>;
	private readonly _assertOwnership?: () => void;
	private readonly _now: () => number;
	private readonly _createId: () => string;
	private _initialized = false;
	private _nextSequence = 1;
	private _fileSize = 0;
	private _fault: Error | undefined;

	constructor(sessionDir: string, options: JournalWriterOptions) {
		const sessionId = options.sessionId;
		const { onAppend, assertOwnership, now = Date.now, createId = randomUUID } = options;
		if (!sessionId) {
			throw new TypeError("JournalWriter requires a non-empty sessionId");
		}
		this.sessionDir = path.resolve(sessionDir);
		this.journalPath = path.join(this.sessionDir, "journal.jsonl");
		this.sessionId = sessionId;
		this.onAppend = onAppend;
		this._assertOwnership = assertOwnership;
		this._now = now;
		this._createId = createId;
	}

	get fault(): Error | undefined {
		return this._fault;
	}

	get failure(): Error | undefined {
		return this._fault;
	}

	async append<K extends DurableEventType>(input: DurableEventInput<K>): Promise<DurableEvent<K>>;
	async append(events: readonly DurableEvent[]): Promise<void>;
	async append(inputOrEvents: DurableEventInput | readonly DurableEvent[]): Promise<DurableEvent | void> {
		if (Array.isArray(inputOrEvents)) {
			await this.appendEvents(inputOrEvents);
			return;
		}
		const events = await this._runPathLocked(() => this._appendUnlocked([inputOrEvents as DurableEventInput]));
		return events[0];
	}

	async appendMany(inputs: readonly DurableEventInput[]): Promise<DurableEvent[]> {
		if (inputs.length === 0) return [];
		return this._runPathLocked(() => this._appendUnlocked(inputs));
	}

	async appendEvents(events: readonly DurableEvent[]): Promise<void> {
		if (events.length === 0) return;
		await this._runPathLocked(() => this._appendUnlocked(events));
	}

	async appendInputs(
		inputs: readonly DurableEventInput[],
		_options: { now?: () => number; createId?: () => string } = {},
	): Promise<readonly DurableEvent[]> {
		return this._runPathLocked(() => this._appendUnlocked(inputs, _options));
	}

	async load(): Promise<DurableEvent[]> {
		return this._runPathLocked(async () => {
			const state = await this._readState();
			this._initialized = state !== undefined;
			this._fileSize = state?.byteSize ?? 0;
			this._nextSequence = (state?.events.length ?? 0) + 1;
			return state?.events ?? [];
		});
	}

	/**
	 * Explicitly deletes this journal and clears the local fault latch.
	 * Callers must treat this as destructive recovery, not normal rotation.
	 */
	async clear(): Promise<void> {
		return this._runPathLocked(async () => {
			try {
				await fs.unlink(this.journalPath);
			} catch (error) {
				if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
					throw error;
				}
			}
			this._initialized = false;
			this._nextSequence = 1;
			this._fileSize = 0;
			this._fault = undefined;
		});
	}

	private async _initializeForWrite(): Promise<void> {
		if (this._initialized) {
			return;
		}
		await fs.mkdir(this.sessionDir, { recursive: true, mode: 0o700 });
		const state = await this._readState();
		if (state) {
			this._initialized = true;
			this._fileSize = state.byteSize;
			this._nextSequence = state.events.length + 1;
			return;
		}

		const header: JournalHeader = {
			type: JOURNAL_HEADER_TYPE,
			formatVersion: JOURNAL_FORMAT_VERSION,
			eventSchemaVersion: EVENT_SCHEMA_VERSION,
			sessionId: this.sessionId,
			createdAt: this._now(),
		};
		const content = serializeLine(header);
		const temporaryPath = `${this.journalPath}.${process.pid}.${this._createId()}.tmp`;
		let handle: fs.FileHandle | undefined;
		try {
			handle = await fs.open(temporaryPath, "wx");
			await handle.writeFile(content, "utf8");
			await handle.sync();
			await handle.close();
			handle = undefined;
			// Linking a fully fsynced temporary file is an atomic, no-overwrite
			// publication step on both POSIX and Windows. Unlike rename on POSIX,
			// it cannot replace a journal created concurrently by another process.
			await fs.link(temporaryPath, this.journalPath);
			await fs.unlink(temporaryPath);
		} catch (error) {
			await handle?.close().catch(() => {});
			await fs.unlink(temporaryPath).catch(() => {});
			if ((error as NodeJS.ErrnoException).code === "EEXIST") {
				const racedState = await this._readState();
				if (racedState) {
					this._initialized = true;
					this._fileSize = racedState.byteSize;
					this._nextSequence = racedState.events.length + 1;
					return;
				}
			}
			throw error;
		}
		this._initialized = true;
		this._fileSize = Buffer.byteLength(content, "utf8");
		this._nextSequence = 1;
	}

	private async _readState(): Promise<JournalState | undefined> {
		let stat;
		try {
			stat = await fs.stat(this.journalPath);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") {
				return undefined;
			}
			throw error;
		}
		if (stat.size === 0) {
			throw new JournalCorruptionError(`Session journal is empty: ${this.journalPath}`);
		}
		if (stat.size > MAX_JOURNAL_BYTES) {
			throw new JournalError(`Session journal exceeds ${MAX_JOURNAL_BYTES} bytes`);
		}

		const text = await fs.readFile(this.journalPath, "utf8");
		if (!text.endsWith("\n")) {
			throw new JournalCorruptionError(`Session journal has an incomplete final line: ${this.journalPath}`);
		}
		const lines = text.slice(0, -1).split("\n");
		if (lines.length === 0 || lines[0] === "") {
			throw new JournalCorruptionError(`Session journal header is missing: ${this.journalPath}`);
		}

		const header = parseJsonLine(lines[0]!, 1);
		assertCompatibleHeader(header, this.sessionId);

		const events: DurableEvent[] = [];
		const eventIds = new Set<string>();
		for (let index = 1; index < lines.length; index += 1) {
			const lineNumber = index + 1;
			const line = lines[index]!;
			if (line === "") {
				throw new JournalCorruptionError(`Blank line at ${this.journalPath}:${lineNumber}`);
			}
			const value = parseJsonLine(line, lineNumber);
			if (!isDurableEvent(value)) {
				throw new JournalCorruptionError(`Invalid durable event at ${this.journalPath}:${lineNumber}`);
			}
			const expectedSequence = index;
			if (value.meta.sequence !== expectedSequence) {
				throw new JournalCorruptionError(
					`Non-contiguous sequence at ${this.journalPath}:${lineNumber}; expected ${expectedSequence}, got ${value.meta.sequence}`,
				);
			}
			if (value.meta.sessionId !== this.sessionId) {
				throw new JournalCorruptionError(
					`Event session mismatch at ${this.journalPath}:${lineNumber}; expected ${this.sessionId}, got ${value.meta.sessionId}`,
				);
			}
			if (eventIds.has(value.meta.eventId)) {
				throw new JournalCorruptionError(`Duplicate eventId at ${this.journalPath}:${lineNumber}`);
			}
			eventIds.add(value.meta.eventId);
			events.push(value);
		}
		return { header, events, byteSize: stat.size };
	}

	private async _appendUnlocked(
		inputs: readonly (DurableEventInput | DurableEvent)[],
		options: { now?: () => number; createId?: () => string } = {},
	): Promise<DurableEvent[]> {
		this._assertWritable();
		try {
			await this._initializeForWrite();
			const events = inputs.map((input, index) =>
				isDurableEvent(input)
					? input
					: this._materialize(
							input,
							this._nextSequence + index,
							options.now ?? this._now,
							options.createId ?? this._createId,
						),
			);
			for (let index = 0; index < events.length; index += 1) {
				if (!isDurableEvent(events[index])) {
					throw new JournalError(`Invalid durable event payload for ${inputs[index]?.type ?? "unknown"}`);
				}
				const event = events[index]!;
				if (event.meta.sequence !== this._nextSequence + index)
					throw new JournalError("Journal event sequence mismatch");
				if (event.meta.sessionId !== this.sessionId) throw new JournalError("Journal event session mismatch");
			}
			const content = events.map((event) => serializeLine(event)).join("");
			const contentBytes = Buffer.byteLength(content, "utf8");
			if (this._fileSize + contentBytes > MAX_JOURNAL_BYTES) {
				throw new JournalError(`Session journal would exceed ${MAX_JOURNAL_BYTES} bytes`);
			}

			const handle = await fs.open(this.journalPath, "a");
			try {
				await handle.writeFile(content, "utf8");
				await handle.sync();
			} finally {
				await handle.close();
			}

			this._fileSize += contentBytes;
			this._nextSequence += events.length;
			for (const event of events) {
				await this._notify(event);
			}
			return events;
		} catch (error) {
			const normalized = asError(error);
			if (shouldLatchFault(normalized)) this._fault = normalized;
			throw normalized;
		}
	}

	private _materialize<K extends DurableEventType>(
		input: DurableEventInput<K>,
		sequence = this._nextSequence,
		now = this._now,
		createId = this._createId,
	): DurableEvent<K> {
		const timestamp = now();
		const context: DurableEventContext = input.meta ?? {};
		return {
			type: input.type,
			meta: {
				schemaVersion: EVENT_SCHEMA_VERSION,
				eventId: createId(),
				sequence,
				sessionId: this.sessionId,
				occurredAt: context.occurredAt ?? timestamp,
				recordedAt: timestamp,
				...(context.turnId === undefined ? {} : { turnId: context.turnId }),
				...(context.stepId === undefined ? {} : { stepId: context.stepId }),
				...(context.toolCallId === undefined ? {} : { toolCallId: context.toolCallId }),
				...(context.causationId === undefined ? {} : { causationId: context.causationId }),
				...(context.correlationId === undefined ? {} : { correlationId: context.correlationId }),
				...(context.activityId === undefined ? {} : { activityId: context.activityId }),
				...(context.parentActivityId === undefined ? {} : { parentActivityId: context.parentActivityId }),
				...(context.parentToolCallId === undefined ? {} : { parentToolCallId: context.parentToolCallId }),
				...(context.actorId === undefined ? {} : { actorId: context.actorId }),
				...(context.timelineId === undefined ? {} : { timelineId: context.timelineId }),
			},
			data: input.data as Readonly<DurableEventDataMap[K]>,
		} as DurableEvent<K>;
	}

	private async _notify(event: DurableEvent): Promise<void> {
		if (!this.onAppend) {
			return;
		}
		try {
			await this.onAppend(event);
		} catch {
			/* persistence already succeeded; observers are best-effort */
		}
	}

	private _assertWritable(): void {
		this._assertOwnership?.();
		if (this._fault) {
			throw new JournalFaultedError("Session journal is faulted; refusing further writes", { cause: this._fault });
		}
	}

	private _runPathLocked<T>(operation: () => Promise<T>): Promise<T> {
		// Windows paths are case-insensitive; POSIX paths are not. Normalizing
		// case unconditionally would serialize unrelated journals and can hide
		// path identity bugs in tests and tooling running on Linux/macOS.
		const key = process.platform === "win32" ? this.journalPath.toLowerCase() : this.journalPath;
		const prior = JournalWriter.pathLocks.get(key) ?? Promise.resolve();
		const result = prior.then(operation, operation);
		const settled = result.then(
			() => undefined,
			() => undefined,
		);
		JournalWriter.pathLocks.set(key, settled);
		void settled.finally(() => {
			if (JournalWriter.pathLocks.get(key) === settled) {
				JournalWriter.pathLocks.delete(key);
			}
		});
		return result;
	}
}

function serializeLine(value: unknown): string {
	let serialized: string | undefined;
	try {
		serialized = JSON.stringify(value);
	} catch (error) {
		throw new JournalError("Session journal event is not JSON serializable", { cause: error });
	}
	if (serialized === undefined) {
		throw new JournalError("Session journal event is not JSON serializable");
	}
	return `${serialized}\n`;
}

function parseJsonLine(line: string, lineNumber: number): unknown {
	try {
		return JSON.parse(line);
	} catch (error) {
		throw new JournalCorruptionError(`Invalid JSON at session journal line ${lineNumber}`, { cause: error });
	}
}

function assertCompatibleHeader(value: unknown, sessionId: string): asserts value is JournalHeader {
	if (!isObject(value) || value["type"] !== JOURNAL_HEADER_TYPE) {
		throw new JournalIncompatibleError("Session journal does not contain a Kageko journal header");
	}
	if (value["formatVersion"] !== JOURNAL_FORMAT_VERSION) {
		throw new JournalIncompatibleError(
			`Unsupported journal format version ${String(value["formatVersion"])}; expected ${JOURNAL_FORMAT_VERSION}`,
		);
	}
	if (value["eventSchemaVersion"] !== EVENT_SCHEMA_VERSION) {
		throw new JournalIncompatibleError(
			`Unsupported event schema version ${String(value["eventSchemaVersion"])}; expected ${EVENT_SCHEMA_VERSION}`,
		);
	}
	if (value["sessionId"] !== sessionId) {
		throw new JournalIncompatibleError(
			`Journal belongs to session ${String(value["sessionId"])}, not requested session ${sessionId}`,
		);
	}
	if (typeof value["createdAt"] !== "number" || !Number.isFinite(value["createdAt"])) {
		throw new JournalCorruptionError("Session journal header has an invalid createdAt");
	}
}

function isObject(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asError(error: unknown): Error {
	return error instanceof Error ? error : new Error(String(error));
}

function shouldLatchFault(error: Error): boolean {
	if (error instanceof JournalCorruptionError || error instanceof JournalIncompatibleError) return true;
	return typeof (error as NodeJS.ErrnoException).code === "string";
}
