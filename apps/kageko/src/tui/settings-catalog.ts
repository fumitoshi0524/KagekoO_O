/**
 * Settings panel catalog: section/field descriptors, dotted-path value reads,
 * display formatting and client-side input pre-validation.
 *
 * The Ajv document schema in
 * packages/application/src/configuration/config-loader.ts is the source of
 * truth for ranges and defaults; the min/max/default figures below are UI
 * hints duplicated from that schema. ConfigService.update re-validates every
 * write server-side and its rejection is surfaced to the user, so a stale hint
 * here can never persist an invalid value.
 *
 * Paths use only `[A-Za-z][A-Za-z0-9]*` segments so they pass the
 * buildConfigPatch safety rules shared with `/config set`.
 */

export type SettingFieldType = "boolean" | "enum" | "number" | "string" | "stringList";

export interface SettingField {
	/** Dotted config path, e.g. "agentGraph.learner.runTimeoutMs". */
	readonly path: string;
	readonly label: string;
	readonly type: SettingFieldType;
	/** Range/default hint shown next to the field and in the editor prompt. */
	readonly hint?: string;
	readonly enumValues?: readonly string[];
	readonly integer?: boolean;
	readonly min?: number;
	readonly max?: number;
}

export interface SettingsSection {
	readonly id: string;
	readonly title: string;
	readonly detail: string;
	/** Footer note; defaults to the composition-time note when omitted. */
	readonly note?: string;
	readonly fields: readonly SettingField[];
}

/** Shown under sections whose values are only read when a session runtime is composed. */
export const SETTINGS_NEW_SESSION_NOTE = "Saved to user config · applies to new sessions";
/** The harness rebuilds agent runtimes as soon as an agentGraph patch lands. */
export const SETTINGS_AGENT_GRAPH_NOTE = "Saved to user config · rebuilds agents in active sessions";

