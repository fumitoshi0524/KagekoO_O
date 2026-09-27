/**
 * OpenAI-compatible chat provider.
 *
 * Uses the standard `/chat/completions` endpoint and SSE streaming format.
 * This covers OpenAI, DeepSeek, Qwen, Moonshot, MiniMax (OpenAI-compatible
 * mode), xAI, OpenRouter, and any other provider that speaks the same wire
 * protocol.
 */
import { randomUUID } from "node:crypto";
import type {
	ChatMessage,
	ChatTool,
	ContentPart,
	Provider,
	ProviderChatOptions,
	ProviderChatResponse,
	ProviderRequestOptions,
	ToolCall,
} from "../types.js";
import { ProviderConnectionError, ProviderError, ProviderProtocolError, parseRetryAfter } from "../errors.js";
import { OPENAI_COMPATIBLE_REGISTRY } from "../types.js";
import { environmentProxyCompatibilityHint, fetchProviderRequest } from "../live-catalog-fetch.js";
export { OPENAI_COMPATIBLE_REGISTRY } from "../types.js";

export interface OpenAICompatibleProviderOptions {
	providerId?: string;
	baseUrl?: string;
	apiKey?: string;
	headers?: Record<string, string>;
}

/**
 * Built-in default base URLs for providers that speak the OpenAI-compatible
 * `/chat/completions` protocol.
 */

/**
 * Create an OpenAI-compatible provider for a known provider id.
 */
export function createOpenAICompatibleProvider(
	providerId: string,
	options: OpenAICompatibleProviderOptions = {},
): OpenAICompatibleProvider {
	const baseUrl = options.baseUrl ?? OPENAI_COMPATIBLE_REGISTRY[providerId];
	return new OpenAICompatibleProvider({ ...options, providerId, baseUrl });
}

interface OpenAIChatCompletion {
	id?: string;
	choices?: Array<{
		message: {
			role?: string;
			content?: string | null | Array<OpenAIContentPart>;
			tool_calls?: Array<OpenAIToolCall>;
		};
		finish_reason?: string | null;
	}>;
	usage?: {
		prompt_tokens?: number;
		completion_tokens?: number;
	};
}

interface OpenAIChatCompletionChunk {
	id?: string;
	choices?: Array<{
		index?: number;
		delta: {
			role?: string;
			content?: string | null;
			tool_calls?: Array<{
				index?: number;
				id?: string;
				type?: string;
				function?: {
					name?: string;
					arguments?: string;
				};
			}>;
		};
		finish_reason?: string | null;
	}>;
	usage?: {
		prompt_tokens?: number;
		completion_tokens?: number;
	};
}

interface OpenAIContentPart {
	type?: string;
	text?: string;
	image_url?: { url?: string };
}

interface OpenAIToolCall {
	id?: string;
	type?: string;
	function?: {
		name?: string;
		arguments?: string;
	};
}

export class OpenAICompatibleProvider implements Provider {
	readonly providerId?: string;
	readonly baseUrl?: string;
	readonly apiKey?: string;
	readonly headers?: Record<string, string>;

	constructor(options: OpenAICompatibleProviderOptions = {}) {
		this.providerId = options.providerId;
		this.baseUrl = options.baseUrl;
		this.apiKey = options.apiKey;
		this.headers = options.headers;
	}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const streaming = Boolean(options.onTextDelta || options.onThinkingDelta || options.onToolCallDelta);
		const baseUrl = this.resolveBaseUrl(options.baseUrl);
		const apiKey = options.apiKey ?? this.apiKey;

		const requestBody = buildRequestBody(options, streaming, this.providerId);
		let response: Response;
		try {
			response = await fetchProviderRequest(`${baseUrl}/chat/completions`, {
				method: "POST",
				headers: buildHeaders(apiKey, this.headers, this.providerId, options.providerOptions, options.modelName),
				body: JSON.stringify(requestBody),
				signal: options.signal,
			});
		} catch (error) {
			throw providerConnectionError(this.providerId ?? "OpenAI-compatible provider", baseUrl, error);
		}

