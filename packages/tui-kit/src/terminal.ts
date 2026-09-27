import { EventEmitter } from "node:events";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const cjsRequire = createRequire(import.meta.url);
const ESCAPE_FLUSH_TIMEOUT_MS = 12;
const PROTOCOL_REPLY_FLUSH_TIMEOUT_MS = 150;

export const TERMINAL_FOCUS_IN = "\x1b[I";
export const TERMINAL_FOCUS_OUT = "\x1b[O";
export const ENABLE_TERMINAL_FOCUS_REPORTING = "\x1b[?1004h";
export const DISABLE_TERMINAL_FOCUS_REPORTING = "\x1b[?1004l";

/**
 * Candidate locations of the win32 console-mode helper relative to the built
 * module and the executable. In the npm/workspace layout `native/` sits next
 * to `dist/` (first candidate); compiled-binary archives copy `native/` next
 * to the executable (last candidate). Ported from pi-tui's terminal.ts loader.
 */
export function win32ConsoleModeCandidates(moduleDir: string, execPath: string): string[] {
	const nativeDirectory = path.join("native", "win32", "prebuilds", `win32-${process.arch}`);
	const nativePath = path.join(nativeDirectory, "win32-console-mode.node");
	return [
		path.join(moduleDir, "..", nativePath),
		path.join(moduleDir, nativePath),
		path.join(path.dirname(execPath), nativePath),
	];
}

export interface TerminalSize {
	readonly columns: number;
	readonly rows: number;
}

export type KeyName =
	| "up"
	| "down"
	| "left"
	| "right"
	| "home"
	| "end"
	| "delete"
	| "pageup"
	| "pagedown"
	| "wheelup"
	| "wheeldown"
	| "mouse"
	| "enter"
	| "newline"
	| "escape"
	| "tab"
	| "shift-tab"
	| "backspace"
	| "f1"
	| "f2"
	| "f3"
	| "f4"
	| "f5"
	| "f6"
	| "f7"
	| "f8"
	| "f9"
	| "f10"
	| "f11"
	| "f12"
	| "ctrl-a"
	| "ctrl-c"
	| "ctrl-d"
	| "ctrl-g"
	| "ctrl-o"
	| "ctrl-t"
	| "ctrl-z"
	| "ctrl-w"
	| "ctrl-u"
	| "ctrl-k"
	| "ctrl-y"
	| "undo"
	| "alt-backspace"
	| "alt-d"
	| "alt-y"
	| "alt-left"
	| "alt-right"
	| "unknown";
export type KeyEventType = "press" | "repeat" | "release";
export type MouseAction = "press" | "release" | "move" | "wheel";
export interface MouseInput {
	/** Terminal coordinates are one-based, matching SGR/X10 reports. */
	readonly col: number;
	readonly row: number;
	readonly action: MouseAction;
	/** 0=left, 1=middle, 2=right, 3=release/unknown; wheel keeps the raw code. */
	readonly button: number;
	readonly shift: boolean;
	readonly meta: boolean;
	readonly ctrl: boolean;
}
export interface KeyModifiers {
	readonly shift?: boolean;
	readonly alt?: boolean;
	readonly ctrl?: boolean;
}
export interface KeyInput {
	readonly name: KeyName;
	readonly text?: string;
	readonly sequence: string;
	readonly mouse?: MouseInput;
	readonly eventType?: KeyEventType;
	readonly modifiers?: KeyModifiers;
}

export interface TerminalPort {
	readonly isTTY: boolean | undefined;
	readonly isRaw?: boolean;
	readonly columns: number | undefined;
	readonly rows: number | undefined;
	write(value: string): boolean;
	on(event: "data" | "resize", listener: (...args: unknown[]) => void): unknown;
	off(event: "data" | "resize", listener: (...args: unknown[]) => void): unknown;
	setRawMode?(enabled: boolean): void;
	resume?(): void;
	pause?(): void;
}

