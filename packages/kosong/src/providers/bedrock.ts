/**
 * Hermes-compatible AWS Bedrock Converse provider.
 *
 * This is intentionally a separate transport from openai-compatible.ts:
 * Bedrock has no /chat/completions endpoint and credentials are resolved by
 * the AWS SDK default provider chain.
 */
import { BedrockRuntimeClient, ConverseCommand, ConverseStreamCommand } from "@aws-sdk/client-bedrock-runtime";
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

const DEFAULT_REGION = "us-east-1";
const DEFAULT_MAX_TOKENS = 4096;

interface BedrockClientLike {
	send(command: unknown, options?: { abortSignal?: AbortSignal }): Promise<any>;
}

export interface BedrockProviderOptions {
	region?: string;
	/** Injectable for request-level tests; production uses BedrockRuntimeClient. */
	client?: BedrockClientLike;
	clientFactory?: (region: string) => BedrockClientLike;
}

export class BedrockProvider implements Provider {
	private readonly defaultRegion?: string;
	private readonly injectedClient?: BedrockClientLike;
	private readonly clientFactory?: (region: string) => BedrockClientLike;
	private readonly clients = new Map<string, BedrockClientLike>();

	constructor(options: BedrockProviderOptions = {}) {
		this.defaultRegion = options.region;
		this.injectedClient = options.client;
		this.clientFactory = options.clientFactory;
	}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const streaming = Boolean(options.onTextDelta || options.onThinkingDelta || options.onToolCallDelta);
		const region =
			options.providerOptions?.awsRegion ??
			this.defaultRegion ??
			process.env["AWS_REGION"] ??
			process.env["AWS_DEFAULT_REGION"] ??
			DEFAULT_REGION;
		const input = buildConverseInput(options);
		const client = this.getClient(region);

		try {
			if (streaming) {
				const response = await client.send(new ConverseStreamCommand(input as any), { abortSignal: options.signal });
				return await consumeConverseStream(response?.stream, options);
			}
			const response = await client.send(new ConverseCommand(input as any), { abortSignal: options.signal });
			return normalizeConverseResponse(response);
		} catch (error) {
			if (error instanceof ProviderProtocolError) throw error;
			throw error;
		}
	}

	async recoverAfterError(error: unknown): Promise<boolean> {
		const value = error as { name?: unknown; code?: unknown; message?: unknown } | null;
		const fingerprint =
			`${String(value?.name ?? "")} ${String(value?.code ?? "")} ${String(value?.message ?? error)}`.toLowerCase();
		if (
			!["connection reset", "broken pipe", "socket hang up", "econnreset", "timeout"].some((part) =>
				fingerprint.includes(part),
			)
		)
			return false;
		for (const client of this.clients.values()) {
			const destroy = (client as { destroy?: () => void }).destroy;
			destroy?.();
		}
		this.clients.clear();
		return true;
	}

	private getClient(region: string): BedrockClientLike {
		if (this.injectedClient) return this.injectedClient;
		const cached = this.clients.get(region);
		if (cached) return cached;
		const client = this.clientFactory?.(region) ?? new BedrockRuntimeClient({ region });
		this.clients.set(region, client);
		return client;
	}
}

function buildConverseInput(options: ProviderChatOptions): Record<string, unknown> {
	const { system, messages } = convertMessagesToConverse(options.messages);
	const input: Record<string, unknown> = {
		modelId: options.modelName,
		messages,
		inferenceConfig: {
			maxTokens: options.maxOutputTokens ?? DEFAULT_MAX_TOKENS,
			...(options.temperature === undefined ? {} : { temperature: options.temperature }),
			...(typeof options.providerOptions?.bedrockTopP === "number"
				? { topP: options.providerOptions.bedrockTopP }
				: {}),
			...(Array.isArray(options.providerOptions?.bedrockStopSequences)
				? { stopSequences: options.providerOptions.bedrockStopSequences }
				: {}),
		},
	};
	if (system.length > 0) input["system"] = system;
	const tools = convertToolsToConverse(options.tools ?? []);
	if (tools.length > 0 && modelSupportsToolUse(options.modelName)) input["toolConfig"] = { tools };
	if (options.providerOptions?.bedrockGuardrailConfig)
		input["guardrailConfig"] = options.providerOptions.bedrockGuardrailConfig;
	return input;
}

