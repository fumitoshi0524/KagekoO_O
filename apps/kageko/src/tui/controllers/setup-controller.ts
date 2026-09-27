import type { DiscoveredModel } from "@kageko/node-sdk";

export interface SetupProviderEntry {
	readonly id: string;
	readonly label: string;
	readonly defaultModel: string;
	readonly authMode: "api" | "oauth";
	/** Hermes routes such as Bedrock and Copilot ACP acquire credentials outside an API-key prompt. */
	readonly credentialMode?: "api_key" | "none";
	readonly requiresBaseUrl?: boolean;
}

export const SETUP_PROVIDERS: readonly SetupProviderEntry[] = [
	{ id: "openai-codex", label: "OpenAI Codex (OAuth)", defaultModel: "gpt-5.3-codex", authMode: "oauth" },
	{ id: "openai-api", label: "OpenAI API", defaultModel: "gpt-5", authMode: "api" },
	{ id: "openrouter", label: "OpenRouter", defaultModel: "openai/gpt-5", authMode: "api" },
	{ id: "kimi-coding", label: "Kimi / Moonshot", defaultModel: "kimi-k2.6", authMode: "api" },
	{ id: "kimi-coding-cn", label: "Kimi / Moonshot (China)", defaultModel: "kimi-k2.6", authMode: "api" },
	{ id: "kimi-code", label: "Kimi Code (OAuth)", defaultModel: "kimi-k2.6", authMode: "oauth" },
	{ id: "deepseek", label: "DeepSeek", defaultModel: "deepseek-chat", authMode: "api" },
	{ id: "xiaomi", label: "Xiaomi MiMo", defaultModel: "mimo-v2.5-pro", authMode: "api" },
	{ id: "custom", label: "Custom (OpenAI-compatible)", defaultModel: "", authMode: "api", requiresBaseUrl: true },
];

export type SetupStep = "provider" | "baseUrl" | "apiKey" | "oauth" | "model";

export interface SetupModelOption extends DiscoveredModel {
	readonly contextSource?: string;
}

export interface SetupResult {
	readonly providerId: string;
	readonly baseUrl?: string;
	readonly authMode: "api" | "oauth";
	readonly apiKey?: string;
	readonly modelName: string;
	readonly discoveredModel?: SetupModelOption;
}

/** Pure wizard state machine; the TUI app owns rendering and SDK calls. */
export class SetupController {
	step: SetupStep = "provider";
	providerIndex = 0;
	buffer = "";
	error: string | undefined;
	status: string | undefined;
	modelOptions: readonly SetupModelOption[] = [];
	modelIndex = 0;
	private baseUrl: string | undefined;
	private apiKey = "";

	get provider(): SetupProviderEntry {
		return SETUP_PROVIDERS[this.providerIndex]!;
	}

	move(delta: number): void {
		this.providerIndex = (this.providerIndex + delta + SETUP_PROVIDERS.length) % SETUP_PROVIDERS.length;
	}

	selectProvider(id: string): void {
		const index = SETUP_PROVIDERS.findIndex((entry) => entry.id === id);
		if (index >= 0) this.providerIndex = index;
	}
	selectRoute(id: string, authMode: "api" | "oauth"): void {
		const index = SETUP_PROVIDERS.findIndex((entry) => entry.id === id && entry.authMode === authMode);
		if (index >= 0) this.providerIndex = index;
	}

	acceptProvider(): void {
		this.buffer = "";
		this.error = undefined;
		this.status = undefined;
		this.modelOptions = [];
		this.modelIndex = 0;
		if (this.provider.requiresBaseUrl) this.step = "baseUrl";
		else if (this.provider.credentialMode === "none") this.step = "model";
		else if (this.provider.authMode === "oauth") this.step = "oauth";
		else this.step = "apiKey";
	}

	type(text: string): void {
		this.buffer += text;
	}
	backspace(): void {
		this.buffer = [...this.buffer].slice(0, -1).join("");
	}
	apiKeyValue(): string {
		return this.apiKey;
	}
	clearBuffer(): void {
		this.buffer = "";
	}
	maskedBuffer(): string {
		return "•".repeat([...this.buffer].length);
	}

	setModels(models: readonly SetupModelOption[]): void {
		this.modelOptions = [...models];
		this.modelIndex = 0;
		this.buffer = models[0]?.id ?? this.provider.defaultModel;
		this.error = models.length ? undefined : "No models were returned for this authenticated route.";
	}

	moveModel(delta: number): void {
		if (!this.modelOptions.length) return;
		this.modelIndex = (this.modelIndex + delta + this.modelOptions.length) % this.modelOptions.length;
		this.buffer = this.modelOptions[this.modelIndex]?.id ?? this.buffer;
	}

	selectedModel(): SetupModelOption | undefined {
		return this.modelOptions[this.modelIndex];
	}

	/** Advance past the current input step; returns the next step, "error", or the final result. */
	submitStep(): SetupStep | "error" | SetupResult {
		const value = this.buffer.trim();
		if (this.step === "baseUrl") {
			if (!/^https?:\/\/.+/.test(value)) {
				this.error = "Base URL must start with http:// or https://";
				return "error";
			}
			this.baseUrl = value;
			this.buffer = "";
			this.error = undefined;
			this.step = "apiKey";
			return this.step;
		}
		if (this.step === "apiKey") {
			if (!value) {
				this.error = "API key must not be empty";
				return "error";
			}
			this.apiKey = value;
			this.buffer = this.provider.defaultModel;
			this.error = undefined;
			this.step = "model";
			return this.step;
		}
		if (this.step === "oauth") return this.step;
		if (this.step === "model") {
			if (!value) {
				this.error = "Model name must not be empty";
				return "error";
			}
			const selectedModel = this.selectedModel();
			return {
				providerId: this.provider.id,
				baseUrl: this.baseUrl,
				authMode: this.provider.authMode,
				...(this.provider.authMode === "api" ? { apiKey: this.apiKey } : {}),
				modelName: value,
				...(selectedModel?.id === value ? { discoveredModel: selectedModel } : {}),
			};
		}
		return this.step;
	}
}
