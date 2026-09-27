/**
 * Mistral AI provider.
 *
 * Uses the official Mistral TypeScript SDK (`@mistralai/mistralai`).
 */
import { Mistral } from "@mistralai/mistralai";
import type {
	ChatCompletionRequest,
	ChatCompletionRequestMessage,
	ChatCompletionRequestTool,
	ChatCompletionResponse,
	CompletionChunk,
	CompletionEvent,
	ContentChunk,
	DeltaMessage,
	ToolCall as MistralToolCall,
} from "@mistralai/mistralai/models/components";
import type {
	ChatMessage,
	ChatTool,
	ContentPart,
	Provider,
	ProviderChatOptions,
	ProviderChatResponse,
	ToolCall,
} from "../types.js";
import { ProviderProtocolError } from "../errors.js";

const MISTRAL_BASE_URL = "https://api.mistral.ai";

export interface MistralProviderOptions {
	/** Mistral API key. Falls back to the MISTRAL_API_KEY environment variable. */
	apiKey?: string;
	/** Optional override for the Mistral API base URL. */
	baseUrl?: string;
	/** Model name used by this provider instance. */
	modelName?: string;
}

export function createMistralProvider(options?: MistralProviderOptions): MistralProvider {
	return new MistralProvider(options);
}

export class MistralProvider implements Provider {
	readonly modelName?: string;
	readonly baseUrl?: string;
	private readonly apiKey?: string;

	constructor(options?: MistralProviderOptions) {
		this.modelName = options?.modelName;
		this.baseUrl = options?.baseUrl ?? MISTRAL_BASE_URL;
		this.apiKey = options?.apiKey;
	}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const client = new Mistral({
			apiKey: options.apiKey ?? this.apiKey,
			serverURL: options.baseUrl ?? this.baseUrl ?? MISTRAL_BASE_URL,
		});

		const streaming = Boolean(options.onTextDelta || options.onThinkingDelta || options.onToolCallDelta);
		const messages = buildMistralMessages(options.messages);
		const tools = buildMistralTools(options.tools);

		if (streaming) {
			const request: ChatCompletionRequest = {
				model: options.modelName,
				messages,
				stream: true,
				tools,
				temperature: options.temperature,
				maxTokens: options.maxOutputTokens,
			};
			return this.handleStream(client, request, options);
		}

		const request: ChatCompletionRequest = {
			model: options.modelName,
			messages,
			stream: false,
			tools,
			temperature: options.temperature,
			maxTokens: options.maxOutputTokens,
		};

		const response = await client.chat.complete(request);
		return mistralResponseToResponse(response);
	}

	private async handleStream(
		client: Mistral,
		request: ChatCompletionRequest,
		options: ProviderChatOptions,
	): Promise<ProviderChatResponse> {
		const stream = await client.chat.stream(request);

		let content = "";
		let finishReason = "stop";
		let promptTokens = 0;
		let completionTokens = 0;
		const toolCallAcc = new Map<number, { id: string; name: string; arguments: string }>();

		for await (const event of stream as AsyncIterable<CompletionEvent>) {
			const chunk = event.data;
			if (!chunk) continue;

			const choice = chunk.choices?.[0];
			if (!choice) continue;

			const delta = choice.delta;
			if (delta) {
				appendDeltaContent(delta, (text) => {
					content += text;
					options.onTextDelta?.(text);
				});
				appendDeltaToolCalls(delta, toolCallAcc, options);
			}

			if (choice.finishReason) {
				finishReason = mapMistralFinishReason(choice.finishReason);
			}

			if (chunk.usage) {
				promptTokens = chunk.usage.promptTokens ?? promptTokens;
				completionTokens = chunk.usage.completionTokens ?? completionTokens;
			}
		}

		const toolCalls = buildToolCallsFromAccumulator(toolCallAcc);
		return {
			content,
			toolCalls,
			finishReason,
			usage: { promptTokens, completionTokens },
		};
	}
}

function buildMistralMessages(messages: ChatMessage[]): ChatCompletionRequestMessage[] {
	return messages.map((message) => {
		switch (message.role) {
			case "system": {
				return { role: "system", content: extractText(message.content) };
			}
			case "user": {
				return { role: "user", content: toMistralContent(message.content) };
			}
			case "assistant": {
				const toolCalls = (message.toolCalls ?? []).map((tc): MistralToolCall => ({
					id: tc.id,
					type: "function",
					function: {
						name: tc.name,
						arguments: tc.arguments,
					},
				}));
				return {
					role: "assistant",
					content: toMistralContent(message.content),
					toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
				};
			}
			case "tool": {
				return {
					role: "tool",
					content: toMistralContent(message.content),
					toolCallId: message.toolCallId ?? "",
				};
			}
			default: {
				const exhaustive: never = message.role;
				throw new Error(`Unsupported chat message role: ${String(exhaustive)}`);
			}
		}
	});
}

