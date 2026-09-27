import type { KeyInput } from "./terminal.js";
import { displayWidth, graphemeCount, sliceGraphemes } from "./width.js";

/**
 * The input side of a Kimi-style TUI component.  Rendering stays in the app,
 * but the component that owns a modal owns its input as well.
 */
export interface InteractiveComponent {
	handleInput(key: KeyInput): void | boolean | Promise<void | boolean>;
	focused?: boolean;
}

export interface OverlayStackOptions {
	nonCapturing?: boolean;
	visible?: () => boolean;
}

export interface OverlayStackHandle {
	hide(): void;
	setHidden(hidden: boolean): void;
	focus(): void;
	unfocus(options?: { readonly target?: InteractiveComponent | null }): void;
	isHidden(): boolean;
	isFocused(): boolean;
}

interface OverlayEntry {
	id: string;
	component: InteractiveComponent;
	options: OverlayStackOptions;
	preFocus: InteractiveComponent | null;
	hidden: boolean;
	order: number;
}

/**
 * Small, renderer-agnostic overlay/focus stack modelled after pi-tui.
 *
 * It deliberately does not know about terminal geometry or mouse hit-testing:
 * those belong to the component/view.  Its job is only ownership, capture,
 * focus restoration, and forwarding one complete input event to the focused
 * component.
 */
export class OverlayStack {
	private readonly entries: OverlayEntry[] = [];
	private focused: InteractiveComponent | null = null;
	private order = 0;

	show(id: string, component: InteractiveComponent, options: OverlayStackOptions = {}): OverlayStackHandle {
		const entry: OverlayEntry = {
			id,
			component,
			options,
			preFocus: this.focused,
			hidden: false,
			order: ++this.order,
		};
		this.entries.push(entry);
		if (!options.nonCapturing && this.isVisible(entry)) this.setFocus(component);
		return this.handleFor(entry);
	}

	hide(id?: string): void {
		const entry = id === undefined ? this.topCapturing() : this.entries.find((candidate) => candidate.id === id);
		if (!entry) return;
		this.remove(entry);
	}

	hasVisible(): boolean {
		return this.entries.some((entry) => this.isVisible(entry));
	}

	contains(id: string): boolean {
		return this.entries.some((entry) => entry.id === id && this.isVisible(entry));
	}

	focusedId(): string | undefined {
		return this.entries.find((entry) => entry.component === this.focused && this.isVisible(entry))?.id;
	}

	topId(): string | undefined {
		return this.topCapturing()?.id;
	}

	/** Forward one complete key to the focused capturing overlay. */
	async handleInput(key: KeyInput): Promise<boolean> {
		const entry = this.topCapturing();
		if (!entry) return false;
		if (this.focused !== entry.component) this.setFocus(entry.component);
		const result = await entry.component.handleInput(key);
		return result !== false;
	}

	private handleFor(entry: OverlayEntry): OverlayStackHandle {
		return {
			hide: () => this.remove(entry),
			setHidden: (hidden) => {
				if (!this.entries.includes(entry) || entry.hidden === hidden) return;
				entry.hidden = hidden;
				if (hidden && this.focused === entry.component) this.restoreFocus(entry);
				else if (!hidden && !entry.options.nonCapturing && this.isVisible(entry)) this.setFocus(entry.component);
			},
			focus: () => {
				if (!this.entries.includes(entry) || !this.isVisible(entry)) return;
				entry.order = ++this.order;
				this.setFocus(entry.component);
			},
			unfocus: (options) => {
				if (this.focused !== entry.component && !options) return;
				this.restoreFocus(entry, options?.target);
			},
			isHidden: () => entry.hidden,
			isFocused: () => this.focused === entry.component,
		};
	}

	private remove(entry: OverlayEntry): void {
		const index = this.entries.indexOf(entry);
		if (index < 0) return;
		this.entries.splice(index, 1);
		for (const candidate of this.entries) {
			if (candidate.preFocus === entry.component) candidate.preFocus = entry.preFocus;
		}
		if (this.focused === entry.component) this.restoreFocus(entry);
	}

