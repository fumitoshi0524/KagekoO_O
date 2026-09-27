import { describe, expect, it } from "vitest";
import {
	compactionOptionsFromConfig,
	coordinatorMaxStepsFromRoute,
	learningSynthesisOptionsFromConfig,
	mcpTimeoutsFromConfig,
	shellTimeoutsFromConfig,
	turnOptionsFromConfig,
} from "./composition-root.js";

describe("coordinatorMaxStepsFromRoute", () => {
	it("returns no override when the coordinator route is absent", () => {
		expect(coordinatorMaxStepsFromRoute(undefined)).toEqual({});
	});

	it("returns no override for a route-only coordinator config, preserving the TurnFlow default", () => {
		expect(coordinatorMaxStepsFromRoute({ provider: "openai", modelName: "gpt-5" })).toEqual({});
	});

	it("carries the configured turn bound", () => {
		expect(coordinatorMaxStepsFromRoute({ maxSteps: 25 })).toEqual({ maxSteps: 25 });
	});
});

describe("turnOptionsFromConfig", () => {
	it("returns no overrides when the section is absent", () => {
		expect(turnOptionsFromConfig(undefined)).toEqual({});
	});

	it("maps configured turn knobs onto agent options, renaming toolResultBudgetChars to budgetToolResult", () => {
		expect(turnOptionsFromConfig({ toolConcurrency: 4, toolResultBudgetChars: 50_000 })).toEqual({
			toolConcurrency: 4,
			budgetToolResult: 50_000,
		});
	});

	it("maps every budget and guardrail knob onto agent options", () => {
		expect(
			turnOptionsFromConfig({
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
			}),
		).toEqual({
			toolConcurrency: 4,
			budgetToolResult: 50_000,
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
});

describe("compactionOptionsFromConfig", () => {
	it("returns no overrides when the section is absent", () => {
		expect(compactionOptionsFromConfig(undefined)).toEqual({});
	});

	it("maps configured compaction ratios onto ContextMemory options", () => {
		expect(
			compactionOptionsFromConfig({ thresholdRatio: 0.7, targetRatio: 0.4, inputRatio: 0.5, minHistoryEvents: 8 }),
		).toEqual({
			compactThreshold: 0.7,
			compactionTargetRatio: 0.4,
			compactionInputRatio: 0.5,
			compactionMinHistoryEvents: 8,
		});
	});
});

describe("mcpTimeoutsFromConfig", () => {
	it("returns no overrides when the section is absent", () => {
		expect(mcpTimeoutsFromConfig(undefined)).toEqual({});
	});

	it("maps configured MCP timeouts", () => {
		expect(mcpTimeoutsFromConfig({ servers: {}, connectTimeoutMs: 5_000, callTimeoutMs: 120_000 })).toEqual({
			connectTimeoutMs: 5_000,
			callTimeoutMs: 120_000,
		});
	});
});

describe("shellTimeoutsFromConfig", () => {
	it("returns no overrides when the section is absent", () => {
		expect(shellTimeoutsFromConfig(undefined)).toEqual({});
	});

	it("maps configured shell timeouts onto bash tool options", () => {
		expect(shellTimeoutsFromConfig({ dialect: "bash", executable: "bash", defaultTimeoutMs: 10_000, maxTimeoutMs: 600_000 })).toEqual({
			defaultTimeoutMs: 10_000,
			maxTimeoutMs: 600_000,
		});
	});
});

describe("learningSynthesisOptionsFromConfig", () => {
	it("returns no overrides when the section is absent", () => {
		expect(learningSynthesisOptionsFromConfig(undefined)).toEqual({});
	});

	it("maps configured synthesis knobs", () => {
		expect(
			learningSynthesisOptionsFromConfig({
				enabled: true,
				proposalKinds: ["skill", "tool", "mcp"],
				synthesizeErrorPatterns: false,
				minContentLength: 8,
				maxContentLength: 50_000,
				erroneousToolThreshold: 2,
				maxPendingEntries: 100,
				autoApproveSkills: false,
				autoApproveCapabilities: false,
				skillMinEvents: 3,
				skillMinCompletedTurns: 3,
				skillSynthesisCooldownEvents: 5,
				skillSynthesisTimeoutMs: 30_000,
				capabilitySynthesisTimeoutMs: 90_000,
				mcpSynthesisTimeoutMs: 600_000,
				skillSimilarityThreshold: 0.7,
			}),
		).toEqual({
			skillSynthesisTimeoutMs: 30_000,
			capabilitySynthesisTimeoutMs: 90_000,
			mcpSynthesisTimeoutMs: 600_000,
			skillSimilarityThreshold: 0.7,
		});
	});
});
