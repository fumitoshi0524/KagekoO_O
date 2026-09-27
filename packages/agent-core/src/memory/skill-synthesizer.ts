import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { LlmClient, SessionEvent, SynthesizedSkill } from "./types.js";

const MAX_TRANSCRIPT_BYTES = 16 * 1024;
const MAX_ARG_VALUE_LENGTH = 80;
const SENSITIVE_ARG_KEYS = /password|secret|token|key|auth|credential|api[_-]?key/i;
export const DEFAULT_SKILL_SYNTHESIS_TIMEOUT_MS = 60_000;
const MIN_DESCRIPTION_LENGTH = 24;
const MIN_INSTRUCTIONS_LENGTH = 80;
const PLACEHOLDER_CONTENT = /(?:\b(?:todo|tbd|lorem ipsum)\b|<[^>]+>|\{\{[^}]+\}\})/i;

export interface SkillSynthesizerOptions {
	cwd: string;
	/** Directory for auto-generated skills, injected by the composition root. */
	autoSkillDir: string;
	llm?: LlmClient;
	/**
	 * Bound on the synthesis LLM call. Synthesis is awaited inside
	 * `LearningBus.flush()` during session close, so it must never hang.
	 * Defaults to 60s.
	 */
	timeoutMs?: number;
}

/**
 * Synthesize a SKILL.md from a completed task record.
 */
export class SkillSynthesizer {
	readonly cwd: string;
	readonly llm?: LlmClient;
	readonly autoSkillDir: string;
	readonly timeoutMs: number;

	constructor({ cwd, autoSkillDir, llm, timeoutMs }: SkillSynthesizerOptions) {
		this.cwd = cwd;
		this.llm = llm;
		this.autoSkillDir = autoSkillDir;
		this.timeoutMs = timeoutMs ?? DEFAULT_SKILL_SYNTHESIS_TIMEOUT_MS;
	}

	async synthesize(events: SessionEvent[], { name }: { name?: string } = {}): Promise<SynthesizedSkill | undefined> {
		if (!this.llm || events.length === 0) {
			return undefined;
		}

		const prompt = [
			"You are the resident learner for an AI agent. Derive one genuinely reusable procedural skill from recurring patterns in the session transcript.",
			"Generalize across the observed tasks, tools, providers, and entity names. Do not merely restate the latest task or hard-code transcript values.",
			"Prefer one coherent skill with the smallest useful workflow. Do not split an operation across several tools when one advertised tool already completes it.",
			"Produce:",
			"1. A short domain-neutral skill name (kebab-case, no spaces) that can route later tasks with the same workflow shape.",
			"2. A one-sentence description stating when the transferable workflow should be used.",
			"3. Concise executable instructions for another agent.",
			"",
			"The instructions must explicitly require the agent to:",
			"- inspect the advertised tool schemas or contracts before choosing operations and arguments;",
			"- select the minimal capable tool chain and preserve every returned identifier, URI, or handle instead of guessing it;",
			"- satisfy prerequisites and execute dependent operations in dependency order;",
			"- handle rejected operations and errors with bounded recovery or retry behavior, without duplicating successful side effects; and",
			"- verify the final state or postconditions with authoritative results or read-back before reporting success.",
			"",
			"Transcript:",
			formatEvents(events, MAX_TRANSCRIPT_BYTES),
			"",
			"Respond in this exact format:",
			"name: <name>",
			"description: <description>",
			"---",
			"<instructions>",
		].join("\n");

		try {
			const response = await withTimeout(
				this.llm.chat({ messages: [{ role: "user", content: prompt }], tools: [] }),
				this.timeoutMs,
			);
			const parsed = parseSkillResponse(response.content ?? "");
			if (!parsed) throw new Error("Model returned an invalid skill document.");
			if (name) parsed.name = name;
			const sanitized = sanitizeSkillName(parsed.name);
			if (!sanitized) throw new Error("Model returned an invalid skill name.");
			parsed.name = sanitized;
			validateSkillQuality(parsed);
			return parsed;
		} catch (error) {
			// Explicit skill generation and resident learning must remain auditable.
			// Returning undefined here made provider failures, timeouts, and malformed
			// generated instructions indistinguishable from "nothing to learn".
			throw new Error(`Skill synthesis failed: ${error instanceof Error ? error.message : String(error)}`, {
				cause: error,
			});
		}
	}