/** Owns raw input plus one in-place terminal TUI lifecycle, like pi-tui. */
export class TerminalController extends EventEmitter {
	private started = false;
	private wasRaw = false;
	// A final stop invalidates temporary external-editor/shell leases. A lease
	// may restore the terminal only if no final stop happened while it awaited.
	private generation = 0;
	private readonly decoder = new InputDecoder();
	private kittyProtocolActive = false;
	private kittyProtocolPushed = false;
	private modifyOtherKeysActive = false;
	private terminalFocused = true;
	private focusInputBuffer = "";
	private readonly focusDecoder = new TextDecoder();
	private flushTimer: ReturnType<typeof setTimeout> | undefined;
	private readonly onData = (chunk: Buffer | string): void => {
		// Node's TTY stream can deliver either strings or raw Buffers. Preserve
		// Buffer chunks until TextDecoder has seen the complete UTF-8 sequence;
		// String(Buffer) would turn bytes such as 😀 into "240,159,152,128".
		const decodedChunk = this.focusDecoder.decode(typeof chunk === "string" ? Buffer.from(chunk) : chunk, {
			stream: true,
		});
		const focus = consumeFocusReports(this.focusInputBuffer + decodedChunk);
		this.focusInputBuffer = focus.remainder;
		for (const focused of focus.events) {
			this.terminalFocused = focused;
			this.emit("focus", focused);
		}
		if (focus.data) this.emitDecoded(this.decoder.push(focus.data));
		// A bare Escape is ambiguous with the beginning of a terminal control
		// sequence, so it flushes after a short timer. An open (or potentially
		// opening) bracketed paste is exempt: it waits indefinitely for its
		// terminator and must never be force-flushed (pi-tui parity).
		const flushTimeout = this.decoder.pendingFlushTimeoutMs();
		const pendingFocusFlushTimeout = this.focusInputBuffer ? ESCAPE_FLUSH_TIMEOUT_MS : undefined;
		if (flushTimeout !== undefined || pendingFocusFlushTimeout !== undefined) {
			if (this.flushTimer) clearTimeout(this.flushTimer);
			this.flushTimer = setTimeout(() => {
				this.flushTimer = undefined;
				if (this.focusInputBuffer) {
					const pendingFocusPrefix = this.focusInputBuffer;
					this.focusInputBuffer = "";
					this.emitDecoded(this.decoder.push(pendingFocusPrefix));
				}
				this.emitDecoded(this.decoder.flush());
			}, flushTimeout ?? pendingFocusFlushTimeout);
		} else if (this.flushTimer) {
			clearTimeout(this.flushTimer);
			this.flushTimer = undefined;
		}
	};
	private readonly onResize = (): void => {
		this.emit("resize", this.size());
	};

	constructor(
		private readonly input: TerminalPort,
		private readonly output: TerminalPort,
	) {
		super();
	}
	size(): TerminalSize {
		return { columns: Math.max(1, this.output.columns ?? 80), rows: Math.max(1, this.output.rows ?? 24) };
	}
	isFocused(): boolean {
		return this.terminalFocused;
	}

	start(): void {
		if (this.started) return;
		if (!this.input.isTTY || !this.output.isTTY)
			throw new Error("Interactive terminal UI requires TTY input and output");
		this.wasRaw = this.input.isRaw ?? false;
		this.started = true;
		try {
			this.input.setRawMode?.(true);
			// Must run AFTER setRawMode(true), which resets console mode flags
			// (pi-tui parity, helper ported from pi-tui — same author lineage).
			this.enableWindowsVTInput();
			this.input.resume?.();
			this.output.write(
				`${ENABLE_TERMINAL_FOCUS_REPORTING}\x1b[?2004h\x1b[?25l\x1b[>7u\x1b[?u\x1b[c`,
			);
			this.terminalFocused = true;
			this.focusInputBuffer = "";
			// The push is tracked unconditionally: the pop must be emitted even
			// when the terminal's reply is missed or reports flags=0 (pi-tui parity).
			this.kittyProtocolPushed = true;
			this.input.on("data", this.onData as never);
			this.output.on("resize", this.onResize as never);
			// SIGWINCH can be lost while the process is suspended. Match pi-tui by
			// forcing one fresh size notification after ownership is established.
			if (process.platform !== "win32") {
				try {
					process.kill(process.pid, "SIGWINCH");
				} catch {
					// Some embedded hosts do not permit self-signalling; the listener
					// above still handles ordinary terminal resize events.
				}
			}
		} catch (error) {
			this.stop();
			throw error;
		}
	}

