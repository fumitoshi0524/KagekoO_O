import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ConfigError, loadConfigRaw, type LearnerAgentRouteConfig } from "./config-loader.js";

const ENV_KEYS = [
	"KAGEKO_HOME",
	"KAGEKO_MODEL_PROVIDER",
	"KAGEKO_MODEL_NAME",
	"KAGEKO_API_KEY",
	"KAGEKO_BASE_URL",
	"KAGEKO_MAX_CONTEXT_SIZE",
	"KAGEKO_MAX_OUTPUT_TOKENS",
	"KAGEKO_PERMISSION_MODE",
	"KAGEKO_PERMISSION_PROFILE",
	"KAGEKO_INTERACTION_MODE",
	"KAGEKO_TELEMETRY_ENABLED",
	"KAGEKO_MAX_WALL_CLOCK_MS",
	"KAGEKO_MAX_TOKENS",
	"KAGEKO_MAX_COST_USD",
	"KAGEKO_INPUT_TOKEN_COST_USD",
	"KAGEKO_OUTPUT_TOKEN_COST_USD",
	"KAGEKO_TOOL_EXECUTION_MS",
	"KAGEKO_TOOL_RETRIES",
	"KAGEKO_MAX_REPEATED_TOOL_CALLS",
	"KAGEKO_MAX_NO_PROGRESS_STEPS",
	"KAGEKO_MAX_CONSECUTIVE_TOOL_FAILURES",
	"KAGEKO_MAX_TOOL_FAILURE_LOOP",
];

let savedEnv: Record<string, string | undefined>;
let homeDir: string;
let projectDir: string;

async function writeProjectConfig(document: Record<string, unknown>): Promise<void> {
	const dir = path.join(projectDir, ".kageko");
	await fs.mkdir(dir, { recursive: true });
	await fs.writeFile(path.join(dir, "config.json"), JSON.stringify(document), "utf8");
}

beforeEach(async () => {
	savedEnv = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));
	for (const key of ENV_KEYS) delete process.env[key];
	homeDir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-config-home-"));
	projectDir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-config-project-"));
	process.env["KAGEKO_HOME"] = homeDir;
});

afterEach(async () => {
	for (const key of ENV_KEYS) {
		const value = savedEnv[key];
		if (value === undefined) delete process.env[key];
		else process.env[key] = value;
	}
	await fs.rm(homeDir, { recursive: true, force: true });
	await fs.rm(projectDir, { recursive: true, force: true });
});