	private restoreFocus(entry: OverlayEntry, explicitTarget?: InteractiveComponent | null): void {
		const next = this.topCapturing(entry);
		this.setFocus(explicitTarget !== undefined ? explicitTarget : (next?.component ?? entry.preFocus));
	}

	private setFocus(component: InteractiveComponent | null): void {
		if (this.focused) this.focused.focused = false;
		this.focused = component;
		if (component) component.focused = true;
	}

	private topCapturing(exclude?: OverlayEntry): OverlayEntry | undefined {
		return this.entries
			.filter((entry) => entry !== exclude && !entry.options.nonCapturing && this.isVisible(entry))
			.sort((left, right) => right.order - left.order)[0];
	}

	private isVisible(entry: OverlayEntry): boolean {
		return !entry.hidden && (entry.options.visible?.() ?? true);
	}
}

/** Small terminal-native editor; values and cursor positions are grapheme based. */
export class TextEditor {
	private cursor = 0;
	private visualWidth = Number.POSITIVE_INFINITY;
	private preferredVisualColumn: number | undefined;
	private undoStack: Array<{ value: string; cursor: number }> = [];
	private killRing: string[] = [];
	private lastYank: { start: number; end: number } | undefined;
	private killIndex = 0;
	constructor(private value = "") {
		this.cursor = graphemeCount(value);
	}
	get text(): string {
		return this.value;
	}
	get cursorIndex(): number {
		return this.cursor;
	}
	set(text: string): void {
		this.value = text;
		this.cursor = graphemeCount(text);
		this.undoStack = [];
		this.lastYank = undefined;
		this.preferredVisualColumn = undefined;
	}
	/** Replaces editor value while retaining a caller-calculated grapheme cursor. */
	setWithCursor(text: string, cursorIndex: number): void {
		this.value = text;
		this.cursor = Math.max(0, Math.min(graphemeCount(text), cursorIndex));
		this.preferredVisualColumn = undefined;
	}
	clear(): void {
		this.set("");
	}
	/** Set the content width used for visual-line up/down navigation. */
	setVisualWidth(width: number | undefined): void {
		const next = width && Number.isFinite(width) ? Math.max(1, Math.floor(width)) : Number.POSITIVE_INFINITY;
		if (next !== this.visualWidth) this.preferredVisualColumn = undefined;
		this.visualWidth = next;
	}

	handle(key: KeyInput): boolean {
		const length = graphemeCount(this.value);
		if (key.name !== "up" && key.name !== "down") this.preferredVisualColumn = undefined;
		if (key.name === "undo") {
			this.undo();
			return true;
		}
		if (key.name === "ctrl-w" || key.name === "alt-backspace") {
			this.deleteWordBackward();
			return true;
		}
		if (key.name === "ctrl-u") {
			this.deleteToLineStart();
			return true;
		}
		if (key.name === "ctrl-k") {
			this.deleteToLineEnd();
			return true;
		}
		if (key.name === "ctrl-y") {
			this.yank();
			return true;
		}
		if (key.name === "alt-y") {
			this.yankPop();
			return true;
		}
		if (key.name === "alt-d") {
			this.deleteWordForward();
			return true;
		}
		if (key.name === "alt-left" || (key.name === "left" && key.modifiers?.ctrl)) {
			this.moveWordBackward();
			return true;
		}
		if (key.name === "alt-right" || (key.name === "right" && key.modifiers?.ctrl)) {
			this.moveWordForward();
			return true;
		}
		if (key.name === "left") {
			this.cursor = Math.max(0, this.cursor - 1);
			return true;
		}
		if (key.name === "right") {
			this.cursor = Math.min(length, this.cursor + 1);
			return true;
		}
		if (key.name === "up" || key.name === "down") {
			this.moveVisualLine(key.name === "up" ? -1 : 1);
			return true;
		}
		if (key.name === "home" || key.name === "end") {
			const before = sliceGraphemes(this.value, 0, this.cursor);
			const column = graphemeCount(before.slice(before.lastIndexOf("\n") + 1));
			if (key.name === "home") this.cursor -= column;
			else {
				const after = sliceGraphemes(this.value, this.cursor);
				const breakAt = after.indexOf("\n");
				this.cursor += graphemeCount(breakAt < 0 ? after : after.slice(0, breakAt));
			}
			return true;
		}
		if (key.name === "backspace" && this.cursor > 0) {
			this.pushUndo();
			this.value = `${sliceGraphemes(this.value, 0, this.cursor - 1)}${sliceGraphemes(this.value, this.cursor)}`;
			this.cursor -= 1;
			this.lastYank = undefined;
			return true;
		}
		if (key.name === "delete" && this.cursor < length) {
			this.pushUndo();
			this.value = `${sliceGraphemes(this.value, 0, this.cursor)}${sliceGraphemes(this.value, this.cursor + 1)}`;
			this.lastYank = undefined;
			return true;
		}
		if (key.name === "newline") {
			this.insert("\n");
			return true;
		}
		if (key.text) {
			const text = key.text.replace(/[\u0000-\u001f\u007f]/g, "");
			if (!text) return true;
			this.insert(text);
			return true;
		}
		return false;
	}

