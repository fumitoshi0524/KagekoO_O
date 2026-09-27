/**
 * Faux LLM for testing the agent loop without an API key.
 *
 * Parses simple natural-language commands and emits deterministic tool calls
 * so we can verify that the loop actually uses function calling instead of
 * falling back to shell scripts.
 */
import type { ChatOptions, ChatResponse, ChatTool, ToolCall } from "./types.js";

export interface FauxLLMOptions {
	systemPrompt?: string;
	modelName?: string;
	failureSequence?: boolean[];
}

export class FauxLLM {
	private systemPrompt: string;
	readonly modelName: string;
	private failureSequence: boolean[];
	private failureIndex = 0;

	constructor({ systemPrompt = "", modelName = "faux", failureSequence = [] }: FauxLLMOptions = {}) {
		this.systemPrompt = systemPrompt;
		this.modelName = modelName;
		this.failureSequence = failureSequence;
	}

	async chat({ messages, tools }: ChatOptions): Promise<ChatResponse> {
		if (this.failureIndex < this.failureSequence.length) {
			const shouldFail = this.failureSequence[this.failureIndex++];
			if (shouldFail) {
				const err = new Error("transient LLM error");
				(err as { isRetryableError?: () => boolean }).isRetryableError = () => true;
				throw err;
			}
		}

		const lastUser = [...messages].reverse().find((m) => m.role === "user");
		const text = extractText(lastUser?.content ?? "");

		// If a tool was already called for this prompt, finish.
		const hadToolResult = messages.some((m) => m.role === "tool");
		if (hadToolResult) {
			return {
				toolCalls: [],
				content: "Done.",
				finishReason: "stop",
				usage: { promptTokens: 0, completionTokens: 0 },
			};
		}

		const toolCalls: ToolCall[] = [];
		const lower = text.toLowerCase();

		if (lower.includes("read ") || lower.includes("show me ")) {
			const path = extractPath(text);
			if (path && tools?.some((t) => t.function.name === "read")) {
				toolCalls.push({ id: "call_1", name: "read", arguments: { path } });
			}
		} else if (lower.includes("write ") || lower.includes("create ")) {
			const path = extractPath(text);
			const content = extractAfter(text, ["with ", "containing ", "saying "]);
			if (path && tools?.some((t) => t.function.name === "write")) {
				toolCalls.push({ id: "call_2", name: "write", arguments: { path, content: content || "" } });
			}
		} else if (lower.includes("list ") || lower.includes("ls ")) {
			const path = extractPath(text) || ".";
			if (tools?.some((t) => t.function.name === "ls")) {
				toolCalls.push({ id: "call_3", name: "ls", arguments: { path } });
			}
		}

		if (toolCalls.length > 0) {
			return {
				toolCalls,
				content: "",
				finishReason: "tool_calls",
				usage: { promptTokens: 0, completionTokens: 0 },
			};
		}

		return {
			toolCalls: [],
			content: `I don't know how to handle that yet.`,
			finishReason: "stop",
			usage: { promptTokens: 0, completionTokens: 0 },
		};
	}

	isRetryableError(error: unknown): boolean {
		if (error && typeof (error as { isRetryableError?: () => boolean }).isRetryableError === "function") {
			return (error as { isRetryableError: () => boolean }).isRetryableError();
		}
		return false;
	}
}

type ContentPartLike = { type?: string; text?: string };

function extractText(content: string | ContentPartLike[]): string {
	if (typeof content === "string") return content;
	if (Array.isArray(content)) {
		return content
			.filter((p): p is ContentPartLike & { type: "text" } => p?.type === "text")
			.map((p) => p.text ?? "")
			.join(" ");
	}
	return String(content ?? "");
}

function extractPath(text: string): string | undefined {
	const m = text.match(/(?:file|path|directory|dir|folder)\s+[`"']?([^`'"\s]+)[`"']?/i);
	return m?.[1];
}

function extractAfter(text: string, prefixes: string[]): string {
	for (const prefix of prefixes) {
		const idx = text.toLowerCase().indexOf(prefix);
		if (idx !== -1) {
			return text.slice(idx + prefix.length).trim();
		}
	}
	return "";
}
