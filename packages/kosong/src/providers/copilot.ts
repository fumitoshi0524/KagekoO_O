import type { Provider, ProviderChatOptions, ProviderChatResponse } from "../types.js";
import { createAnthropicProvider } from "./anthropic.js";
import { CodexResponsesProvider } from "./codex-responses.js";
import { OpenAICompatibleProvider } from "./openai-compatible.js";

const COPILOT_BASE_URL = "https://api.githubcopilot.com";

/** Hermes Copilot routing: GPT-5/Codex → Responses, Claude → Messages, rest → Chat Completions. */
export class CopilotProvider implements Provider {
	constructor(
		private readonly apiKey?: string,
		private readonly baseUrl?: string,
	) {}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const model = options.modelName.trim().toLowerCase();
		if (isClaudeModel(model)) return this.chatAnthropic(options);
		if (isResponsesModel(model)) {
			return new CodexResponsesProvider(undefined, {
				providerId: "github-copilot",
				apiKey: this.apiKey,
				baseUrl: this.baseUrl ?? COPILOT_BASE_URL,
				headers: copilotHeaders(),
			}).chat(options);
		}
		return new OpenAICompatibleProvider({
			providerId: "github-copilot",
			apiKey: this.apiKey,
			baseUrl: this.baseUrl ?? COPILOT_BASE_URL,
			headers: copilotHeaders(),
		}).chat(options);
	}

	private async chatAnthropic(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		return createAnthropicProvider({
			authToken: this.apiKey,
			baseUrl: this.baseUrl ?? COPILOT_BASE_URL,
			defaultHeaders: copilotHeaders(),
		}).chat(options);
	}
}

function isClaudeModel(model: string): boolean {
	return model.includes("claude");
}

function isResponsesModel(model: string): boolean {
	return /^(gpt-5|o[1-9]|codex)/.test(model) || model.includes("codex");
}

function copilotHeaders(): Record<string, string> {
	return {
		"Editor-Version": "vscode/1.104.1",
		"User-Agent": "HermesAgent/1.0",
		"Copilot-Integration-Id": "vscode-chat",
		"Openai-Intent": "conversation-edits",
		"x-initiator": "agent",
	};
}
