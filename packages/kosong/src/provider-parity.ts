/**
 * Hermes provider identity and credential parity.
 *
 * Source of truth: hermes_cli/providers.py overlays plus
 * model-provider plugin profiles. Keep aliases and environment
 * acquisition here so provider selection cannot silently diverge from the
 * request transport.
 */

export const HERMES_PROVIDER_ALIASES: Readonly<Record<string, string>> = {
	// Hermes overlay aliases.
	openai: "openrouter",
	"open-router": "openrouter",
	or: "openrouter",
	"openai-api": "openai-api",
	claude: "anthropic",
	"claude-code": "anthropic",
	codex: "openai-codex",
	openai_codex: "openai-codex",
	nousresearch: "nous",
	"x-ai": "xai",
	"x.ai": "xai",
	grok: "xai",
	"github-copilot": "github-copilot",
	copilot: "github-copilot",
	"github-models": "github-copilot",
	"github-model": "github-copilot",
	github: "github-copilot",
	"github-copilot-acp": "copilot-acp",
	"copilot-acp-agent": "copilot-acp",
	"ai-gateway": "ai-gateway",
	vercel: "ai-gateway",
	"vercel-ai-gateway": "ai-gateway",
	ai_gateway: "ai-gateway",
	aigateway: "ai-gateway",
	"opencode-zen": "opencode-zen",
	opencode: "opencode-zen",
	opencode_zen: "opencode-zen",
	zen: "opencode-zen",
	opencode_go: "opencode-go",
	go: "opencode-go",
	"opencode-go-sub": "opencode-go",
	kilocode: "kilocode",
	"kilo-code": "kilocode",
	kilo: "kilocode",
	"kilo-gateway": "kilocode",
	"deep-seek": "deepseek",
	"deepseek-chat": "deepseek",
	dashscope: "alibaba",
	aliyun: "alibaba",
	"alibaba-cloud": "alibaba",
	"qwen-dashscope": "alibaba",
	alibaba_coding: "alibaba-coding-plan",
	"alibaba-coding": "alibaba-coding-plan",
	alibaba_coding_plan: "alibaba-coding-plan",
	"dashscope-coding": "alibaba-coding-plan",
	hf: "huggingface",
	"hugging-face": "huggingface",
	"huggingface-hub": "huggingface",
	"novita-ai": "novita",
	novitaai: "novita",
	mimo: "xiaomi",
	"xiaomi-mimo": "xiaomi",
	tencent: "tencent-tokenhub",
	tokenhub: "tencent-tokenhub",
	"tencent-cloud": "tencent-tokenhub",
	tencentmaas: "tencent-tokenhub",
	aws: "bedrock",
	"aws-bedrock": "bedrock",
	"amazon-bedrock": "bedrock",
	amazon: "bedrock",
	"arcee-ai": "arcee",
	arceeai: "arcee",
	"gmi-cloud": "gmi",
	gmicloud: "gmi",
	"lm-studio": "lmstudio",
	lm_studio: "lmstudio",
	"minimax-china": "minimax-cn",
	minimax_cn: "minimax-cn",
	"minimax-global": "minimax",
	"mini-max": "minimax",
	nim: "nvidia",
	"nvidia-nim": "nvidia",
	"build-nvidia": "nvidia",
	nemotron: "nvidia",
	ollama_cloud: "ollama-cloud",
	ollama: "custom",
	local: "custom",
	vllm: "custom",
	llamacpp: "custom",
	"llama.cpp": "custom",
	"llama-cpp": "custom",
	azure: "azure-foundry",
	"azure-ai-foundry": "azure-foundry",
	"azure-ai": "azure-foundry",
	glm: "zai",
	"z-ai": "zai",
	"z.ai": "zai",
	zhipu: "zai",
	step: "stepfun",
	"stepfun-coding-plan": "stepfun",
	// Kimi plugin profile aliases.
	kimi: "kimi-coding",
	moonshot: "kimi-coding",
	// Kimi For Coding is the subscription-backed managed service. Keep it
	// separate from Moonshot Open Platform API-key routes so an OAuth bearer is
	// never sent to api.moonshot.* (and an Open Platform key is never sent to
	// api.kimi.com/coding).
	"kimi-for-coding": "kimi-code",
	"kimi-cn": "kimi-coding-cn",
	"moonshot-cn": "kimi-coding-cn",
};

/** OAuth policy is intentionally limited to the two maintained subscription
 * routes. Provider setup owns the supported API-key roster; do not infer that
 * a legacy alias is an OAuth-capable product feature just because it exists in
 * the compatibility table. */
export const PROVIDER_AUTH_POLICY = {
	"kimi-code": "oauth",
	"openai-codex": "oauth",
} as const satisfies Readonly<Record<string, "api" | "oauth" | "api-or-oauth">>;

export function providerAuthPolicy(providerId: string): "api" | "oauth" | "api-or-oauth" {
	return PROVIDER_AUTH_POLICY[canonicalHermesProviderId(providerId) as keyof typeof PROVIDER_AUTH_POLICY] ?? "api";
}

