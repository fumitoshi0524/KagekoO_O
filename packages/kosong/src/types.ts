/**
 * Core types for the Kageko LLM abstraction layer.
 *
 * The shapes are intentionally close to the previous pi-ai-based API so that
 * consumers such as @kageko/agent-core keep compiling without changes.
 */
import type { OAuthCredentialResolver } from "./credentials.js";

export interface ContentPart {
	type: string;
	text?: string;
	image_url?: { url: string };
	thinking?: string;
	thinkingSignature?: string;
}

export interface ToolCall {
	id: string;
	name: string;
	arguments: Record<string, unknown>;
}

export interface ChatMessage {
	role: "system" | "user" | "assistant" | "tool";
	content: string | ContentPart[];
	toolCalls?: ToolCall[];
	toolCallId?: string;
	isError?: boolean;
}

export interface ChatTool {
	function: {
		name: string;
		description: string;
		parameters: Record<string, unknown>;
	};
}

export interface ChatOptions {
	messages: ChatMessage[];
	tools?: ChatTool[];
	/** Provider-specific request knobs mirrored from Hermes provider profiles. */
	providerOptions?: ProviderRequestOptions;
	onTextDelta?: (delta: string) => void;
	onThinkingDelta?: (delta: string) => void;
	onToolCallDelta?: (delta: { id: string; name: string; argumentsPartial: string }) => void;
	signal?: AbortSignal;
}

export interface ProviderRequestOptions {
	/** Full Hermes-style reasoning configuration. */
	reasoningConfig?: Record<string, unknown>;
	/** Whether the selected model advertises reasoning support. */
	supportsReasoning?: boolean;
	/** Session identity used by provider-side prompt/cache routing. */
	sessionId?: string;
	/** OpenRouter provider routing preferences. */
	providerPreferences?: Record<string, unknown>;
	/** Qwen Portal metadata sent as a top-level request field. */
	qwenSessionMetadata?: Record<string, unknown>;
	/** Pareto Router minimum coding score. */
	openrouterMinCodingScore?: number | string;
	/** Ollama/custom context size forwarded under options.num_ctx. */
	ollamaNumCtx?: number;
	/** AWS Bedrock Converse region; credentials come from the AWS SDK chain. */
	awsRegion?: string;
	/** Bedrock Converse inferenceConfig extensions mirrored from Hermes. */
	bedrockTopP?: number;
	bedrockStopSequences?: string[];
	bedrockGuardrailConfig?: Record<string, unknown>;
	/** Copilot ACP subprocess overrides mirrored from Hermes copilot_acp_client.py. */
	acpCommand?: string;
	acpArgs?: string[];
	acpCwd?: string;
	acpTimeoutMs?: number;
}

export interface ChatResponse {
	toolCalls: ToolCall[];
	content: string;
	finishReason: string;
	usage: {
		promptTokens: number;
		completionTokens: number;
	};
	/** True when a streaming transport ended without its terminal sentinel. */
	truncated?: boolean;
}

export interface LLMConfig {
	provider: string;
	modelName: string;
	authMode?: "api" | "oauth";
	apiKey?: string;
	baseUrl?: string;
	/** Provider-reported model context window, when available. */
	contextLength?: number;
	/** Provider-reported capabilities such as tools, vision, or reasoning. */
	capabilities?: readonly string[];
	/** Provider-specific reasoning/thinking selection retained with the route. */
	reasoningConfig?: Record<string, unknown>;
	maxContextSize?: number;
	maxOutputTokens?: number;
	/** Abort a streaming request after this long without any provider delta. Defaults to five minutes. */
	idleTimeoutMs?: number;
	/** Optional hard request deadline. Omitted by default so active long streams may complete. */
	totalTimeoutMs?: number;
	/** Provenance for metadata values carried by this route. */
	provenance?: ModelMetadataProvenance;
	/** Provider endpoint identity for authoritative metadata, or catalog identity for a fallback. */
	metadataSource?: ModelMetadataOrigin;
	temperature?: number;
	providerOptions?: ProviderRequestOptions;
	/** Injected by the composition root; required by OAuth-backed providers. */
	oauthCredentialResolver?: OAuthCredentialResolver;
}

