import { describe, expect, it } from "vitest";

import { SETUP_PROVIDERS } from "../src/tui/controllers/setup-controller.js";

describe("product provider scope", () => {
	it("exposes only maintained provider routes in setup and credentials", () => {
		expect(SETUP_PROVIDERS.map(({ id, authMode }) => [id, authMode])).toEqual([
			["openai-codex", "oauth"],
			["openai-api", "api"],
			["openrouter", "api"],
			["kimi-coding", "api"],
			["kimi-coding-cn", "api"],
			["kimi-code", "oauth"],
			["deepseek", "api"],
			["xiaomi", "api"],
			["custom", "api"],
		]);
	});

	it("does not expose unmaintained OAuth providers", () => {
		const ids = new Set(SETUP_PROVIDERS.map(({ id }) => id));
		for (const provider of ["anthropic", "google-gemini-cli", "minimax-oauth", "nous", "qwen-oauth", "xai-oauth"])
			expect(ids).not.toContain(provider);
	});
});
