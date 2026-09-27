import { describe, expect, it } from "vitest";
import { AgentGraph } from "./agent-graph.js";
import type { AgentGraphEdge, AgentGraphNode } from "./agent-graph.js";

describe("AgentGraph.startLearnerRun", () => {
	it("starts a running learner node linked from the resident learner with a run edge", () => {
		const graph = new AgentGraph();
		const coordinator = graph.register({ id: "coordinator", role: "coordinator" });
		const learner = graph.registerResidentLearner("learner", coordinator.id);

		const run = graph.startLearnerRun(learner.id, "nightly pass");

		expect(run.role).toBe("learner");
		expect(run.status).toBe("running");
		expect(run.parentId).toBe(learner.id);
		expect(run.label).toBe("nightly pass");
		expect(run.id).not.toBe(learner.id);

		const { edges } = graph.snapshot();
		expect(edges).toContainEqual(expect.objectContaining({ from: learner.id, to: run.id, kind: "run" }));
	});

	it("throws for an unknown learner id", () => {
		const graph = new AgentGraph();
		expect(() => graph.startLearnerRun("missing")).toThrow(/resident learner/i);
	});

	it("throws when the node is not a learner", () => {
		const graph = new AgentGraph();
		const executor = graph.register({ id: "executor", role: "executor", status: "running" });
		expect(() => graph.startLearnerRun(executor.id)).toThrow(/resident learner/i);
	});

	it("throws when the learner is not resident", () => {
		const graph = new AgentGraph();
		const learner = graph.register({ id: "learner", role: "learner", status: "running" });
		expect(() => graph.startLearnerRun(learner.id)).toThrow(/resident learner/i);
	});

	it("returns a defensive copy that cannot mutate graph state", () => {
		const graph = new AgentGraph();
		graph.registerResidentLearner("learner", "coordinator");
		const run = graph.startLearnerRun("learner");
		(run as { status: string }).status = "failed";
		const stored = graph.snapshot().nodes.find((node) => node.id === run.id);
		expect(stored?.status).toBe("running");
	});
});

describe("AgentGraph learner run lifecycle", () => {
	it("finish() completes the run and links a result edge back to the resident learner", () => {
		const graph = new AgentGraph();
		graph.registerResidentLearner("learner", "coordinator");
		const run = graph.startLearnerRun("learner");

		graph.finish(run.id, "completed");

		const snapshot = graph.snapshot();
		expect(snapshot.nodes.find((node) => node.id === run.id)?.status).toBe("completed");
		expect(snapshot.edges).toContainEqual(
			expect.objectContaining({ from: run.id, to: "learner", kind: "result" }),
		);
		// The resident learner itself stays resident and keeps observing.
		expect(snapshot.nodes.find((node) => node.id === "learner")?.status).toBe("resident");
	});

	it("double-finish is a silent no-op: terminal status and result edge from the first call win", () => {
		const graph = new AgentGraph();
		graph.registerResidentLearner("learner", "coordinator");
		const run = graph.startLearnerRun("learner");

		graph.finish(run.id, "completed");
		graph.finish(run.id, "failed");

		const snapshot = graph.snapshot();
		expect(snapshot.nodes.find((node) => node.id === run.id)?.status).toBe("completed");
		expect(snapshot.edges.filter((edge) => edge.kind === "result" && edge.from === run.id)).toHaveLength(1);
	});

	it("start() still refuses learner roles", () => {
		const graph = new AgentGraph();
		graph.registerResidentLearner("learner", "coordinator");
		expect(() => graph.start("learner", "learner")).toThrow(/Only executor agents can be started/);
	});
});

describe("AgentGraph.snapshot", () => {
	it("returns defensive copies unaffected by later mutations", () => {
		const graph = new AgentGraph();
		graph.registerResidentLearner("learner", "coordinator");
		const run = graph.startLearnerRun("learner");

		const snapshot = graph.snapshot();
		(snapshot.nodes[0] as { status: string }).status = "failed";
		(snapshot.edges[0] as { kind: string }).kind = "plan";
		(snapshot.nodes as AgentGraphNode[]).push({ id: "injected", role: "executor", status: "running" });
		(snapshot.edges as AgentGraphEdge[]).length = 0;

		const fresh = graph.snapshot();
		expect(fresh.nodes.find((node) => node.id === "learner")?.status).toBe("resident");
		expect(fresh.nodes.find((node) => node.id === "injected")).toBeUndefined();
		expect(fresh.edges).toContainEqual(expect.objectContaining({ from: "learner", to: run.id, kind: "run" }));
	});
});