function modelSupportsToolUse(model: string): boolean {
	const value = model.toLowerCase();
	return !["deepseek.r1", "deepseek-r1", "stability.", "cohere.embed", "amazon.titan-embed"].some((pattern) =>
		value.includes(pattern),
	);
}

function convertToolsToConverse(tools: ChatTool[]): Array<Record<string, unknown>> {
	return tools.map((tool) => ({
		toolSpec: {
			name: tool.function.name,
			description: tool.function.description,
			inputSchema: { json: tool.function.parameters },
		},
	}));
}

function convertMessagesToConverse(messages: ChatMessage[]): {
	system: Array<Record<string, unknown>>;
	messages: Array<{ role: "user" | "assistant"; content: Array<Record<string, unknown>> }>;
} {
	const system: Array<Record<string, unknown>> = [];
	const result: Array<{ role: "user" | "assistant"; content: Array<Record<string, unknown>> }> = [];

	for (const message of messages) {
		if (message.role === "system") {
			for (const part of contentParts(message.content)) {
				if ("text" in part) system.push({ text: (part as { text?: unknown })["text"] });
			}
			continue;
		}

		if (message.role === "tool") {
			const block = {
				toolResult: {
					toolUseId: message.toolCallId ?? "",
					content: [{ text: typeof message.content === "string" ? message.content : JSON.stringify(message.content) }],
				},
			};
			appendMessage(result, "user", [block]);
			continue;
		}

		const blocks = contentParts(message.content);
		if (message.role === "assistant") {
			for (const call of message.toolCalls ?? []) {
				blocks.push({ toolUse: { toolUseId: call.id, name: call.name, input: call.arguments } });
			}
			appendMessage(result, "assistant", blocks.length > 0 ? blocks : [{ text: " " }]);
		} else {
			appendMessage(result, "user", blocks.length > 0 ? blocks : [{ text: " " }]);
		}
	}

	if (result.length > 0 && result[0]?.role !== "user") result.unshift({ role: "user", content: [{ text: " " }] });
	if (result.length > 0 && result[result.length - 1]?.role !== "user")
		result.push({ role: "user", content: [{ text: " " }] });
	return { system, messages: result };
}

function appendMessage(
	messages: Array<{ role: "user" | "assistant"; content: Array<Record<string, unknown>> }>,
	role: "user" | "assistant",
	content: Array<Record<string, unknown>>,
): void {
	const previous = messages[messages.length - 1];
	if (previous?.role === role) previous.content.push(...content);
	else messages.push({ role, content });
}

function contentParts(content: string | ContentPart[]): Array<Record<string, unknown>> {
	if (typeof content === "string") return [{ text: content.trim() ? content : " " }];
	const result: Array<Record<string, unknown>> = [];
	for (const part of content) {
		if (typeof part === "string") {
			result.push({ text: part });
			continue;
		}
		if (part.type === "text") {
			result.push({ text: part.text?.trim() ? part.text : " " });
		} else if (part.type === "image_url") {
			const url = part.image_url?.url ?? "";
			if (url.startsWith("data:")) {
				const [header, data = ""] = url.split(",", 2);
				const mime = (header ?? "data:image/jpeg").slice(5).split(";", 1)[0] || "image/jpeg";
				result.push({
					image: {
						format: mime.split("/", 2)[1] ?? "jpeg",
						source: { bytes: Uint8Array.from(Buffer.from(data, "base64")) },
					},
				});
			} else {
				result.push({ text: `[Image: ${url}]` });
			}
		}
	}
	return result.length > 0 ? result : [{ text: " " }];
}

