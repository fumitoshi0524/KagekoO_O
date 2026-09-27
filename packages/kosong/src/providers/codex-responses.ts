import { createHash } from "node:crypto";
import type { OAuthCredentialResolver } from "../credentials.js";
import type {
	ChatMessage,
	ChatTool,
	ContentPart,
	Provider,
	ProviderChatOptions,
	ProviderChatResponse,
	ToolCall,
} from "../types.js";
import {
	ProviderConnectionError,
	ProviderError,
	ProviderProtocolError,
	ProviderReloginRequiredError,
	parseRetryAfter,
} from "../errors.js";
import { environmentProxyCompatibilityHint, fetchProviderRequest } from "../live-catalog-fetch.js";

export interface ResponsesProviderOptions {
	/** Provider id passed to the OAuth resolver (Codex or xAI OAuth). */
	providerId?: string;
	/** API-key route for xAI's Responses endpoint. */
	apiKey?: string;
	/** Optional route-specific base URL. */
	baseUrl?: string;
	/** An explicit user/provider route override takes precedence over stored OAuth metadata. */
	preferRouteBaseUrl?: boolean;
	/** Additional first-party headers for the route. */
	headers?: Record<string, string>;
	/** xAI uses the same Responses wire format with model-specific reasoning rules. */
	isXai?: boolean;
}

interface ResponsesOutputItem {
	type?: string;
	id?: string;
	status?: string;
	phase?: string;
	call_id?: string;
	name?: string;
	arguments?: string;
	input?: string;
	content?: Array<{ type?: string; text?: string }>;
}

interface ResponsesPayload {
	status?: string;
	output?: ResponsesOutputItem[];
	output_text?: string;
	usage?: { input_tokens?: number; output_tokens?: number };
	incomplete_details?: { reason?: string };
	error?: { message?: string } | string;
}

interface ResponsesStreamEvent {
	type?: string;
	delta?: string;
	text?: string;
	arguments?: string;
	item_id?: string;
	output_index?: number;
	item?: ResponsesOutputItem;
	response?: ResponsesPayload;
}

/** ChatGPT OAuth Codex transport. The Codex backend implements Responses API,
 * not Chat Completions. */