export interface LLM {
	readonly modelName: string;
	readonly model: ModelMetadata;
	chat(options: ChatOptions): Promise<ChatResponse>;
	isRetryableError?(error: unknown): boolean;
	recoverAfterError?(error: unknown, context: ProviderRecoveryContext): Promise<boolean>;
}

/** Stable model route metadata shared by every provider implementation. */
export interface ModelMetadata {
	readonly provider: string;
	readonly modelName: string;
	readonly contextLength?: number;
	readonly capabilities?: readonly string[];
	readonly reasoningConfig?: Readonly<Record<string, unknown>>;
	/** Local execution cap; this may be lower than the provider window. */
	readonly maxContextSize?: number;
	readonly maxOutputTokens?: number;
	readonly authMode?: "api" | "oauth";
	/** How each displayed metadata value was obtained. Missing values are unknown. */
	readonly provenance?: ModelMetadataProvenance;
	readonly metadataSource?: ModelMetadataOrigin;
	/** Compatibility accessors for consumers that prefer field-level names. */
	readonly contextLengthSource?: ModelMetadataSource;
	readonly capabilitiesSource?: ModelMetadataSource;
	readonly maxContextSizeSource?: ModelMetadataSource;
	readonly maxOutputTokensSource?: ModelMetadataSource;
}

/** A local setting or estimate must not be rendered as if it came from a provider. */
export type ModelMetadataSource = "authoritative" | "catalog" | "configured" | "estimated" | "unknown";

export type ModelDiscoverySource = "provider-live" | "public-catalog" | "local-cache" | "static-fallback";

export interface ModelMetadataProvenance {
	readonly contextLength: ModelMetadataSource;
	readonly capabilities: ModelMetadataSource;
	readonly maxContextSize: ModelMetadataSource;
	readonly maxOutputTokens: ModelMetadataSource;
}

export interface ModelMetadataOrigin {
	readonly kind: "provider" | "catalog";
	readonly providerId: string;
	readonly endpoint?: string;
	readonly authMode?: "api" | "oauth";
	/** Exact discovery source. `kind` is retained for config/SDK compatibility. */
	readonly source?: "provider-live" | "public-catalog" | "local-cache" | "static-fallback";
	/** False means the route is selectable, but was not validated by the provider. */
	readonly authoritative?: boolean;
}

export interface ProviderRecoveryContext {
	attempt: number;
	signal: AbortSignal;
}

export interface ProviderChatOptions extends ChatOptions {
	modelName: string;
	authMode?: "api" | "oauth";
	temperature?: number;
	apiKey?: string;
	baseUrl?: string;
	maxContextSize?: number;
	maxOutputTokens?: number;
}

export interface ProviderChatResponse {
	toolCalls: ToolCall[];
	content: string;
	finishReason: string;
	usage: {
		promptTokens: number;
		completionTokens: number;
	};
	/** True when a streaming transport ended without its terminal sentinel. */
	truncated?: boolean;
}

export interface Provider {
	readonly modelName?: string;
	chat(options: ProviderChatOptions): Promise<ProviderChatResponse>;
	/** Optional lifecycle hook for stateful transports to discard stale clients. */
	recoverAfterError?(error: unknown, context: ProviderRecoveryContext): Promise<boolean>;
}

