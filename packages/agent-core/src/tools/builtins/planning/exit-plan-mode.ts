import type { Tool, ToolContext } from "../../types.js";

interface PlanOption {
	label: string;
	description?: string;
}

export const exitPlanModeTool: Tool<{ options?: PlanOption[] }> = {
	name: "exit_plan_mode",
	description: "Exit plan mode and return the finalized plan content. Optionally provide 1-3 follow-up option labels.",
	parameters: {
		type: "object",
		properties: {
			options: {
				type: "array",
				items: {
					type: "object",
					properties: {
						label: { type: "string", description: "Short option label" },
						description: { type: "string", description: "Optional option description" },
					},
					required: ["label"],
				},
				minItems: 1,
				maxItems: 3,
				description: "Optional follow-up options (1-3 items)",
			},
		},
	},
	async execute({ options }: { options?: PlanOption[] }, { session }: ToolContext) {
		if (!session?.planMode) {
			return { output: "Session does not support plan mode", isError: true };
		}
		if (options && (options.length < 1 || options.length > 3)) {
			return { output: "options must contain 1-3 items", isError: true };
		}
		const planContent = await session.planMode.exit();
		let output = "Exited plan mode. Plan content:\n" + (planContent || "(empty)");
		if (options?.length) {
			output +=
				"\n\nFollow-up options:\n" +
				options.map((o, i) => `${i + 1}. ${o.label}${o.description ? ` - ${o.description}` : ""}`).join("\n");
		}
		return { output };
	},
};
