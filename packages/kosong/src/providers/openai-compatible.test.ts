import { afterEach, describe, expect, it, vi } from "vitest";
import { createOpenAICompatibleProvider } from "./openai-compatible.js";
import type { ChatMessage } from "../types.js";

afterEach(() => {
	vi.unstubAllGlobals();
});

describe("OpenAICompatibleProvider image handling (deepseek)", () => {
	it("hoists tool-result images into a user message with the data url intact", async () => {
		const url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==";
		const body = await captureRequest([
			{ role: "user", content: "look at this" },
			{
				role: "tool",
				toolCallId: "call_1",
				content: [
					{ type: "text", text: "<system>Read image file.</system>" },
					// read_media emits camelCase imageUrl parts.
					{ type: "image_url", imageUrl: { url } } as never,
				],
			},
		]);

		const messages = body["messages"] as Array<Record<string, unknown>>;
		const toolMessage = messages.find((message) => message["role"] === "tool");
		expect(toolMessage?.["content"]).toBe("<system>Read image file.</system>");
		const userMessages = messages.filter((message) => message["role"] === "user");
		const hoisted = userMessages.at(-1)?.["content"] as Array<Record<string, unknown>>;
		expect(hoisted).toContainEqual({ type: "image_url", image_url: { url } });
	});

	it("keeps valid snake_case image parts as-is on the generic path", async () => {
		const url = "data:image/jpeg;base64,/9j/4AAQSkZJRg==";
		const body = await captureRequest(
			[
				{
					role: "user",
					content: [{ type: "image_url", image_url: { url } }],
				},
			],
			"openrouter",
		);
		const messages = body["messages"] as Array<Record<string, unknown>>;
		expect(messages[0]?.["content"]).toEqual([{ type: "image_url", image_url: { url } }]);
	});

	it.each([
		["empty url", { type: "image_url", image_url: { url: "" } }],
		["missing both casings", { type: "image_url" }],
		["non-data url", { type: "image_url", image_url: { url: "https://example.com/x.png" } }],
		["unsupported mime", { type: "image_url", image_url: { url: "data:image/svg+xml;base64,PHN2Zy8+" } }],
		["truncated base64 marker", { type: "image_url", image_url: { url: "data:image/png;base64," } }],
	])("replaces an image part with %s by a text note", async (_label, imagePart) => {
		const body = await captureRequest([
			{ role: "user", content: "look at this" },
			{
				role: "tool",
				toolCallId: "call_1",
				content: [{ type: "text", text: "before" }, imagePart as never, { type: "text", text: "after" }],
			},
		]);

		const serialized = JSON.stringify(body["messages"]);
		expect(serialized).not.toContain('"image_url"');
		expect(serialized).toContain("[image attachment omitted: invalid payload]");
	});

	it("drops only the invalid image and keeps valid ones in the same request", async () => {
		const valid = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==";
		const body = await captureRequest([
			{ role: "user", content: "compare" },
			{
				role: "tool",
				toolCallId: "call_1",
				content: [
					{ type: "image_url", imageUrl: { url: "" } } as never,
					{ type: "image_url", imageUrl: { url: valid } } as never,
				],
			},
		]);

		const serialized = JSON.stringify(body["messages"]);
		expect(serialized).toContain(valid);
		expect(serialized).toContain("[image attachment omitted: invalid payload]");
	});
});

async function captureRequest(messages: ChatMessage[], providerId = "deepseek"): Promise<Record<string, unknown>> {
	let captured: Record<string, unknown> | undefined;
	vi.stubGlobal(
		"fetch",
		vi.fn(async (_url: string, init: RequestInit) => {
			captured = JSON.parse(String(init.body)) as Record<string, unknown>;
			return new Response(
				JSON.stringify({
					choices: [{ message: { role: "assistant", content: "ok" }, finish_reason: "stop" }],
					usage: { prompt_tokens: 1, completion_tokens: 1 },
				}),
				{ status: 200, headers: { "content-type": "application/json" } },
			);
		}),
	);
	const provider = createOpenAICompatibleProvider(providerId, { apiKey: "fixture", baseUrl: "https://fixture.invalid" });
	await provider.chat({ modelName: "fixture-model", messages, tools: [] });
	if (!captured) throw new Error("provider did not issue a request");
	return captured;
}
