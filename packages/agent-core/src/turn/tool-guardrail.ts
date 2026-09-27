import type { ToolResult } from "./turn-runner.js";

export interface ToolFailureGuardrailOptions {
	/** Number of consecutive identical (tool, args) failures before forcing a stop. */
	readonly maxConsecutiveFailures?: number;
	/** Consecutive failures of one tool — with any arguments — before forcing a stop. */
	readonly maxFailureLoop?: number;
}

export interface ToolFailureObservation {
	readonly toolName: string;
	readonly args: unknown;
	readonly result: ToolResult;
}

export interface ToolFailureDecision {
	readonly consecutiveFailures: number;
	/** Consecutive failures of the same tool, regardless of arguments. */
	readonly failureStreak: number;
	/** Consecutive failures of the same tool with the same normalized error class. */
	readonly errorClassStreak: number;
	readonly forceStop: boolean;
	readonly reminder?: string;
}

const OBSERVATION_CLASS_MAX_LENGTH = 120;

// Escalating steering reminders before the loop force stop, mirroring
// STREAK_REMINDER_THRESHOLDS in turn-runner.ts.
const FAILURE_LOOP_REMINDER_THRESHOLDS = [3, 5];

/**
 * Collapse an error or observation text into a comparable class: volatile
 * details (UUIDs, long hex ids, absolute paths, numbers, quoted strings) are
 * stripped so that the same recurring failure or page is recognized even when
 * the model varies identifiers between attempts.
 */
export function normalizeObservationText(text: string): string {
	return text
		.replace(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g, " ")
		.replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g, " ")
		.replace(/(?:[A-Za-z]:[\\/]|\\\\|~\/|\/)[^\s]+/g, " ")
		.replace(/\b[0-9a-fA-F]{12,}\b/g, " ")
		.replace(/\b\d+(?:\.\d+)?\b/g, " ")
		.replace(/\s+/g, " ")
		.trim()
		.toLowerCase()
		.slice(0, OBSERVATION_CLASS_MAX_LENGTH);
}

/**
 * Tracks three failure sequences at once: identical (tool, args) signatures,
 * consecutive failures of the same tool regardless of arguments, and
 * consecutive failures of the same tool with the same normalized error class.
 * Any successful result resets all three, so legitimate retries with a changed
 * plan are not suppressed, but reissuing a failing call with tweaked arguments
 * can no longer reset the loop detectors.
 */
export class ToolFailureGuardrail {
	private readonly maxConsecutiveFailures: number;
	private readonly maxFailureLoop: number;
	private previousSignature: string | undefined;
	private consecutiveFailures = 0;
	private loopTool: string | undefined;
	private failureStreak = 0;
	private loopErrorClass: string | undefined;
	private errorClassStreak = 0;

	constructor({ maxConsecutiveFailures = 3, maxFailureLoop = 8 }: ToolFailureGuardrailOptions = {}) {
		if (!Number.isInteger(maxConsecutiveFailures) || maxConsecutiveFailures < 1)
			throw new TypeError("maxConsecutiveFailures must be a positive integer");
		if (!Number.isInteger(maxFailureLoop) || maxFailureLoop < 1)
			throw new TypeError("maxFailureLoop must be a positive integer");
		this.maxConsecutiveFailures = maxConsecutiveFailures;
		this.maxFailureLoop = maxFailureLoop;
	}

	observe({ toolName, args, result }: ToolFailureObservation): ToolFailureDecision {
		if (!result.isError) {
			this.reset();
			return { consecutiveFailures: 0, failureStreak: 0, errorClassStreak: 0, forceStop: false };
		}
		const signature = stableSignature(toolName, args);
		this.consecutiveFailures = signature === this.previousSignature ? this.consecutiveFailures + 1 : 1;
		this.previousSignature = signature;
		this.failureStreak = toolName === this.loopTool ? this.failureStreak + 1 : 1;
		this.loopTool = toolName;
		const errorClass = normalizeObservationText(resultText(result));
		const classKey = `${toolName}:${errorClass}`;
		this.errorClassStreak = classKey === this.loopErrorClass ? this.errorClassStreak + 1 : 1;
		this.loopErrorClass = classKey;
		const forceStop =
			this.consecutiveFailures >= this.maxConsecutiveFailures || this.failureStreak >= this.maxFailureLoop;
		return {
			consecutiveFailures: this.consecutiveFailures,
			failureStreak: this.failureStreak,
			errorClassStreak: this.errorClassStreak,
			forceStop,
			reminder: this.reminder(toolName),
		};
	}

	reset(): void {
		this.previousSignature = undefined;
		this.consecutiveFailures = 0;
		this.loopTool = undefined;
		this.failureStreak = 0;
		this.loopErrorClass = undefined;
		this.errorClassStreak = 0;
	}

	private reminder(toolName: string): string | undefined {
		const reminders: string[] = [];
		reminders.push(
			this.consecutiveFailures === 1
				? `Tool ${toolName} failed. Inspect the error and its unmet prerequisites before retrying; use only identifiers returned by successful calls. Reissuing this call with tweaked arguments is treated as the same failure. Change strategy instead — use a different tool, verify the current state first, or extract what you need another way.`
				: `Tool ${toolName} failed identically ${this.consecutiveFailures} times. Stop retrying this call; change strategy — use a different tool, verify the current state first, or extract what you need another way.`,
		);
		const sameError = this.errorClassStreak >= 2 ? " The same error repeats each time." : "";
		if (this.failureStreak >= this.maxFailureLoop) {
			reminders.push(
				`Tool ${toolName} has failed ${this.failureStreak} times in a row, even though the arguments varied.${sameError} No retry of this call is making progress; checkpointing this task for recovery or human review.`,
			);
		} else if (FAILURE_LOOP_REMINDER_THRESHOLDS.includes(this.failureStreak)) {
			reminders.push(
				`Tool ${toolName} has failed ${this.failureStreak} times in a row, even though the arguments varied.${sameError} Tweaking parameters of the same failing call is treated as the same failure. Change strategy: use a different tool, verify the current state first, or extract what you need another way.`,
			);
		}
		return reminders.join("\n");
	}
}

function resultText(result: ToolResult): string {
	if (typeof result.output === "string") return result.output;
	try {
		return JSON.stringify(result.output ?? "");
	} catch {
		return "";
	}
}

function stableSignature(toolName: string, args: unknown): string {
	try {
		return `${toolName}:${JSON.stringify(args ?? {})}`;
	} catch {
		return `${toolName}:[unserializable]`;
	}
}
