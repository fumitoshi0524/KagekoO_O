import { graphemeCount, sliceGraphemes } from "@kageko/tui-kit";
import { slashCommandCompletions, slashCommandNames } from "../commands/registry.js";

export interface CompletionMenu {
	readonly kind: "/" | "@";
	readonly values: readonly string[];
	readonly selected: number;
	readonly start: number;
}

/** Finds the active slash/file token without owning the editor or filesystem. */
export function completionFor(
	text: string,
	cursorIndex: number,
	entries: readonly string[],
): CompletionMenu | undefined {
	const before = sliceGraphemes(text, 0, cursorIndex);
	const match = before.match(/(^|\s)([/@])([^\s]*)$/);
	if (!match) return undefined;
	const kind = match[2] as "/" | "@";
	const query = match[3] ?? "";
	const values = kind === "/" ? slashCommandCompletions(query) : fileCompletionCandidates(entries, query);
	return values.length
		? { kind, values, selected: 0, start: cursorIndex - graphemeCount(`${kind}${query}`) }
		: undefined;
}

export function moveCompletion(menu: CompletionMenu, delta: -1 | 1): CompletionMenu {
	const count = menu.values.length;
	return { ...menu, selected: count ? (menu.selected + (delta < 0 ? count - 1 : 1)) % count : 0 };
}

/** Applies a selected completion at the original grapheme boundary. */
export function applyCompletion(
	text: string,
	cursorIndex: number,
	menu: CompletionMenu,
): { readonly text: string; readonly cursorIndex: number } {
	const value = menu.values[menu.selected];
	if (!value) return { text, cursorIndex };
	const before = sliceGraphemes(text, 0, menu.start);
	const after = sliceGraphemes(text, cursorIndex);
	return { text: `${before}${value}${after}`, cursorIndex: graphemeCount(before) + graphemeCount(value) };
}

/** Decision helper used by the coordinator before sending a normal prompt. */
export function shouldQueuePrompt(turnLive: boolean): boolean {
	return turnLive;
}

/** Keep completion aligned with the coordinator's supported slash commands. */
export const slashCompletionCommands = slashCommandNames();

/** Filtering precedes display pagination so a late matching cwd entry remains discoverable. */
export function fileCompletionCandidates(entries: readonly string[], query: string): readonly string[] {
	return entries.filter((entry) => entry.slice(1).toLowerCase().startsWith(query.toLowerCase()));
}
