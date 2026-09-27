import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { describe, expect, it } from "vitest";
import { AUTO_TOOL_ARGUMENTS_PLACEHOLDER, loadAutoTools } from "./auto-loader.js";

describe("auto tool argument substitution", () => {
	it("passes an empty argument for an omitted optional schema field", async () => {
		const root = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-auto-tool-"));
		try {
			const capabilityDir = path.join(root, "optional-args");
			await fs.mkdir(capabilityDir, { recursive: true });
			await fs.writeFile(
				path.join(capabilityDir, "manifest.json"),
				JSON.stringify({
					name: "optional_args",
					description: "Exercise optional structured arguments.",
					command: "node",
					args: ["optional-args/tool.cjs", "{{requiredValue}}", "{{optionalValue}}"],
					parameters: {
						type: "object",
						properties: { requiredValue: { type: "string" }, optionalValue: { type: "object" } },
						required: ["requiredValue"],
					},
				}),
				"utf8",
			);
			await fs.writeFile(
				path.join(capabilityDir, "tool.cjs"),
				"process.stdout.write(JSON.stringify(process.argv.slice(2)));",
				"utf8",
			);

			const [tool] = await loadAutoTools(root, (environment) => environment as Record<string, string>);
			const result = await tool!.execute!({ requiredValue: "kept" }, { session: { cwd: root } } as never);

			expect(result.isError).not.toBe(true);
			expect(JSON.parse(String(result.output))).toEqual(["kept", ""]);
		} finally {
			await fs.rm(root, { recursive: true, force: true });
		}
	});

	it("passes the complete function-call arguments as one JSON envelope", async () => {
		const root = await fs.mkdtemp(path.join(os.tmpdir(), "kageko-auto-tool-envelope-"));
		try {
			const capabilityDir = path.join(root, "json-envelope");
			await fs.mkdir(capabilityDir, { recursive: true });
			await fs.writeFile(
				path.join(capabilityDir, "manifest.json"),
				JSON.stringify({
					name: "json_envelope",
					description: "Receive one complete function argument object.",
					command: "node",
					args: ["json-envelope/tool.cjs", AUTO_TOOL_ARGUMENTS_PLACEHOLDER],
					parameters: {
						type: "object",
						properties: { requiredValue: { type: "object" }, optionalValue: { type: "boolean" } },
						required: ["requiredValue"],
					},
				}),
				"utf8",
			);
			await fs.writeFile(path.join(capabilityDir, "tool.cjs"), "process.stdout.write(process.argv[2]);", "utf8");

			const [tool] = await loadAutoTools(root, (environment) => environment as Record<string, string>);
			const args = { requiredValue: { nested: [1, true, null] } };
			const result = await tool!.execute!(args, { session: { cwd: root } } as never);

			expect(result.isError).not.toBe(true);
			expect(JSON.parse(String(result.output))).toEqual(args);
		} finally {
			await fs.rm(root, { recursive: true, force: true });
		}
	});
});
