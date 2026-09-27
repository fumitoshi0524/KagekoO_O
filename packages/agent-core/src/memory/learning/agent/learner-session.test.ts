import { describe, expect, it } from "vitest";
import { createLearnerRunScope } from "./learner-session.js";

describe("createLearnerRunScope", () => {
	it("journals events in memory with durable metadata and never touches an external store", async () => {
		const scope = createLearnerRunScope("learner-run-test");
		const first = await scope.recordStore.append({
			type: "turn.started",
			meta: { turnId: "turn-1", activityId: "turn-1" },
			data: {},
		});
		const second = await scope.recordStore.append({
			type: "tool.call",
			meta: { turnId: "turn-1", activityId: "turn-1" },
			data: { call: { id: "call-1", name: "propose_skill", arguments: {} } },
		});

		expect(first.meta.sessionId).toBe("learner-run-test");
		expect(second.meta.sequence).toBe(first.meta.sequence + 1);
		const loaded = await scope.recordStore.load();
		expect(loaded.map((event) => event.type)).toEqual(["turn.started", "tool.call"]);
		expect(scope.events).toHaveLength(2);
	});

	it("provides the narrow session surface without learning bus, hooks, or goals", () => {
		const scope = createLearnerRunScope("learner-run-surface");
		expect(scope.session.sessionId).toBe("learner-run-surface");
		expect(scope.session.isClosed?.()).toBe(false);
		// Deliberately absent: a learning bus here would feed the learner's own
		// tool traffic back into the pipeline as new evidence.
		expect("learningBus" in scope.session).toBe(false);
		expect("hookEngine" in scope.session).toBe(false);
		expect("goalStore" in scope.session).toBe(false);
		expect("runTurn" in scope.session).toBe(false);
	});
});