	async writeSkill(skill: SynthesizedSkill & { learnedThroughTurns?: number }): Promise<string> {
		const name = sanitizeSkillName(skill.name);
		if (!name) {
			throw new Error("Invalid skill name.");
		}
		skill.name = name;
		validateSkillQuality(skill);
		const dir = path.join(this.autoSkillDir, skill.name);
		await fs.mkdir(dir, { recursive: true });
		const filePath = path.join(dir, "SKILL.md");
		const content = [
			"---",
			`name: ${skill.name}`,
			`description: ${skill.description}`,
			`type: prompt`,
			"when-to-use: Auto-generated from a previous successful task.",
			...(Number.isSafeInteger(skill.learnedThroughTurns) && skill.learnedThroughTurns! >= 0
				? [`learned-through-turns: ${skill.learnedThroughTurns}`]
				: []),
			"---",
			"",
			skill.instructions,
		].join("\n");
		await fs.writeFile(filePath, content, "utf-8");
		return filePath;
	}
}

export function validateSkillQuality(skill: SynthesizedSkill): void {
	const description = skill.description?.trim() ?? "";
	const instructions = skill.instructions?.trim() ?? "";
	if (description.length < MIN_DESCRIPTION_LENGTH) {
		throw new Error("Generated skill description is too short to route reliably.");
	}
	if (instructions.length < MIN_INSTRUCTIONS_LENGTH) {
		throw new Error("Generated skill instructions are too short to be executable.");
	}
	if (PLACEHOLDER_CONTENT.test(description) || PLACEHOLDER_CONTENT.test(instructions)) {
		throw new Error("Generated skill contains unresolved placeholder content.");
	}
}

/**
 * Same timeout pattern as `KnowledgeStore.summarizeWithTimeout`: reject after
 * `ms` so a hung provider call cannot block session close.
 */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error("Skill synthesis timed out.")), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

function formatEvents(events: SessionEvent[], maxBytes = MAX_TRANSCRIPT_BYTES): string {
	const text = events
		.map((e) => {
			if (e.type === "user.prompt") {
				return e.data.origin === undefined || e.data.origin === "user" ? `User: ${e.data.content}` : "";
			}
			if (e.type === "assistant.text") return `Assistant: ${e.data.content}`;
			if (e.type === "tool.call") {
				return `Tool call: ${e.data.call.name}(${redactArgs(e.data.call.arguments)})`;
			}
			if (e.type === "tool.result") return `Tool result: ${String(e.data.result.output ?? "").slice(0, 200)}`;
			return JSON.stringify(e);
		})
		.join("\n");
	const buf = Buffer.from(text, "utf-8");
	if (buf.length <= maxBytes) return text;
	return buf.subarray(0, maxBytes).toString("utf-8");
}

function redactArgs(args: unknown): string {
	if (!args || typeof args !== "object") return "";
	const redacted: Record<string, string> = {};
	for (const [key, value] of Object.entries(args as Record<string, unknown>)) {
		if (SENSITIVE_ARG_KEYS.test(key)) {
			redacted[key] = "[redacted]";
		} else {
			const str = String(value);
			redacted[key] = str.length > MAX_ARG_VALUE_LENGTH ? `${str.slice(0, MAX_ARG_VALUE_LENGTH)}…` : str;
		}
	}
	return JSON.stringify(redacted);
}

export function sanitizeSkillName(name: unknown): string | undefined {
	if (!name) return undefined;
	const cleaned = String(name)
		.toLowerCase()
		.replace(/[^a-z0-9_-]+/g, "-")
		.replace(/^-+|-+$/g, "");
	if (!cleaned || cleaned.length > 64) return undefined;
	return cleaned;
}

function parseSkillResponse(text: string): SynthesizedSkill | undefined {
	const lines = text.split(/\r?\n/);
	let name: string | undefined;
	let description: string | undefined;
	let instructionsStart = -1;
	for (let i = 0; i < lines.length; i++) {
		const line = lines[i] as string;
		if (line.startsWith("name:")) {
			name = line.slice("name:".length).trim();
		} else if (line.startsWith("description:")) {
			description = line.slice("description:".length).trim();
		} else if (line.trim() === "---") {
			instructionsStart = i + 1;
			break;
		}
	}
	if (!name || !description) return undefined;
	const instructions = (instructionsStart === -1 ? "" : lines.slice(instructionsStart).join("\n")).trim();
	return { name, description, instructions };
}
