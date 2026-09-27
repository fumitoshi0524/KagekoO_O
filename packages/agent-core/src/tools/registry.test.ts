import { describe, expect, it } from "vitest";
import { noAccess } from "./accesses.js";
import { ToolRegistry } from "./registry.js";

describe("ToolRegistry JSON Schema validation", () => {
	it("preserves the default additionalProperties semantics of nested objects", () => {
		const registry = new ToolRegistry();
		registry.register(
			{
				name: "nested_payload",
				description: "Accept an open configuration object.",
				parameters: {
					type: "object",
					properties: { parameters: { type: "object" } },
					required: ["parameters"],
				},
				execute: () => ({ output: "ok" }),
			},
			{ origin: "builtin", accesses: noAccess() },
		);

		expect(() =>
			registry.validateArgs("nested_payload", {
				parameters: { httpMethod: "POST", path: "sum", nested: { arbitrary: true } },
			}),
		).not.toThrow();
	});

	it("still enforces additionalProperties false when the contract declares it", () => {
		const registry = new ToolRegistry();
		registry.register(
			{
				name: "strict_payload",
				description: "Reject undeclared configuration fields.",
				parameters: {
					type: "object",
					properties: {
						parameters: {
							type: "object",
							properties: { known: { type: "string" } },
							additionalProperties: false,
						},
					},
					required: ["parameters"],
				},
				execute: () => ({ output: "ok" }),
			},
			{ origin: "builtin", accesses: noAccess() },
		);

		expect(() => registry.validateArgs("strict_payload", { parameters: { unknown: true } })).toThrow(
			"must NOT have additional properties",
		);
	});
});
