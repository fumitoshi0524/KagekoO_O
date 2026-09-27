import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
	cli,
	createProductEnvironment,
	json,
	runProduct,
	startLearningModel,
	type ProductEnvironment,
} from "./product-fixture.js";

const products: ProductEnvironment[] = [];

afterEach(async () => {
	await Promise.all(products.splice(0).map((product) => product.cleanup()));
});

describe("production learning mission", () => {
	it("turns two evidenced gaps into one approved tool and one approved MCP, then generates a reusable skill across fresh processes", async () => {
		await access(cli, constants.R_OK | constants.X_OK);
		const model = await startLearningModel();
		try {
			const product = await createProductEnvironment({
				KAGEKO_MODEL_PROVIDER: "custom",
				KAGEKO_MODEL_NAME: "acceptance-model",
				KAGEKO_API_KEY: "acceptance-key",
				KAGEKO_BASE_URL: model.baseUrl,
			});
			products.push(product);
			const session = await runProduct(product, ["session", "create", "--json"]);
			expect(session.code, session.stderr).toBe(0);
			const sessionId = (json(session) as { sessionId: string }).sessionId;
			const trusted = await runProduct(product, ["trust", "grant"]);
			expect(trusted.code, trusted.stderr).toBe(0);

			for (const prompt of [
				"Please identify a reusable capability for concise release notes.",
				"Please identify a reusable capability for the remote test feed.",
			]) {
				const result = await runProduct(product, [
					"--session",
					sessionId,
					"--prompt",
					prompt,
					"--permission",
					"unrestricted",
					"--interaction",
					"unattended",
				]);
				expect(result.code, result.stderr).toBe(0);
				expect(result.stdout).toContain("need_capability");
			}

			const pending = await runProduct(product, ["learning", "pending", "--session", sessionId, "--json"]);
			expect(pending.code, pending.stderr).toBe(0);
			const entries = json(pending) as Array<{
				event: { id: string };
				output?: { kind?: string; name?: string; description?: string; code?: string };
			}>;
			const tool = entries.find((entry) => entry.output?.kind === "tool");
			const mcp = entries.find((entry) => entry.output?.kind === "mcp");
			expect(tool?.output, JSON.stringify(entries)).toMatchObject({
				name: "release-note",
				description: expect.stringContaining("release"),
			});
			expect(mcp?.output, JSON.stringify(entries)).toMatchObject({
				name: "release-feed",
				description: expect.stringContaining("release"),
			});
			expect(entries).toHaveLength(2);
			expect(tool).toBeDefined();
			const approvedTool = await runProduct(product, ["learning", "approve", tool!.event.id, "--session", sessionId]);
			expect(approvedTool.code, approvedTool.stderr).toBe(0);
			// The first approval creates executable project content, so the user
			// explicitly trusts that reviewed artifact before approving another one.
			const trustedArtifacts = await runProduct(product, ["trust", "grant"]);
			expect(trustedArtifacts.code, trustedArtifacts.stderr).toBe(0);
			expect(mcp).toBeDefined();
			const approvedMcp = await runProduct(product, ["learning", "approve", mcp!.event.id, "--session", sessionId]);
			expect(approvedMcp.code, approvedMcp.stderr).toBe(0);
			const trustedMcp = await runProduct(product, ["trust", "grant"]);
			expect(trustedMcp.code, trustedMcp.stderr).toBe(0);

			const toolManifest = path.join(product.workspace, ".kageko", "tools", "auto", "release-note", "manifest.json");
			const mcpManifest = path.join(product.workspace, ".kageko", "mcp", "auto", "release-feed", "manifest.json");
			const generatedTool = JSON.parse(await readFile(toolManifest, "utf8")) as {
				command: string;
				args: string[];
				parameters: { required: string[] };
			};
			const generatedMcp = JSON.parse(await readFile(mcpManifest, "utf8")) as { command: string; args: string[] };
			expect(generatedTool).toMatchObject({ command: "node", parameters: { required: ["subject"] } });
			// On-disk layout: the generated script path plus the JSON arguments placeholder.
			expect(generatedTool.args).toHaveLength(2);
			expect(generatedTool.args[1]).toBe("{{__args_json}}");
			expect(generatedMcp).toMatchObject({ command: "node" });
			expect(generatedMcp.args).toHaveLength(1);

			const capabilities = await runProduct(product, [
				"capability",
				"list",
				"--session",
				sessionId,
				"--kind",
				"tool",
				"--json",
			]);
			expect(capabilities.code, capabilities.stderr).toBe(0);
			expect(json(capabilities)).toEqual(
				expect.arrayContaining([expect.objectContaining({ name: "auto__release_note" })]),
			);
			const mcpCapabilities = await runProduct(product, ["mcp", "list", "--session", sessionId, "--json"]);
			expect(mcpCapabilities.code, mcpCapabilities.stderr).toBe(0);
			expect(json(mcpCapabilities)).toEqual(expect.arrayContaining([expect.objectContaining({ id: "release-feed" })]));

			const generatedSkill = await runProduct(product, ["memory", "generate-skill", "--session", sessionId]);
			expect(generatedSkill.code, generatedSkill.stderr).toBe(0);
			expect(generatedSkill.stdout).toContain("release-validation");
			const skillPath = path.join(product.workspace, ".kageko", "skills", "auto", "release-validation", "SKILL.md");
			const skill = await readFile(skillPath, "utf8");
			expect(skill).toMatch(/^---\nname: release-validation\ndescription: .+\n/);
			expect(skill).toContain("Run the product acceptance suite.");
			const trustedSkill = await runProduct(product, ["trust", "grant"]);
			expect(trustedSkill.code, trustedSkill.stderr).toBe(0);

			const reloaded = await runProduct(product, ["session", "create", "--json"]);
			expect(reloaded.code, reloaded.stderr).toBe(0);
			const freshSessionId = (json(reloaded) as { sessionId: string }).sessionId;
			const freshSkills = await runProduct(product, ["skill", "list", "--session", freshSessionId, "--json"]);
			expect(freshSkills.code, freshSkills.stderr).toBe(0);
			expect(json(freshSkills)).toEqual(
				expect.arrayContaining([expect.objectContaining({ id: "release-validation" })]),
			);
			const freshMcp = await runProduct(product, ["mcp", "list", "--session", freshSessionId, "--json"]);
			expect(freshMcp.code, freshMcp.stderr).toBe(0);
			expect(json(freshMcp)).toEqual(expect.arrayContaining([expect.objectContaining({ id: "release-feed" })]));
		} finally {
			await model.close();
		}
	}, 180_000);
});