		if (!response.ok) {
			throw await buildError(response);
		}

		if (streaming) {
			return this.handleStream(response, options);
		}

		return this.handleNonStream(response);
	}

	private resolveBaseUrl(override?: string): string {
		const base = override ?? this.baseUrl;
		if (!base) {
			throw new Error("OpenAICompatibleProvider requires a baseUrl.");
		}
		return base.replace(/\/$/, "");
	}

	private async handleNonStream(response: Response): Promise<ProviderChatResponse> {
		let data: OpenAIChatCompletion;
		let body = "";
		try {
			body = await response.text();
			data = JSON.parse(body) as OpenAIChatCompletion;
		} catch (error) {
			const mediaType = response.headers.get("content-type")?.split(";", 1)[0]?.trim() || "unknown content-type";
			const shape = !body
				? "empty body"
				: body.trimStart().startsWith("data:")
					? body.includes('"tool_calls"')
						? "SSE tool-call payload"
						: "SSE completion payload"
					: body.trimStart().startsWith("<")
						? "HTML-like payload"
						: "non-JSON payload";
			throw new ProviderProtocolError(
				`OpenAI-compatible response returned malformed JSON (${mediaType}, ${Buffer.byteLength(body, "utf8")} bytes, ${shape})`,
				{ cause: error },
			);
		}
		if (!Array.isArray(data.choices) || data.choices.length === 0) {
			throw new ProviderProtocolError("OpenAI-compatible response did not contain a completion choice");
		}
		const choice = data.choices?.[0];
		const message = choice?.message;

		const content = extractContent(message?.content);
		const toolCalls = extractToolCalls(message?.tool_calls ?? []);
		const finishReason = mapFinishReason(choice?.finish_reason);

		return {
			content,
			toolCalls,
			finishReason,
			usage: {
				promptTokens: data.usage?.prompt_tokens ?? 0,
				completionTokens: data.usage?.completion_tokens ?? 0,
			},
		};
	}

	private async handleStream(response: Response, options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const reader = response.body?.getReader();
		if (!reader) {
			throw new Error("Streaming response has no readable body.");
		}

		const decoder = new TextDecoder();
		let buffer = "";
		let content = "";
		let finishReason = "stop";
		let promptTokens = 0;
		let completionTokens = 0;
		const toolCallAcc = new Map<number, { id: string; name: string; arguments: string }>();
		let eventData: string[] = [];
		let sawDone = false;
		const processEvent = (): boolean => {
			if (eventData.length === 0) return false;
			const payload = eventData.join("\n");
			eventData = [];
			if (payload === "[DONE]") {
				sawDone = true;
				return true;
			}

			let parsed: unknown;
			try {
				parsed = JSON.parse(payload);
			} catch (error) {
				throw new ProviderProtocolError("OpenAI-compatible stream returned malformed JSON data", { cause: error });
			}
			if (!isObject(parsed))
				throw new ProviderProtocolError("OpenAI-compatible stream returned a non-object data frame");
			if (isObject(parsed["error"])) {
				const message =
					typeof parsed["error"]["message"] === "string" ? parsed["error"]["message"] : "unknown provider error";
				const status = typeof parsed["error"]["status"] === "number" ? parsed["error"]["status"] : undefined;
				const code = typeof parsed["error"]["code"] === "string" ? parsed["error"]["code"] : undefined;
				throw new ProviderError(`OpenAI-compatible stream error: ${message}`, { status, code });
			}

			const chunk = parsed as unknown as OpenAIChatCompletionChunk;
			const choice = chunk.choices?.[0];
			if (choice) {
				const delta = choice.delta;
				if (typeof delta.content === "string") {
					content += delta.content;
					options.onTextDelta?.(delta.content);
				}
				if (Array.isArray(delta.tool_calls)) {
					for (const d of delta.tool_calls) {
						const idx = d.index ?? 0;
						let acc = toolCallAcc.get(idx);
						if (!acc) {
							acc = { id: d.id ?? "", name: d.function?.name ?? "", arguments: "" };
							toolCallAcc.set(idx, acc);
						}
						if (d.id) acc.id = d.id;
						if (d.function?.name) acc.name = d.function.name;
						if (typeof d.function?.arguments === "string") {
							acc.arguments += d.function.arguments;
							options.onToolCallDelta?.({ id: acc.id, name: acc.name, argumentsPartial: d.function.arguments });
						}
					}
				}
				if (choice.finish_reason) finishReason = mapFinishReason(choice.finish_reason);
			}
			if (chunk.usage) {
				promptTokens = chunk.usage.prompt_tokens ?? promptTokens;
				completionTokens = chunk.usage.completion_tokens ?? completionTokens;
			}
			return false;
		};
		const processLine = (line: string): boolean => {
			const normalized = line.endsWith("\r") ? line.slice(0, -1) : line;
			if (normalized === "") return processEvent();
			if (normalized.startsWith(":")) return false;
			if (!normalized.startsWith("data:")) return false;
			const value = normalized.slice("data:".length);
			eventData.push(value.startsWith(" ") ? value.slice(1) : value);
			return false;
		};

		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) {
					buffer += decoder.decode();
					if (buffer) processLine(buffer);
					processEvent();
					break;
				}

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() ?? "";

				for (const line of lines) {
					if (processLine(line)) {
						return this.buildStreamResult(content, toolCallAcc, finishReason, promptTokens, completionTokens);
					}
				}
			}
		} finally {
			try {
				await reader.cancel();
			} catch {
				// The stream may already be closed or errored; ownership is still released below.
			}
			reader.releaseLock();
		}

		const result = this.buildStreamResult(content, toolCallAcc, finishReason, promptTokens, completionTokens);
		return sawDone ? result : { ...result, truncated: true };
	}

	private buildStreamResult(
		content: string,
		toolCallAcc: Map<number, { id: string; name: string; arguments: string }>,
		finishReason: string,
		promptTokens: number,
		completionTokens: number,
	): ProviderChatResponse {
		const toolCalls = buildToolCallsFromAccumulator(toolCallAcc);
		return {
			content,
			toolCalls,
			finishReason,
			usage: { promptTokens, completionTokens },
		};
	}
}