export class CodexResponsesProvider implements Provider {
	constructor(
		private readonly resolveOAuth?: OAuthCredentialResolver,
		private readonly route: ResponsesProviderOptions = {},
	) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		if (!this.resolveOAuth && !this.route.apiKey) {
			throw new Error(
				`OAuth provider "${this.route.providerId ?? "openai-codex"}" requires a credential resolver. Inject one via LLMConfig.oauthCredentialResolver.`,
			);
		}
		const providerName = this.route.isXai ? "xAI" : "OpenAI Codex";
		let auth: { headers: Record<string, string>; baseUrl?: string };
		try {
			auth = this.resolveOAuth
				? await this.resolveOAuth(this.route.providerId ?? "openai-codex")
				: { headers: {}, baseUrl: this.route.baseUrl };
		} catch (error) {
			throw authResolutionError(providerName, error);
		}
		const baseUrl = this.route.preferRouteBaseUrl
			? (this.route.baseUrl ?? auth.baseUrl ?? (this.route.isXai ? "https://api.x.ai/v1" : undefined))
			: (auth.baseUrl ?? this.route.baseUrl ?? (this.route.isXai ? "https://api.x.ai/v1" : undefined));
		if (!baseUrl) throw new Error(`${this.route.providerId ?? "OpenAI Codex"} OAuth did not provide a base URL.`);
		const { instructions, input } = toResponsesInput(options.messages);
		const tools = toResponsesTools(options.tools);
		const reasoningConfig = options.providerOptions?.reasoningConfig;
		const reasoningEnabled = reasoningConfig?.["enabled"] !== false;
		const reasoningEffort = normalizeReasoningEffort(reasoningConfig?.["effort"]);
		const isXaiReasoningModel = !this.route.isXai || supportsXaiReasoningEffort(options.modelName);
		const body: Record<string, unknown> = {
			model: options.modelName,
			instructions: instructions || "You are a helpful coding assistant.",
			input,
			store: false,
			// The ChatGPT Codex endpoint requires the Responses SSE contract.  It
			// also gives the TUI real deltas instead of fabricating one after a JSON
			// response has completed.
			stream: true,
		};
		if (reasoningEnabled) {
			body["include"] = ["reasoning.encrypted_content"];
			if (isXaiReasoningModel) {
				body["reasoning"] = this.route.isXai
					? { effort: reasoningEffort }
					: { effort: reasoningEffort, summary: "auto" };
			}
		} else if (!this.route.isXai) {
			body["include"] = [];
		}
		if (tools.length > 0) {
			body["tools"] = tools;
			body["tool_choice"] = "auto";
			body["parallel_tool_calls"] = true;
		}
		const sessionId = options.providerOptions?.sessionId;
		if (this.route.isXai && sessionId) body["prompt_cache_key"] = sessionId;
		const endpoint = `${baseUrl.replace(/\/$/, "")}/responses`;
		let response: Response;
		try {
			response = await fetchProviderRequest(endpoint, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Accept: "text/event-stream",
					...(this.route.apiKey ? { Authorization: `Bearer ${this.route.apiKey}` } : {}),
					...this.route.headers,
					...auth.headers,
					...(this.route.isXai && sessionId ? { "x-grok-conv-id": sessionId } : {}),
				},
				body: JSON.stringify(body),
				signal: options.signal,
			});
		} catch (error) {
			throw connectionError(providerName, endpoint, error);
		}
		if (!response.ok) {
			if (response.status === 401) {
				throw new ProviderReloginRequiredError(
					`${providerName} rejected this session (HTTP 401). It may have expired or been revoked; run \`kageko auth login openai-codex\` and try again.`,
				);
			}
			if (response.status === 407) {
				throw new ProviderError(
					`${providerName} proxy authentication failed (HTTP 407). Check your HTTPS_PROXY credentials or Windows system proxy settings.`,
					{ status: response.status, retryable: false },
				);
			}
			throw new ProviderError(
				`${providerName} request failed: ${response.status} ${response.statusText} ${(await response.text()).slice(0, 300)}`,
				{ status: response.status, retryAfterMs: parseRetryAfter(response.headers?.get?.("retry-after") ?? null) },
			);
		}
		return this.readResponse(response, options, providerName);
	}

	private async readResponse(
		response: Response,
		options: ProviderChatOptions,
		providerName: string,
	): Promise<ProviderChatResponse> {
		// Keep explicit proxy/compatibility routes usable when they acknowledge
		// stream=true but return one completed JSON payload rather than SSE.
		if (!response.body || response.headers.get("content-type")?.toLowerCase().includes("application/json"))
			return this.readJsonResponse(response, options, providerName);
		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		const toolCalls = new Map<string, { id: string; name: string; argumentsText: string }>();
		let content = "";
		let completed: ResponsesPayload | undefined;
		let buffer = "";

		const onEvent = (event: ResponsesStreamEvent): void => {
			if (event.type === "response.output_text.delta" && typeof event.delta === "string") {
				content += event.delta;
				options.onTextDelta?.(event.delta);
				return;
			}
			if (event.type === "response.output_text.done" && !content && typeof event.text === "string") {
				content = event.text;
				options.onTextDelta?.(event.text);
				return;
			}
			if (event.type === "response.output_item.added" && event.item?.type === "function_call") {
				this.captureToolCall(toolCalls, event.item, event.output_index);
				return;
			}
			if (event.type === "response.output_item.done" && event.item?.type === "function_call") {
				this.captureToolCall(toolCalls, event.item, event.output_index);
				return;
			}
			if (event.type === "response.function_call_arguments.delta" && typeof event.delta === "string") {
				const call = toolCalls.get(streamToolCallKey(event));
				if (!call) return;
				call.argumentsText += event.delta;
				options.onToolCallDelta?.({ id: call.id, name: call.name, argumentsPartial: call.argumentsText });
				return;
			}
			if (event.type === "response.function_call_arguments.done" && typeof event.arguments === "string") {
				const call = toolCalls.get(streamToolCallKey(event));
				if (!call) return;
				call.argumentsText = event.arguments;
				options.onToolCallDelta?.({ id: call.id, name: call.name, argumentsPartial: call.argumentsText });
				return;
			}
			if (
				event.type === "response.completed" ||
				event.type === "response.incomplete" ||
				event.type === "response.failed"
			) {
				completed = event.response ?? { status: event.type.slice("response.".length) };
			}
		};

		const consumeFrame = (frame: string): void => {
			const data = frame
				.split(/\r?\n/)
				.filter((line) => line.startsWith("data:"))
				.map((line) => line.slice(5).trimStart())
				.join("\n");
			if (!data || data === "[DONE]") return;
			try {
				onEvent(JSON.parse(data) as ResponsesStreamEvent);
			} catch (error) {
				throw new ProviderProtocolError(`${providerName} stream returned malformed SSE data`, { cause: error });
			}
		};

		try {
			for (;;) {
				const { value, done } = await reader.read();
				buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
				const frames = buffer.split(/\r?\n\r?\n/);
				buffer = frames.pop() ?? "";
				for (const frame of frames) consumeFrame(frame);
				if (done) break;
			}
			if (buffer.trim()) consumeFrame(buffer);
		} catch (error) {
			if (error instanceof ProviderProtocolError) throw error;
			throw new ProviderProtocolError(`${providerName} stream ended unexpectedly`, { cause: error });
		}

		// The ChatGPT Codex stream can carry the callable item only through the
		// output-item/argument events while the terminal response contains status
		// and usage but an empty output array. Never discard the stream accumulator
		// merely because a terminal response object was present.
		if (completed) return fromResponsesPayload(mergeStreamState(completed, content, toolCalls));
		return fromResponsesPayload({
			status: "incomplete",
			output: [...new Map([...toolCalls.values()].map((call) => [call.id, call])).values()].map((call) => ({
				type: "function_call",
				call_id: call.id,
				name: call.name,
				arguments: call.argumentsText || "{}",
			})),
			output_text: content,
		});
	}

	private async readJsonResponse(
		response: Response,
		options: ProviderChatOptions,
		providerName: string,
	): Promise<ProviderChatResponse> {
		let payload: ResponsesPayload;
		try {
			payload = (await response.json()) as ResponsesPayload;
		} catch (error) {
			throw new ProviderProtocolError(`${providerName} response returned malformed JSON`, { cause: error });
		}
		const result = fromResponsesPayload(payload);
		if (result.content) options.onTextDelta?.(result.content);
		for (const call of result.toolCalls) {
			options.onToolCallDelta?.({ id: call.id, name: call.name, argumentsPartial: JSON.stringify(call.arguments) });
		}
		return result;
	}

	private captureToolCall(
		calls: Map<string, { id: string; name: string; argumentsText: string }>,
		item: ResponsesOutputItem,
		outputIndex: number | undefined,
	): void {
		if (!item.name) return;
		const id = item.call_id || item.id || deterministicCallId(item.name, item.arguments ?? "{}", calls.size);
		const outputKey = outputIndex === undefined ? undefined : String(outputIndex);
		const call = (item.id ? calls.get(item.id) : undefined) ??
			(item.call_id ? calls.get(item.call_id) : undefined) ??
			(outputKey ? calls.get(outputKey) : undefined) ?? { id, name: item.name, argumentsText: "" };
		call.id = id;
		call.name = item.name;
		// output_item.done carries the authoritative complete arguments. An added
		// item commonly has an empty string, which must not erase collected deltas.
		if (typeof item.arguments === "string" && item.arguments.length > 0) call.argumentsText = item.arguments;
		// Responses argument events identify the item, while completed output
		// identifies the callable `call_id`; retain both aliases.
		calls.set(item.id ?? item.call_id ?? String(outputIndex ?? calls.size), call);
		if (item.call_id) calls.set(item.call_id, call);
		if (outputIndex !== undefined) calls.set(String(outputIndex), call);
	}
}

