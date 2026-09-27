import type { KagekoClient, SessionClient } from "@kageko/node-sdk";

/** A slash command names an intent; the panel owns all arguments and mutations. */
export type InteractivePanelName =
	| "new"
	| "help"
	| "sessions"
	| "rename"
	| "fork"
	| "archive"
	| "delete"
	| "activity"
	| "capabilities"
	| "cron"
	| "goal"
	| "plan"
	| "memory"
	| "learn"
	| "skills"
	| "mcp"
	| "plugins"
	| "tools"
	| "compact"
	| "model"
	| "graph"
	| "config"
	| "theme"
	| "undo"
	| "auth"
	| "trust";

/** Services a slash command may use; provided by the TUI app. */
export interface CommandContext {
	readonly client: KagekoClient;
	readonly session: SessionClient | undefined;
	readonly cwd: string;
	/** Print a transcript record (kind: status|warning|error|system). */
	notice(kind: "status" | "warning" | "error" | "system", text: string): void;
	/** Open the scrollable list modal filled with plain text lines. */
	showLines(lines: readonly string[]): void;
	/** Open the details modal (single scrollable payload, e.g. task output). */
	showDetails(lines: readonly string[]): void;
	/** Open one of the built-in overlays; the sessions picker resolves after loading. */
	showOverlay(overlay: "help" | "sessions"): Promise<void> | void;
	/** Open the pending approval/question overlay (no-op when none pending). */
	showInteractions(): void;
	/** Lease the terminal and open a subshell. */
	openShell(): Promise<void>;
	/** Open the provider/model setup wizard. */
	openSetup(): Promise<void>;
	/** Open the credential-only OAuth login wizard for a provider, when the host has one. */
	openOAuthSetup?: (provider: string) => Promise<void>;
	/** Open an interactive panel while preserving typed slash-command arguments. */
	openPanel?: (panel: InteractivePanelName, args?: readonly string[]) => Promise<void> | void;
	/** Refresh the host's pending-learning indicator after a resolve outside the /learn panel. */
	refreshLearningPending?: () => void;
	/** Ask for confirmation; resolves true on confirm. */
	confirm(message: string): Promise<boolean>;
	/** Switch to another session handle. */
	switchSession(session: SessionClient): Promise<void>;
	/** Close the TUI. */
	quit(): Promise<void>;
}

export type CommandCategory = "session" | "modes" | "memory" | "capabilities" | "config" | "info";

export interface SlashCommand {
	readonly name: string;
	readonly aliases?: readonly string[];
	/** Compatibility-only commands remain executable without cluttering discovery/help. */
	readonly hidden?: boolean;
	readonly category: CommandCategory;
	readonly description: string;
	readonly argumentHint?: string;
	/** "always" commands run even while a turn is live; default "idle". */
	readonly availability?: "always" | "idle";
	/** Requires an active session; the dispatcher prints a warning otherwise. */
	readonly needsSession?: boolean;
	run(args: readonly string[], ctx: CommandContext): Promise<void> | void;
}