	stop(): void {
		this.generation += 1;
		this.release(true);
	}

	/**
	 * On Windows, add ENABLE_VIRTUAL_TERMINAL_INPUT after setRawMode so the
	 * console sends VT sequences for modified keys such as Shift+Tab.
	 */
	private enableWindowsVTInput(): void {
		if (process.platform !== "win32") return;
		try {
			const arch = process.arch;
			if (arch !== "x64" && arch !== "arm64") return;

			// Dynamic require keeps non-Windows and bundled/browser paths independent
			// of the optional native helper.
			const moduleDir = path.dirname(fileURLToPath(import.meta.url));
			for (const modulePath of win32ConsoleModeCandidates(moduleDir, process.execPath)) {
				try {
					const helper = cjsRequire(modulePath) as { enableVirtualTerminalInput?: () => boolean };
					helper.enableVirtualTerminalInput?.();
					return;
				} catch {
					// Try the next possible packaging location.
				}
			}
		} catch {
			// Native helper not available — VT input cannot be enabled here.
		}
	}

	private release(final = false): void {
		if (!this.started) return;
		const kittyProtocolPushed = this.kittyProtocolPushed || this.kittyProtocolActive;
		const modifyOtherKeysActive = this.modifyOtherKeysActive;
		this.started = false;
		if (this.flushTimer) clearTimeout(this.flushTimer);
		this.flushTimer = undefined;
		this.decoder.reset();
		this.focusDecoder.decode();
		this.focusInputBuffer = "";
		this.terminalFocused = true;
		this.kittyProtocolActive = false;
		this.kittyProtocolPushed = false;
		this.modifyOtherKeysActive = false;
		// Cleanup must be best effort and complete: one failing stream operation
		// must not leave raw mode, paste mode, or cursor visibility owned.
		attempt(() => this.input.off("data", this.onData as never));
		attempt(() => this.output.off("resize", this.onResize as never));
		attempt(() => this.input.pause?.());
		attempt(() => this.input.setRawMode?.(this.wasRaw));
		attempt(() =>
			this.output.write(
				`${DISABLE_TERMINAL_FOCUS_REPORTING}\x1b[?2004l${kittyProtocolPushed ? "\x1b[<u" : ""}${modifyOtherKeysActive ? "\x1b[>4;0m" : ""}\x1b[0m\x1b[?25h${final ? "\r\n" : ""}`,
			),
		);
	}

	async withTerminal<T>(operation: () => Promise<T>): Promise<T> {
		const wasStarted = this.started;
		const lease = this.generation;
		if (wasStarted) this.release();
		try {
			return await operation();
		} finally {
			if (wasStarted && this.generation === lease) {
				this.start();
				this.emit("resize", this.size());
			}
		}
	}

	/** Let already-buffered key releases drain before ownership is returned. */
	async drainInput(maxMs = 1000, idleMs = 50): Promise<void> {
		if (!this.started) return;
		const listener = this.onData;
		if (this.flushTimer) clearTimeout(this.flushTimer);
		this.flushTimer = undefined;
		attempt(() => this.input.off("data", listener as never));
		let idleTimer: ReturnType<typeof setTimeout> | undefined;
		let maxTimer: ReturnType<typeof setTimeout> | undefined;
		let resolveDrain!: () => void;
		const finish = () => {
			if (idleTimer) clearTimeout(idleTimer);
			if (maxTimer) clearTimeout(maxTimer);
			resolveDrain?.();
		};
		const drainListener = () => {
			if (idleTimer) clearTimeout(idleTimer);
			idleTimer = setTimeout(finish, idleMs);
		};
		this.input.on("data", drainListener as never);
		try {
			if (this.kittyProtocolPushed || this.kittyProtocolActive) attempt(() => this.output.write("\x1b[<u"));
			this.kittyProtocolPushed = false;
			this.kittyProtocolActive = false;
			await new Promise<void>((resolve) => {
				resolveDrain = resolve;
				idleTimer = setTimeout(finish, idleMs);
				maxTimer = setTimeout(finish, maxMs);
			});
		} finally {
			attempt(() => this.input.off("data", drainListener as never));
			if (this.started) this.input.on("data", listener as never);
		}
	}