/** API-key lookup order mirrors Hermes profile env_vars and overlays. */
export const HERMES_PROVIDER_API_KEY_ENV: Readonly<Record<string, readonly string[]>> = {
	"openai-api": ["OPENAI_API_KEY"],
	openrouter: ["OPENROUTER_API_KEY", "OPENAI_API_KEY"],
	anthropic: ["ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN"],
	"github-copilot": ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
	kimi: ["KIMI_API_KEY", "KIMI_CODING_API_KEY"],
	"kimi-coding": ["KIMI_API_KEY", "KIMI_CODING_API_KEY"],
	"kimi-coding-cn": ["KIMI_CN_API_KEY"],
	qwen: ["QWEN_API_KEY"],
	minimax: ["MINIMAX_API_KEY"],
	"minimax-cn": ["MINIMAX_CN_API_KEY"],
	deepseek: ["DEEPSEEK_API_KEY"],
	alibaba: ["DASHSCOPE_API_KEY"],
	"alibaba-coding-plan": ["ALIBABA_CODING_PLAN_API_KEY", "DASHSCOPE_API_KEY"],
	"ai-gateway": ["AI_GATEWAY_API_KEY"],
	arcee: ["ARCEEAI_API_KEY"],
	gmi: ["GMI_API_KEY"],
	huggingface: ["HF_TOKEN"],
	kilocode: ["KILOCODE_API_KEY"],
	novita: ["NOVITA_API_KEY"],
	nvidia: ["NVIDIA_API_KEY"],
	"ollama-cloud": ["OLLAMA_API_KEY"],
	"opencode-zen": ["OPENCODE_ZEN_API_KEY"],
	"opencode-go": ["OPENCODE_GO_API_KEY"],
	stepfun: ["STEPFUN_API_KEY"],
	xai: ["XAI_API_KEY"],
	xiaomi: ["XIAOMI_API_KEY"],
	zai: ["GLM_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"],
	"tencent-tokenhub": ["TOKENHUB_API_KEY"],
	"azure-foundry": ["AZURE_FOUNDRY_API_KEY"],
	lmstudio: ["LM_API_KEY"],
	mistral: ["MISTRAL_API_KEY"],
	groq: ["GROQ_API_KEY"],
	together: ["TOGETHER_API_KEY"],
	fireworks: ["FIREWORKS_API_KEY"],
	cerebras: ["CEREBRAS_API_KEY"],
};

export const HERMES_PROVIDER_BASE_URL_ENV: Readonly<Record<string, readonly string[]>> = {
	"openai-api": ["OPENAI_BASE_URL"],
	openrouter: ["OPENROUTER_BASE_URL"],
	anthropic: ["ANTHROPIC_BASE_URL"],
	"github-copilot": ["COPILOT_API_BASE_URL"],
	"ai-gateway": ["AI_GATEWAY_BASE_URL"],
	bedrock: ["BEDROCK_BASE_URL"],
	"openai-codex": ["HERMES_CODEX_BASE_URL"],
	nous: ["NOUS_INFERENCE_BASE_URL"],
	xai: ["XAI_BASE_URL"],
	lmstudio: ["LM_BASE_URL"],
	zai: ["GLM_BASE_URL"],
	"kimi-coding": ["KIMI_BASE_URL"],
	stepfun: ["STEPFUN_BASE_URL"],
	minimax: ["MINIMAX_BASE_URL"],
	"minimax-cn": ["MINIMAX_CN_BASE_URL"],
	deepseek: ["DEEPSEEK_BASE_URL"],
	alibaba: ["DASHSCOPE_BASE_URL"],
	"alibaba-coding-plan": ["ALIBABA_CODING_PLAN_BASE_URL"],
	"opencode-zen": ["OPENCODE_ZEN_BASE_URL"],
	"opencode-go": ["OPENCODE_GO_BASE_URL"],
	kilocode: ["KILOCODE_BASE_URL"],
	huggingface: ["HF_BASE_URL"],
	novita: ["NOVITA_BASE_URL"],
	nvidia: ["NVIDIA_BASE_URL"],
	xiaomi: ["XIAOMI_BASE_URL"],
	"tencent-tokenhub": ["TOKENHUB_BASE_URL"],
	"ollama-cloud": ["OLLAMA_BASE_URL"],
	"azure-foundry": ["AZURE_FOUNDRY_BASE_URL"],
	"copilot-acp": ["COPILOT_ACP_BASE_URL"],
	arcee: ["ARCEE_BASE_URL"],
	gmi: ["GMI_BASE_URL"],
};

export function canonicalHermesProviderId(provider: string): string {
	const normalized = provider.trim().toLowerCase();
	return HERMES_PROVIDER_ALIASES[normalized] ?? normalized;
}

export function resolveHermesApiKey(provider: string): string | undefined {
	return firstEnvironmentValue(HERMES_PROVIDER_API_KEY_ENV[provider]);
}

export function resolveHermesBaseUrl(provider: string): string | undefined {
	return firstEnvironmentValue(HERMES_PROVIDER_BASE_URL_ENV[provider]);
}

/**
 * Mirrors hermes `_PLACEHOLDER_SECRET_VALUES` / `has_usable_secret`
 * (hermes_cli/auth.py): placeholder or too-short values never count as a
 * configured credential, so they cannot shadow a real secret later in the
 * env-var lookup order.
 */
const HERMES_PLACEHOLDER_SECRET_VALUES: ReadonlySet<string> = new Set([
	"*",
	"**",
	"***",
	"changeme",
	"your_api_key",
	"your_api_key_here",
	"your-api-key",
	"placeholder",
	"example",
	"dummy",
	"null",
	"none",
]);

const HERMES_MIN_SECRET_LENGTH = 4;

function hasUsableSecret(value: string | undefined): value is string {
	if (typeof value !== "string") return false;
	const cleaned = value.trim();
	if (cleaned.length < HERMES_MIN_SECRET_LENGTH) return false;
	return !HERMES_PLACEHOLDER_SECRET_VALUES.has(cleaned.toLowerCase());
}

function firstEnvironmentValue(names: readonly string[] | undefined): string | undefined {
	if (!names) return undefined;
	for (const name of names) {
		const value = process.env[name];
		if (hasUsableSecret(value)) return value.trim();
	}
	return undefined;
}
