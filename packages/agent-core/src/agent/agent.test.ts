import { describe, expect, it } from "vitest";
import { KagekoAgent, type PromptPart } from "./agent.js";
import type { AgentLlm } from "../turn/turn-runner.js";
import type { DurableEventInput } from "@kageko/protocol";

function stubLlm(): AgentLlm {
	return {
		chat: async () => ({
			content: "done",
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		}),
		model: { contextLength: 128000 },
		modelName: "stub",
		isRetryableError: () => false,
	} as unknown as AgentLlm;
}

function stubAgent(recorded: DurableEventInput<"user.prompt">[]): KagekoAgent {
	return new KagekoAgent({
		llm: stubLlm(),
		registry: { asFunctions: () => [] } as never,
		kaos: {},
		tracker: {} as never,
		permission: {} as never,
		telemetry: { record: () => {} } as never,
		recordStore: {
			append: async (event: DurableEventInput<"user.prompt">) => {
				recorded.push(event);
			},
		} as never,
	});
}

describe("KagekoAgent prompt journaling of image parts", () => {
	it("preserves camelCase imageUrl payloads instead of journaling an empty url", async () => {
		const recorded: DurableEventInput<"user.prompt">[] = [];
		const agent = stubAgent(recorded);
		const url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==";

		await agent.prompt([
			{ type: "text", text: "hi" },
			{ type: "image_url", imageUrl: { url } } as unknown as PromptPart,
		]);

		const parts = recorded.find((event) => event.type === "user.prompt")?.data.parts;
		expect(parts).toContainEqual({ type: "image_url", image_url: { url } });
	});

	it("drops image parts without a resolvable url rather than journaling an empty one", async () => {
		const recorded: DurableEventInput<"user.prompt">[] = [];
		const agent = stubAgent(recorded);

		await agent.prompt([{ type: "image_url" } as unknown as PromptPart]);

		const parts = recorded.find((event) => event.type === "user.prompt")?.data.parts ?? [];
		expect(parts.some((part) => part.type === "image_url")).toBe(false);
	});
});