function providerConnectionError(providerName: string, baseUrl: string, error: unknown): ProviderConnectionError {
	const cause = error instanceof Error ? error : new Error(String(error));
	const code = errorCode(cause);
	const host = safeHost(baseUrl);
	const lower = `${cause.message} ${code ?? ""}`.toLowerCase();
	if (code === "ENOTFOUND" || code === "EAI_AGAIN")
		return new ProviderConnectionError(
			`${providerName} could not resolve ${host}. Check DNS, VPN, or proxy configuration before retrying.`,
			{ cause, code },
		);
	if (code === "ECONNREFUSED")
		return new ProviderConnectionError(
			`${providerName} could not connect to ${host}. Check whether your proxy or firewall is accepting HTTPS connections.`,
			{ cause, code },
		);
	if (lower.includes("certificate") || lower.includes("unable_to_verify") || lower.includes("self signed"))
		return new ProviderConnectionError(
			`${providerName} could not verify the TLS certificate for ${host}. Install your network's trusted root certificate; do not disable certificate verification.`,
			{ cause, code },
		);
	return new ProviderConnectionError(
		`${providerName} could not reach ${host}. Check your network, HTTPS proxy, VPN, or firewall, then retry.${environmentProxyCompatibilityHint() ?? ""} (${cause.message})`,
		{ cause, code },
	);
}

function errorCode(error: Error): string | undefined {
	const candidate = error as Error & { code?: unknown; cause?: unknown };
	if (typeof candidate.code === "string") return candidate.code;
	return candidate.cause instanceof Error ? errorCode(candidate.cause) : undefined;
}

function safeHost(baseUrl: string): string {
	try {
		return new URL(baseUrl).host;
	} catch {
		return baseUrl;
	}
}

