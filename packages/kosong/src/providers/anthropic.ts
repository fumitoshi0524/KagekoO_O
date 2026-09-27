/**
 * Anthropic Claude provider.
 *
 * Uses the official Anthropic Messages API via `@anthropic-ai/sdk`.
 */
import Anthropic from "@anthropic-ai/sdk";
import type {
	ContentBlock,
	ContentBlockParam,
	ImageBlockParam,
	Message,
	MessageCreateParams,
	MessageCreateParamsBase,
	MessageCreateParamsNonStreaming,
	MessageParam,
	RawMessageStreamEvent,
	TextBlock,
	TextBlockParam,
	ToolResultBlockParam,
	ToolUnion,
	ToolUseBlock,
	ToolUseBlockParam,
	URLImageSource,
} from "@anthropic-ai/sdk/resources/messages.js";
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

const ANTHROPIC_BASE_URL = "https://api.anthropic.com";
const DEFAULT_MAX_TOKENS = 4096;

export interface AnthropicProviderOptions {
	/** Anthropic API key. Falls back to the ANTHROPIC_API_KEY environment variable. */
	apiKey?: string;
	/** Bearer token for Anthropic-compatible providers that do not accept x-api-key. */
	authToken?: string;
	/** Optional override for the Anthropic API base URL. */
	baseUrl?: string;
	/** Provider-required headers merged into every SDK request. */
	defaultHeaders?: Record<string, string>;
	/** Model name used by this provider instance. */
	modelName?: string;
	/** Default value for `max_tokens` when not supplied in chat options. */
	defaultMaxTokens?: number;
}

export function createAnthropicProvider(options?: AnthropicProviderOptions): AnthropicProvider {
	return new AnthropicProvider(options);
}

export class AnthropicProvider implements Provider {
	readonly modelName?: string;
	readonly baseUrl?: string;
	private readonly apiKey?: string;
	private readonly authToken?: string;
	private readonly defaultHeaders?: Record<string, string>;
	private readonly defaultMaxTokens: number;
	private client: Anthropic | undefined;
	private clientKey: string | undefined;

	constructor(options?: AnthropicProviderOptions) {
		this.modelName = options?.modelName;
		this.baseUrl = options?.baseUrl ?? ANTHROPIC_BASE_URL;
		this.apiKey = options?.apiKey;
		this.authToken = options?.authToken;
		this.defaultHeaders = options?.defaultHeaders;
		this.defaultMaxTokens = options?.defaultMaxTokens ?? DEFAULT_MAX_TOKENS;
	}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const apiKey = this.authToken ? undefined : (options.apiKey ?? this.apiKey);
		const baseURL = options.baseUrl ?? this.baseUrl ?? ANTHROPIC_BASE_URL;
		const clientKey = JSON.stringify([apiKey, this.authToken, baseURL, this.defaultHeaders]);
		if (!this.client || this.clientKey !== clientKey) {
			this.client = new Anthropic({
				apiKey,
				authToken: this.authToken,
				baseURL,
				defaultHeaders: this.defaultHeaders,
			});
			this.clientKey = clientKey;
		}
		const client = this.client;

		const streaming = Boolean(options.onTextDelta || options.onThinkingDelta || options.onToolCallDelta);
		const { system, messages } = buildAnthropicMessages(options.messages);
		const tools = buildAnthropicTools(options.tools);

		const params: MessageCreateParamsBase & { stream: boolean } = {
			model: options.modelName,
			max_tokens: options.maxOutputTokens ?? this.defaultMaxTokens,
			messages,
			stream: streaming,
		};

		if (system !== undefined) {
			params.system = system;
		}

		if (tools.length > 0) {
			params.tools = tools;
		}

		if (options.temperature !== undefined) {
			params.temperature = options.temperature;
		}

		if (streaming) {
			return this.handleStream(client, params, options);
		}

