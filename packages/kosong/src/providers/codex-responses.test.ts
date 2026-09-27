import { afterEach, describe, expect, it, vi } from "vitest";
import { CodexResponsesProvider } from "./codex-responses.js";

afterEach(() => {
	vi.unstubAllGlobals();
});

describe("CodexResponsesProvider streaming tool calls", () => {
	it("preserves a streamed function call when the terminal response output is empty", async () => {
		const deltas: string[] = [];
		stubSse([
			{
				type: "response.output_item.added",
				output_index: 0,
				item: { type: "function_call", id: "item_1", call_id: "call_1", name: "search_files", arguments: "" },
			},
			{
				type: "response.function_call_arguments.delta",
				item_id: "item_1",
				output_index: 0,
				delta: '{"query":"spring',
			},
			{
				type: "response.function_call_arguments.done",
				item_id: "item_1",
				output_index: 0,
				arguments: '{"query":"spring launch"}',
			},
			{
				type: "response.completed",
				response: { status: "completed", output: [], usage: { input_tokens: 12, output_tokens: 7 } },
			},
		]);

		const result = await provider().chat({
			modelName: "gpt-5.6-terra",
			messages: [{ role: "user", content: "Find the file" }],
			tools: [tool("search_files")],
			onToolCallDelta: (delta) => deltas.push(delta.argumentsPartial),
		});

		expect(result).toEqual({
			content: "",
			toolCalls: [{ id: "call_1", name: "search_files", arguments: { query: "spring launch" } }],
			finishReason: "tool_calls",
			usage: { promptTokens: 12, completionTokens: 7 },
		});
		expect(deltas.at(-1)).toBe('{"query":"spring launch"}');
	});

	it("uses output_item.done as the final streamed call without duplicating it", async () => {
		stubSse([
			{
				type: "response.output_item.added",
				output_index: 2,
				item: { type: "function_call", id: "item_2", call_id: "call_2", name: "create_draft", arguments: "" },
			},
			{
				type: "response.function_call_arguments.delta",
				item_id: "item_2",
				output_index: 2,
				delta: '{"subject":"Draft"}',
			},
			{
				type: "response.output_item.done",
				output_index: 2,
				item: {
					type: "function_call",
					id: "item_2",
					call_id: "call_2",
					name: "create_draft",
					arguments: '{"subject":"Final"}',
				},
			},
			{
				type: "response.completed",
				response: {
					status: "completed",
					output: [
						{
							type: "function_call",
							id: "item_2",
							call_id: "call_2",
							name: "create_draft",
							arguments: '{"subject":"Final"}',
						},
					],
				},
			},
		]);

		const result = await provider().chat({
			modelName: "gpt-5.6-terra",
			messages: [{ role: "user", content: "Create it" }],
			tools: [tool("create_draft")],
		});

		expect(result.toolCalls).toEqual([{ id: "call_2", name: "create_draft", arguments: { subject: "Final" } }]);
		expect(result.finishReason).toBe("tool_calls");
	});
});

function provider(): CodexResponsesProvider {
	return new CodexResponsesProvider(async () => ({
		headers: { Authorization: "Bearer fixture" },
		baseUrl: "https://fixture.invalid/backend-api/codex",
	}));
}

function tool(name: string) {
	return {
		function: {
			name,
			description: `${name} fixture`,
			parameters: { type: "object", additionalProperties: true },
		},
	};
}

function stubSse(events: readonly Record<string, unknown>[]): void {
	const body = `${events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("")}data: [DONE]\n\n`;
	vi.stubGlobal(
		"fetch",
		vi.fn(async () => new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } })),
	);
}