function buildRequestBody(
	options: ProviderChatOptions,
	streaming: boolean,
	providerId?: string,
): Record<string, unknown> {
	const normalizedProvider = providerId?.trim().toLowerCase();
	const profile = providerProfile(normalizedProvider, options);
	const body: Record<string, unknown> = {
		model: options.modelName,
		messages: profile.prepareMessages(options.messages),
		stream: streaming,
	};

	if (!profile.omitTemperature && options.temperature !== undefined) {
		body["temperature"] = options.temperature;
	}

	if (options.maxOutputTokens !== undefined) {
		body["max_tokens"] = options.maxOutputTokens;
	} else if (profile.defaultMaxTokens !== undefined) {
		body["max_tokens"] = profile.defaultMaxTokens;
	}

	if (options.tools && options.tools.length > 0) {
		body["tools"] = options.tools.map((tool) => ({
			type: "function",
			function: tool.function,
		}));
	}

	if (streaming) {
		body["stream_options"] = { include_usage: true };
	}

	Object.assign(body, profile.extraBody);
	Object.assign(body, profile.topLevel);

	return body;
}

function buildHeaders(
	apiKey?: string,
	extraHeaders?: Record<string, string>,
	providerId?: string,
	providerOptions?: ProviderRequestOptions,
	model?: string,
): Record<string, string> {
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
		Accept: "text/event-stream",
	};
	Object.assign(headers, defaultProviderHeaders(providerId, providerOptions, model));
	if (apiKey) {
		headers["Authorization"] = `Bearer ${apiKey}`;
	}
	return { ...headers, ...extraHeaders };
}

interface ProviderProfileRequest {
	omitTemperature: boolean;
	defaultMaxTokens?: number;
	prepareMessages: (messages: ChatMessage[]) => Array<Record<string, unknown>>;
	extraBody: Record<string, unknown>;
	topLevel: Record<string, unknown>;
}

function providerProfile(providerId: string | undefined, options: ProviderChatOptions): ProviderProfileRequest {
	const providerOptions = options.providerOptions ?? {};
	const reasoning = providerOptions.reasoningConfig;
	const supportsReasoning = providerOptions.supportsReasoning === true;
	const extraBody: Record<string, unknown> = {};
	const topLevel: Record<string, unknown> = {};
	let defaultMaxTokens: number | undefined;
	let omitTemperature = false;
	let prepareMessages = (messages: ChatMessage[]) => messages.map(toOpenAIMessage);

	switch (providerId) {
		case "kimi":
		case "kimi-code":
		case "kimi-coding":
		case "kimi-coding-cn":
		case "moonshot":
		case "moonshotai": {
			omitTemperature = true;
			defaultMaxTokens = 32000;
			const enabled = !isReasoningDisabled(reasoning);
			extraBody["thinking"] = { type: enabled ? "enabled" : "disabled" };
			if (enabled) topLevel["reasoning_effort"] = normalizeEffort(reasoning?.["effort"], "medium");
			break;
		}
		case "qwen": {
			defaultMaxTokens = 65536;
			prepareMessages = toQwenMessages;
			extraBody["vl_high_resolution_images"] = true;
			if (providerOptions.qwenSessionMetadata) topLevel["metadata"] = providerOptions.qwenSessionMetadata;
			break;
		}
		case "nous": {
			extraBody["tags"] = nousPortalTags();
			if (supportsReasoning && !isReasoningDisabled(reasoning)) {
				extraBody["reasoning"] = reasoning ? { ...reasoning } : { enabled: true, effort: "medium" };
			}
			break;
		}
		case "openrouter":
		case "or": {
			if (providerOptions.providerPreferences) extraBody["provider"] = providerOptions.providerPreferences;
			if (options.modelName === "openrouter/pareto-code") {
				const score = parseBoundedScore(providerOptions.openrouterMinCodingScore);
				if (score !== undefined) extraBody["plugins"] = [{ id: "pareto-router", min_coding_score: score }];
			}
			if (supportsReasoning)
				extraBody["reasoning"] = reasoning ? { ...reasoning } : { enabled: true, effort: "medium" };
			break;
		}
		case "ai-gateway":
		case "vercel": {
			extraBody["reasoning"] = reasoning ? { ...reasoning } : { enabled: true, effort: "medium" };
			break;
		}
		case "deepseek":
		case "deepseek-chat": {
			// DeepSeek's Chat Completions API permits image_url only in a vision
			// input message, not in a role="tool" result. Preserve the tool result
			// as text and attach any media immediately afterwards as user input.
			prepareMessages = toDeepSeekMessages;
			if (supportsDeepSeekThinking(options.modelName)) {
				const enabled = !isReasoningDisabled(reasoning);
				extraBody["thinking"] = { type: enabled ? "enabled" : "disabled" };
				if (enabled && reasoning?.["effort"] !== undefined) {
					topLevel["reasoning_effort"] = normalizeDeepSeekEffort(reasoning["effort"]);
				}
			}
			break;
		}
		case "opencode-go": {
			if (isKimiK2(options.modelName)) {
				if (reasoning) {
					const enabled = !isReasoningDisabled(reasoning);
					extraBody["thinking"] = { type: enabled ? "enabled" : "disabled" };
					if (enabled && reasoning["effort"] !== undefined)
						topLevel["reasoning_effort"] = normalizeEffort(reasoning["effort"]);
				}
			} else if (isDeepSeekThinking(options.modelName)) {
				const enabled = !isReasoningDisabled(reasoning);
				extraBody["thinking"] = { type: enabled ? "enabled" : "disabled" };
				if (enabled && reasoning?.["effort"] !== undefined)
					topLevel["reasoning_effort"] = normalizeDeepSeekEffort(reasoning["effort"]);
			}
			break;
		}
		case "custom":
		case "ollama":
		case "local":
		case "vllm": {
			if (providerOptions.ollamaNumCtx) extraBody["options"] = { num_ctx: providerOptions.ollamaNumCtx };
			if (isReasoningDisabled(reasoning)) extraBody["think"] = false;
			break;
		}
		case "nvidia":
		case "nvidia-nim":
			defaultMaxTokens = 16384;
			break;
	}

	return { omitTemperature, defaultMaxTokens, prepareMessages, extraBody, topLevel };
}

