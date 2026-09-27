import { describe, expect, it } from "vitest";

import { resolveCheckpointAction } from "../src/cli/checkpoint-resume.js";

describe("resolveCheckpointAction", () => {
	it("stops when no checkpoint was emitted", () => {
		expect(resolveCheckpointAction(undefined, true, "session-1")).toEqual({ kind: "stop" });
	});

	it("stops when --resume-on-checkpoint is not set", () => {
		expect(resolveCheckpointAction({ reason: "slice_exhausted" }, false, "session-1")).toEqual({ kind: "stop" });
		expect(resolveCheckpointAction({ reason: "stalled" }, false, "session-1")).toEqual({ kind: "stop" });
		expect(resolveCheckpointAction({ reason: "budget_exhausted" }, false, "session-1")).toEqual({ kind: "stop" });
	});

	it("auto-resumes a slice_exhausted checkpoint with the continuation prompt", () => {
		const action = resolveCheckpointAction({ reason: "slice_exhausted" }, true, "session-1");
		expect(action.kind).toBe("resume");
		if (action.kind === "resume") {
			expect(action.prompt).toContain("durable checkpoint");
		}
	});

	it("auto-resumes a stalled checkpoint with a different-strategy prompt", () => {
		const action = resolveCheckpointAction({ reason: "stalled" }, true, "session-1");
		expect(action.kind).toBe("resume");
		if (action.kind === "resume") {
			expect(action.prompt).toContain("circuit-broken");
			expect(action.prompt).toContain("different strategy");
			expect(action.prompt).not.toContain("durable checkpoint");
		}
	});

	it("escalates a budget_exhausted checkpoint with usage and resume instructions", () => {
		const action = resolveCheckpointAction(
			{ reason: "budget_exhausted", tokensUsed: 12_345, costUsd: 0.42 },
			true,
			"session-9",
		);
		expect(action.kind).toBe("escalate");
		if (action.kind === "escalate") {
			expect(action.message).toContain("budget_exhausted");
			expect(action.message).toContain("12345");
			expect(action.message).toContain("$0.4200");
			expect(action.message).toContain("--session session-9");
		}
	});

	it("escalates without usage figures when the checkpoint omits them", () => {
		const action = resolveCheckpointAction({ reason: "budget_exhausted" }, true, "session-9");
		expect(action.kind).toBe("escalate");
		if (action.kind === "escalate") {
			expect(action.message).toContain("budget_exhausted");
			expect(action.message).not.toContain("tokens");
			expect(action.message).toContain("--session session-9");
		}
	});
});
