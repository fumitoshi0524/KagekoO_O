import { describe, expect, it } from "vitest";
import { needCapabilityTool } from "./need-capability.js";
import type { LearningEvent } from "../../memory/learning/event.js";

const evidence = {
	scope: "local_operation" as const,
	futureTasks: ["Create a daily report", "Create a weekly report"],
	alternativesChecked: ["Checked all loaded capabilities"],
};

function captureBus() {
	const enqueued: LearningEvent[] = [];
	const session = {
		learningBus: {
			enqueue: (event: LearningEvent) => {
				enqueued.push(event);
			},
		},
	};
	return { enqueued, session };
}

describe("need_capability", () => {
	it("passes structured required contracts through to the capability-gap event", async () => {
		const { enqueued, session } = captureBus();
		const requiredContracts = [
			{ name: "exact_tool", inputSchema: { type: "object", properties: { value: { type: "string" } } } },
		];

		const result = await needCapabilityTool.execute!(
			{ description: "Provide exact_tool.", evidence, requiredContracts },
			{ session } as never,
		);

		expect(result.isError).not.toBe(true);
		expect(enqueued).toHaveLength(1);
		expect(enqueued[0]?.source).toBe("capability_gap");
		expect(enqueued[0]?.payload["requiredContracts"]).toEqual(requiredContracts);
	});

	it("accepts input_schema as an alias for inputSchema", async () => {
		const { enqueued, session } = captureBus();
		const schema = { type: "object", properties: { value: { type: "string" } } };

		const result = await needCapabilityTool.execute!(
			{
				description: "Provide aliased_contract.",
				evidence,
				requiredContracts: [{ name: "aliased_contract", input_schema: schema }],
			},
			{ session } as never,
		);

		expect(result.isError).not.toBe(true);
		expect(enqueued[0]?.payload["requiredContracts"]).toEqual([{ name: "aliased_contract", inputSchema: schema }]);
	});

	it("omits requiredContracts when none are supplied", async () => {
		const { enqueued, session } = captureBus();

		const result = await needCapabilityTool.execute!(
			{ description: "Provide a reusable workflow capability.", evidence },
			{ session } as never,
		);

		expect(result.isError).not.toBe(true);
		expect(enqueued).toHaveLength(1);
		expect(enqueued[0]?.payload["requiredContracts"]).toBeUndefined();
	});

	it("drops contract entries without a usable name or schema", async () => {
		const { enqueued, session } = captureBus();

		const result = await needCapabilityTool.execute!(
			{
				description: "Provide partially specified contracts.",
				evidence,
				requiredContracts: [
					{ name: "valid_tool", inputSchema: { type: "object" } },
					{ inputSchema: { type: "object" } },
					{ name: "missing_schema" },
				],
			},
			{ session } as never,
		);

		expect(result.isError).not.toBe(true);
		expect(enqueued[0]?.payload["requiredContracts"]).toEqual([
			{ name: "valid_tool", inputSchema: { type: "object" } },
		]);
	});

	it("omits requiredContracts when every supplied entry is malformed", async () => {
		const { enqueued, session } = captureBus();

		const result = await needCapabilityTool.execute!(
			{
				description: "Provide contracts that are all unusable.",
				evidence,
				requiredContracts: [
					{ name: "  ", inputSchema: { type: "object" } },
					{ name: "array_schema", inputSchema: [{ type: "object" }] as never },
					{ input_schema: { type: "object" } },
				],
			},
			{ session } as never,
		);

		expect(result.isError).not.toBe(true);
		expect(enqueued).toHaveLength(1);
		expect(enqueued[0]?.payload["requiredContracts"]).toBeUndefined();
	});

	it("keeps the existing validation of description and evidence", async () => {
		const { enqueued, session } = captureBus();

		const tooShort = await needCapabilityTool.execute!({ description: "no", evidence }, { session } as never);
		expect(tooShort.isError).toBe(true);

		const noEvidence = await needCapabilityTool.execute!(
			{
				description: "Provide a reusable capability.",
				evidence: { ...evidence, futureTasks: ["only one task"] },
			},
			{ session } as never,
		);
		expect(noEvidence.isError).toBe(true);
		expect(enqueued).toHaveLength(0);
	});
});