function normalizeConverseResponse(response: any): ProviderChatResponse {
	const blocks = response?.output?.message?.content;
	if (!Array.isArray(blocks))
		throw new ProviderProtocolError("Bedrock Converse response did not contain output.message.content");
	let content = "";
	const thinking: string[] = [];
	const toolCalls: ToolCall[] = [];
	for (const block of blocks) {
		if (typeof block?.text === "string") content += block.text;
		const reasoning = block?.reasoningContent?.text;
		if (typeof reasoning === "string") thinking.push(reasoning);
		const tool = block?.toolUse;
		if (tool)
			toolCalls.push({
				id: String(tool.toolUseId ?? ""),
				name: String(tool.name ?? ""),
				arguments: asObject(tool.input),
			});
	}
	return {
		content,
		toolCalls,
		finishReason: mapStopReason(response?.stopReason, toolCalls),
		usage: {
			promptTokens: response?.usage?.inputTokens ?? 0,
			completionTokens: response?.usage?.outputTokens ?? 0,
		},
		...(thinking.length > 0 ? { reasoning: thinking.join("\n\n") } : {}),
	};
}

async function consumeConverseStream(
	stream: AsyncIterable<any> | undefined,
	options: ProviderChatOptions,
): Promise<ProviderChatResponse> {
	if (!stream || typeof stream[Symbol.asyncIterator] !== "function")
		throw new ProviderProtocolError("Bedrock Converse stream was missing");
	let content = "";
	const thinking: string[] = [];
	const toolCalls = new Map<number, { id: string; name: string; json: string }>();
	let stopReason = "end_turn";
	let promptTokens = 0;
	let completionTokens = 0;
	let activeToolIndex: number | undefined;

	for await (const event of stream) {
		const start = event?.contentBlockStart;
		if (start?.start?.toolUse) {
			activeToolIndex = Number(start.contentBlockIndex ?? event?.contentBlockIndex ?? toolCalls.size);
			const tool = start.start.toolUse;
			toolCalls.set(activeToolIndex, { id: String(tool.toolUseId ?? ""), name: String(tool.name ?? ""), json: "" });
		}
		const delta = event?.contentBlockDelta?.delta;
		if (typeof delta?.text === "string") {
			content += delta.text;
			options.onTextDelta?.(delta.text);
		}
		if (typeof delta?.reasoningContent?.text === "string") {
			thinking.push(delta.reasoningContent.text);
			options.onThinkingDelta?.(delta.reasoningContent.text);
		}
		if (typeof delta?.toolUse?.input === "string" && activeToolIndex !== undefined) {
			const tool = toolCalls.get(activeToolIndex);
			if (tool) {
				tool.json += delta.toolUse.input;
				options.onToolCallDelta?.({ id: tool.id, name: tool.name, argumentsPartial: delta.toolUse.input });
			}
		}
		if (event?.contentBlockStop && activeToolIndex !== undefined) activeToolIndex = undefined;
		if (typeof event?.messageStop?.stopReason === "string") stopReason = event.messageStop.stopReason;
		const usage = event?.metadata?.usage;
		if (usage) {
			promptTokens = usage.inputTokens ?? promptTokens;
			completionTokens = usage.outputTokens ?? completionTokens;
		}
	}

	return {
		content,
		toolCalls: [...toolCalls.values()].map((tool) => ({
			id: tool.id,
			name: tool.name,
			arguments: asObject(tool.json),
		})),
		finishReason: mapStopReason(stopReason, [...toolCalls.values()]),
		usage: { promptTokens, completionTokens },
		...(thinking.length > 0 ? { reasoning: thinking.join("\n\n") } : {}),
	};
}

function asObject(value: unknown): Record<string, unknown> {
	if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
	if (typeof value === "string") {
		try {
			const parsed = JSON.parse(value);
			if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed as Record<string, unknown>;
		} catch {
			// Match Hermes' tolerant empty-object fallback for malformed tool JSON.
		}
	}
	return {};
}

function mapStopReason(reason: unknown, tools: unknown[]): string {
	if (tools.length > 0 && (!reason || reason === "end_turn")) return "tool_calls";
	return (
		(
			{
				end_turn: "stop",
				stop_sequence: "stop",
				tool_use: "tool_calls",
				max_tokens: "length",
				content_filtered: "content_filter",
				guardrail_intervened: "content_filter",
			} as Record<string, string>
		)[String(reason ?? "end_turn")] ?? "stop"
	);
}