function mergeStreamState(
	payload: ResponsesPayload,
	content: string,
	calls: Map<string, { id: string; name: string; argumentsText: string }>,
): ResponsesPayload {
	const output = [...(payload.output ?? [])];
	const accumulated = [...new Map([...calls.values()].map((call) => [call.id, call])).values()];
	for (const call of accumulated) {
		const existingIndex = output.findIndex(
			(item) => item.type === "function_call" && (item.call_id === call.id || item.id === call.id),
		);
		const streamed: ResponsesOutputItem = {
			type: "function_call",
			call_id: call.id,
			name: call.name,
			arguments: call.argumentsText || "{}",
		};
		if (existingIndex < 0) output.push(streamed);
		else {
			const existing = output[existingIndex]!;
			output[existingIndex] = {
				...streamed,
				...existing,
				name: existing.name || streamed.name,
				arguments: existing.arguments || streamed.arguments,
			};
		}
	}
	return {
		...payload,
		output,
		...(payload.output_text === undefined && content ? { output_text: content } : {}),
	};
}

function streamToolCallKey(event: ResponsesStreamEvent): string {
	return event.item_id ?? String(event.output_index ?? "");
}

function authResolutionError(providerName: string, error: unknown): Error {
	if (hasReloginRequirement(error)) {
		return new ProviderReloginRequiredError(
			`${providerName} session expired or was revoked. Run \`kageko auth login openai-codex\` and try again.`,
			{ cause: error },
		);
	}
	return error instanceof Error ? error : new Error(String(error));
}

