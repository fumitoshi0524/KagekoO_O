export interface SystemPromptInput {
	readonly workspace: string;
	readonly tools: readonly string[];
	readonly instructions?: string;
}

/**
 * Shared runtime guidance for selecting and recovering from function calls.
 * Keep this independent of any benchmark task: it describes observable-state
 * planning and the boundary between using an existing function and learning a
 * genuinely missing one.
 */
export function buildCapabilityUseInstructions(tools: readonly string[]): readonly string[] {
	const instructions = [
		"Translate each requested action into the observable state it must produce before selecting tools. User wording does not imply a one-to-one tool name: use any available operation whose schema can create that state, and reuse an operation when distinct artifacts require it.",
		"Execute prerequisites before dependent calls. Preserve identifiers, paths, and URLs returned by successful tools and pass those exact values forward; never guess a replacement.",
		"After a tool error, inspect the error and unmet prerequisite, then change the arguments or approach. Never repeat an identical failed call.",
	];
	if (tools.some((tool) => tool.startsWith("skill_")))
		instructions.push(
			"Treat skill_* tools as learned procedural memory. If a skill description matches the request, the first function call must invoke the single best-matching skill before task operations, then apply its returned instructions with the task's concrete values. Invoking the skill is how you consult it; silently following a remembered pattern does not load its instructions. You decide whether a match exists, and must not invoke unrelated or redundant skills.",
		);
	if (tools.includes("need_capability"))
		instructions.push(
			"Use need_capability only after inspecting every relevant available tool schema and confirming that none can perform the unmet state transition. A missing exact verb, one failed mapping, or an unmet prerequisite that an existing tool can create is not a capability gap. Include concrete future-task evidence and the alternatives checked. A remote service that was merely discovered, or a one-off script, does not make the reusable capability available. The .kageko/tools/auto, .kageko/mcp/auto, and .kageko/skills/auto directories are owned by the learner's pending, validation, and approval lifecycle: never create or edit entries there with file or shell tools, even by copying an existing generated capability.",
		);
	return instructions;
}

export function buildSystemPrompt(input: SystemPromptInput): string {
	const tools = input.tools.length ? `\nAvailable tools: ${input.tools.join(", ")}` : "";
	return `Workspace: ${input.workspace}${tools}${input.instructions ? `\n${input.instructions}` : ""}`;
}