	private emitDecoded(keys: readonly KeyInput[]): void {
		if (!keys.length) return;
		const protocolKeys = keys.filter((key) => isProtocolReply(key.sequence));
		for (const key of protocolKeys) {
			const kittyFlags = /^\x1b\[\?([0-9]+)u$/.exec(key.sequence);
			if (kittyFlags) {
				this.kittyProtocolActive = Number(kittyFlags[1]) > 0;
				if (this.kittyProtocolActive) {
					// A kitty-capable terminal answered: undo any fallback the DA
					// sentinel enabled first (pi-tui parity).
					if (this.modifyOtherKeysActive) {
						attempt(() => this.output.write("\x1b[>4;0m"));
						this.modifyOtherKeysActive = false;
					}
				} else if (!this.modifyOtherKeysActive) {
					// Kitty unsupported (e.g. Windows Terminal): fall back to
					// modifyOtherKeys so Shift+Enter/newline still decodes (pi-tui parity).
					attempt(() => this.output.write("\x1b[>4;2m"));
					this.modifyOtherKeysActive = true;
				}
				continue;
			}
			if (/^\x1b\[\?[0-9;]+c$/.test(key.sequence)) {
				// Device-attributes reply to the trailing "\x1b[c" sentinel: a
				// terminal that knows kitty answers the flags query instead, so a
				// DA reply without kitty active means kitty is unsupported.
				if (!this.kittyProtocolActive && !this.modifyOtherKeysActive) {
					attempt(() => this.output.write("\x1b[>4;2m"));
					this.modifyOtherKeysActive = true;
				}
				continue;
			}
			if (key.sequence.includes(">4;")) this.modifyOtherKeysActive = true;
		}
		const userKeys = keys
			.filter((key) => !protocolKeys.includes(key))
			.map((key) =>
				this.kittyProtocolActive && key.sequence === "\n" && key.name === "enter"
					? ({ ...key, name: "newline", modifiers: { shift: true } } satisfies KeyInput)
					: key,
			);
		if (userKeys.length) this.emit("input", userKeys);
	}
}

/** Stateful decoder: terminal sequences are allowed to arrive in arbitrary chunks. */
export class InputDecoder {
	private buffer = "";
	private utf8 = new TextDecoder();
	private pendingKittyPrintableCodepoint: number | undefined;
	push(chunk: string | Uint8Array): readonly KeyInput[] {
		this.buffer += typeof chunk === "string" ? chunk : this.utf8.decode(chunk, { stream: true });
		return this.drain(false);
	}
	flush(): readonly KeyInput[] {
		this.buffer += this.utf8.decode();
		return this.drain(true);
	}
	hasPending(): boolean {
		return this.buffer.length > 0;
	}
	needsEscapeFlush(): boolean {
		return this.buffer === "\x1b";
	}
	pendingFlushTimeoutMs(): number | undefined {
		if (!this.needsPendingFlush()) return undefined;
		return this.isProtocolReplyPrefix() ? PROTOCOL_REPLY_FLUSH_TIMEOUT_MS : ESCAPE_FLUSH_TIMEOUT_MS;
	}
	/**
	 * Incomplete escape sequences share one short ambiguity timeout, but an open
	 * (or potentially opening) bracketed paste waits indefinitely for its
	 * terminator — a chunked paste must never be force-flushed (pi-tui parity).
	 */
	needsPendingFlush(): boolean {
		if (!this.buffer.startsWith("\x1b")) return false;
		if (this.buffer.length > 1 && ("\x1b[200~".startsWith(this.buffer) || this.buffer.startsWith("\x1b[200~")))
			return false;
		return true;
	}
	private isProtocolReplyPrefix(): boolean {
		return /^\x1b\[\?(?:[0-9;]*)$/.test(this.buffer);
	}
	reset(): void {
		this.buffer = "";
		this.utf8 = new TextDecoder();
		this.pendingKittyPrintableCodepoint = undefined;
	}

	private drain(force: boolean): readonly KeyInput[] {
		const output: KeyInput[] = [];
		while (this.buffer) {
			const paste = this.readPaste(force);
			if (paste === "wait") break;
			if (paste) {
				output.push(paste);
				continue;
			}
			const mouse = readMouseSequence(this.buffer, force);
			if (mouse === "wait") break;
			if (mouse) {
				this.buffer = this.buffer.slice(mouse.sequence.length);
				output.push(mouse);
				continue;
			}
			const known = matchKnown(this.buffer);
			if (known === "wait" && !force) break;
			if (known && known !== "wait") {
				this.buffer = this.buffer.slice(known.sequence.length);
				output.push(known);
				continue;
			}
			if (this.buffer.startsWith("\x1b")) {
				// WezTerm can concatenate a raw Escape press with the Kitty
				// Escape-release CSI-u sequence. Do not classify ESC+ESC as Alt+
				// Escape when the second byte starts another terminal sequence.
				if (this.buffer.startsWith("\x1b\x1b") && /^[\[\]OP_^]/.test(this.buffer[2] ?? "")) {
					output.push({ name: "escape", sequence: "\x1b" });
					this.buffer = this.buffer.slice(1);
					continue;
				}
				if (!force && isEscapePrefix(this.buffer)) break;
				const sequence = readEscapeSequence(this.buffer);
				const decoded = decodeEscapeKey(sequence);
				if (decoded) {
					if (decoded.text) this.pendingKittyPrintableCodepoint = decoded.text.codePointAt(0);
					output.push(decoded);
				} else output.push({ name: sequence === "\x1b" ? "escape" : "unknown", sequence });
				this.buffer = this.buffer.slice(sequence.length);
				continue;
			}
			const character = Array.from(this.buffer)[0]!;
			this.buffer = this.buffer.slice(character.length);
			const codepoint = character.codePointAt(0);
			if (this.pendingKittyPrintableCodepoint === codepoint) {
				this.pendingKittyPrintableCodepoint = undefined;
				continue;
			}
			this.pendingKittyPrintableCodepoint = undefined;
			output.push({ name: "unknown", text: character, sequence: character });
		}
		return output;
	}

	private readPaste(force: boolean): KeyInput | undefined | "wait" {
		const start = "\x1b[200~";
		const end = "\x1b[201~";
		if (!this.buffer.startsWith(start)) return undefined;
		const endIndex = this.buffer.indexOf(end, start.length);
		if (endIndex < 0) {
			if (!force) return "wait";
			const sequence = this.buffer;
			this.buffer = "";
			return { name: "unknown", text: normalizePaste(sequence.slice(start.length)), sequence };
		}
		const sequence = this.buffer.slice(0, endIndex + end.length);
		this.buffer = this.buffer.slice(sequence.length);
		return { name: "unknown", text: normalizePaste(sequence.slice(start.length, -end.length)), sequence };
	}
}

export function decodeInput(sequence: string): readonly KeyInput[] {
	const decoder = new InputDecoder();
	return [...decoder.push(sequence), ...decoder.flush()];
}

function matchKnown(buffer: string): KeyInput | "wait" | undefined {
	const entries: readonly [string, KeyName][] = [
		["\u0001", "ctrl-a"],
		["\u0003", "ctrl-c"],
		["\u0004", "ctrl-d"],
		["\u0007", "ctrl-g"],
		["\u000f", "ctrl-o"],
		["\u0014", "ctrl-t"],
		["\u001a", "ctrl-z"],
		["\u0017", "ctrl-w"],
		["\u0015", "ctrl-u"],
		["\u000b", "ctrl-k"],
		["\u0019", "ctrl-y"],
		["\u001f", "undo"],
		["\r", "enter"],
		["\n", "enter"],
		["\t", "tab"],
		["\u007f", "backspace"],
		["\u0008", "backspace"],
		["\x1b\r", "newline"],
		["\x1bOM", "enter"],
		["\x1b[A", "up"],
		["\x1b[B", "down"],
		["\x1b[C", "right"],
		["\x1b[D", "left"],
		["\x1bOA", "up"],
		["\x1bOB", "down"],
		["\x1bOC", "right"],
		["\x1bOD", "left"],
		["\x1b[H", "home"],
		["\x1b[F", "end"],
		["\x1bOH", "home"],
		["\x1bOF", "end"],
		["\x1b[Z", "shift-tab"],
		["\x1b[3~", "delete"],
		["\x1b[5~", "pageup"],
		["\x1b[6~", "pagedown"],
		["\x1bOP", "f1"],
		["\x1bOQ", "f2"],
		["\x1bOR", "f3"],
		["\x1bOS", "f4"],
		["\x1b[15~", "f5"],
		["\x1b[17~", "f6"],
		["\x1b[18~", "f7"],
		["\x1b[19~", "f8"],
		["\x1b[20~", "f9"],
		["\x1b[21~", "f10"],
		["\x1b[23~", "f11"],
		["\x1b[24~", "f12"],
		["\x1b[12~", "f2"],
	];
	for (const [sequence, name] of entries) {
		if (buffer.startsWith(sequence)) return take(sequence, name);
		if (sequence.startsWith(buffer)) return "wait";
	}
	return undefined;
}

function readMouseSequence(value: string, force: boolean): KeyInput | "wait" | undefined {
	if (value.startsWith("\x1b[<")) {
		const end = value.search(/[Mm]/);
		if (end < 0) return force ? { name: "unknown", sequence: value } : "wait";
		const sequence = value.slice(0, end + 1);
		const parts = sequence.slice(3, -1).split(";");
		const code = Number(parts[0]);
		const col = Number(parts[1]);
		const row = Number(parts[2]);
		if (![code, col, row].every(Number.isFinite) || col < 1 || row < 1) return { name: "unknown", sequence };
		return mouseInput(code, col, row, sequence.at(-1) === "m", sequence);
	}
	if (value.startsWith("\x1b[M")) {
		if (value.length < 6) return force ? { name: "unknown", sequence: value } : "wait";
		const sequence = value.slice(0, 6);
		const code = value.charCodeAt(3) - 32;
		const col = value.charCodeAt(4) - 32;
		const row = value.charCodeAt(5) - 32;
		return mouseInput(code, col, row, false, sequence);
	}
	return undefined;
}

function mouseInput(code: number, col: number, row: number, released: boolean, sequence: string): KeyInput {
	const shift = Boolean(code & 4);
	const meta = Boolean(code & 8);
	const ctrl = Boolean(code & 16);
	if (code & 64) {
		const mouse: MouseInput = { action: "wheel", button: code, col, row, shift, meta, ctrl };
		return { name: code & 1 ? "wheeldown" : "wheelup", mouse, sequence };
	}
	const motion = Boolean(code & 32);
	const mouse: MouseInput = {
		action: motion ? "move" : released || (code & 3) === 3 ? "release" : "press",
		button: code & 3,
		col,
		row,
		shift,
		meta,
		ctrl,
	};
	return { name: "mouse", mouse, sequence };
}

function take(sequence: string, name: KeyName): KeyInput {
	return { name, sequence };
}

function decodeEscapeKey(sequence: string): KeyInput | undefined {
	if (sequence === "\x1b[Z") return { name: "shift-tab", sequence };
	const alt = /^\x1b([\x7f\x08bBfFdDyY])$/.exec(sequence);
	if (alt) {
		const names: Record<string, KeyName> = {
			"\x7f": "alt-backspace",
			"\x08": "alt-backspace",
			b: "alt-left",
			B: "alt-left",
			f: "alt-right",
			F: "alt-right",
			d: "alt-d",
			D: "alt-d",
			y: "alt-y",
			Y: "alt-y",
		};
		return { name: names[alt[1]!]!, sequence };
	}
	const arrow = /^\x1b\[1;(\d+)(?::(\d+))?([ABCDHF])$/.exec(sequence);
	if (arrow) {
		const names: Record<string, KeyName> = { A: "up", B: "down", C: "right", D: "left", H: "home", F: "end" };
		const modifiers = kittyModifiers(Number(arrow[1]));
		return {
			name: names[arrow[3]!]!,
			sequence,
			eventType: kittyEventType(arrow[2]),
			...(modifiers ? { modifiers } : {}),
		};
	}
	const kitty = /^\x1b\[([0-9]+)(?::([0-9]+))?(?::([0-9]+))?(?:;(\d+)(?::(\d+))?)?u$/.exec(sequence);
	if (kitty) {
		const modifierValue = Number(kitty[4] ?? "1");
		const codepoint = ((modifierValue - 1) & 1) !== 0 && kitty[2] ? Number(kitty[2]) : Number(kitty[1]);
		return decodeKittyCodepoint(codepoint, modifierValue, kitty[5], sequence);
	}
	const modifyOtherKeys = /^\x1b\[27;(\d+);([0-9]+)~$/.exec(sequence);
	if (modifyOtherKeys)
		return decodeKittyCodepoint(Number(modifyOtherKeys[2]), Number(modifyOtherKeys[1]), undefined, sequence);
	const functional = /^\x1b\[([0-9]+);(\d+)(?::(\d+))?~$/.exec(sequence);
	if (functional) {
		const names: Record<number, KeyName> = {
			3: "delete",
			11: "f1",
			12: "f2",
			13: "f3",
			14: "f4",
			15: "f5",
			17: "f6",
			18: "f7",
			19: "f8",
			20: "f9",
			21: "f10",
			23: "f11",
			24: "f12",
		};
		const name = names[Number(functional[1])];
		if (name) {
			const modifiers = kittyModifiers(Number(functional[2]));
			return { name, sequence, eventType: kittyEventType(functional[3]), ...(modifiers ? { modifiers } : {}) };
		}
	}
	return undefined;
}

function decodeKittyCodepoint(
	codepoint: number,
	modifierValue: number,
	event: string | undefined,
	sequence: string,
): KeyInput {
	// Kitty includes Caps Lock and Num Lock in the modifier bitset. They do not
	// change key identity and must not turn keypad Enter/navigation into unknown
	// input. This matches pi-tui's lock-mask normalization.
	const modifiers = (modifierValue - 1) & ~(64 | 128);
	const keyModifiers = kittyModifiers(modifierValue);
	const eventType = kittyEventType(event);
	const special: Record<number, KeyName> = {
		9: "tab",
		13: "enter",
		27: "escape",
		127: "backspace",
		57414: "enter",
		57417: "left",
		57418: "right",
		57419: "up",
		57420: "down",
		57421: "pageup",
		57422: "pagedown",
		57423: "home",
		57424: "end",
	};
	const control: Record<number, KeyName> = {
		1: "ctrl-a",
		3: "ctrl-c",
		4: "ctrl-d",
		7: "ctrl-g",
		11: "ctrl-k",
		15: "ctrl-o",
		20: "ctrl-t",
		21: "ctrl-u",
		23: "ctrl-w",
		25: "ctrl-y",
		26: "ctrl-z",
		31: "undo",
	};
	const name = control[codepoint];
	if (name && (modifiers & 4) !== 0)
		return { name, sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
	if (codepoint === 9 && (modifiers & 1) !== 0)
		return { name: "shift-tab", sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
	if (codepoint === 13 && ((modifiers & 1) !== 0 || (modifiers & 2) !== 0))
		return { name: "newline", sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
	if (special[codepoint])
		return { name: special[codepoint]!, sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
	if ((modifiers & 4) !== 0) {
		if (codepoint >= 0x40 && codepoint <= 0x7f) {
			const ctrlCode = codepoint & 0x1f;
			const ctrlName: Record<number, KeyName> = {
				1: "ctrl-a",
				3: "ctrl-c",
				4: "ctrl-d",
				7: "ctrl-g",
				11: "ctrl-k",
				15: "ctrl-o",
				20: "ctrl-t",
				21: "ctrl-u",
				23: "ctrl-w",
				25: "ctrl-y",
				26: "ctrl-z",
				31: "undo",
			};
			if (ctrlName[ctrlCode])
				return { name: ctrlName[ctrlCode]!, sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
		}
		// Ctrl with no known ctrl key (e.g. a caps-locked letter like "\x1b[68;5u"):
		// swallow it instead of inserting a stray character (kimi parity).
		return { name: "unknown", sequence, eventType, ...(keyModifiers ? { modifiers: keyModifiers } : {}) };
	}
	const text = String.fromCodePoint(codepoint);
	return { name: "unknown", text, sequence, eventType };
}

function kittyEventType(value: string | undefined): KeyEventType {
	return value === "2" ? "repeat" : value === "3" ? "release" : "press";
}

function kittyModifiers(modifierValue: number): KeyModifiers | undefined {
	const bits = (modifierValue - 1) & ~(64 | 128);
	if (bits <= 0) return undefined;
	const modifiers: { shift?: boolean; alt?: boolean; ctrl?: boolean } = {};
	if (bits & 1) modifiers.shift = true;
	if (bits & 2) modifiers.alt = true;
	if (bits & 4) modifiers.ctrl = true;
	return modifiers;
}

function isProtocolReply(sequence: string): boolean {
	return (
		/^\x1b\[\?(?:[0-9;]+)[cuy]$/.test(sequence) ||
		/^\x1b\[>(?:[0-9;]+)u$/.test(sequence) ||
		/^\x1b\[[0-9]+;[0-9]+R$/.test(sequence)
	);
}

function isEscapePrefix(value: string): boolean {
	if (value === "\x1b" || /^\x1b\[[0-9;?]*$/.test(value) || "\x1b[200~".startsWith(value)) return true;
	if (/^\x1b[\]P_^]/.test(value)) return !hasStringTerminator(value);
	if (value === "\x1bO") return true;
	return false;
}

/** Consume one escape sequence without swallowing printable input that follows it. */
function readEscapeSequence(value: string): string {
	if (value === "\x1b") return value;
	if (/^\x1b[\]P_^]/.test(value)) {
		const bell = value.startsWith("\x1b]") ? value.indexOf("\x07", 2) : -1;
		const stringTerminator = value.indexOf("\x1b\\", 2);
		const end = [bell, stringTerminator].filter((index) => index >= 0).sort((left, right) => left - right)[0];
		return end === undefined ? value : value.slice(0, end + (end === stringTerminator ? 2 : 1));
	}
	if (value.startsWith("\x1b[")) {
		for (let index = 2; index < value.length; index += 1) {
			const code = value.charCodeAt(index);
			if (code >= 0x40 && code <= 0x7e) return value.slice(0, index + 1);
		}
	}
	if (value.startsWith("\x1bO")) return value.slice(0, Math.min(3, value.length));
	// Alt+key and other two-byte escape forms consume only that key. The
	// remaining buffer must still be decoded as ordinary user input.
	return value.slice(0, Math.min(2, value.length));
}

function hasStringTerminator(value: string): boolean {
	return (value.startsWith("\x1b]") && value.includes("\x07", 2)) || value.includes("\x1b\\", 2);
}

function normalizePaste(value: string): string {
	return value
		.replaceAll("\r\n", "\n")
		.replaceAll("\r", "\n")
		.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g, "");
}

type FocusReportResult = { readonly data: string; readonly events: readonly boolean[]; readonly remainder: string };

/** Remove Xterm focus reports before the ordinary decoder sees them. */
function consumeFocusReports(value: string): FocusReportResult {
	const events: boolean[] = [];
	let data = "";
	let index = 0;
	while (index < value.length) {
		if (value.startsWith(TERMINAL_FOCUS_IN, index)) {
			events.push(true);
			index += TERMINAL_FOCUS_IN.length;
			continue;
		}
		if (value.startsWith(TERMINAL_FOCUS_OUT, index)) {
			events.push(false);
			index += TERMINAL_FOCUS_OUT.length;
			continue;
		}
		const suffix = value.slice(index);
		if (suffix.length >= 1 && (TERMINAL_FOCUS_IN.startsWith(suffix) || TERMINAL_FOCUS_OUT.startsWith(suffix)))
			return { data, events, remainder: suffix };
		data += value[index]!;
		index += 1;
	}
	return { data, events, remainder: "" };
}

function attempt(operation: () => unknown): void {
	try {
		operation();
	} catch {
		/* terminal restoration continues */
	}
}