function connectionError(providerName: string, endpoint: string, error: unknown): ProviderConnectionError {
	const cause = error instanceof Error ? error : new Error(String(error));
	const code = errorCode(cause);
	const lower = `${cause.message} ${code ?? ""}`.toLowerCase();
	const host = new URL(endpoint).host;
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
			`${providerName} could not verify the TLS certificate for ${host}. If your network intercepts TLS, install its trusted root certificate; do not disable certificate verification.`,
			{ cause, code },
		);
	if (code === "ETIMEDOUT" || code === "UND_ERR_CONNECT_TIMEOUT" || code === "UND_ERR_HEADERS_TIMEOUT")
		return new ProviderConnectionError(
			`${providerName} timed out while connecting to ${host}. Check VPN, proxy, firewall, and network reachability.`,
			{ cause, code },
		);
	return new ProviderConnectionError(
		`${providerName} could not reach ${host}. Check your network, HTTPS proxy, VPN, or firewall, then retry.${environmentProxyCompatibilityHint() ?? ""} (${cause.message})`,
		{ cause, code },
	);
}

function hasReloginRequirement(error: unknown): boolean {
	return !!error && typeof error === "object" && (error as { reloginRequired?: unknown }).reloginRequired === true;
}

function errorCode(error: Error): string | undefined {
	const candidate = error as Error & { code?: unknown; cause?: unknown };
	if (typeof candidate.code === "string") return candidate.code;
	if (candidate.cause instanceof Error) return errorCode(candidate.cause);
	return undefined;
}

function toResponsesInput(messages: ChatMessage[]): { instructions: string; input: Array<Record<string, unknown>> } {
	const instructions = messages
		.filter((message) => message.role === "system")
		.map((message) => contentText(message.content))
		.join("\n\n");
	const input: Array<Record<string, unknown>> = [];
	for (const message of messages) {
		if (message.role === "system") continue;
		if (message.role === "tool") {
			if (message.toolCallId) {
				input.push({ type: "function_call_output", call_id: message.toolCallId, output: contentText(message.content) });
			}
			continue;
		}
		const renderedContent = responseContent(message.content, message.role);
		const hasContent = typeof renderedContent === "string" ? renderedContent.length > 0 : renderedContent.length > 0;
		if (message.role === "user" || hasContent) input.push({ role: message.role, content: renderedContent });
		for (const call of message.toolCalls ?? []) {
			if (!call.name.trim()) continue;
			input.push({
				type: "function_call",
				call_id: call.id || deterministicCallId(call.name, JSON.stringify(call.arguments), input.length),
				name: call.name,
				arguments: JSON.stringify(call.arguments),
			});
		}
	}
	return { instructions, input };
}