	private insert(text: string): void {
		this.pushUndo();
		this.value = `${sliceGraphemes(this.value, 0, this.cursor)}${text}${sliceGraphemes(this.value, this.cursor)}`;
		this.cursor += graphemeCount(text);
		this.lastYank = undefined;
	}

	private moveVisualLine(delta: -1 | 1): void {
		const lines = this.visualLines();
		const current = lines.findIndex(
			(line, index) =>
				this.cursor >= line.start &&
				(this.cursor < line.end ||
					(this.cursor === line.end &&
						(index === lines.length - 1 || lines[index + 1]?.logicalLine !== line.logicalLine))),
		);
		if (current < 0) return;
		const target = lines[current + delta];
		if (!target) return;
		const source = lines[current]!;
		const sourceColumn = this.cursor - source.start;
		const desired = this.preferredVisualColumn ?? sourceColumn;
		this.preferredVisualColumn = desired;
		let offset = 0;
		while (target.start + offset < target.end) {
			if (offset >= desired) break;
			offset += 1;
		}
		this.cursor = target.start + offset;
	}

	private visualLines(): readonly { readonly logicalLine: number; readonly start: number; readonly end: number }[] {
		const result: Array<{ logicalLine: number; start: number; end: number }> = [];
		let global = 0;
		for (const [logicalLine, value] of this.value.split("\n").entries()) {
			const length = graphemeCount(value);
			if (!length) result.push({ logicalLine, start: global, end: global });
			else if (!Number.isFinite(this.visualWidth)) result.push({ logicalLine, start: global, end: global + length });
			else {
				let start = 0;
				let width = 0;
				for (let offset = 0; offset < length; offset += 1) {
					const glyph = sliceGraphemes(value, offset, offset + 1);
					const glyphWidth = displayWidth(glyph);
					if (width > 0 && width + glyphWidth > this.visualWidth) {
						result.push({ logicalLine, start: global + start, end: global + offset });
						start = offset;
						width = 0;
					}
					width += glyphWidth;
				}
				result.push({ logicalLine, start: global + start, end: global + length });
			}
			global += length + 1;
		}
		return result;
	}