function toMistralContent(content: string | ContentPart[]): string | ContentChunk[] {
	if (typeof content === "string") {
		return content;
	}

	return content.map((part) => {
		if (part.type === "text") {
			return { type: "text", text: part.text ?? "" };
		}
		if (part.type === "image_url") {
			return { type: "image_url", imageUrl: { url: part.image_url?.url ?? "" } };
		}
		if (part.type === "thinking") {
			return { type: "text", text: part.thinking ?? "" };
		}
		return { type: "text", text: JSON.stringify(part) };
	});
}

function buildMistralTools(tools?: ChatTool[]): ChatCompletionRequestTool[] | undefined {
	if (!tools || tools.length === 0) return undefined;
	return tools.map((tool) => ({
		type: "function" as const,
		function: {
			name: tool.function.name,
			description: tool.function.description,
			parameters: tool.function.parameters,
		},
	}));
}

function mistralResponseToResponse(response: ChatCompletionResponse | undefined): ProviderChatResponse {
	if (!response) {
		return { content: "", toolCalls: [], finishReason: "stop", usage: { promptTokens: 0, completionTokens: 0 } };
	}

	const choice = response.choices?.[0];
	const message = choice?.message;
	const content = extractMistralContent(message?.content);
	const toolCalls: ToolCall[] = (message?.toolCalls ?? []).map((tc) => ({
		id: tc.id ?? "",
		name: tc.function?.name ?? "",
		arguments: parseMistralToolArguments(tc.function?.arguments),
	}));

	return {
		content,
		toolCalls,
		finishReason: mapMistralFinishReason(choice?.finishReason),
		usage: {
			promptTokens: response.usage?.promptTokens ?? 0,
			completionTokens: response.usage?.completionTokens ?? 0,
		},
	};
}

function extractMistralContent(content: string | ContentChunk[] | null | undefined): string {
	if (content === null || content === undefined) return "";
	if (typeof content === "string") return content;
	return content
		.filter((chunk): chunk is ContentChunk & { type: "text" } => chunk.type === "text")
		.map((chunk) => ("text" in chunk ? chunk.text : ""))
		.join("");
}

function appendDeltaContent(delta: DeltaMessage, onText: (text: string) => void): void {
	const content = delta.content;
	if (content === null || content === undefined) return;
	if (typeof content === "string") {
		onText(content);
		return;
	}
	for (const chunk of content) {
		if (chunk.type === "text" && "text" in chunk) {
			onText(chunk.text);
		}
	}
}

function appendDeltaToolCalls(
	delta: DeltaMessage,
	acc: Map<number, { id: string; name: string; arguments: string }>,
	options: ProviderChatOptions,
): void {
	if (!delta.toolCalls || delta.toolCalls.length === 0) return;

	for (const toolCall of delta.toolCalls) {
		const idx = toolCall.index ?? 0;
		let entry = acc.get(idx);
		if (!entry) {
			entry = {
				id: toolCall.id ?? "",
				name: toolCall.function?.name ?? "",
				arguments: "",
			};
			acc.set(idx, entry);
		}
		if (toolCall.id) entry.id = toolCall.id;
		if (toolCall.function?.name) entry.name = toolCall.function.name;

		const args = toolCall.function?.arguments;
		if (typeof args === "string") {
			entry.arguments += args;
			options.onToolCallDelta?.({
				id: entry.id,
				name: entry.name,
				argumentsPartial: args,
			});
		} else if (args && typeof args === "object") {
			entry.arguments = JSON.stringify(args);
		}
	}
}

function buildToolCallsFromAccumulator(acc: Map<number, { id: string; name: string; arguments: string }>): ToolCall[] {
	const entries = Array.from(acc.entries());
	entries.sort((a, b) => a[0] - b[0]);
	return entries.map(([, value]) => ({
		id: value.id,
		name: value.name,
		arguments: parseMistralToolArguments(value.arguments),
	}));
}

export function parseMistralToolArguments(raw: string | Record<string, unknown> | undefined): Record<string, unknown> {
	if (!raw) return {};
	if (typeof raw === "object") {
		if (!Array.isArray(raw)) return raw;
		throw new ProviderProtocolError("Mistral tool call returned malformed arguments", { retryable: false });
	}
	try {
		const parsed = JSON.parse(raw);
		if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed))
			return parsed as Record<string, unknown>;
		throw new Error("arguments must be a JSON object");
	} catch (error) {
		throw new ProviderProtocolError("Mistral tool call returned malformed arguments", {
			cause: error,
			retryable: false,
		});
	}
}

function mapMistralFinishReason(reason: unknown): string {
	if (!reason) return "stop";
	if (reason === "tool_calls") return "tool_calls";
	if (reason === "length" || reason === "model_length") return "length";
	return typeof reason === "string" ? reason : String(reason);
}

function extractText(content: string | ContentPart[]): string {
	if (typeof content === "string") return content;
	return content
		.filter((part): part is ContentPart & { type: "text" } => part.type === "text")
		.map((part) => part.text ?? "")
		.join("");
}