function toResponsesTools(tools: ChatTool[] | undefined): Array<Record<string, unknown>> {
	return (tools ?? []).map((tool) => ({
		type: "function",
		name: tool.function.name,
		description: tool.function.description,
		parameters: tool.function.parameters,
		strict: false,
	}));
}

function responseContent(
	content: string | ContentPart[],
	role: "user" | "assistant",
): string | Array<Record<string, unknown>> {
	if (typeof content === "string") return content;
	const textType = role === "assistant" ? "output_text" : "input_text";
	const parts: Array<Record<string, unknown>> = [];
	for (const part of content) {
		if (part.type === "text") parts.push({ type: textType, text: part.text ?? "" });
		if (part.type === "image_url") parts.push({ type: "input_image", image_url: part.image_url?.url ?? "" });
	}
	return parts;
}

function contentText(content: string | ContentPart[]): string {
	if (typeof content === "string") return content;
	return content.map((part) => part.text ?? part.thinking ?? "").join("");
}

function fromResponsesPayload(payload: ResponsesPayload): ProviderChatResponse {
	if (payload.status === "failed" || payload.status === "cancelled") {
		const error = typeof payload.error === "string" ? payload.error : payload.error?.message;
		throw new ProviderError(`OpenAI Codex response ${payload.status}${error ? `: ${error}` : ""}`, {
			retryable: false,
		});
	}
	let contentParts: string[] = [];
	const toolCalls: ToolCall[] = [];
	for (const item of payload.output ?? []) {
		if (item.type === "message") {
			for (const part of item.content ?? []) {
				if (part.type === "output_text" && part.text) contentParts.push(part.text);
			}
		} else if (item.type === "function_call") {
			if (!item.name) {
				throw new ProviderProtocolError("OpenAI Codex returned a function call without name", { retryable: false });
			}
			const callId = item.call_id || deterministicCallId(item.name, item.arguments ?? "{}", toolCalls.length);
			let args: Record<string, unknown>;
			try {
				const decoded: unknown = JSON.parse(item.arguments ?? "{}");
				if (!decoded || typeof decoded !== "object" || Array.isArray(decoded))
					throw new TypeError("arguments must be an object");
				args = decoded as Record<string, unknown>;
			} catch (error) {
				throw new ProviderProtocolError(`OpenAI Codex tool call ${callId} returned malformed arguments`, {
					cause: error,
					retryable: false,
				});
			}
			toolCalls.push({ id: callId, name: item.name, arguments: args });
		}
	}
	if (contentParts.length === 0 && typeof payload.output_text === "string") contentParts.push(payload.output_text);
	const content = contentParts.join("\n");
	const hasIncompleteItem = (payload.output ?? []).some((item) =>
		["queued", "in_progress", "incomplete"].includes(item.status ?? ""),
	);
	return {
		content,
		toolCalls,
		finishReason:
			payload.status === "incomplete" || hasIncompleteItem ? "length" : toolCalls.length > 0 ? "tool_calls" : "stop",
		usage: {
			promptTokens: payload.usage?.input_tokens ?? 0,
			completionTokens: payload.usage?.output_tokens ?? 0,
		},
	};
}

function supportsXaiReasoningEffort(model: string): boolean {
	const normalized = model.toLowerCase().replace(/^x-ai\//, "");
	const bare = normalized.split("/").pop() ?? normalized;
	return bare.startsWith("grok-3-mini") || bare.startsWith("grok-4.20-multi-agent") || bare.startsWith("grok-4.3");
}

function normalizeReasoningEffort(value: unknown): string {
	if (typeof value !== "string" || value.trim() === "") return "medium";
	return value.trim().toLowerCase() === "minimal" ? "low" : value.trim().toLowerCase();
}

function deterministicCallId(name: string, argumentsText: string, index: number): string {
	const digest = createHash("sha256").update(`${name}:${argumentsText}:${index}`).digest("hex").slice(0, 12);
	return `call_${digest}`;
}