	private pushUndo(): void {
		const previous = this.undoStack.at(-1);
		if (!previous || previous.value !== this.value || previous.cursor !== this.cursor)
			this.undoStack.push({ value: this.value, cursor: this.cursor });
		if (this.undoStack.length > 100) this.undoStack.shift();
	}
	private undo(): void {
		const previous = this.undoStack.pop();
		if (!previous) return;
		this.value = previous.value;
		this.cursor = previous.cursor;
		this.lastYank = undefined;
	}
	private deleteWordBackward(): void {
		if (!this.cursor) return;
		const before = sliceGraphemes(this.value, 0, this.cursor);
		let remove = 0;
		while (
			remove < graphemeCount(before) &&
			isEditorWhitespace(sliceGraphemes(before, graphemeCount(before) - remove - 1, graphemeCount(before) - remove))
		)
			remove += 1;
		while (
			remove < graphemeCount(before) &&
			!isEditorWhitespace(sliceGraphemes(before, graphemeCount(before) - remove - 1, graphemeCount(before) - remove))
		)
			remove += 1;
		if (!remove) return;
		this.pushUndo();
		const deleted = sliceGraphemes(before, graphemeCount(before) - remove);
		this.kill(deleted);
		this.value = `${sliceGraphemes(this.value, 0, this.cursor - remove)}${sliceGraphemes(this.value, this.cursor)}`;
		this.cursor -= remove;
		this.lastYank = undefined;
	}
	private deleteWordForward(): void {
		const after = sliceGraphemes(this.value, this.cursor);
		let remove = 0;
		while (remove < graphemeCount(after) && isEditorWhitespace(sliceGraphemes(after, remove, remove + 1))) remove += 1;
		while (remove < graphemeCount(after) && !isEditorWhitespace(sliceGraphemes(after, remove, remove + 1))) remove += 1;
		if (!remove) return;
		this.pushUndo();
		this.kill(sliceGraphemes(after, 0, remove));
		this.value = `${sliceGraphemes(this.value, 0, this.cursor)}${sliceGraphemes(this.value, this.cursor + remove)}`;
		this.lastYank = undefined;
	}
	private deleteToLineStart(): void {
		const before = sliceGraphemes(this.value, 0, this.cursor);
		const newline = before.lastIndexOf("\n");
		const lineStart = newline < 0 ? 0 : graphemeCount(before.slice(0, newline + 1));
		if (lineStart === this.cursor) return;
		this.pushUndo();
		this.kill(sliceGraphemes(before, lineStart));
		this.value = `${sliceGraphemes(this.value, 0, lineStart)}${sliceGraphemes(this.value, this.cursor)}`;
		this.cursor = lineStart;
		this.lastYank = undefined;
	}
	private deleteToLineEnd(): void {
		const after = sliceGraphemes(this.value, this.cursor);
		const newline = after.indexOf("\n");
		const remove = graphemeCount(newline < 0 ? after : after.slice(0, newline));
		if (!remove) return;
		this.pushUndo();
		this.kill(sliceGraphemes(after, 0, remove));
		this.value = `${sliceGraphemes(this.value, 0, this.cursor)}${sliceGraphemes(this.value, this.cursor + remove)}`;
		this.lastYank = undefined;
	}
	private kill(text: string): void {
		if (!text) return;
		this.killRing.unshift(text);
		this.killRing = this.killRing.slice(0, 20);
		this.killIndex = 0;
	}
	private yank(): void {
		const text = this.killRing[this.killIndex];
		if (!text) return;
		this.pushUndo();
		const start = this.cursor;
		this.value = `${sliceGraphemes(this.value, 0, this.cursor)}${text}${sliceGraphemes(this.value, this.cursor)}`;
		this.cursor += graphemeCount(text);
		this.lastYank = { start, end: this.cursor };
	}
	private yankPop(): void {
		if (!this.lastYank || this.killRing.length < 2) return;
		this.pushUndo();
		this.value = `${sliceGraphemes(this.value, 0, this.lastYank.start)}${sliceGraphemes(this.value, this.lastYank.end)}`;
		this.cursor = this.lastYank.start;
		this.killIndex = (this.killIndex + 1) % this.killRing.length;
		this.yank();
	}
	private moveWordBackward(): void {
		let cursor = this.cursor;
		while (cursor > 0 && isEditorWhitespace(sliceGraphemes(this.value, cursor - 1, cursor))) cursor -= 1;
		while (cursor > 0 && !isEditorWhitespace(sliceGraphemes(this.value, cursor - 1, cursor))) cursor -= 1;
		this.cursor = cursor;
	}
	private moveWordForward(): void {
		const length = graphemeCount(this.value);
		let cursor = this.cursor;
		while (cursor < length && isEditorWhitespace(sliceGraphemes(this.value, cursor, cursor + 1))) cursor += 1;
		while (cursor < length && !isEditorWhitespace(sliceGraphemes(this.value, cursor, cursor + 1))) cursor += 1;
		this.cursor = cursor;
	}
}

