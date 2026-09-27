import { createHash } from "node:crypto";
import { safeStringify } from "../utils.js";
import type { LearningEvent } from "./event.js";
import type { TriageDecision } from "./types.js";

export interface ToolRegistryLike {
	isMcpTool(toolName: string): boolean;
}

export interface LearningTriageConfig {
	minContentLength?: number;
	maxContentLength?: number;
	allowedToolNames?: Set<string> | string[];
	erroneousToolThreshold?: number;
}

export interface LearningTriageOptions {
	config?: LearningTriageConfig;
	registry?: ToolRegistryLike;
}

interface ResolvedTriageConfig {
	minContentLength: number;
	maxContentLength: number;
	allowedToolNames: Set<string>;
	erroneousToolThreshold: number;
}

/**
 * Value-judgment layer for the learning pipeline.
 *
 * Decides whether a learning event is worth keeping, what it should become,
 * and whether it needs user confirmation before persistence.
 */
export class LearningTriage {
	readonly config: ResolvedTriageConfig;
	readonly registry?: ToolRegistryLike;
	private _errorCounts = new Map<string, number>();
	private _maxErrorKeys = 200;

	constructor(options: LearningTriageOptions = {}) {
		const merged = {
			minContentLength: 8,
			maxContentLength: 50_000,
			allowedToolNames: new Set<string>(["bash", "read", "read_media", "glob", "grep"]),
			erroneousToolThreshold: 2,
			...options.config,
		};
		// `...options.config` can replace the Set with an Array; normalize it.
		this.config = {
			...merged,
			allowedToolNames: new Set(merged.allowedToolNames ?? []),
		};
		this.registry = options.registry;
	}

	async triage(event: LearningEvent): Promise<TriageDecision> {
		switch (event.source) {
			case "tool_result":
				return this._triageToolResult(event);
			case "user_feedback":
				return this._triageUserFeedback(event);
			case "session_record":
				return this._triageSessionRecord(event);
			case "external_fetch":
				return this._triageExternalFetch(event);
			case "file_change":
				return this._triageFileChange(event);
			case "plugin":
				return this._triagePlugin(event);
			case "capability_gap":
				return this._triageCapabilityGap(event);
			default:
				return { action: "drop", reason: "unknown source" };
		}
	}

	private _triageToolResult(event: LearningEvent): TriageDecision {
		const { toolName, result } = event.payload as {
			toolName: string;
			result?: unknown;
			arguments?: Record<string, unknown>;
		};
		const isMcp = this.registry ? this.registry.isMcpTool(toolName) : String(toolName).startsWith("mcp__");
		if (!isMcp && !this.config.allowedToolNames.has(toolName)) {
			return { action: "drop", reason: "tool not in allow-list" };
		}

		const text = redactSecrets(this._extractText(result));
		if (!text) {
			return { action: "drop", reason: "empty result" };
		}

		if (text.length < this.config.minContentLength) {
			return { action: "drop", reason: "too short" };
		}
		if (text.length > this.config.maxContentLength) {
			return { action: "drop", reason: "too long" };
		}

		if ((result as { isError?: boolean } | undefined)?.isError) {
			const key = `${toolName}:${text.slice(0, 120)}`;
			const count = (this._errorCounts.get(key) ?? 0) + 1;
			this._errorCounts.set(key, count);
			if (this._errorCounts.size > this._maxErrorKeys) {
				const firstKey = this._errorCounts.keys().next().value as string;
				this._errorCounts.delete(firstKey);
			}
			if (count < this.config.erroneousToolThreshold) {
				return { action: "drop", reason: "error pattern not yet stable" };
			}
			return { action: "learn", target: "error_pattern", reason: "recurring error" };
		}

		if (this._looksLikeEcho(text, toolName, (event.payload as { arguments?: Record<string, unknown> }).arguments)) {
			return { action: "drop", reason: "looks like command echo" };
		}

		if (isMcp) {
			return { action: "learn", target: "mcp", reason: "mcp tool output" };
		}

		return { action: "learn", target: "knowledge", reason: "valuable tool output" };
	}

	private _triageUserFeedback(event: LearningEvent): TriageDecision {
		const { kind } = event.payload as { kind?: string };
		switch (kind) {
			case "remember":
				return { action: "learn", target: "profile", reason: "explicit user fact" };
			case "deny":
				return { action: "learn", target: "profile", reason: "user boundary" };
			case "correction":
				return { action: "pending", target: "profile", reason: "user correction needs approval" };
			case "preference":
				return { action: "pending", target: "profile", reason: "inferred preference needs approval" };
			default:
				return { action: "drop", reason: "unhandled feedback kind" };
		}
	}

	private _triageSessionRecord(event: LearningEvent): TriageDecision {
		const { kind } = event.payload as { kind?: string };
		if (kind === "goal.completed") {
			return { action: "pending", target: "skill", reason: "potentially reusable workflow" };
		}
		if (kind === "turn.end") {
			// A resident learner must be able to improve across a long sequence of
			// ordinary user turns; requiring callers to manufacture goals turns the
			// graph into a benchmark-only workflow. SkillLearner applies the expensive
			// cooldown, minimum-history and value checks before it calls the model, so
			// short or tool-free turns still produce no artifact.
			return { action: "pending", target: "skill", reason: "candidate reusable turn sequence" };
		}
		if (kind === "session.summary") {
			return { action: "learn", target: "profile", reason: "session takeaway" };
		}
		return { action: "drop", reason: "unhandled session record" };
	}