function defaultProviderHeaders(
	providerId?: string,
	providerOptions?: ProviderRequestOptions,
	model?: string,
): Record<string, string> {
	const normalizedProvider = providerId?.trim().toLowerCase();
	if (
		(normalizedProvider === "openrouter" || normalizedProvider === "or") &&
		providerOptions?.sessionId &&
		model &&
		/^x-ai\/grok-|^xai\/grok-/.test(model)
	) {
		return { "x-grok-conv-id": providerOptions.sessionId };
	}
	switch (normalizedProvider) {
		case "kimi":
		case "kimi-code":
		case "kimi-coding":
		case "kimi-coding-cn":
		case "moonshot":
		case "moonshotai":
			return { "User-Agent": "hermes-agent/1.0" };
		case "gmi":
		case "gmi-cloud":
		case "gmicloud":
			return { "User-Agent": "HermesAgent/1.0" };
		case "github-copilot":
		case "copilot":
			return {
				"Editor-Version": "vscode/1.104.1",
				"User-Agent": "HermesAgent/1.0",
				"Copilot-Integration-Id": "vscode-chat",
				"Openai-Intent": "conversation-edits",
				"x-initiator": "agent",
			};
		case "ai-gateway":
		case "vercel":
			return { "HTTP-Referer": "https://hermes-agent.nousresearch.com", "X-Title": "Hermes Agent" };
		default:
			return {};
	}
}

function toQwenMessages(messages: ChatMessage[]): Array<Record<string, unknown>> {
	const result = messages.map((message) => {
		const converted = toOpenAIMessage(message);
		const content = converted["content"];
		if (typeof content === "string") converted["content"] = [{ type: "text", text: content }];
		else if (Array.isArray(content))
			converted["content"] = content.map((part) => (typeof part === "string" ? { type: "text", text: part } : part));
		return converted;
	});
	const system = result.find((message) => message["role"] === "system");
	const content = system?.["content"];
	if (Array.isArray(content) && content.length > 0 && isObject(content[content.length - 1])) {
		(content[content.length - 1] as Record<string, unknown>)["cache_control"] = { type: "ephemeral" };
	}
	return result;
}

