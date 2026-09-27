import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { LearningProcessor } from "./processor.js";
import type { LearningEvent } from "./event.js";

function makeProcessor(dir: string, overrides: Record<string, unknown> = {}) {
	const onOutput = vi.fn();
	const processor = new LearningProcessor({
		bus: { subscribe: () => () => {} } as never,
		triage: { triage: async () => ({ action: "drop" }) } as never,
		pendingDir: dir,
		onOutput,
		...overrides,
	});
	return { processor, onOutput };
}

function makeEvent(id: string, source: LearningEvent["source"] = "capability_gap"): LearningEvent {
	return { id, source, timestamp: 1, payload: { description: `proposal ${id}` } };
}

describe("LearningProcessor.submitAgentProposal", () => {
	it("stashes a proposal with the exact legacy pending entry shape", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor, onOutput } = makeProcessor(dir);
		const event = makeEvent("agent-1", "capability_gap");
		const output = { kind: "tool", name: "read-file", status: "pending" };

		const result = await processor.submitAgentProposal("capability_gap", event, output);

		expect(result).toEqual({ stashed: true });
		const lines = (await fs.readFile(processor.pendingPath, "utf-8")).trim().split("\n");
		expect(lines).toHaveLength(1);
		expect(JSON.parse(lines[0]!)).toEqual({
			event: { id: "agent-1", source: "capability_gap", timestamp: 1, payload: { description: "proposal agent-1" } },
			decision: { action: "pending", target: "capability_gap", reason: "learner-agent proposal" },
			output: { kind: "tool", name: "read-file", status: "pending" },
		});
		expect(onOutput).toHaveBeenCalledOnce();
		expect(onOutput.mock.calls[0]?.[0]).toEqual({ action: "pending", target: "capability_gap", reason: "learner-agent proposal" });
	});

	it("dedupes by event id and reports the duplicate", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor } = makeProcessor(dir);
		const event = makeEvent("agent-dup");

		expect((await processor.submitAgentProposal("skill", event, { name: "a" })).stashed).toBe(true);
		expect(await processor.submitAgentProposal("skill", event, { name: "a" })).toEqual({
			stashed: false,
			reason: "duplicate",
		});
		expect(await processor.listPending()).toHaveLength(1);
	});

	it("redacts secrets from the event payload before stashing", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor } = makeProcessor(dir);
		const event = makeEvent("agent-secret");
		event.payload = { description: "connect with api_key=supersecretvalue" };

		const result = await processor.submitAgentProposal("capability_gap", event, { name: "x" });

		expect(result.stashed).toBe(true);
		const raw = await fs.readFile(processor.pendingPath, "utf-8");
		expect(raw).not.toContain("supersecretvalue");
		expect(raw).toContain("[redacted]");
	});

	it("degrades a throwing onOutput hook to a diagnostic after stashing", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const onDiagnostic = vi.fn();
		const { processor } = makeProcessor(dir, {
			onOutput: async () => {
				throw new Error("reload failed");
			},
			onDiagnostic,
		});

		const result = await processor.submitAgentProposal("skill", makeEvent("agent-hook"), { name: "x" });

		expect(result).toEqual({ stashed: true });
		expect(await processor.listPending()).toHaveLength(1);
		expect(onDiagnostic).toHaveBeenCalledOnce();
		expect(String(onDiagnostic.mock.calls[0]?.[0])).toContain("onOutput hook failed");
	});

	it("does not stash empty output and does not fire onOutput", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor, onOutput } = makeProcessor(dir);

		expect(await processor.submitAgentProposal("skill", makeEvent("agent-empty"), undefined)).toEqual({
			stashed: false,
			reason: "empty output",
		});
		expect(await processor.listPending()).toHaveLength(0);
		expect(onOutput).not.toHaveBeenCalled();
	});

	it("skips already-approved output but still fires onOutput", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor, onOutput } = makeProcessor(dir);
		const event = makeEvent("agent-approved");
		const output = { kind: "tool", name: "auto-tool", status: "approved", filePath: "x" };

		const result = await processor.submitAgentProposal("capability_gap", event, output);

		expect(result).toEqual({ stashed: false, reason: "already approved" });
		expect(await processor.listPending()).toHaveLength(0);
		expect(onOutput).toHaveBeenCalledOnce();
		expect(onOutput.mock.calls[0]?.[2]).toEqual(output);
	});

	it("prunes past maxPendingEntries, keeping the newest", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor } = makeProcessor(dir, { maxPendingEntries: 2 });

		await processor.submitAgentProposal("skill", makeEvent("agent-1"), { name: "one" });
		await processor.submitAgentProposal("skill", makeEvent("agent-2"), { name: "two" });
		await processor.submitAgentProposal("skill", makeEvent("agent-3"), { name: "three" });

		const pending = await processor.listPending();
		expect(pending.map((entry) => entry.event.id)).toEqual(["agent-2", "agent-3"]);
		// A pruned id may be stashed again.
		expect((await processor.submitAgentProposal("skill", makeEvent("agent-1"), { name: "one" })).stashed).toBe(true);
		expect((await processor.listPending()).map((entry) => entry.event.id)).toEqual(["agent-3", "agent-1"]);
	});

	it("marks onOutput with stashed info so hosts can notify on new proposals", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-submit-proposal-"));
		const { processor, onOutput } = makeProcessor(dir);
		processor.registerLearner("capability_gap", { handle: () => undefined, approve: (output) => output });
		const event = makeEvent("agent-stash");

		await processor.submitAgentProposal("capability_gap", event, { kind: "tool", name: "x" });
		expect(onOutput.mock.calls[0]?.[3]).toEqual({ stashed: true });

		// A duplicate submission is not a new proposal.
		await processor.submitAgentProposal("capability_gap", event, { kind: "tool", name: "x" });
		expect(onOutput.mock.calls[1]?.[3]).toEqual({ stashed: false });

		// Approval reports carry no stash marker.
		await processor.approvePending(event.id);
		const approvalCall = onOutput.mock.calls[2];
		expect(approvalCall?.[2]).toMatchObject({ status: "approved" });
		expect(approvalCall?.[3]).toBeUndefined();
	});
});