	private _triageExternalFetch(event: LearningEvent): TriageDecision {
		const { kind, content } = event.payload as { kind?: string; content?: unknown };
		if (kind === "url" || kind === "topic" || kind === "explore") {
			const text = typeof content === "string" ? content : JSON.stringify(content ?? "");
			if (text.length < this.config.minContentLength) {
				return { action: "drop", reason: "too short" };
			}
			if (text.length > this.config.maxContentLength) {
				return { action: "drop", reason: "too long" };
			}
			return { action: "learn", target: "knowledge", reason: "external source" };
		}
		return { action: "drop", reason: "unhandled external fetch" };
	}

	private _triageFileChange(event: LearningEvent): TriageDecision {
		const { path: filePath } = event.payload as { path?: string };
		if (!filePath) return { action: "drop", reason: "missing path" };
		// Tools report native paths; on Windows that means `\` separators.
		// Normalize, then match on whole segments so `my-node_modules-utils`
		// is not mistaken for a `node_modules` directory.
		const segments = filePath.replace(/\\/g, "/").split("/");
		if (segments.includes("node_modules") || segments.includes(".git")) {
			return { action: "drop", reason: "ignored path" };
		}
		return { action: "learn", target: "graph", reason: "source file changed" };
	}

	private _triagePlugin(event: LearningEvent): TriageDecision {
		const { kind, content } = event.payload as { kind?: string; content?: unknown };
		if (kind !== "command.run") return { action: "drop", reason: "not a runnable command" };
		const text = typeof content === "string" ? content : JSON.stringify(content ?? "");
		if (text.length < this.config.minContentLength) {
			return { action: "drop", reason: "too short" };
		}
		if (text.length > this.config.maxContentLength) {
			return { action: "drop", reason: "too long" };
		}
		return { action: "learn", target: "plugin", reason: "plugin command output" };
	}

	private _triageCapabilityGap(event: LearningEvent): TriageDecision {
		const { description } = event.payload as { description?: unknown };
		const text = typeof description === "string" ? description : "";
		if (text.length < this.config.minContentLength) {
			return { action: "drop", reason: "too short" };
		}
		return { action: "pending", target: "capability_gap", reason: "missing capability needs design" };
	}

	private _extractText(result: unknown): string {
		const r = result as { output?: unknown; content?: unknown } | string | null | undefined;
		if (typeof (r as { output?: unknown })?.output === "string") return (r as { output: string }).output;
		if (typeof (r as { content?: unknown })?.content === "string") return (r as { content: string }).content;
		if (typeof r === "string") return r;
		if (r && typeof r === "object") return safeStringify(r);
		return "";
	}

	private _looksLikeEcho(text: string, toolName: string, args?: Record<string, unknown>): boolean {
		if (toolName === "bash" && typeof args?.["command"] === "string") {
			const command = args["command"].trim();
			if (text.trim() === command || text.trim().startsWith(command)) {
				return true;
			}
		}
		return false;
	}

	static fingerprint(text: unknown): string {
		const normalized = String(text).toLowerCase().replace(/\s+/g, " ").trim().slice(0, 2000);
		return createHash("sha256").update(normalized).digest("hex");
	}
}

/**
 * Redact common credential patterns before tool output is considered for
 * persistent learning. This is defense-in-depth; it may catch false
 * positives, which is preferable to leaking secrets into knowledge.jsonl.
 *
 * The primary choke point is {@link LearningBus.enqueue}, which redacts the
 * whole event payload before the event can be persisted to queue.jsonl;
 * {@link LearningProcessor} redacts again before triage/learner dispatch as
 * defense in depth, and triage applies it to extracted text so its
 * length/echo checks operate on the same redacted content the learners see.
 */
export function redactSecrets(text: string): string {
	if (typeof text !== "string") return text;
	return text
		.replace(/\b(api[_-]?key|token|password|secret|auth)\s*[:=]\s*\S+/gi, "$1: [redacted]")
		.replace(/\bAuthorization:\s*Bearer\s+\S+/gi, "Authorization: Bearer [redacted]")
		.replace(/\b(private[_-]?key|ssh[_-]?key)\s*[:=]\s*\S+/gi, "$1: [redacted]");
}

/** Redact every string in an event payload, returning a redacted copy. */
export function redactLearningEvent(event: LearningEvent): LearningEvent {
	return { ...event, payload: redactPayloadValue(event.payload, new WeakSet(), 0) as Record<string, unknown> };
}

/** Placeholder for payload values that cannot be safely redacted in place. */
const REDACTED_PLACEHOLDER = "[object]";
const MAX_REDACT_DEPTH = 10;

function redactPayloadValue(value: unknown, seen: WeakSet<object>, depth: number): unknown {
	if (typeof value === "string") return redactSecrets(value);
	if (depth > MAX_REDACT_DEPTH) return REDACTED_PLACEHOLDER;
	if (Array.isArray(value)) {
		if (seen.has(value)) return REDACTED_PLACEHOLDER;
		seen.add(value);
		return value.map((item) => redactPayloadValue(item, seen, depth + 1));
	}
	if (value && typeof value === "object") {
		// Only plain objects are walked; Maps, class instances, typed arrays,
		// etc. would explode into index-keyed objects, so replace them.
		const proto: unknown = Object.getPrototypeOf(value);
		if (proto !== Object.prototype && proto !== null) return REDACTED_PLACEHOLDER;
		if (seen.has(value)) return REDACTED_PLACEHOLDER;
		seen.add(value);
		const redacted: Record<string, unknown> = {};
		for (const [key, nested] of Object.entries(value)) {
			redacted[key] = redactPayloadValue(nested, seen, depth + 1);
		}
		return redacted;
	}
	return value;
}
