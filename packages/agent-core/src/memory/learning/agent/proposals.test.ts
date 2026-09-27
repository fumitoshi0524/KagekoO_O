import { describe, expect, it } from "vitest";
import { validateCapabilityProposal, validateSkillProposal } from "./proposals.js";

const VALID_INSTRUCTIONS =
	"Inspect the advertised tool schemas before choosing operations, preserve every returned identifier, " +
	"execute dependencies in order, and verify final postconditions with authoritative read-back.";

const VALID_DESCRIPTION = "Reuse a verified stateful workflow safely across tasks.";

describe("validateSkillProposal", () => {
	it("accepts a well-formed novel proposal and returns the sanitized skill", () => {
		const verdict = validateSkillProposal(
			{ name: "My Cool Skill!!", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			[],
		);
		expect(verdict.ok).toBe(true);
		if (verdict.ok) {
			expect(verdict.skill).toEqual({
				name: "my-cool-skill",
				description: VALID_DESCRIPTION,
				instructions: VALID_INSTRUCTIONS,
			});
		}
	});

	it("rejects placeholder content", () => {
		const verdict = validateSkillProposal(
			{ name: "placeholder-skill", description: VALID_DESCRIPTION, instructions: `${VALID_INSTRUCTIONS} TODO fill in.` },
			[],
		);
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("placeholder");
	});

	it("rejects a too-short description", () => {
		const verdict = validateSkillProposal({ name: "short-desc", description: "Too short.", instructions: VALID_INSTRUCTIONS }, []);
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("description is too short");
	});

	it("rejects too-short instructions", () => {
		const verdict = validateSkillProposal(
			{ name: "short-instructions", description: VALID_DESCRIPTION, instructions: "Do the thing." },
			[],
		);
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("instructions are too short");
	});

	it("rejects an invalid or overlong name", () => {
		expect(validateSkillProposal({ name: "!!!", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS }, []).ok).toBe(
			false,
		);
		expect(
			validateSkillProposal({ name: "a".repeat(65), description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS }, []).ok,
		).toBe(false);
	});

	it("rejects an exact name collision with an existing skill", () => {
		const verdict = validateSkillProposal(
			{ name: "Existing-Workflow", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			[{ name: "existing-workflow", description: "Unrelated active instructions." }],
		);
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("already covers");
	});

	it("rejects a paraphrase above the Jaccard threshold", () => {
		const verdict = validateSkillProposal(
			{ name: "new-name", description: VALID_DESCRIPTION, instructions: VALID_INSTRUCTIONS },
			[{ name: "other-name", description: VALID_INSTRUCTIONS }],
		);
		expect(verdict.ok).toBe(false);
	});

	it("applies the relaxed containment rule only to auto-sourced skills", () => {
		const common = "inspect schemas preserve identifiers dependency order recover errors verify final state";
		const existingBody = `${common} create artifact export upload email calendar attendee draft recipient subject body url handle provider`;
		const proposalInstructions = `${common} transform asset publish distribute message collaboration candidate materialize project link status job retry prerequisite authoritative`;
		const base = { name: "artifact-publishing", description: VALID_DESCRIPTION, instructions: proposalInstructions };

		const againstAuto = validateSkillProposal(base, [{ name: "prepare-artifacts", content: existingBody, source: "auto" }]);
		expect(againstAuto.ok).toBe(false);

		const againstProject = validateSkillProposal(base, [{ name: "prepare-artifacts", content: existingBody, source: "project" }]);
		expect(againstProject.ok).toBe(true);
	});
});

const TOOL_SCHEMA = { type: "object", properties: { file: { type: "string" } }, required: ["file"] };

function validToolCandidate() {
	return {
		kind: "tool" as const,
		name: "Read File Tool",
		description: "Read a UTF-8 file from the workspace.",
		parameters: TOOL_SCHEMA,
		command: "node",
		args: ["{{__args_json}}"],
		code: "const {file}=JSON.parse(process.argv[2]); process.stdout.write(String(file));",
	};
}

describe("validateCapabilityProposal", () => {
	it("accepts a valid inline tool candidate and shapes it like a CapabilityOutput", () => {
		const verdict = validateCapabilityProposal(validToolCandidate());
		expect(verdict.ok).toBe(true);
		if (verdict.ok) {
			expect(verdict.output.kind).toBe("tool");
			expect(verdict.output.name).toBe("read-file-tool");
			expect(verdict.output.code).toContain("process.argv[2]");
			expect(verdict.output.parameters).toEqual(TOOL_SCHEMA);
		}
	});

	it("rejects a tool candidate whose args are not the JSON envelope placeholder", () => {
		const verdict = validateCapabilityProposal({ ...validToolCandidate(), args: ["--file", "x"] });
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("{{__args_json}}");
	});

	it("rejects a schema mismatch against required contracts", () => {
		const verdict = validateCapabilityProposal({
			...validToolCandidate(),
			name: "exact_tool",
			requiredContracts: [{ name: "exact_tool", inputSchema: { type: "object", properties: { other: { type: "number" } } } }],
		});
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("exact public schema");
	});

	it("accepts a candidate matching the required contract exactly", () => {
		const verdict = validateCapabilityProposal({
			...validToolCandidate(),
			name: "exact_tool",
			parameters: TOOL_SCHEMA,
			requiredContracts: [{ name: "exact_tool", inputSchema: TOOL_SCHEMA }],
		});
		expect(verdict.ok).toBe(true);
	});

	it("forces the kind from the required contracts topology", () => {
		const contracts = [
			{ name: "op_one", inputSchema: { type: "object" } },
			{ name: "op_two", inputSchema: { type: "object" } },
		];
		// Two public operations require an MCP server; a tool candidate conflicts.
		const asTool = validateCapabilityProposal({ ...validToolCandidate(), requiredContracts: contracts });
		expect(asTool.ok).toBe(false);
		if (!asTool.ok) expect(asTool.reason).toContain("does not match required kind mcp");

		const asMcp = validateCapabilityProposal({
			kind: "mcp",
			name: "shared-service",
			description: "A coherent two-operation stateful service.",
			command: "node",
			args: [],
			code: "process.stdin.resume();",
			requiredContracts: contracts,
		});
		expect(asMcp.ok).toBe(true);
		if (asMcp.ok) expect(asMcp.output.kind).toBe("mcp");
	});

	it("rejects syntactically invalid implementation code", () => {
		const verdict = validateCapabilityProposal({ ...validToolCandidate(), code: "const = broken (" });
		expect(verdict.ok).toBe(false);
		if (!verdict.ok) expect(verdict.reason).toContain("invalid JavaScript syntax");
	});
});