function toDeepSeekMessages(messages: ChatMessage[]): Array<Record<string, unknown>> {
	const result: Array<Record<string, unknown>> = [];
	for (let index = 0; index < messages.length; index += 1) {
		const message = messages[index]!;
		if (message.role !== "tool") {
			result.push(toOpenAIMessage(message));
			continue;
		}

		const images: OpenAIContentPart[] = [];
		for (; index < messages.length && messages[index]?.role === "tool"; index += 1) {
			const tool = messages[index]!;
			const content = toOpenAIContent(tool.content);
			if (!Array.isArray(content)) {
				result.push(toOpenAIMessage(tool));
				continue;
			}
			const text = content.filter((part) => part.type !== "image_url");
			images.push(...content.filter((part) => part.type === "image_url"));
			result.push({
				role: "tool",
				tool_call_id: tool.toolCallId ?? "",
				content: text.map((part) => part.text ?? "").join("\n") || "Tool produced an image attachment.",
			});
		}
		if (images.length > 0) {
			result.push({
				role: "user",
				content: [
					{ type: "text", text: "The preceding tool output includes image attachment(s). Analyze them before continuing." },
					...images,
				],
			});
		}
		index -= 1;
	}
	return result;
}

function nousPortalTags(): string[] {
	return ["product=hermes-agent", "client=hermes-client-v0.1.0"];
}

function isReasoningDisabled(reasoning: Record<string, unknown> | undefined): boolean {
	return reasoning?.["enabled"] === false || reasoning?.["effort"] === "none";
}

function normalizeEffort(value: unknown, fallback = "medium"): string {
	const effort = typeof value === "string" ? value.trim().toLowerCase() : "";
	if (effort === "xhigh" || effort === "max") return "high";
	return ["low", "medium", "high"].includes(effort) ? effort : fallback;
}

function normalizeDeepSeekEffort(value: unknown): string {
	const effort = typeof value === "string" ? value.trim().toLowerCase() : "";
	return effort === "xhigh" || effort === "max" ? "max" : normalizeEffort(effort);
}

function parseBoundedScore(value: number | string | undefined): number | undefined {
	if (value === undefined || value === "") return undefined;
	const score = typeof value === "number" ? value : Number(value);
	return Number.isFinite(score) && score >= 0 && score <= 1 ? score : undefined;
}

function supportsDeepSeekThinking(model: string): boolean {
	const normalized = model.trim().toLowerCase();
	return (
		(normalized.startsWith("deepseek-v") && !normalized.startsWith("deepseek-v3")) || normalized === "deepseek-reasoner"
	);
}

function isKimiK2(model: string): boolean {
	return model.trim().toLowerCase().split("/").pop()?.startsWith("kimi-k2") ?? false;
}

function isDeepSeekThinking(model: string): boolean {
	const normalized = model.trim().toLowerCase().split("/").pop() ?? "";
	return (
		(normalized.startsWith("deepseek-v") && !normalized.startsWith("deepseek-v3")) || normalized === "deepseek-reasoner"
	);
}

async function buildError(response: Response): Promise<Error> {
	let detail = "";
	try {
		const data = (await response.json()) as { error?: { message?: string } };
		if (data.error?.message) detail = `: ${data.error.message}`;
	} catch {
		// Ignore malformed error bodies.
	}
	const message = `OpenAI-compatible API error: ${response.status} ${response.statusText}${detail}`;
	return new ProviderError(message, {
		status: response.status,
		retryAfterMs: parseRetryAfter(response.headers?.get?.("retry-after") ?? null),
	});
}