export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
	{
		id: "permission",
		title: "Permission",
		detail: "Default profile and allow/deny/ask rules",
		fields: [
			{
				path: "permission.defaultProfile",
				label: "Default profile",
				type: "enum",
				enumValues: ["manual", "workspace", "unrestricted"],
				hint: "manual · workspace · unrestricted",
			},
			{ path: "permission.allowList", label: "Allow list", type: "stringList", hint: "Auto-approved rules" },
			{ path: "permission.denyList", label: "Deny list", type: "stringList", hint: "Always-denied rules" },
			{ path: "permission.askList", label: "Ask list", type: "stringList", hint: "Rules that always prompt" },
		],
	},
	{
		id: "interaction",
		title: "Interaction",
		detail: "How the agent asks for input",
		fields: [
			{
				path: "interaction.defaultMode",
				label: "Default mode",
				type: "enum",
				enumValues: ["interactive", "unattended"],
				hint: "interactive · unattended",
			},
		],
	},
	{
		id: "shell",
		title: "Shell",
		detail: "Dialect, executable and foreground timeouts",
		fields: [
			{
				path: "shell.dialect",
				label: "Dialect",
				type: "enum",
				enumValues: ["bash", "powershell", "cmd"],
				hint: "bash · powershell · cmd",
			},
			{ path: "shell.executable", label: "Executable", type: "string", hint: "e.g. bash, pwsh" },
			{
				path: "shell.defaultTimeoutMs",
				label: "Default timeout",
				type: "number",
				integer: true,
				min: 1_000,
				hint: "≥ 1000 ms · default 60000",
			},
			{
				path: "shell.maxTimeoutMs",
				label: "Maximum timeout",
				type: "number",
				integer: true,
				min: 1_000,
				hint: "≥ 1000 ms · default 300000",
			},
		],
	},
	{
		id: "telemetry",
		title: "Telemetry",
		detail: "Local observability collection",
		fields: [{ path: "telemetry.enabled", label: "Enabled", type: "boolean" }],
	},
	{
		id: "memory",
		title: "Memory",
		detail: "Session memory indexing",
		fields: [
			{ path: "memory.autoIndex", label: "Auto-index", type: "boolean" },
			{ path: "memory.rememberSessions", label: "Remember sessions", type: "boolean" },
		],
	},
	{
		id: "learning",
		title: "Learning",
		detail: "Resident learner triggers and synthesis bounds",
		fields: [
			{ path: "learning.autoApproveSkills", label: "Auto-approve skills", type: "boolean" },
			{ path: "learning.autoApproveCapabilities", label: "Auto-approve capabilities", type: "boolean" },
			{
				path: "learning.minContentLength",
				label: "Minimum content length",
				type: "number",
				min: 0,
				hint: "≥ 0 · default 8",
			},
			{
				path: "learning.maxContentLength",
				label: "Maximum content length",
				type: "number",
				min: 1,
				hint: "≥ 1 · default 50000",
			},
			{
				path: "learning.erroneousToolThreshold",
				label: "Erroneous tool threshold",
				type: "number",
				min: 1,
				hint: "≥ 1 · default 2",
			},
			{
				path: "learning.maxPendingEntries",
				label: "Max pending entries",
				type: "number",
				min: 1,
				hint: "≥ 1 · default 100",
			},
			{
				path: "learning.skillMinEvents",
				label: "Skill minimum events",
				type: "number",
				integer: true,
				min: 1,
				max: 100,
				hint: "1–100 · default 3",
			},
			{
				path: "learning.skillMinCompletedTurns",
				label: "Skill minimum completed turns",
				type: "number",
				integer: true,
				min: 1,
				max: 100,
				hint: "1–100 · default 3",
			},
			{
				path: "learning.skillSynthesisCooldownEvents",
				label: "Skill synthesis cooldown",
				type: "number",
				integer: true,
				min: 1,
				max: 100,
				hint: "1–100 events · default 5",
			},
			{
				path: "learning.skillSynthesisTimeoutMs",
				label: "Skill synthesis timeout",
				type: "number",
				integer: true,
				min: 1_000,
				hint: "≥ 1000 ms · default 60000",
			},
			{
				path: "learning.capabilitySynthesisTimeoutMs",
				label: "Capability synthesis timeout",
				type: "number",
				integer: true,
				min: 1_000,
				hint: "≥ 1000 ms · default 120000",
			},
			{
				path: "learning.mcpSynthesisTimeoutMs",
				label: "MCP synthesis timeout",
				type: "number",
				integer: true,
				min: 1_000,
				hint: "≥ 1000 ms · default 300000",
			},
			{
				path: "learning.skillSimilarityThreshold",
				label: "Skill similarity threshold",
				type: "number",
				min: 0,
				max: 1,
				hint: "0–1 · default 0.85",
			},
		],
	},
	{
		id: "agents",
		title: "Agents",
		detail: "Coordinator/learner bounds and subagent concurrency",
		note: SETTINGS_AGENT_GRAPH_NOTE,
		fields: [
			{
				path: "agentGraph.coordinator.maxSteps",
				label: "Coordinator max steps",
				type: "number",
				integer: true,
				min: 1,
				max: 50,
				hint: "1–50",
			},
			{
				path: "agentGraph.learner.maxSteps",
				label: "Learner max steps",
				type: "number",
				integer: true,
				min: 1,
				max: 20,
				hint: "1–20",
			},
			{
				path: "agentGraph.learner.runTimeoutMs",
				label: "Learner run timeout",
				type: "number",
				integer: true,
				min: 30_000,
				max: 900_000,
				hint: "30000–900000 ms",
			},
			{
				path: "agentGraph.learner.maxQueuedRuns",
				label: "Learner queued runs",
				type: "number",
				integer: true,
				min: 1,
				max: 16,
				hint: "1–16",
			},
			{
				path: "agentGraph.maxConcurrentSubagents",
				label: "Max concurrent subagents",
				type: "number",
				integer: true,
				min: 1,
				max: 16,
				hint: "1–16",
			},
		],
	},
	{
		id: "turns",
		title: "Turns & compaction",
		detail: "Tool execution and context compaction policy",
		fields: [
			{
				path: "turns.toolConcurrency",
				label: "Tool concurrency",
				type: "number",
				integer: true,
				min: 1,
				max: 16,
				hint: "1–16 · default 8",
			},
			{
				path: "turns.toolResultBudgetChars",
				label: "Tool result budget",
				type: "number",
				integer: true,
				min: 10_000,
				max: 1_000_000,
				hint: "10000–1000000 chars · default 100000",
			},
			{
				path: "compaction.thresholdRatio",
				label: "Compaction threshold ratio",
				type: "number",
				min: 0,
				max: 1,
				hint: "0–1 · default 0.8",
			},
			{
				path: "compaction.targetRatio",
				label: "Compaction target ratio",
				type: "number",
				min: 0,
				max: 1,
				hint: "0–1 · default 0.5",
			},
			{
				path: "compaction.inputRatio",
				label: "Compaction input ratio",
				type: "number",
				min: 0,
				max: 1,
				hint: "0–1 · default 0.6",
			},
			{
				path: "compaction.minHistoryEvents",
				label: "Compaction min history events",
				type: "number",
				integer: true,
				min: 1,
				hint: "≥ 1 · default 4",
			},
		],
	},
	{
		id: "mcp",
		title: "MCP",
		detail: "Server connect and call timeouts",
		fields: [
			{
				path: "mcp.connectTimeoutMs",
				label: "Connect timeout",
				type: "number",
				integer: true,
				min: 1_000,
				max: 120_000,
				hint: "1000–120000 ms · default 30000",
			},
			{
				path: "mcp.callTimeoutMs",
				label: "Call timeout",
				type: "number",
				integer: true,
				min: 1_000,
				max: 600_000,
				hint: "1000–600000 ms · default 30000",
			},
		],
	},
];