		const response = await client.messages.create(params as MessageCreateParamsNonStreaming, {
			signal: options.signal,
		});
		return anthropicMessageToResponse(response.content, response.stop_reason, response.usage);
	}

	private async handleStream(
		client: Anthropic,
		params: MessageCreateParamsBase & { stream: boolean },
		options: ProviderChatOptions,
	): Promise<ProviderChatResponse> {
		const { stream, ...streamParams } = params;
		const streamInstance = client.messages.stream(streamParams as MessageCreateParams, {
			signal: options.signal,
		});

		let content = "";
		let finishReason = "stop";
		let promptTokens = 0;
		let completionTokens = 0;
		const toolCallAcc = new Map<number, { id: string; name: string; arguments: string }>();

		streamInstance.on("streamEvent", (event: RawMessageStreamEvent) => {
			switch (event.type) {
				case "content_block_start": {
					const block = event.content_block;
					if (block.type === "tool_use") {
						toolCallAcc.set(event.index, {
							id: block.id,
							name: block.name,
							arguments: "",
						});
					}
					break;
				}
				case "content_block_delta": {
					const delta = event.delta;
					if (delta.type === "text_delta") {
						content += delta.text;
						options.onTextDelta?.(delta.text);
					} else if (delta.type === "thinking_delta") {
						options.onThinkingDelta?.(delta.thinking);
					} else if (delta.type === "input_json_delta") {
						const acc = toolCallAcc.get(event.index);
						if (acc) {
							acc.arguments += delta.partial_json;
							options.onToolCallDelta?.({
								id: acc.id,
								name: acc.name,
								argumentsPartial: delta.partial_json,
							});
						}
					}
					break;
				}
				case "message_delta": {
					if (event.delta.stop_reason) {
						finishReason = mapFinishReason(event.delta.stop_reason);
					}
					if (event.usage) {
						promptTokens = event.usage.input_tokens ?? promptTokens;
						completionTokens = event.usage.output_tokens ?? completionTokens;
					}
					break;
				}
				case "message_start": {
					if (event.message.usage) {
						promptTokens = event.message.usage.input_tokens ?? promptTokens;
						completionTokens = event.message.usage.output_tokens ?? completionTokens;
					}
					break;
				}
			}
		});

		const finalMessage = await streamInstance.finalMessage();
		const toolCalls = buildToolCallsFromAccumulator(toolCallAcc);

		return {
			content,
			toolCalls,
			finishReason,
			usage: {
				promptTokens: finalMessage.usage?.input_tokens ?? promptTokens,
				completionTokens: finalMessage.usage?.output_tokens ?? completionTokens,
			},
		};
	}
}

function buildAnthropicMessages(messages: ChatMessage[]): {
	system?: string | TextBlockParam[];
	messages: MessageParam[];
} {
	const systemParts: string[] = [];
	const anthropicMessages: MessageParam[] = [];

	for (const message of messages) {
		if (message.role === "system") {
			systemParts.push(extractText(message.content));
			continue;
		}
		if (message.role === "assistant" && extractText(message.content) === "" && !message.toolCalls?.length) continue;

		anthropicMessages.push(toAnthropicMessage(message));
	}

	const system = systemParts.length > 0 ? systemParts.join("\n\n") : undefined;
	return { system, messages: anthropicMessages };
}

function toAnthropicMessage(message: ChatMessage): MessageParam {
	switch (message.role) {
		case "user": {
			return { role: "user", content: toAnthropicContent(message.content) };
		}
		case "assistant": {
			const contentBlocks = toAnthropicAssistantContent(message.content);
			for (const toolCall of message.toolCalls ?? []) {
				contentBlocks.push({
					type: "tool_use",
					id: toolCall.id,
					name: toolCall.name,
					input: toolCall.arguments,
				} satisfies ToolUseBlockParam);
			}
			return { role: "assistant", content: contentBlocks };
		}
		case "tool": {
			return {
				role: "user",
				content: [
					{
						type: "tool_result",
						tool_use_id: message.toolCallId ?? "",
						content: extractText(message.content),
						is_error: message.isError,
					} satisfies ToolResultBlockParam,
				],
			};
		}
		case "system":
			throw new Error("System messages must be extracted before converting Anthropic messages");
		default: {
			throw new Error(`Unsupported chat message role: ${String(message.role)}`);
		}
	}
}