describe("loadConfigRaw learning trigger knobs", () => {
	it("defaults to the complete learner and accepts bounded proposal-product ablations", async () => {
		const defaults = await loadConfigRaw(projectDir);
		expect(defaults.learning.enabled).toBe(true);
		expect(defaults.learning.proposalKinds).toEqual(["skill", "tool", "mcp"]);
		expect(defaults.learning.synthesizeErrorPatterns).toBe(false);

		await writeProjectConfig({ learning: { enabled: false, proposalKinds: [] } });
		const disabled = await loadConfigRaw(projectDir);
		expect(disabled.learning).toMatchObject({ enabled: false, proposalKinds: [] });
	});

	it("requires opt-in before recurring errors wake generative synthesis", async () => {
		await writeProjectConfig({ learning: { synthesizeErrorPatterns: true } });
		expect((await loadConfigRaw(projectDir)).learning.synthesizeErrorPatterns).toBe(true);
	});

	it("rejects invalid learning proposal-product configurations", async () => {
		await writeProjectConfig({ learning: { proposalKinds: ["skill", "unknown"] } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/learning/proposalKinds/1");
	});

	it("applies the hardcoded trigger constants as defaults when the keys are absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.learning.skillMinEvents).toBe(3);
		expect(config.learning.skillMinCompletedTurns).toBe(3);
		expect(config.learning.skillSynthesisCooldownEvents).toBe(5);
	});

	it("parses configured trigger knobs", async () => {
		await writeProjectConfig({
			learning: { skillMinEvents: 7, skillMinCompletedTurns: 4, skillSynthesisCooldownEvents: 12 },
		});
		const config = await loadConfigRaw(projectDir);
		expect(config.learning.skillMinEvents).toBe(7);
		expect(config.learning.skillMinCompletedTurns).toBe(4);
		expect(config.learning.skillSynthesisCooldownEvents).toBe(12);
	});

	it("rejects out-of-range trigger knobs", async () => {
		for (const [key, value] of [
			["skillMinEvents", 0],
			["skillMinCompletedTurns", 0],
			["skillSynthesisCooldownEvents", 0],
			["skillMinEvents", 101],
		] as const) {
			await writeProjectConfig({ learning: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/learning/${key}`);
		}
	});

	it("rejects non-integer trigger knobs", async () => {
		await writeProjectConfig({ learning: { skillMinEvents: 2.5 } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
	});

	it("still rejects unknown learning keys", async () => {
		await writeProjectConfig({ learning: { bogusKey: true } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/learning/bogusKey is not a recognized setting");
	});
});

describe("loadConfigRaw agentGraph.learner run parameters", () => {
	it("leaves run parameters absent on a route-only learner config", async () => {
		await writeProjectConfig({ agentGraph: { learner: { provider: "openai", modelName: "gpt-5" } } });
		const config = await loadConfigRaw(projectDir);
		expect(config.agentGraph?.learner).toEqual({ provider: "openai", modelName: "gpt-5" });
	});

	it("parses configured run parameters alongside the route fields", async () => {
		await writeProjectConfig({
			agentGraph: {
				learner: {
					provider: "openai",
					modelName: "gpt-5",
					authMode: "api",
					maxSteps: 10,
					runTimeoutMs: 120_000,
					maxQueuedRuns: 2,
				},
			},
		});
		const learner: LearnerAgentRouteConfig | undefined = (await loadConfigRaw(projectDir)).agentGraph?.learner;
		expect(learner).toEqual({
			provider: "openai",
			modelName: "gpt-5",
			authMode: "api",
			maxSteps: 10,
			runTimeoutMs: 120_000,
			maxQueuedRuns: 2,
		});
	});

	it("rejects out-of-range run parameters", async () => {
		for (const [key, value] of [
			["maxSteps", 0],
			["maxSteps", 21],
			["runTimeoutMs", 29_999],
			["runTimeoutMs", 900_001],
			["maxQueuedRuns", 0],
			["maxQueuedRuns", 17],
		] as const) {
			await writeProjectConfig({ agentGraph: { learner: { [key]: value } } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/agentGraph/learner/${key}`);
		}
	});

	it("still rejects unknown learner route keys", async () => {
		await writeProjectConfig({ agentGraph: { learner: { timeoutMs: 60_000 } } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow(
			"/agentGraph/learner/timeoutMs is not a recognized setting",
		);
	});

	it("accepts coordinator maxSteps within the turn bound range", async () => {
		await writeProjectConfig({ agentGraph: { coordinator: { maxSteps: 4 }, executor: { maxSteps: 4 } } });
		const config = await loadConfigRaw(projectDir);
		expect(config.agentGraph?.coordinator).toEqual({ maxSteps: 4 });
		expect(config.agentGraph?.executor).toEqual({ maxSteps: 4 });
	});

	it("rejects out-of-range coordinator maxSteps", async () => {
		for (const value of [0, 251, 2.5] as const) {
			await writeProjectConfig({ agentGraph: { coordinator: { maxSteps: value } } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow("/agentGraph/coordinator/maxSteps");
		}
	});

	it("still rejects non-route coordinator keys", async () => {
		await writeProjectConfig({ agentGraph: { coordinator: { systemPrompt: "custom" } } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow(
			"/agentGraph/coordinator/systemPrompt is not a recognized setting",
		);
	});
});

describe("loadConfigRaw turns section", () => {
	it("applies the agent-core turn defaults when the section is absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.turns).toEqual({ toolConcurrency: 8, toolResultBudgetChars: 100_000 });
	});

	it("parses configured turn knobs", async () => {
		await writeProjectConfig({ turns: { toolConcurrency: 4, toolResultBudgetChars: 50_000 } });
		const config = await loadConfigRaw(projectDir);
		expect(config.turns).toEqual({ toolConcurrency: 4, toolResultBudgetChars: 50_000 });
	});

	it("passes through every schema-validated budget and guardrail knob", async () => {
		await writeProjectConfig({
			turns: {
				toolConcurrency: 4,
				toolResultBudgetChars: 50_000,
				maxWallClockMs: 600_000,
				maxTokens: 200_000,
				maxCostUsd: 5,
				inputTokenCostUsd: 0.000003,
				outputTokenCostUsd: 0.000015,
				maxToolExecutionMs: 120_000,
				maxToolRetries: 3,
				maxRepeatedToolCalls: 6,
				maxNoProgressSteps: 4,
				maxConsecutiveToolFailures: 5,
				maxToolFailureLoop: 9,
			},
		});
		const config = await loadConfigRaw(projectDir);
		expect(config.turns).toEqual({
			toolConcurrency: 4,
			toolResultBudgetChars: 50_000,
			maxWallClockMs: 600_000,
			maxTokens: 200_000,
			maxCostUsd: 5,
			inputTokenCostUsd: 0.000003,
			outputTokenCostUsd: 0.000015,
			maxToolExecutionMs: 120_000,
			maxToolRetries: 3,
			maxRepeatedToolCalls: 6,
			maxNoProgressSteps: 4,
			maxConsecutiveToolFailures: 5,
			maxToolFailureLoop: 9,
		});
	});

	it("lets turn environment variables override the config file", async () => {
		await writeProjectConfig({
			turns: {
				maxWallClockMs: 600_000,
				maxTokens: 200_000,
				maxCostUsd: 5,
				inputTokenCostUsd: 0.000003,
				outputTokenCostUsd: 0.000015,
				maxToolExecutionMs: 120_000,
				maxToolRetries: 3,
				maxRepeatedToolCalls: 6,
				maxNoProgressSteps: 4,
			},
		});
		process.env["KAGEKO_MAX_WALL_CLOCK_MS"] = "300000";
		process.env["KAGEKO_MAX_TOKENS"] = "100000";
		process.env["KAGEKO_MAX_COST_USD"] = "2.5";
		process.env["KAGEKO_INPUT_TOKEN_COST_USD"] = "0.000001";
		process.env["KAGEKO_OUTPUT_TOKEN_COST_USD"] = "0.000005";
		process.env["KAGEKO_TOOL_EXECUTION_MS"] = "60000";
		process.env["KAGEKO_TOOL_RETRIES"] = "1";
		process.env["KAGEKO_MAX_REPEATED_TOOL_CALLS"] = "3";
		process.env["KAGEKO_MAX_NO_PROGRESS_STEPS"] = "2";
		process.env["KAGEKO_MAX_CONSECUTIVE_TOOL_FAILURES"] = "2";
		process.env["KAGEKO_MAX_TOOL_FAILURE_LOOP"] = "7";
		const config = await loadConfigRaw(projectDir);
		expect(config.turns).toEqual({
			toolConcurrency: 8,
			toolResultBudgetChars: 100_000,
			maxWallClockMs: 300_000,
			maxTokens: 100_000,
			maxCostUsd: 2.5,
			inputTokenCostUsd: 0.000001,
			outputTokenCostUsd: 0.000005,
			maxToolExecutionMs: 60_000,
			maxToolRetries: 1,
			maxRepeatedToolCalls: 3,
			maxNoProgressSteps: 2,
			maxConsecutiveToolFailures: 2,
			maxToolFailureLoop: 7,
		});
	});

	it("rejects a non-numeric turn environment variable", async () => {
		process.env["KAGEKO_MAX_TOKENS"] = "many";
		await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("KAGEKO_MAX_TOKENS");
	});

	it("rejects out-of-range turn knobs", async () => {
		for (const [key, value] of [
			["toolConcurrency", 0],
			["toolConcurrency", 17],
			["toolConcurrency", 2.5],
			["toolResultBudgetChars", 9_999],
			["toolResultBudgetChars", 1_000_001],
			["maxConsecutiveToolFailures", 0],
			["maxConsecutiveToolFailures", 1.5],
			["maxToolFailureLoop", 0],
			["maxToolFailureLoop", 101],
		] as const) {
			await writeProjectConfig({ turns: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/turns/${key}`);
		}
	});

	it("still rejects unknown turns keys", async () => {
		await writeProjectConfig({ turns: { bogusKey: true } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/turns/bogusKey is not a recognized setting");
	});
});

describe("loadConfigRaw compaction section", () => {
	it("applies the agent-core compaction defaults when the section is absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.compaction).toEqual({ thresholdRatio: 0.8, targetRatio: 0.5, inputRatio: 0.6, minHistoryEvents: 4 });
	});

	it("parses configured compaction knobs", async () => {
		await writeProjectConfig({
			compaction: { thresholdRatio: 0.7, targetRatio: 0.4, inputRatio: 0.5, minHistoryEvents: 8 },
		});
		const config = await loadConfigRaw(projectDir);
		expect(config.compaction).toEqual({ thresholdRatio: 0.7, targetRatio: 0.4, inputRatio: 0.5, minHistoryEvents: 8 });
	});

	it("rejects out-of-range compaction knobs", async () => {
		for (const [key, value] of [
			["thresholdRatio", 1.5],
			["thresholdRatio", -0.1],
			["targetRatio", 2],
			["inputRatio", -1],
			["minHistoryEvents", 0],
			["minHistoryEvents", 1.5],
		] as const) {
			await writeProjectConfig({ compaction: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/compaction/${key}`);
		}
	});

	it("still rejects unknown compaction keys", async () => {
		await writeProjectConfig({ compaction: { bogusKey: true } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/compaction/bogusKey is not a recognized setting");
	});
});

describe("loadConfigRaw mcp timeouts", () => {
	it("applies the agent-core MCP timeout defaults when the keys are absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.mcp.connectTimeoutMs).toBe(30_000);
		expect(config.mcp.callTimeoutMs).toBe(30_000);
	});

	it("parses configured MCP timeouts", async () => {
		await writeProjectConfig({ mcp: { connectTimeoutMs: 5_000, callTimeoutMs: 120_000 } });
		const config = await loadConfigRaw(projectDir);
		expect(config.mcp.connectTimeoutMs).toBe(5_000);
		expect(config.mcp.callTimeoutMs).toBe(120_000);
	});

	it("rejects out-of-range MCP timeouts", async () => {
		for (const [key, value] of [
			["connectTimeoutMs", 999],
			["connectTimeoutMs", 120_001],
			["callTimeoutMs", 999],
			["callTimeoutMs", 600_001],
		] as const) {
			await writeProjectConfig({ mcp: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/mcp/${key}`);
		}
	});

	it("still rejects unknown mcp keys", async () => {
		await writeProjectConfig({ mcp: { bogusKey: true } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/mcp/bogusKey is not a recognized setting");
	});
});

describe("loadConfigRaw shell timeouts", () => {
	it("applies the bash-tool timeout defaults when the keys are absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.shell.defaultTimeoutMs).toBe(60_000);
		expect(config.shell.maxTimeoutMs).toBe(300_000);
	});

	it("parses configured shell timeouts", async () => {
		await writeProjectConfig({ shell: { defaultTimeoutMs: 10_000, maxTimeoutMs: 600_000 } });
		const config = await loadConfigRaw(projectDir);
		expect(config.shell.defaultTimeoutMs).toBe(10_000);
		expect(config.shell.maxTimeoutMs).toBe(600_000);
	});

	it("rejects out-of-range shell timeouts", async () => {
		for (const [key, value] of [
			["defaultTimeoutMs", 999],
			["maxTimeoutMs", 999],
			["defaultTimeoutMs", 1.5],
		] as const) {
			await writeProjectConfig({ shell: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/shell/${key}`);
		}
	});

	it("still rejects unknown shell keys", async () => {
		await writeProjectConfig({ shell: { bogusKey: true } });
		await expect(loadConfigRaw(projectDir)).rejects.toThrow("/shell/bogusKey is not a recognized setting");
	});
});

describe("loadConfigRaw learning synthesis knobs", () => {
	it("applies the agent-core synthesis defaults when the keys are absent", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.learning.skillSynthesisTimeoutMs).toBe(60_000);
		expect(config.learning.capabilitySynthesisTimeoutMs).toBe(120_000);
		expect(config.learning.mcpSynthesisTimeoutMs).toBe(300_000);
		expect(config.learning.skillSimilarityThreshold).toBe(0.85);
	});

	it("parses configured synthesis knobs", async () => {
		await writeProjectConfig({
			learning: {
				skillSynthesisTimeoutMs: 30_000,
				capabilitySynthesisTimeoutMs: 90_000,
				mcpSynthesisTimeoutMs: 600_000,
				skillSimilarityThreshold: 0.7,
			},
		});
		const config = await loadConfigRaw(projectDir);
		expect(config.learning.skillSynthesisTimeoutMs).toBe(30_000);
		expect(config.learning.capabilitySynthesisTimeoutMs).toBe(90_000);
		expect(config.learning.mcpSynthesisTimeoutMs).toBe(600_000);
		expect(config.learning.skillSimilarityThreshold).toBe(0.7);
	});

	it("rejects out-of-range synthesis knobs", async () => {
		for (const [key, value] of [
			["skillSynthesisTimeoutMs", 999],
			["capabilitySynthesisTimeoutMs", 999],
			["mcpSynthesisTimeoutMs", 999],
			["skillSimilarityThreshold", 1.5],
			["skillSimilarityThreshold", -0.1],
		] as const) {
			await writeProjectConfig({ learning: { [key]: value } });
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(`/learning/${key}`);
		}
	});
});

describe("loadConfigRaw subagent bounds", () => {
	it("leaves maxConcurrentSubagents absent when not configured", async () => {
		const config = await loadConfigRaw(projectDir);
		expect(config.agentGraph?.maxConcurrentSubagents).toBeUndefined();
	});

	it("parses maxConcurrentSubagents and per-profile timeoutMs", async () => {
		await writeProjectConfig({
			agentGraph: { maxConcurrentSubagents: 2, subagents: { coder: { timeoutMs: 600_000 } } },
		});
		const config = await loadConfigRaw(projectDir);
		expect(config.agentGraph?.maxConcurrentSubagents).toBe(2);
		expect(config.agentGraph?.subagents["coder"]?.timeoutMs).toBe(600_000);
	});

	it("rejects out-of-range subagent bounds", async () => {
		for (const document of [
			{ agentGraph: { maxConcurrentSubagents: 0 } },
			{ agentGraph: { maxConcurrentSubagents: 17 } },
			{ agentGraph: { subagents: { coder: { timeoutMs: 9_999 } } } },
			{ agentGraph: { subagents: { coder: { timeoutMs: 7_200_001 } } } },
		] as const) {
			await writeProjectConfig(document);
			await expect(loadConfigRaw(projectDir)).rejects.toThrow(ConfigError);
		}
	});
});