describe("LearningProcessor.listPending diagnostics", () => {
	it("reports skipped corrupt lines instead of reading them as absent", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-list-pending-"));
		const onDiagnostic = vi.fn();
		const { processor } = makeProcessor(dir, { onDiagnostic });
		await processor.submitAgentProposal("skill", makeEvent("good-1"), { name: "one" });
		await fs.appendFile(processor.pendingPath, "{not json\n");

		const pending = await processor.listPending();

		expect(pending.map((entry) => entry.event.id)).toEqual(["good-1"]);
		expect(onDiagnostic).toHaveBeenCalledOnce();
		expect(String(onDiagnostic.mock.calls[0]?.[0])).toContain("skipped 1 unreadable line(s)");
	});

	it("reports an unreadable queue file instead of reading it as empty", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-list-pending-"));
		const onDiagnostic = vi.fn();
		// A directory at the pending path stats fine but cannot be read as a file.
		const pendingPath = path.join(dir, "pending.jsonl");
		await fs.mkdir(pendingPath);
		const { processor } = makeProcessor(dir, { onDiagnostic, pendingPath });

		expect(await processor.listPending()).toEqual([]);
		expect(onDiagnostic).toHaveBeenCalledOnce();
		expect(String(onDiagnostic.mock.calls[0]?.[0])).toContain("pending queue is unreadable");
	});

	it("stays silent when the queue file does not exist", async () => {
		const dir = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-list-pending-"));
		const onDiagnostic = vi.fn();
		const { processor } = makeProcessor(dir, { onDiagnostic });

		expect(await processor.listPending()).toEqual([]);
		expect(onDiagnostic).not.toHaveBeenCalled();
	});
});