/** One-line section summary for the Settings root menu, including the first values. */
export function settingsSectionSummary(section: SettingsSection, config: Record<string, unknown>): string {
	const values = section.fields
		.slice(0, 2)
		.map((field) => formatSettingValue(field, readSettingValue(config, field.path)));
	return values.length ? `${section.detail} · ${values.join(" · ")}` : section.detail;
}

export function settingsSectionById(id: string): SettingsSection | undefined {
	return SETTINGS_SECTIONS.find((section) => section.id === id);
}

/** Read a dotted path out of the merged effective configuration. */
export function readSettingValue(config: Record<string, unknown>, path: string): unknown {
	let current: unknown = config;
	for (const segment of path.split(".")) {
		if (typeof current !== "object" || current === null || Array.isArray(current)) return undefined;
		current = (current as Record<string, unknown>)[segment];
	}
	return current;
}

/** Render the effective value for a field row; absent values show as the built-in default. */
export function formatSettingValue(field: SettingField, value: unknown): string {
	if (value === undefined || value === null) return "default";
	if (field.type === "boolean") return value === true ? "on" : "off";
	if (field.type === "stringList") {
		const entries = Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
		if (!entries.length) return "empty";
		const joined = entries.join(", ");
		return joined.length > 40 ? `${entries.length} entries` : joined;
	}
	if (typeof value === "string") return value;
	if (typeof value === "number" && Number.isFinite(value)) return String(value);
	return "default";
}

export type SettingInputResult =
	{ readonly ok: true; readonly value: string | number } | { readonly ok: false; readonly message: string };

/**
 * Parse and pre-validate a text input for a field. Server-side validation in
 * ConfigService.update remains authoritative; this only fails fast on input
 * that can never pass the document schema.
 */
export function parseSettingInput(field: SettingField, raw: string): SettingInputResult {
	const value = raw.trim();
	if (!value) return { ok: false, message: `${field.label} requires a value.` };
	if (field.type === "string" || field.type === "stringList") return { ok: true, value };
	if (field.type === "enum") {
		return field.enumValues?.includes(value)
			? { ok: true, value }
			: { ok: false, message: `${field.label} must be one of: ${(field.enumValues ?? []).join(", ")}.` };
	}
	if (field.type !== "number") return { ok: false, message: `${field.label} is not editable as text.` };
	const parsed = Number(value);
	if (!Number.isFinite(parsed)) return { ok: false, message: `${field.label} must be a number.` };
	if (field.integer && !Number.isInteger(parsed)) return { ok: false, message: `${field.label} must be an integer.` };
	if (field.min !== undefined && parsed < field.min)
		return {
			ok: false,
			message:
				field.max !== undefined
					? `${field.label} must be between ${field.min} and ${field.max}.`
					: `${field.label} must be at least ${field.min}.`,
		};
	if (field.max !== undefined && parsed > field.max)
		return {
			ok: false,
			message:
				field.min !== undefined
					? `${field.label} must be between ${field.min} and ${field.max}.`
					: `${field.label} must be at most ${field.max}.`,
		};
	return { ok: true, value: parsed };
}
