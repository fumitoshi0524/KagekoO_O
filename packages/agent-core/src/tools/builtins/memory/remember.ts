import { createUserFeedbackEvent } from "../../../memory/learning/event.js";
import type { Tool, ToolContext } from "../../types.js";

interface RememberArgs {
	fact: string;
	scope?: "user" | "project";
}

export const rememberTool: Tool<RememberArgs> = {
	name: "remember",
	description: "Remember a user preference or project convention for future sessions.",
	parameters: {
		type: "object",
		properties: {
			fact: { type: "string", description: "The fact or preference to remember" },
			scope: {
				type: "string",
				enum: ["user", "project"],
				description: "Whether this fact applies to the user globally or just the current project (default project)",
			},
		},
		required: ["fact"],
	},
	async execute({ fact, scope = "project" }: RememberArgs, { session }: ToolContext) {
		if (!session?.memory?.profile) {
			return { output: "Memory engine is not available.", isError: true };
		}
		if (!fact?.trim()) {
			return { output: "fact must be a non-empty string.", isError: true };
		}
		const entry = await session.memory.remember(scope, fact.trim());
		session?.learningBus?.enqueue(
			createUserFeedbackEvent("remember", { scope, fact: fact.trim() }, { toolName: "remember" }),
		);
		return { output: `Remembered (${entry.scope}): ${entry.fact}` };
	},
};
