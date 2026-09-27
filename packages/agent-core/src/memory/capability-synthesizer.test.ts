import { describe, expect, it, vi } from "vitest";
import { CapabilitySynthesizer } from "./capability-synthesizer.js";
import type { SessionEvent } from "./types.js";

describe("CapabilitySynthesizer", () => {
	it("retains the authoritative user contract after later discovery events", async () => {
		const chat = vi.fn().mockResolvedValue({
			content: JSON.stringify({ manifest: { kind: "none" } }),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events: SessionEvent[] = [
			{
				type: "user.prompt",
				data: {
					content: 'Required public tool contracts: {"name":"exact_public_name","input_schema":{"type":"object"}}',
				},
			} as unknown as SessionEvent,
			...Array.from(
				{ length: 20 },
				(_, index) =>
					({
						type: "tool.call",
						data: { call: { id: `call-${index}`, name: "discovery", arguments: { index } } },
					}) as unknown as SessionEvent,
			),
		];

		await synthesizer.synthesize({
			description: "Provide a reusable capability.",
			recentEvents: events,
		});

		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("exact_public_name");
		expect(prompt).toContain("preserve every tool name and recursive input schema exactly");
		expect(prompt).toContain("number accepts finite non-integer values");
		expect(prompt).toContain("Never hard-code their argument or result values");
		expect(prompt).toContain("preserve the caller's original JSON values");
		expect(prompt).toContain("do not infer isError from wording alone");
		expect(prompt).toContain("String.fromCharCode(10)");
		expect(prompt).toContain("binding architecture constraint");
		expect(prompt).toContain("do not authorize transformations or restrictions");
		expect(prompt).toContain("Do not strip namespace prefixes");
		expect(prompt).toContain("optional fields omitted");
		expect(prompt).toContain("do not spread undeclared input fields");
		expect(prompt).toContain("must count values that actually changed or were removed");
		expect(prompt).toContain("call sequences, lifecycle rules, and preconditions");
		expect(prompt).toContain("store it beneath process.cwd()");
		expect(prompt).toContain("never write mutable state beside __filename");
	});

	it("repairs a capability that violates the required architecture kind", async () => {
		const chat = vi
			.fn()
			.mockResolvedValueOnce({
				content: JSON.stringify({
					manifest: { kind: "mcp", name: "single-op-server", description: "Too much", command: "node", args: [] },
					code: "",
				}),
				toolCalls: [],
				finishReason: "stop",
				usage: { promptTokens: 1, completionTokens: 1 },
			})
			.mockResolvedValueOnce({
				content: JSON.stringify({
					manifest: {
						kind: "tool",
						name: "single-op",
						description: "One operation",
						parameters: { type: "object", properties: {} },
						command: "node",
						args: ["{{__args_json}}"],
					},
					code: "process.stdout.write('{}')",
				}),
				toolCalls: [],
				finishReason: "stop",
				usage: { promptTokens: 1, completionTokens: 1 },
			});
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({ description: "Perform one operation.", proposedKind: "tool" });

		expect(result?.manifest.kind).toBe("tool");
		expect(chat).toHaveBeenCalledTimes(2);
		const repairPrompt = chat.mock.calls[1]?.[0].messages.at(-1)?.content as string;
		expect(repairPrompt).toContain("manifest kind mcp does not match required kind tool");
	});

	it("derives an MCP boundary from multiple exact public operations instead of trusting a wrong agent hint", async () => {
		const chat = vi.fn().mockResolvedValue({
			content: JSON.stringify({
				manifest: {
					kind: "mcp",
					name: "journey-service",
					description: "Two stateful journey operations",
					command: "node",
					args: [],
				},
				code: "process.stdin.resume()",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts (names and input schemas are exact):\n${JSON.stringify([
						{ name: "journey_step", input_schema: { type: "object", properties: {} } },
						{ name: "journey_summary", input_schema: { type: "object", properties: {} } },
					])}`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Provide two stateful journey operations.",
			proposedKind: "tool",
			recentEvents: events,
		});

		expect(result?.manifest.kind).toBe("mcp");
		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("Required capability kind: mcp");
		expect(prompt).toContain("Agent architecture hint: tool");
		expect(chat).toHaveBeenCalledOnce();
	});

	it("repairs an inflated MCP proposal when the public surface has one operation", async () => {
		const response = (kind: "tool" | "mcp") => ({
			content: JSON.stringify(
				kind === "mcp"
					? {
							manifest: {
								kind,
								name: "debate-session",
								description: "One action surface with shared session state",
								command: "node",
								args: [],
							},
							code: "process.stdin.resume()",
						}
					: {
							manifest: {
								kind,
								name: "debate",
								description: "One local debate operation with workspace-backed state",
								parameters: { type: "object", properties: {} },
								command: "node",
								args: ["{{__args_json}}"],
							},
							code: "process.stdout.write('{}')",
						},
			),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi.fn().mockResolvedValueOnce(response("mcp")).mockResolvedValueOnce(response("tool"));
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts:\n${JSON.stringify([
						{ name: "debate", input_schema: { type: "object", properties: {} } },
					])}`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Track debate actions across calls.",
			proposedKind: "mcp",
			recentEvents: events,
		});

		expect(result?.manifest.kind).toBe("tool");
		expect(result?.manifest.name).toBe("debate");
		expect(chat.mock.calls[0]?.[0].messages[0].content).toContain("Required capability kind: tool");
		expect(chat.mock.calls[0]?.[0].messages[0].content).toContain("Agent architecture hint: mcp");
		expect(chat).toHaveBeenCalledTimes(2);
	});

	it("repairs a local tool that changes an exact public name or schema", async () => {
		const schema = { type: "object", properties: { value: { type: "string" } }, required: ["value"] };
		const response = (name: string, parameters: Record<string, unknown>) => ({
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name,
					description: "Echo one exact value",
					parameters,
					command: "node",
					args: ["{{__args_json}}"],
				},
				code: "process.stdout.write(JSON.parse(process.argv[2]).value)",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi
			.fn()
			.mockResolvedValueOnce(response("exact-name", { type: "object", properties: {} }))
			.mockResolvedValueOnce(response("exact_name", schema));
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts (names and input schemas are exact):\n${JSON.stringify([
						{ name: "exact_name", input_schema: schema },
					])}\n\nPublic behavior examples:`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Provide exact_name.",
			proposedKind: "tool",
			recentEvents: events,
		});

		expect(result?.manifest.name).toBe("exact_name");
		expect(result?.manifest.parameters).toEqual(schema);
		expect(chat).toHaveBeenCalledTimes(2);
		expect(chat.mock.calls[1]?.[0].messages.at(-1)?.content).toContain("does not match exact public name exact_name");
	});

	it("repairs generated CommonJS that does not parse", async () => {
		const response = (code: string) => ({
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name: "parse-safe",
					description: "Execute one parse-safe local operation",
					parameters: { type: "object", properties: {} },
					command: "node",
					args: ["{{__args_json}}"],
				},
				code,
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi
			.fn()
			.mockResolvedValueOnce(response("process.stdout.write('broken');)"))
			.mockResolvedValueOnce(response("process.stdout.write('ok')"));
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({
			description: "Perform one parse-safe operation.",
			proposedKind: "tool",
		});

		expect(result?.code).toBe("process.stdout.write('ok')");
		expect(chat.mock.calls[1]?.[0].messages.at(-1)?.content).toContain("invalid JavaScript syntax");
		expect(chat).toHaveBeenCalledTimes(2);
	});

	it("repairs a positional local-tool ABI into one complete JSON argument envelope", async () => {
		const response = (args: string[], code: string) => ({
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name: "optional-safe",
					description: "Handle omitted optional values without positional ambiguity",
					parameters: {
						type: "object",
						properties: { requiredValue: { type: "object" }, optionalValue: { type: "boolean" } },
						required: ["requiredValue"],
					},
					command: "node",
					args,
				},
				code,
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi
			.fn()
			.mockResolvedValueOnce(
				response(
					["{{requiredValue}}", "{{optionalValue}}"],
					"const value=JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify(value));",
				),
			)
			.mockResolvedValueOnce(
				response(
					["{{__args_json}}"],
					"const args=JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify(args));",
				),
			);
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({ description: "Provide optional-safe.", proposedKind: "tool" });

		expect(result?.manifest.args).toEqual(["{{__args_json}}"]);
		expect(chat).toHaveBeenCalledTimes(2);
		expect(chat.mock.calls[1]?.[0].messages.at(-1)?.content).toContain("one complete JSON argument object");
	});

	it("adversarially reviews a structurally valid exact-contract tool before accepting it", async () => {
		const schema = {
			type: "object",
			properties: { value: { type: "string" }, optional: { type: "boolean", default: false } },
			required: ["value"],
		};
		const response = (code: string) => ({
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name: "reviewed_tool",
					description: "Return a reviewed value",
					parameters: schema,
					command: "node",
					args: ["{{__args_json}}"],
				},
				code,
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi
			.fn()
			.mockResolvedValueOnce(response("const args=JSON.parse(process.argv[2]); process.stdout.write(args.value);"))
			.mockResolvedValueOnce(
				response(
					"const args=JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify({value:args.value,optional:args.optional??false}));",
				),
			);
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts:\n${JSON.stringify([
						{ name: "reviewed_tool", input_schema: schema },
					])}\n\nPublic behavior examples:`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Provide reviewed_tool.",
			proposedKind: "tool",
			recentEvents: events,
		});

		expect(result?.code).toContain("optional:args.optional??false");
		expect(chat).toHaveBeenCalledTimes(2);
		const reviewPrompt = chat.mock.calls[1]?.[0].messages.at(-1)?.content as string;
		expect(reviewPrompt).toContain("strict adversarial review");
		expect(reviewPrompt).toContain("atomic rollback");
		expect(reviewPrompt).toContain("prototype-pollution");
		expect(reviewPrompt).toContain("phase boundaries");
		expect(reviewPrompt).toContain("values declared to replace atomically");
		expect(reviewPrompt).toContain("{{__args_json}}");
		const initialPrompt = chat.mock.calls[0]?.[0].messages[0]?.content as string;
		expect(initialPrompt).toContain("transformation scope and traversal scope distinct");
		expect(initialPrompt).toContain("preserve its nested values exactly");
	});

	it("repairs an MCP implementation that publishes the dataset schema spelling on the wire", async () => {
		const response = (schemaField: "input_schema" | "inputSchema") => ({
			content: JSON.stringify({
				manifest: {
					kind: "mcp",
					name: "wire-safe",
					description: "Expose MCP operations using the protocol wire schema",
					command: "node",
					args: [],
				},
				code: `const tools=[{${schemaField}:{type:'object',properties:{}}}]; process.stdin.resume()`,
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const chat = vi.fn().mockResolvedValueOnce(response("input_schema")).mockResolvedValueOnce(response("inputSchema"));
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({
			description: "Expose a stateful MCP service.",
			proposedKind: "mcp",
		});

		expect(result?.code).toContain("inputSchema");
		expect(result?.code).not.toContain("input_schema");
		expect(chat.mock.calls[1]?.[0].messages.at(-1)?.content).toContain("required inputSchema wire field");
		expect(chat).toHaveBeenCalledTimes(2);
	});

	it("rejects a repaired proposal that still violates the required kind", async () => {
		const response = {
			content: JSON.stringify({
				manifest: { kind: "mcp", name: "single-op-server", description: "Too much", command: "node", args: [] },
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		};
		const chat = vi.fn().mockResolvedValue(response);
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		await expect(
			synthesizer.synthesize({ description: "Perform one operation.", proposedKind: "tool" }),
		).rejects.toThrow("manifest kind mcp does not match required kind tool");
		expect(chat).toHaveBeenCalledTimes(2);
	});

	it("forces the kind from structured required contracts without a prompt marker", async () => {
		const schema = { type: "object", properties: { value: { type: "string" } }, required: ["value"] };
		const response = {
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name: "structured_tool",
					description: "Echo one exact value",
					parameters: schema,
					command: "node",
					args: ["{{__args_json}}"],
				},
				code: "process.stdout.write(JSON.parse(process.argv[2]).value)",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		};
		const chat = vi.fn().mockResolvedValue(response);
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({
			description: "Provide structured_tool.",
			proposedKind: "mcp",
			requiredContracts: [{ name: "structured_tool", inputSchema: schema }],
		});

		expect(result?.manifest.kind).toBe("tool");
		expect(result?.manifest.name).toBe("structured_tool");
		expect(result?.manifest.parameters).toEqual(schema);
		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("Required capability kind: tool");
		expect(prompt).toContain("Agent architecture hint: mcp");
		// A single exact-contract tool still goes through the adversarial review pass.
		expect(chat).toHaveBeenCalledTimes(2);
	});

	it("lets structured required contracts outrank the free-text marker", async () => {
		const schema = { type: "object", properties: { value: { type: "string" } }, required: ["value"] };
		const response = {
			content: JSON.stringify({
				manifest: {
					kind: "tool",
					name: "structured_tool",
					description: "Echo one exact value",
					parameters: schema,
					command: "node",
					args: ["{{__args_json}}"],
				},
				code: "process.stdout.write(JSON.parse(process.argv[2]).value)",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		};
		const chat = vi.fn().mockResolvedValue(response);
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		// The marker alone would force an MCP server (two public operations).
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts:\n${JSON.stringify([
						{ name: "marker_write", input_schema: { type: "object", properties: {} } },
						{ name: "marker_read", input_schema: { type: "object", properties: {} } },
					])}`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Provide structured_tool.",
			requiredContracts: [{ name: "structured_tool", inputSchema: schema }],
			recentEvents: events,
		});

		expect(result?.manifest.kind).toBe("tool");
		expect(result?.manifest.name).toBe("structured_tool");
		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("Required capability kind: tool");
		expect(prompt).not.toContain("Required capability kind: mcp");
	});

	it("derives an MCP boundary from multiple structured contracts without a marker", async () => {
		const chat = vi.fn().mockResolvedValue({
			content: JSON.stringify({
				manifest: {
					kind: "mcp",
					name: "journey-service",
					description: "Two stateful journey operations",
					command: "node",
					args: [],
				},
				code: "process.stdin.resume()",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});

		const result = await synthesizer.synthesize({
			description: "Provide two stateful journey operations.",
			proposedKind: "tool",
			requiredContracts: [
				{ name: "journey_step", inputSchema: { type: "object", properties: {} } },
				{ name: "journey_summary", inputSchema: { type: "object", properties: {} } },
			],
		});

		expect(result?.manifest.kind).toBe("mcp");
		const prompt = chat.mock.calls[0]?.[0].messages[0].content as string;
		expect(prompt).toContain("Required capability kind: mcp");
		expect(prompt).toContain("Agent architecture hint: tool");
		expect(chat).toHaveBeenCalledOnce();
	});

	it("falls back to the free-text marker when structured contracts are an empty array", async () => {
		const chat = vi.fn().mockResolvedValue({
			content: JSON.stringify({
				manifest: {
					kind: "mcp",
					name: "journey-service",
					description: "Two stateful journey operations",
					command: "node",
					args: [],
				},
				code: "process.stdin.resume()",
			}),
			toolCalls: [],
			finishReason: "stop",
			usage: { promptTokens: 1, completionTokens: 1 },
		});
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			llm: { chat } as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts:\n${JSON.stringify([
						{ name: "journey_step", input_schema: { type: "object", properties: {} } },
						{ name: "journey_summary", input_schema: { type: "object", properties: {} } },
					])}`,
				},
			},
		] as SessionEvent[];

		const result = await synthesizer.synthesize({
			description: "Provide two stateful journey operations.",
			requiredContracts: [],
			recentEvents: events,
		});

		expect(result?.manifest.kind).toBe("mcp");
		expect(chat.mock.calls[0]?.[0].messages[0].content).toContain("Required capability kind: mcp");
	});

	it("aborts a provider request when the synthesis deadline expires", async () => {
		let providerSignal: AbortSignal | undefined;
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			timeoutMs: 5,
			llm: {
				chat: ({ signal }: { signal?: AbortSignal }) => {
					providerSignal = signal;
					return new Promise(() => {});
				},
			} as never,
		});

		await expect(synthesizer.synthesize({ description: "Create a reusable local capability." })).rejects.toThrow(
			"Capability synthesis timed out",
		);
		expect(providerSignal?.aborted).toBe(true);
	});

	it("uses a separately bounded deadline for a multi-operation MCP synthesis", async () => {
		let providerSignal: AbortSignal | undefined;
		const synthesizer = new CapabilitySynthesizer({
			cwd: "C:\\fixture",
			autoToolsDir: "C:\\fixture\\tools",
			autoMcpDir: "C:\\fixture\\mcp",
			timeoutMs: 1_000,
			mcpTimeoutMs: 5,
			llm: {
				chat: ({ signal }: { signal?: AbortSignal }) => {
					providerSignal = signal;
					return new Promise(() => {});
				},
			} as never,
		});
		const events = [
			{
				type: "user.prompt",
				data: {
					content: `Required public tool contracts:\n${JSON.stringify([
						{ name: "session_write", input_schema: { type: "object", properties: {} } },
						{ name: "session_read", input_schema: { type: "object", properties: {} } },
					])}`,
				},
			},
		] as SessionEvent[];

		await expect(
			synthesizer.synthesize({
				description: "Create a coherent stateful service.",
				proposedKind: "mcp",
				recentEvents: events,
			}),
		).rejects.toThrow("Capability synthesis timed out");
		expect(synthesizer.timeoutMs).toBe(1_000);
		expect(synthesizer.mcpTimeoutMs).toBe(5);
		expect(providerSignal?.aborted).toBe(true);
	});
});