function isEditorWhitespace(value: string): boolean {
	return /^\s$/u.test(value);
}

/** Generic filtered selection state for modal lists. */
export class SelectableList<T> implements InteractiveComponent {
	private selected = 0;
	private filterValue = "";
	focused = false;
	onSelect?: (item: T) => void | Promise<void>;
	onCancel?: () => void | Promise<void>;
	constructor(
		private items: readonly T[],
		private readonly label: (item: T) => string,
	) {}
	get filter(): string {
		return this.filterValue;
	}
	get selectedIndex(): number {
		return this.selected;
	}
	visible(): readonly T[] {
		const query = this.filterValue.trim().toLocaleLowerCase();
		return query ? this.items.filter((item) => this.label(item).toLocaleLowerCase().includes(query)) : this.items;
	}
	setItems(items: readonly T[]): void {
		this.items = items;
		this.selected = Math.min(this.selected, Math.max(0, this.visible().length - 1));
	}
	move(delta: number): void {
		const count = this.visible().length;
		this.selected = count ? (this.selected + delta + count) % count : 0;
	}
	append(text: string): void {
		this.filterValue += text;
		this.selected = 0;
	}
	backspace(): void {
		this.filterValue = sliceGraphemes(this.filterValue, 0, Math.max(0, graphemeCount(this.filterValue) - 1));
		this.selected = 0;
	}
	chosen(): T | undefined {
		return this.visible()[this.selected];
	}
	async handleInput(key: KeyInput): Promise<boolean> {
		if (key.name === "up") this.move(-1);
		else if (key.name === "down") this.move(1);
		else if (key.name === "backspace") this.backspace();
		else if (key.name === "escape") {
			await this.onCancel?.();
			return true;
		} else if (key.name === "enter") {
			const item = this.chosen();
			if (item !== undefined) await this.onSelect?.(item);
			return true;
		} else if (key.text) this.append(key.text);
		else return false;
		return true;
	}
}

/** Offset helper shared by transcript and long modal views. */
export class Viewport {
	private offset = 0;
	reset(): void {
		this.offset = 0;
	}
	move(delta: number, contentRows: number, visibleRows: number): void {
		this.offset = Math.max(0, Math.min(Math.max(0, contentRows - visibleRows), this.offset + delta));
	}
	/** Top-origin scrolling for modal content (unlike transcript's bottom origin). */
	moveFromStart(delta: number, contentRows: number, visibleRows: number): void {
		this.offset = Math.max(0, Math.min(Math.max(0, contentRows - visibleRows), this.offset + delta));
	}
	slice<T>(items: readonly T[], visibleRows: number): readonly T[] {
		const start = Math.max(0, items.length - visibleRows - this.offset);
		const end = Math.max(0, items.length - this.offset);
		return items.slice(start, end);
	}
	sliceFromStart<T>(items: readonly T[], visibleRows: number): readonly T[] {
		return items.slice(this.offset, this.offset + Math.max(0, visibleRows));
	}
	/** Keeps a materialized row range in view. Rows are zero based. */
	ensureVisible(startRow: number, endRow: number, contentRows: number, visibleRows: number): void {
		const visible = Math.max(1, visibleRows);
		const maximum = Math.max(0, contentRows - visible);
		let top = Math.max(0, contentRows - visible - this.offset);
		if (startRow < top) top = startRow;
		else if (endRow >= top + visible) top = endRow - visible + 1;
		top = Math.max(0, Math.min(maximum, top));
		this.offset = maximum - top;
	}
	ensureVisibleFromStart(startRow: number, endRow: number, contentRows: number, visibleRows: number): void {
		const visible = Math.max(1, visibleRows);
		const maximum = Math.max(0, contentRows - visible);
		if (startRow < this.offset) this.offset = startRow;
		else if (endRow >= this.offset + visible) this.offset = endRow - visible + 1;
		this.offset = Math.max(0, Math.min(maximum, this.offset));
	}
	get scrollOffset(): number {
		return this.offset;
	}
}