function toAnthropicContent(content: string | ContentPart[]): string | ContentBlockParam[] {
	if (typeof content === "string") {
		return content;
	}

	return content.map((part) => {
		if (part.type === "text") {
			return { type: "text", text: part.text ?? "" };
		}
		if (part.type === "image_url") {
			const url = part.image_url?.url ?? "";
			if (url.startsWith("data:")) {
				const parsed = parseDataUrl(url);
				return {
					type: "image",
					source: {
						type: "base64",
						media_type: normalizeImageMimeType(parsed?.mimeType),
						data: parsed?.data ?? "",
					},
				} satisfies ImageBlockParam;
			}
			return {
				type: "image",
				source: { type: "url", url } satisfies URLImageSource,
			} satisfies ImageBlockParam;
		}
		if (part.type === "thinking") {
			return { type: "text", text: part.thinking ?? "" };
		}
		return { type: "text", text: JSON.stringify(part) };
	});
}

function toAnthropicAssistantContent(content: string | ContentPart[]): ContentBlockParam[] {
	if (typeof content === "string") {
		if (content === "") return [];
		return [{ type: "text", text: content }];
	}
	return toAnthropicContent(content) as ContentBlockParam[];
}

function buildAnthropicTools(tools?: ChatTool[]): ToolUnion[] {
	if (!tools || tools.length === 0) return [];
	return tools.map((tool) => ({
		name: tool.function.name,
		description: tool.function.description,
		input_schema: {
			type: "object" as const,
			...tool.function.parameters,
		},
	}));
}

function anthropicMessageToResponse(
	contentBlocks: ContentBlock[],
	stopReason: Message["stop_reason"],
	usage: Message["usage"],
): ProviderChatResponse {
	const content = contentBlocks
		.filter((block): block is TextBlock => block.type === "text")
		.map((block) => block.text)
		.join("");

	const toolCalls: ToolCall[] = contentBlocks
		.filter((block): block is ToolUseBlock => block.type === "tool_use")
		.map((block) => ({
			id: block.id,
			name: block.name,
			arguments: requireToolArguments(block.input, block.id),
		}));

	return {
		content,
		toolCalls,
		finishReason: mapFinishReason(stopReason),
		usage: {
			promptTokens: usage?.input_tokens ?? 0,
			completionTokens: usage?.output_tokens ?? 0,
		},
	};
}

function buildToolCallsFromAccumulator(acc: Map<number, { id: string; name: string; arguments: string }>): ToolCall[] {
	const entries = Array.from(acc.entries());
	entries.sort((a, b) => a[0] - b[0]);
	return entries.map(([, value]) => ({
		id: value.id,
		name: value.name,
		arguments: parseAnthropicToolArguments(value.arguments),
	}));
}

export function parseAnthropicToolArguments(raw?: string): Record<string, unknown> {
	if (!raw) return {};
	try {
		return requireToolArguments(JSON.parse(raw), "streamed");
	} catch (error) {
		if (error instanceof ProviderProtocolError) throw error;
		throw new ProviderProtocolError("Anthropic tool call returned malformed arguments", {
			cause: error,
			retryable: false,
		});
	}
}

function requireToolArguments(value: unknown, id: string): Record<string, unknown> {
	if (isRecord(value)) return value;
	throw new ProviderProtocolError(`Anthropic tool call ${id} returned malformed arguments`, { retryable: false });
}

function mapFinishReason(reason: string | null | undefined): string {
	if (!reason) return "stop";
	if (reason === "tool_use") return "tool_calls";
	if (reason === "max_tokens") return "length";
	return reason;
}

function extractText(content: string | ContentPart[]): string {
	if (typeof content === "string") return content;
	return content
		.filter((part): part is ContentPart & { type: "text" } => part.type === "text")
		.map((part) => part.text ?? "")
		.join("");
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseDataUrl(url: string): { mimeType: string; data: string } | undefined {
	const match = /^data:([^;]+);base64,(.+)$/.exec(url);
	if (!match) return undefined;
	return { mimeType: match[1] ?? "image/png", data: match[2] ?? "" };
}

function normalizeImageMimeType(value: string | undefined): "image/gif" | "image/jpeg" | "image/png" | "image/webp" {
	return value === "image/gif" || value === "image/jpeg" || value === "image/webp" ? value : "image/png";
}
