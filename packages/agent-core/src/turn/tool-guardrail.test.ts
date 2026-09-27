import { describe, expect, it } from "vitest";
import { normalizeObservationText, ToolFailureGuardrail } from "./tool-guardrail.js";

describe("ToolFailureGuardrail", () => {
	it("warns after the first failure before the model can repeat it", () => {
		const guardrail = new ToolFailureGuardrail();
		const decision = guardrail.observe({
			toolName: "create_draft",
			args: { attachment: "guessed://id" },
			result: { output: "missing prerequisite", isError: true },
		});
		expect(decision).toMatchObject({ consecutiveFailures: 1, failureStreak: 1, forceStop: false });
		expect(decision.reminder).toContain("identifiers returned by successful calls");
		expect(decision.reminder).toContain("Change strategy");
		expect(decision.reminder).not.toContain("Change the arguments");
	});

	it("counts identical failures and eventually stops", () => {
		const guardrail = new ToolFailureGuardrail({ maxConsecutiveFailures: 3 });
		const failed = { output: "no", isError: true };
		expect(guardrail.observe({ toolName: "write", args: { path: "a" }, result: failed }).forceStop).toBe(false);
		expect(guardrail.observe({ toolName: "write", args: { path: "a" }, result: failed }).consecutiveFailures).toBe(2);
		expect(guardrail.observe({ toolName: "write", args: { path: "b" }, result: failed }).consecutiveFailures).toBe(1);
		guardrail.observe({ toolName: "write", args: { path: "b" }, result: failed });
		expect(guardrail.observe({ toolName: "write", args: { path: "b" }, result: failed }).forceStop).toBe(true);
		expect(
			guardrail.observe({ toolName: "write", args: { path: "b" }, result: { output: "ok" } }).consecutiveFailures,
		).toBe(0);
	});

	it("force-stops an arg-varied failure loop on the same tool", () => {
		const guardrail = new ToolFailureGuardrail({ maxConsecutiveFailures: 3, maxFailureLoop: 4 });
		const fail = (command: string) =>
			guardrail.observe({
				toolName: "bash",
				args: { command },
				result: { output: "Downloaded file not found at expected path", isError: true },
			});
		// Every failure has fresh arguments, so the identical-signature counter
		// never reaches maxConsecutiveFailures; the loop counter must still stop it.
		expect(fail("agent-browser download a").forceStop).toBe(false);
		expect(fail("agent-browser download b").forceStop).toBe(false);
		expect(fail("agent-browser download c").forceStop).toBe(false);
		const decision = fail("agent-browser download d");
		expect(decision.consecutiveFailures).toBe(1);
		expect(decision.failureStreak).toBe(4);
		expect(decision.forceStop).toBe(true);
		expect(decision.reminder).toContain("even though the arguments varied");
	});

	it("escalates loop reminders before the force stop", () => {
		const guardrail = new ToolFailureGuardrail({ maxConsecutiveFailures: 100, maxFailureLoop: 8 });
		const reminders: string[] = [];
		for (let i = 1; i <= 7; i += 1) {
			const decision = guardrail.observe({
				toolName: "bash",
				args: { command: `attempt ${i}` },
				result: { output: `attempt ${i} failed`, isError: true },
			});
			expect(decision.forceStop).toBe(false);
			if (decision.reminder?.includes("times in a row")) reminders.push(decision.reminder);
		}
		expect(reminders).toHaveLength(2);
		expect(reminders[0]).toContain("3 times in a row");
		expect(reminders[1]).toContain("5 times in a row");
		expect(reminders[0]).toContain("Change strategy");
	});

	it("resets the failure loop on any success", () => {
		const guardrail = new ToolFailureGuardrail({ maxFailureLoop: 3 });
		const fail = () =>
			guardrail.observe({ toolName: "bash", args: { command: "x" }, result: { output: "no", isError: true } });
		fail();
		fail();
		guardrail.observe({ toolName: "read", args: {}, result: { output: "ok" } });
		const decision = fail();
		expect(decision.failureStreak).toBe(1);
		expect(decision.forceStop).toBe(false);
	});

	it("resets the failure loop when a different tool fails", () => {
		const guardrail = new ToolFailureGuardrail({ maxFailureLoop: 3 });
		const fail = (toolName: string) =>
			guardrail.observe({ toolName, args: {}, result: { output: "no", isError: true } });
		fail("bash");
		fail("bash");
		const decision = fail("read");
		expect(decision.failureStreak).toBe(1);
		expect(decision.forceStop).toBe(false);
	});

	it("groups errors that differ only in volatile details into one error class", () => {
		const guardrail = new ToolFailureGuardrail({ maxConsecutiveFailures: 100, maxFailureLoop: 100 });
		const fail = (output: string) =>
			guardrail.observe({ toolName: "bash", args: { command: output }, result: { output, isError: true } });
		expect(fail('Download failed: file "report-1042.pdf" missing at /tmp/dl/9f2e1a/output after 30 retries').errorClassStreak).toBe(1);
		expect(fail('Download failed: file "report-2048.pdf" missing at /tmp/dl/71bc09/output after 12 retries').errorClassStreak).toBe(2);
		const decision = fail('Download failed: file "report-4096.pdf" missing at C:\\dl\\aa0055\\output after 7 retries');
		expect(decision.errorClassStreak).toBe(3);
		expect(decision.reminder).toContain("same error");
	});
});

describe("normalizeObservationText", () => {
	it("strips UUIDs, long hex ids, absolute paths, numbers, and quoted strings", () => {
		const normalized = normalizeObservationText(
			'Error 5503 at F:\\work\\dl\\out.bin for "session 9f2e1a" (id 3f2504e0-4f89-41d3-9a0c-0305e82c3301, ref deadbeefdeadbeef)',
		);
		expect(normalized).not.toContain("5503");
		expect(normalized).not.toContain("9f2e1a");
		expect(normalized).not.toContain("3f2504e0");
		expect(normalized).not.toContain("deadbeef");
		expect(normalized).not.toContain("F:\\work\\dl\\out.bin");
		expect(normalized).toContain("error");
	});

	it("collapses whitespace and truncates to a bounded length", () => {
		const normalized = normalizeObservationText(`  a   b\n\n${"x".repeat(500)}  `);
		expect(normalized.startsWith("a b")).toBe(true);
		expect(normalized.length).toBeLessThanOrEqual(120);
	});
});