/** Base URLs for OpenAI-compatible providers, kept independent of provider SDK modules. */
export const OPENAI_COMPATIBLE_REGISTRY: Record<string, string> = {
	openai: "https://api.openai.com/v1",
	// DeepSeek's OpenAI-compatible API is rooted at /v1. Omitting it makes
	// both /models and /chat/completions target the wrong host path.
	deepseek: "https://api.deepseek.com/v1",
	// Qwen API-key access uses DashScope.
	qwen: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
	"github-copilot": "https://api.githubcopilot.com",
	copilot: "https://api.githubcopilot.com",
	nous: "https://inference.nousresearch.com/v1",
	// Kimi Code's OpenAI-compatible endpoint includes /v1.
	kimi: "https://api.moonshot.ai/v1",
	"kimi-code": "https://api.kimi.com/coding/v1",
	// MiniMax exposes its supported coding models through Anthropic Messages.
	// The provider transport selects Bearer auth for this route.
	minimax: "https://api.minimax.io/anthropic",
	xai: "https://api.x.ai/v1",
	moonshotai: "https://api.moonshot.cn/v1",
	moonshot: "https://api.moonshot.ai/v1",
	openrouter: "https://openrouter.ai/api/v1",
	or: "https://openrouter.ai/api/v1",
	together: "https://api.together.xyz/v1",
	fireworks: "https://api.fireworks.ai/inference/v1",
	groq: "https://api.groq.com/openai/v1",
	stepfun: "https://api.stepfun.ai/step_plan/v1",
	mistral: "https://api.mistral.ai/v1",
	cerebras: "https://api.cerebras.ai/v1",
	"ai-gateway": "https://ai-gateway.vercel.sh/v1",
	vercel: "https://ai-gateway.vercel.sh/v1",
	"vercel-ai-gateway": "https://ai-gateway.vercel.sh/v1",
	ai_gateway: "https://ai-gateway.vercel.sh/v1",
	aigateway: "https://ai-gateway.vercel.sh/v1",
	"gmi-cloud": "https://api.gmi-serving.com/v1",
	gmi: "https://api.gmi-serving.com/v1",
	custom: "",
	ollama: "",
	local: "",
	vllm: "",
	llamacpp: "",
	"llama.cpp": "",
	"llama-cpp": "",
	"azure-foundry": "",
	azure: "",
	"azure-ai-foundry": "",
	"azure-ai": "",
	opencode: "https://opencode.ai/zen/v1",
	"opencode-zen": "https://opencode.ai/zen/v1",
	"opencode-go": "https://opencode.ai/zen/go/v1",
	alibaba: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
	"alibaba-coding-plan": "https://coding-intl.dashscope.aliyuncs.com/v1",
	arcee: "https://api.arcee.ai/api/v1",
	"arcee-ai": "https://api.arcee.ai/api/v1",
	arceeai: "https://api.arcee.ai/api/v1",
	huggingface: "https://router.huggingface.co/v1",
	hf: "https://router.huggingface.co/v1",
	"hugging-face": "https://router.huggingface.co/v1",
	"huggingface-hub": "https://router.huggingface.co/v1",
	kilocode: "https://api.kilo.ai/api/gateway",
	"kilo-code": "https://api.kilo.ai/api/gateway",
	kilo: "https://api.kilo.ai/api/gateway",
	"kilo-gateway": "https://api.kilo.ai/api/gateway",
	"kimi-coding": "https://api.moonshot.ai/v1",
	"kimi-coding-cn": "https://api.moonshot.cn/v1",
	"kimi-for-coding": "https://api.kimi.com/coding/v1",
	lmstudio: "http://127.0.0.1:1234/v1",
	"minimax-cn": "https://api.minimaxi.com/anthropic",
	"mini-max": "https://api.minimax.io/anthropic",
	"minimax-china": "https://api.minimaxi.com/anthropic",
	novita: "https://api.novita.ai/openai/v1",
	"novita-ai": "https://api.novita.ai/openai/v1",
	novitaai: "https://api.novita.ai/openai/v1",
	nvidia: "https://integrate.api.nvidia.com/v1",
	"nvidia-nim": "https://integrate.api.nvidia.com/v1",
	"ollama-cloud": "https://ollama.com/v1",
	ollama_cloud: "https://ollama.com/v1",
	"tencent-tokenhub": "https://tokenhub.tencentmaas.com/v1",
	xiaomi: "https://api.xiaomimimo.com/v1",
	mimo: "https://api.xiaomimimo.com/v1",
	"xiaomi-mimo": "https://api.xiaomimimo.com/v1",
	zai: "https://api.z.ai/api/paas/v4",
	glm: "https://api.z.ai/api/paas/v4",
	"z-ai": "https://api.z.ai/api/paas/v4",
	"z.ai": "https://api.z.ai/api/paas/v4",
	zhipu: "https://api.z.ai/api/paas/v4",
	"alibaba-coding": "https://coding-intl.dashscope.aliyuncs.com/v1",
	alibaba_coding: "https://coding-intl.dashscope.aliyuncs.com/v1",
	"dashscope-coding": "https://coding-intl.dashscope.aliyuncs.com/v1",
	"qwen-dashscope": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
	"alibaba-cloud": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
	dashscope: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
};
