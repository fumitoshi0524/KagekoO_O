import type { Tool, ToolContext } from "../types.js";

interface AskUserArgs {
	question: string;
	options?: string[];
	timeout?: number;
}

export const askUserTool: Tool<AskUserArgs> = {
	name: "ask_user",
	description: "Ask the user a question and wait for an answer. Use when information is missing or ambiguous.",
	parameters: {
		type: "object",
		properties: {
			question: { type: "string", description: "Question to ask the user" },
			options: {
				type: "array",
				items: { type: "string" },
				description: "Optional list of choices",
			},
			timeout: { type: "number", description: "Timeout in milliseconds (default 300000)" },
		},
		required: ["question"],
	},
	async execute({ question, options }: AskUserArgs, { session }: ToolContext) {
		if (!session?.interaction)
			return { output: "No application interaction service is configured for this session.", isError: true };
		try {
			const answer = await session.interaction.ask(question, options);
			return { output: Array.isArray(answer) ? answer.join(", ") : answer };
		} catch (error) {
			return { output: error instanceof Error ? error.message : String(error), isError: true };
		}
	},
};