function toOpenAIMessage(message: ChatMessage): Record<string, unknown> {
	switch (message.role) {
		case "system":
		case "user":
			return { role: message.role, content: toOpenAIContent(message.content) };
		case "assistant": {
			const toolCalls = (message.toolCalls ?? []).map((tc) => ({
				id: tc.id,
				type: "function",
				function: {
					name: tc.name,
					arguments: JSON.stringify(tc.arguments),
				},
			}));
			const content = toOpenAIContent(message.content);
			const msg: Record<string, unknown> = { role: "assistant" };
			if (Array.isArray(content) ? content.length > 0 : content) {
				msg["content"] = content;
			}
			if (toolCalls.length > 0) {
				msg["tool_calls"] = toolCalls;
			}
			return msg;
		}
		case "tool": {
			return {
				role: "tool",
				tool_call_id: message.toolCallId ?? "",
				content: toOpenAIContent(message.content),
			};
		}
		default: {
			const exhaustive: never = message.role;
			throw new Error(`Unsupported chat message role: ${String(exhaustive)}`);
		}
	}
}

function toOpenAIContent(content: string | ContentPart[]): string | Array<OpenAIContentPart> {
	if (typeof content === "string") {
		return content;
	}
	return content.map((part) => {
		if (part.type === "text") {
			return { type: "text", text: part.text ?? "" };
		}
		if (part.type === "image_url") {
			const toolImage = part as ContentPart & { imageUrl?: { url?: string } };
			const url = part.image_url?.url ?? toolImage.imageUrl?.url ?? "";
			// Never put an undeliverable image on the wire: providers reject the
			// whole request, and because the part stays in conversation history
			// every subsequent request fails the same way. Degrade to text.
			if (!isSendableImageUrl(url)) {
				return { type: "text", text: "[image attachment omitted: invalid payload]" };
			}
			return { type: "image_url", image_url: { url } };
		}
		if (part.type === "thinking") {
			return { type: "text", text: part.thinking ?? "" };
		}
		return { type: "text", text: JSON.stringify(part) };
	});
}

const SENDABLE_IMAGE_URL = /^data:image\/(?:png|jpe?g|webp|gif);base64,[A-Za-z0-9+/]+={0,2}$/;

function isSendableImageUrl(url: string): boolean {
	return SENDABLE_IMAGE_URL.test(url);
}

function extractContent(content: string | Array<OpenAIContentPart> | null | undefined): string {
	if (content === null || content === undefined) return "";
	if (typeof content === "string") return content;
	return content.map((part) => (part.type === "text" ? (part.text ?? "") : "")).join("");
}

function extractToolCalls(toolCalls: Array<OpenAIToolCall>): ToolCall[] {
	return toolCalls
		.filter((tc) => tc.type === undefined || tc.type === "function")
		.map((tc, index) => normalizeToolCall(tc.id, tc.function?.name, tc.function?.arguments, index));
}

function buildToolCallsFromAccumulator(acc: Map<number, { id: string; name: string; arguments: string }>): ToolCall[] {
	const entries = Array.from(acc.entries());
	entries.sort((a, b) => a[0] - b[0]);
	return entries.map(([index, value]) => normalizeToolCall(value.id, value.name, value.arguments, index));
}

function normalizeToolCall(
	id: string | undefined,
	name: string | undefined,
	raw: string | undefined,
	index: number,
): ToolCall {
	const resolvedId = id?.trim() || `call_${randomUUID()}`;
	if (!name?.trim())
		throw new ProviderProtocolError(`OpenAI-compatible tool call ${resolvedId || index} is missing a function name`, {
			retryable: false,
		});
	return { id: resolvedId, name, arguments: parseArguments(raw, resolvedId) };
}

function parseArguments(raw: string | undefined, toolCallId: string): Record<string, unknown> {
	if (!raw) return {};
	try {
		const value: unknown = JSON.parse(raw);
		if (!isObject(value)) throw new TypeError("tool arguments must decode to an object");
		return value;
	} catch (error) {
		throw new ProviderProtocolError(`OpenAI-compatible tool call ${toolCallId} returned malformed arguments`, {
			cause: error,
			retryable: false,
		});
	}
}

function mapFinishReason(reason: string | null | undefined): string {
	if (!reason) return "stop";
	if (reason === "tool_calls") return "tool_calls";
	if (reason === "length") return "length";
	return reason;
}

function isObject(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}
